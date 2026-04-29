"""Playoff bracket builder.

Walks `game_logs` rows tagged with ``season_type="Playoffs"`` and folds them
into a normalized ``playoff_series`` table (one row per matchup) plus
back-references on the originating game logs (``series_id``,
``series_game_num``, ``playoff_seed``).

Idempotent: every public entry point upserts and is safe to re-run after
each game.

EA1 (Sprint 73a) owns the canonical ORM declaration of ``PlayoffSeries`` and
the ``game_logs.series_id``/``series_game_num``/``playoff_seed``/
``season_type`` columns via Alembic migration ``0012_playoffs_data_layer``.
While EA1's branch is in flight, this module falls back to a local mirror of
the same schema so the bracket service and its unit tests stay decoupled
from the migration ordering. When EA1's model is present, we import that
canonical class instead.
"""
from __future__ import annotations

import logging
import math
from datetime import date
from typing import Dict, List, Optional, Tuple

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from db.database import Base
from db.models import GameLog, Team, TeamSeasonStat

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PlayoffSeries ORM — prefer EA1's canonical model when available; otherwise
# declare a local mirror so this service remains self-contained.
# ---------------------------------------------------------------------------
try:
    from db.models import PlayoffSeries  # type: ignore  # noqa: F401
except ImportError:  # pragma: no cover - exercised only pre-EA1 merge
    class PlayoffSeries(Base):  # type: ignore[no-redef]
        """Fallback mirror of EA1's `playoff_series` table.

        Schema mirrors the contract documented in the Sprint 73a EA1 spec.
        When EA1's canonical class lands, this fallback is bypassed.
        """

        __tablename__ = "playoff_series"
        __table_args__ = (
            UniqueConstraint(
                "season",
                "round",
                "top_seed_team_id",
                "bottom_seed_team_id",
                name="uq_playoff_series_matchup",
            ),
            Index("ix_playoff_series_season", "season"),
        )

        id = Column(Integer, primary_key=True, autoincrement=True)
        season = Column(String(10), nullable=False)
        round = Column(Integer, nullable=False)
        series_id = Column(String(80), nullable=False, unique=True)
        top_seed_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
        bottom_seed_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
        top_seed = Column(Integer, default=99)
        bottom_seed = Column(Integer, default=99)
        top_wins = Column(Integer, default=0)
        bottom_wins = Column(Integer, default=0)
        status = Column(String(20), default="active")
        winner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
        created_at = Column(DateTime, server_default=func.now())
        updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Inferred round windows by ISO month-day. NBA postseason runs in a fairly
# stable cadence: round 1 mid-April, round 2 early-May, conf finals
# late-May, finals in June. Used only when seeds are unavailable.
_ROUND_WINDOWS = (
    # (round, (start_month, start_day))
    (1, (4, 14)),
    (2, (5, 1)),
    (3, (5, 18)),
    (4, (6, 1)),
)


def _infer_round_from_first_game(first_game_date: Optional[date]) -> int:
    """Return a 1..4 round number based on the earliest game date."""
    if first_game_date is None:
        return 1
    inferred = 1
    for round_number, (month, day) in _ROUND_WINDOWS:
        if (first_game_date.month, first_game_date.day) >= (month, day):
            inferred = round_number
    return inferred


def _seed_lookup(team_id: int, season: str, db: Session) -> Optional[int]:
    """Best-effort seed inference for a team in a given season.

    Looks for an explicit playoff-rank field on `team_season_stats` first;
    falls back to ranking by regular-season ``w_pct`` within the league. If
    nothing is available, returns ``None`` so the caller can fall through to
    the seed=99 placeholder.
    """
    row = (
        db.query(TeamSeasonStat)
        .filter(
            TeamSeasonStat.team_id == team_id,
            TeamSeasonStat.season == season,
            TeamSeasonStat.is_playoff == False,  # noqa: E712
        )
        .first()
    )
    if row is None:
        return None

    explicit_seed = getattr(row, "playoff_rank", None)
    if explicit_seed is not None:
        try:
            seed_value = int(explicit_seed)
            if seed_value > 0:
                return seed_value
        except (TypeError, ValueError):
            pass

    # Fallback: derive seed from regular-season W% rank within the league.
    # The first 8 teams by W% map to seeds 1..8 (rough — pre-play-in this
    # is fine; play-in winners may be misranked but get reseeded once
    # series start, which our caller can override with explicit ranks
    # when available).
    all_team_rows = (
        db.query(TeamSeasonStat)
        .filter(
            TeamSeasonStat.season == season,
            TeamSeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    if not all_team_rows:
        return None
    sorted_rows = sorted(
        all_team_rows,
        key=lambda r: (-(r.w_pct or 0.0), r.team_id),
    )
    for rank_idx, candidate in enumerate(sorted_rows, start=1):
        if candidate.team_id == team_id:
            return rank_idx
    return None


def _matchup_key(home_id: Optional[int], away_id: Optional[int]) -> Optional[Tuple[int, int]]:
    if home_id is None or away_id is None:
        return None
    a, b = sorted((int(home_id), int(away_id)))
    return (a, b)


def _team_abbr(db: Session, team_id: int, cache: Dict[int, str]) -> str:
    if team_id in cache:
        return cache[team_id]
    team = db.query(Team).filter(Team.id == team_id).first()
    abbr = team.abbreviation if team and team.abbreviation else f"T{team_id}"
    cache[team_id] = abbr
    return abbr


def _team_conference(db: Session, team_id: int, cache: Dict[int, str]) -> str:
    if team_id in cache:
        return cache[team_id]
    team = db.query(Team).filter(Team.id == team_id).first()
    conf = (getattr(team, "conference", "") or "").strip().upper() if team else ""
    short = conf[:1] if conf else "X"
    cache[team_id] = short
    return short


def _winner_for_game(game: GameLog) -> Optional[int]:
    home_score = game.home_score
    away_score = game.away_score
    if home_score is None or away_score is None:
        return None
    if home_score > away_score:
        return int(game.home_team_id) if game.home_team_id is not None else None
    if away_score > home_score:
        return int(game.away_team_id) if game.away_team_id is not None else None
    return None


def _game_season_type(game: GameLog) -> str:
    """Read season_type defensively — column may not yet be on the GameLog."""
    return getattr(game, "season_type", "Regular Season") or "Regular Season"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_or_refresh_bracket(db: Session, season: str) -> int:
    """Rebuild ``playoff_series`` rows for ``season`` from `game_logs` data.

    Returns the count of distinct series rows that were inserted or updated.
    Safe to re-run after every playoff game.
    """
    games_query = db.query(GameLog).filter(GameLog.season == season)
    if hasattr(GameLog, "season_type"):
        games_query = games_query.filter(GameLog.season_type == "Playoffs")

    all_games: List[GameLog] = games_query.all()
    if hasattr(GameLog, "season_type"):
        playoff_games = all_games
    else:
        # Pre-EA1: GameLog has no season_type column yet — assume the caller
        # only has playoff rows in scope, and trust everything we got back.
        playoff_games = all_games

    if not playoff_games:
        logger.info("build_or_refresh_bracket: no playoff games found for %s", season)
        return 0

    matchups: Dict[Tuple[int, int], List[GameLog]] = {}
    for game in playoff_games:
        key = _matchup_key(game.home_team_id, game.away_team_id)
        if key is None:
            continue
        matchups.setdefault(key, []).append(game)

    abbr_cache: Dict[int, str] = {}
    conf_cache: Dict[int, str] = {}
    refreshed = 0

    for (team_a, team_b), games in matchups.items():
        games_sorted = sorted(
            games,
            key=lambda g: (g.game_date or date.max, g.game_id),
        )

        seed_a = _seed_lookup(team_a, season, db)
        seed_b = _seed_lookup(team_b, season, db)
        seed_a_value = seed_a if seed_a is not None else 99
        seed_b_value = seed_b if seed_b is not None else 99

        if seed_a_value <= seed_b_value:
            top_id, bottom_id = team_a, team_b
            top_seed_value, bottom_seed_value = seed_a_value, seed_b_value
        else:
            top_id, bottom_id = team_b, team_a
            top_seed_value, bottom_seed_value = seed_b_value, seed_a_value

        if seed_a is None or seed_b is None:
            logger.warning(
                "Seed lookup incomplete for series in %s: team_a=%s seed=%s, team_b=%s seed=%s — using placeholder seed=99",
                season,
                team_a,
                seed_a,
                team_b,
                seed_b,
            )

        top_wins = 0
        bottom_wins = 0
        for game in games_sorted:
            winner_id = _winner_for_game(game)
            if winner_id == top_id:
                top_wins += 1
            elif winner_id == bottom_id:
                bottom_wins += 1

        if top_wins >= 4 or bottom_wins >= 4:
            status = "closed"
            winner_team_id = top_id if top_wins >= 4 else bottom_id
        else:
            status = "active"
            winner_team_id = None

        round_number = _infer_round_from_first_game(games_sorted[0].game_date)

        conf_token = _team_conference(db, top_id, conf_cache)
        top_abbr = _team_abbr(db, top_id, abbr_cache)
        bottom_abbr = _team_abbr(db, bottom_id, abbr_cache)
        series_id_value = "{0}-{1}-R{2}-{3}-{4}".format(
            season, conf_token, round_number, top_abbr, bottom_abbr
        )

        existing = (
            db.query(PlayoffSeries)
            .filter(
                PlayoffSeries.season == season,
                PlayoffSeries.series_id == series_id_value,
            )
            .first()
        )
        if existing is None:
            existing = PlayoffSeries(
                season=season,
                round=round_number,
                series_id=series_id_value,
                top_seed_team_id=top_id,
                bottom_seed_team_id=bottom_id,
                top_seed=top_seed_value,
                bottom_seed=bottom_seed_value,
                top_wins=top_wins,
                bottom_wins=bottom_wins,
                status=status,
                winner_team_id=winner_team_id,
            )
            db.add(existing)
        else:
            existing.season = season
            existing.round = round_number
            existing.top_seed_team_id = top_id
            existing.bottom_seed_team_id = bottom_id
            existing.top_seed = top_seed_value
            existing.bottom_seed = bottom_seed_value
            existing.top_wins = top_wins
            existing.bottom_wins = bottom_wins
            existing.status = status
            existing.winner_team_id = winner_team_id

        refreshed += 1

        # Update each GameLog row with series back-references where the
        # columns exist (post-EA1 migration).
        for game_index, game in enumerate(games_sorted, start=1):
            if hasattr(game, "series_id"):
                setattr(game, "series_id", series_id_value)
            if hasattr(game, "series_game_num"):
                setattr(game, "series_game_num", game_index)
            if hasattr(game, "playoff_seed"):
                home_id = int(game.home_team_id) if game.home_team_id is not None else None
                if home_id == top_id:
                    setattr(game, "playoff_seed", top_seed_value)
                elif home_id == bottom_id:
                    setattr(game, "playoff_seed", bottom_seed_value)

    db.commit()
    logger.info(
        "build_or_refresh_bracket complete for %s: series_refreshed=%s games_seen=%s",
        season,
        refreshed,
        len(playoff_games),
    )
    return refreshed


# ---------------------------------------------------------------------------
# Sprint 77 — Headline storyline derived from team season-stat differentials.
# ---------------------------------------------------------------------------

# Per-stat presentation: (orm_field, leader_phrase, trailer_phrase, higher_is_better)
# - leader_phrase: "{Leader} chasing {leader_phrase}; ..."
# - trailer_phrase: "...; {Trailer} fighting {trailer_phrase} math"
# higher_is_better=True means the team with the larger value is the "leader".
_STORYLINE_STATS: Tuple[Tuple[str, str, str, bool], ...] = (
    ("pts_pg", "scoring volume", "elimination", True),
    ("off_rating", "offensive firepower", "stalled offense", True),
    ("def_rating", "defensive lockdown", "leaky defense", False),
    ("pace", "tempo control", "tempo reverse", True),
    ("ts_pct", "shotmaking edge", "efficiency drought", True),
)


def _league_team_stats(db: Session, season: str, is_playoff: bool) -> List[TeamSeasonStat]:
    return (
        db.query(TeamSeasonStat)
        .filter(
            TeamSeasonStat.season == season,
            TeamSeasonStat.is_playoff == is_playoff,
        )
        .all()
    )


def _stat_value(row: Optional[TeamSeasonStat], field: str) -> Optional[float]:
    if row is None:
        return None
    raw = getattr(row, field, None)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _league_z(values: List[float], target: float) -> Optional[float]:
    """Return the z-score of ``target`` against ``values`` (excluding NaN)."""
    cleaned = [v for v in values if v is not None and not math.isnan(v)]
    if len(cleaned) < 2:
        return None
    mean = sum(cleaned) / len(cleaned)
    variance = sum((v - mean) ** 2 for v in cleaned) / len(cleaned)
    if variance <= 0:
        return None
    std = math.sqrt(variance)
    if std == 0:
        return None
    return (target - mean) / std


def _team_season_stat_for(
    db: Session, team_id: int, season: str
) -> Optional[TeamSeasonStat]:
    """Prefer playoff row for the team, fall back to regular-season row."""
    if team_id is None:
        return None
    playoff_row = (
        db.query(TeamSeasonStat)
        .filter(
            TeamSeasonStat.team_id == team_id,
            TeamSeasonStat.season == season,
            TeamSeasonStat.is_playoff == True,  # noqa: E712
        )
        .first()
    )
    if playoff_row is not None:
        return playoff_row
    return (
        db.query(TeamSeasonStat)
        .filter(
            TeamSeasonStat.team_id == team_id,
            TeamSeasonStat.season == season,
            TeamSeasonStat.is_playoff == False,  # noqa: E712
        )
        .first()
    )


def _team_short_name(team: Optional[Team]) -> Optional[str]:
    if team is None:
        return None
    name = (getattr(team, "city", None) or getattr(team, "name", None) or "").strip()
    if name:
        return name
    abbr = getattr(team, "abbreviation", None)
    return abbr if abbr else None


def compute_game_storyline(
    db: Session,
    game: GameLog,
    home_team: Team,
    away_team: Team,
) -> Optional[str]:
    """One-line storyline for a playoff game, derived from the most lopsided
    season-stat differential between the two teams.

    Strategy:
        1. Pull TeamSeasonStat rows for both teams (current season, is_playoff=True
           if available, falling back to is_playoff=False).
        2. Compute z-score for each of [pts_pg, off_rating, def_rating, pace, ts_pct]
           across the league this season.
        3. Find the largest absolute z-score gap between the two teams.
        4. Return a one-line storyline:
           "{Leader} chasing {stat_name}; {Trailer} fighting {opposing_action} math"

    If neither team has enough data, return None (UI falls back to "Game N · {tipoff}").
    """
    season = getattr(game, "season", None)
    if not season or home_team is None or away_team is None:
        return None

    home_row = _team_season_stat_for(db, home_team.id, season)
    away_row = _team_season_stat_for(db, away_team.id, season)
    if home_row is None or away_row is None:
        return None

    # League sample is drawn from the same season-type bucket as the home
    # row. We z-score both teams against that frame to find the largest gap.
    league_rows = _league_team_stats(
        db, season, bool(getattr(home_row, "is_playoff", False))
    )

    best_gap: float = 0.0
    best_spec: Optional[Tuple[str, str, str, bool]] = None
    best_home_z: Optional[float] = None
    best_away_z: Optional[float] = None

    for spec in _STORYLINE_STATS:
        field, _, _, _ = spec
        home_value = _stat_value(home_row, field)
        away_value = _stat_value(away_row, field)
        if home_value is None or away_value is None:
            continue

        league_floats: List[float] = [
            v for v in (_stat_value(row, field) for row in league_rows) if v is not None
        ]
        home_z = _league_z(league_floats, home_value)
        away_z = _league_z(league_floats, away_value)
        if home_z is None or away_z is None:
            continue

        gap = abs(home_z - away_z)
        if gap > best_gap:
            best_gap = gap
            best_spec = spec
            best_home_z = home_z
            best_away_z = away_z

    if best_spec is None or best_home_z is None or best_away_z is None:
        return None

    _, leader_phrase, trailer_phrase, higher_is_better = best_spec
    home_leads = best_home_z > best_away_z if higher_is_better else best_home_z < best_away_z
    leader_team = home_team if home_leads else away_team
    trailer_team = away_team if home_leads else home_team

    leader_name = _team_short_name(leader_team)
    trailer_name = _team_short_name(trailer_team)
    if leader_name is None or trailer_name is None:
        return None

    return "{0} chasing {1}; {2} fighting {3} math".format(
        leader_name, leader_phrase, trailer_name, trailer_phrase
    )


# Public re-export so ``from services.playoff_bracket_service import PlayoffSeries``
# works even when the fallback class above is used.
__all__ = ["build_or_refresh_bracket", "compute_game_storyline", "PlayoffSeries"]
