"""Playoff API surface (Sprint 73).

Routes:

- ``GET /api/playoffs/bracket?season=2025-26`` — full bracket grouped by
  conference plus the finals, if it exists.
- ``GET /api/playoffs/series/{series_id}`` — a single series with all games
  in ``series_game_num`` order.
- ``GET /api/playoffs/today?date=YYYY-MM-DD`` — playoff games on a given date
  (defaults to "today" in US/Pacific). When the request is for today's date,
  upcoming/in-progress games are merged in from the live CDN scoreboard so
  the slate is populated even before the daily sync ingests them.
- ``GET /api/playoffs/series-simulation/{series_id}`` — Monte-Carlo projection.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Set

import pytz
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from data.nba_client import get_todays_scoreboard
from db.database import get_db
from db.models import GameLog, Team
from models.playoffs import (
    PlayoffBracketResponse,
    PlayoffLeadersResponse,
    PlayoffSeriesIntelligenceResponse,
    PlayoffSeriesGame,
    PlayoffSeriesGameWithMatchup,
    PlayoffSeriesPlayerLogsResponse,
    PlayoffSeriesResponse,
    PlayoffStoryRailResponse,
    PlayoffTodayResponse,
    SeriesSimulationResponse,
)
from services.playoff_bracket_service import compute_game_storyline
from services.playoff_leaders_service import compute_playoff_leaders
from services.playoff_series_intelligence_service import build_playoff_series_intelligence
from services.playoff_series_player_logs_service import build_series_player_logs
from services.playoff_simulator_service import simulate_series
from services.story_rail_service import compute_data_as_of, compute_story_rail

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Static EAST/WEST fallback used when `Team.conference` is empty.
# ---------------------------------------------------------------------------

_EAST_ABBRS = {
    "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DET", "IND", "MIA",
    "MIL", "NYK", "ORL", "PHI", "TOR", "WAS",
}
_WEST_ABBRS = {
    "DAL", "DEN", "GSW", "HOU", "LAC", "LAL", "MEM", "MIN", "NOP",
    "OKC", "PHX", "POR", "SAC", "SAS", "UTA",
}


# US Pacific via pytz (DST-aware). Stdlib `zoneinfo` isn't available on Python
# 3.8 without a third-party install, but pytz is already in the dep tree.
_PACIFIC_TZ = pytz.timezone("US/Pacific")


def _today_pacific() -> date:
    return datetime.now(tz=_PACIFIC_TZ).date()


def _conference_for_team(team: Optional[Team], abbr_fallback: Optional[str]) -> Optional[str]:
    if team is not None:
        conf = (team.conference or "").strip()
        if conf:
            normalized = conf.upper()
            if normalized.startswith("E"):
                return "East"
            if normalized.startswith("W"):
                return "West"
    abbr = (abbr_fallback or "").upper()
    if abbr in _EAST_ABBRS:
        return "East"
    if abbr in _WEST_ABBRS:
        return "West"
    return None


def _team_lookup(db: Session, team_ids: List[int]) -> Dict[int, Team]:
    if not team_ids:
        return {}
    rows = db.query(Team).filter(Team.id.in_(team_ids)).all()
    return {row.id: row for row in rows}


def _winner_team_id(game: GameLog) -> Optional[int]:
    if game.home_score is None or game.away_score is None:
        return None
    if game.home_score > game.away_score:
        return game.home_team_id
    if game.away_score > game.home_score:
        return game.away_team_id
    return None


def _games_for_series(
    db: Session, series_id: str, team_lookup: Optional[Dict[int, Team]] = None
) -> List[PlayoffSeriesGame]:
    rows = (
        db.query(GameLog)
        .filter(GameLog.series_id == series_id)
        .order_by(
            GameLog.series_game_num.asc(),
            GameLog.game_date.asc(),
            GameLog.game_id.asc(),
        )
        .all()
    )
    needed_team_ids: List[int] = []
    for row in rows:
        if row.home_team_id is not None:
            needed_team_ids.append(row.home_team_id)
        if row.away_team_id is not None:
            needed_team_ids.append(row.away_team_id)
    if team_lookup is None:
        team_lookup = _team_lookup(db, list(set(needed_team_ids)))

    games: List[PlayoffSeriesGame] = []
    for row in rows:
        home_team = team_lookup.get(row.home_team_id) if row.home_team_id is not None else None
        away_team = team_lookup.get(row.away_team_id) if row.away_team_id is not None else None
        games.append(
            PlayoffSeriesGame(
                game_id=row.game_id,
                game_date=row.game_date,
                home_team_id=row.home_team_id,
                home_team_abbr=home_team.abbreviation if home_team is not None else None,
                away_team_id=row.away_team_id,
                away_team_abbr=away_team.abbreviation if away_team is not None else None,
                home_pts=row.home_score,
                away_pts=row.away_score,
                winner_team_id=_winner_team_id(row),
                series_game_num=row.series_game_num,
            )
        )
    return games


def _resolve_parent_label_fields(
    db: Session, parent_series_id: Optional[str]
):
    """Sprint 86 — return ``(seed, [top_abbr, bottom_abbr])`` for a parent
    series, or ``(None, None)`` when the pointer is null or the row is missing.

    ``seed`` is the parent's lower-numbered seed (e.g. 1 for a 1v8 series),
    which the frontend uses together with the abbreviation pair to render
    richer TBD labels like ``"winner of 1v8 (OKC/PHX)"``.
    """
    if not parent_series_id:
        return None, None

    from db.models import PlayoffSeries  # local import — avoids router cycle

    parent = (
        db.query(PlayoffSeries)
        .filter(PlayoffSeries.series_id == parent_series_id)
        .first()
    )
    if parent is None:
        return None, None

    top_seed = parent.top_seed
    bottom_seed = parent.bottom_seed
    if top_seed is not None and bottom_seed is not None:
        # Convention: render as "{lower}v{higher}" — store the lower seed only;
        # the frontend pairs it with the parent series's higher seed.
        seed_pair_top = min(int(top_seed), int(bottom_seed))
    elif top_seed is not None:
        seed_pair_top = int(top_seed)
    elif bottom_seed is not None:
        seed_pair_top = int(bottom_seed)
    else:
        seed_pair_top = None

    top_abbr = None
    bottom_abbr = None
    if parent.top_seed_team_id is not None:
        top_team = (
            db.query(Team).filter(Team.id == parent.top_seed_team_id).first()
        )
        top_abbr = top_team.abbreviation if top_team is not None else None
    if parent.bottom_seed_team_id is not None:
        bottom_team = (
            db.query(Team).filter(Team.id == parent.bottom_seed_team_id).first()
        )
        bottom_abbr = bottom_team.abbreviation if bottom_team is not None else None

    abbrs = [top_abbr, bottom_abbr] if (top_abbr or bottom_abbr) else None
    return seed_pair_top, abbrs


def _series_to_response(
    series,
    team_lookup: Dict[int, Team],
    games: List[PlayoffSeriesGame],
    db: Optional[Session] = None,
) -> PlayoffSeriesResponse:
    top = (
        team_lookup.get(series.top_seed_team_id)
        if series.top_seed_team_id is not None
        else None
    )
    bottom = (
        team_lookup.get(series.bottom_seed_team_id)
        if series.bottom_seed_team_id is not None
        else None
    )

    parent_top_series_id = getattr(series, "parent_top_series_id", None)
    parent_bottom_series_id = getattr(series, "parent_bottom_series_id", None)

    # Sprint 86 — resolve the parent series's seed + team abbreviations so the
    # frontend can label TBD slots as "winner of 1v8 (OKC/PHX)" etc.
    parent_top_seed = None
    parent_top_team_abbrs = None
    parent_bottom_seed = None
    parent_bottom_team_abbrs = None
    if db is not None:
        if parent_top_series_id:
            parent_top_seed, parent_top_team_abbrs = _resolve_parent_label_fields(
                db, parent_top_series_id
            )
        if parent_bottom_series_id:
            (
                parent_bottom_seed,
                parent_bottom_team_abbrs,
            ) = _resolve_parent_label_fields(db, parent_bottom_series_id)

    # Sprint 91 — bypass the stale PlayoffSeries.top_wins/bottom_wins
    # denormalized cache (only updated by the 6am daily sync). Count fresh
    # from the games list, which is built from GameLog rows whose scores
    # are write-through-updated by /today's scoreboard overlay. Same
    # pattern Sprint 90 applied to /today; now /bracket and /series/{id}
    # see fresh records the moment a game finishes.
    fresh_top_wins = sum(
        1
        for g in games
        if g.winner_team_id is not None
        and series.top_seed_team_id is not None
        and g.winner_team_id == series.top_seed_team_id
    )
    fresh_bottom_wins = sum(
        1
        for g in games
        if g.winner_team_id is not None
        and series.bottom_seed_team_id is not None
        and g.winner_team_id == series.bottom_seed_team_id
    )

    return PlayoffSeriesResponse(
        season=series.season,
        round=series.round,
        series_id=series.series_id,
        top_seed_team_id=series.top_seed_team_id,
        bottom_seed_team_id=series.bottom_seed_team_id,
        top_seed_team_abbr=top.abbreviation if top is not None else None,
        bottom_seed_team_abbr=bottom.abbreviation if bottom is not None else None,
        top_seed=series.top_seed,
        bottom_seed=series.bottom_seed,
        top_wins=fresh_top_wins,
        bottom_wins=fresh_bottom_wins,
        status=series.status,
        winner_team_id=series.winner_team_id,
        games=games,
        # Sprint 85 — bracket auto-advancement parent pointers.
        parent_top_series_id=parent_top_series_id,
        parent_bottom_series_id=parent_bottom_series_id,
        # Sprint 86 — richer TBD labels: parent seed + abbrs.
        parent_top_seed=parent_top_seed,
        parent_bottom_seed=parent_bottom_seed,
        parent_top_team_abbrs=parent_top_team_abbrs,
        parent_bottom_team_abbrs=parent_bottom_team_abbrs,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/bracket", response_model=PlayoffBracketResponse)
def get_bracket(
    season: str = Query(...),
    db: Session = Depends(get_db),
) -> PlayoffBracketResponse:
    """Return the full playoff bracket for ``season`` grouped by conference."""
    from db.models import PlayoffSeries  # local import — see season_phase_service

    series_rows = (
        db.query(PlayoffSeries)
        .filter(PlayoffSeries.season == season)
        .order_by(PlayoffSeries.round.asc(), PlayoffSeries.top_seed.asc())
        .all()
    )

    team_ids: List[int] = []
    for s in series_rows:
        if s.top_seed_team_id is not None:
            team_ids.append(s.top_seed_team_id)
        if s.bottom_seed_team_id is not None:
            team_ids.append(s.bottom_seed_team_id)
    team_lookup = _team_lookup(db, list(set(team_ids)))

    east: List[PlayoffSeriesResponse] = []
    west: List[PlayoffSeriesResponse] = []
    finals: Optional[PlayoffSeriesResponse] = None

    for s in series_rows:
        games = _games_for_series(db, s.series_id, team_lookup)
        response = _series_to_response(s, team_lookup, games, db=db)

        if s.round == 4:
            finals = response
            continue

        # Determine conference from either top-seed or bottom-seed team.
        top_team = team_lookup.get(s.top_seed_team_id)
        bottom_team = team_lookup.get(s.bottom_seed_team_id)
        top_abbr = top_team.abbreviation if top_team is not None else None
        bottom_abbr = bottom_team.abbreviation if bottom_team is not None else None
        conference = _conference_for_team(top_team, top_abbr) or _conference_for_team(
            bottom_team, bottom_abbr
        )
        if conference == "East":
            east.append(response)
        elif conference == "West":
            west.append(response)
        else:
            # Unknown conference (e.g. a play-in or test seed without a team
            # mapping) — drop into east as a neutral default.
            east.append(response)

    return PlayoffBracketResponse(season=season, east=east, west=west, finals=finals)


@router.get("/series/{series_id}", response_model=PlayoffSeriesResponse)
def get_series(
    series_id: str,
    db: Session = Depends(get_db),
) -> PlayoffSeriesResponse:
    """Return a single playoff series with games in series_game_num order."""
    from db.models import PlayoffSeries  # local import

    series = (
        db.query(PlayoffSeries)
        .filter(PlayoffSeries.series_id == series_id)
        .first()
    )
    if series is None:
        raise HTTPException(status_code=404, detail=f"Playoff series '{series_id}' not found")

    team_ids: List[int] = []
    if series.top_seed_team_id is not None:
        team_ids.append(series.top_seed_team_id)
    if series.bottom_seed_team_id is not None:
        team_ids.append(series.bottom_seed_team_id)
    team_lookup = _team_lookup(db, team_ids)

    games = _games_for_series(db, series_id, team_lookup)
    return _series_to_response(series, team_lookup, games, db=db)


@router.get("/series/{series_id}/intelligence", response_model=PlayoffSeriesIntelligenceResponse)
def get_series_intelligence(
    series_id: str,
    db: Session = Depends(get_db),
) -> PlayoffSeriesIntelligenceResponse:
    """Return deterministic coach/analyst intelligence for one playoff series."""
    response = build_playoff_series_intelligence(db, series_id)
    if response is None:
        raise HTTPException(status_code=404, detail=f"Playoff series '{series_id}' not found")
    return response


def _scoreboard_games_for_today() -> Dict[str, dict]:
    """Return playoff games from the live CDN scoreboard, keyed by game_id.

    Returns an empty dict on any failure (network error, malformed payload).
    The endpoint uses this as a supplement, never a replacement, so a CDN
    outage degrades cleanly to DB-only data.
    """
    try:
        payload = get_todays_scoreboard()
    except Exception as exc:  # pragma: no cover — best-effort enrichment
        logger.warning("Failed to fetch live scoreboard for /playoffs/today: %s", exc)
        return {}

    scoreboard = payload.get("scoreboard") or {}
    games = scoreboard.get("games") or []
    out: Dict[str, dict] = {}
    for game in games:
        game_id = (game.get("gameId") or "").strip()
        # Only keep playoff games. Game ID format: "00" + type + season + num.
        # type=4 is playoffs.
        if not game_id or not game_id.startswith("004"):
            continue
        out[game_id] = game
    return out


def _build_scheduled_game_from_scoreboard(
    sb_game: dict,
    target: date,
    db: Session,
) -> Optional[PlayoffSeriesGameWithMatchup]:
    """Translate a scoreboard payload entry into PlayoffSeriesGameWithMatchup.

    Pulls series context from the DB if any prior game in the same series
    has been ingested. If the series is brand-new (no rows yet), series
    context is null and the card renders as a generic upcoming game.
    """
    from db.models import PlayoffSeries  # local import to avoid cycle

    game_id = sb_game.get("gameId")
    if not game_id:
        return None

    home_sb = sb_game.get("homeTeam") or {}
    away_sb = sb_game.get("awayTeam") or {}
    home_team_id = home_sb.get("teamId")
    away_team_id = away_sb.get("teamId")
    home_abbr = (home_sb.get("teamTricode") or "").upper() or None
    away_abbr = (away_sb.get("teamTricode") or "").upper() or None

    # Scoreboard scores: 0 for upcoming, real for live/final. Use None when
    # the game hasn't tipped (gameStatus 1) so the frontend renders the
    # "scheduled" state instead of "0–0 live".
    game_status = sb_game.get("gameStatus")
    home_pts: Optional[int] = home_sb.get("score") if game_status != 1 else None
    away_pts: Optional[int] = away_sb.get("score") if game_status != 1 else None
    winner_team_id: Optional[int] = None
    if game_status == 3 and home_pts is not None and away_pts is not None:
        if home_pts > away_pts:
            winner_team_id = home_team_id
        elif away_pts > home_pts:
            winner_team_id = away_team_id

    tipoff_utc = sb_game.get("gameTimeUTC") or None
    broadcasters = sb_game.get("broadcasters") or {}
    national = (broadcasters.get("nationalTvBroadcasters") or [])
    broadcaster: Optional[str] = None
    if national:
        broadcaster = national[0].get("broadcasterDisplay") or national[0].get("broadcasterAbbreviation") or None

    # Series context — try to find any existing PlayoffSeries record where
    # the two teams already met this postseason.
    series_id: Optional[str] = None
    season: Optional[str] = None
    round_no: Optional[int] = None
    top_abbr: Optional[str] = None
    bot_abbr: Optional[str] = None
    status = None

    if home_team_id is not None and away_team_id is not None:
        series_row = (
            db.query(PlayoffSeries)
            .filter(
                ((PlayoffSeries.top_seed_team_id == home_team_id) & (PlayoffSeries.bottom_seed_team_id == away_team_id))
                | ((PlayoffSeries.top_seed_team_id == away_team_id) & (PlayoffSeries.bottom_seed_team_id == home_team_id))
            )
            .order_by(PlayoffSeries.round.desc())
            .first()
        )
        if series_row is not None:
            series_id = series_row.series_id
            season = series_row.season
            round_no = series_row.round
            status = series_row.status
            top_team = db.query(Team).filter(Team.id == series_row.top_seed_team_id).first()
            bot_team = db.query(Team).filter(Team.id == series_row.bottom_seed_team_id).first()
            top_abbr = top_team.abbreviation if top_team else None
            bot_abbr = bot_team.abbreviation if bot_team else None

    # Sprint 90 hotfix — top_wins/bottom_wins are intentionally None here;
    # `get_today` patches them in its single post-pass after computing the
    # fresh series win count from GameLog + live scoreboard finals.
    return PlayoffSeriesGameWithMatchup(
        game_id=game_id,
        game_date=target,
        home_team_id=home_team_id,
        home_team_abbr=home_abbr,
        away_team_id=away_team_id,
        away_team_abbr=away_abbr,
        home_pts=home_pts,
        away_pts=away_pts,
        winner_team_id=winner_team_id,
        series_game_num=None,  # not always reliable from scoreboard
        series_id=series_id,
        season=season,
        round=round_no,
        top_seed_team_abbr=top_abbr,
        bottom_seed_team_abbr=bot_abbr,
        top_wins=None,
        bottom_wins=None,
        status=status,
        headline_storyline=None,
        tipoff_utc=tipoff_utc,
        broadcaster=broadcaster,
    )


@router.get("/today", response_model=PlayoffTodayResponse)
def get_today(
    date_param: Optional[str] = Query(None, alias="date", description="YYYY-MM-DD; defaults to today (US/Pacific)."),
    db: Session = Depends(get_db),
) -> PlayoffTodayResponse:
    """Return all playoff games on a given date along with their series context.

    For today's date, also fetches the live CDN scoreboard and merges in any
    scheduled or in-progress games that haven't been ingested into the DB yet.
    DB rows remain authoritative for completed games (scores, series context,
    storyline). For upcoming games, the scoreboard supplies tipoff time,
    broadcaster, and current live scores.
    """
    from db.models import PlayoffSeries  # local import

    if date_param is None:
        target = _today_pacific()
    else:
        try:
            target = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="`date` must be formatted YYYY-MM-DD")

    is_today = target == _today_pacific()

    rows = (
        db.query(GameLog)
        .filter(GameLog.season_type == "Playoffs")
        .filter(GameLog.game_date == target)
        .order_by(GameLog.game_id.asc())
        .all()
    )

    # Fetch scoreboard supplements only for today — historical dates don't
    # need a live CDN call.
    scoreboard_lookup: Dict[str, dict] = {}
    if is_today:
        scoreboard_lookup = _scoreboard_games_for_today()

    series_ids = list({row.series_id for row in rows if row.series_id})
    series_rows = []
    if series_ids:
        series_rows = (
            db.query(PlayoffSeries)
            .filter(PlayoffSeries.series_id.in_(series_ids))
            .all()
        )
    series_lookup = {s.series_id: s for s in series_rows}

    # Sprint 90 hotfix — series_completed_wins is built up below as we
    # discover which series are involved in today's slate (DB-row games AND
    # scoreboard-only games not yet ingested into GameLog). Final patch of
    # every game's top_wins / bottom_wins happens in a single post-pass.
    series_completed_wins: Dict[str, Dict[int, int]] = {}

    needed_team_ids: List[int] = []
    for row in rows:
        if row.home_team_id is not None:
            needed_team_ids.append(row.home_team_id)
        if row.away_team_id is not None:
            needed_team_ids.append(row.away_team_id)
    for s in series_rows:
        if s.top_seed_team_id is not None:
            needed_team_ids.append(s.top_seed_team_id)
        if s.bottom_seed_team_id is not None:
            needed_team_ids.append(s.bottom_seed_team_id)
    team_lookup = _team_lookup(db, list(set(needed_team_ids)))

    games: List[PlayoffSeriesGameWithMatchup] = []
    db_game_ids = set()
    for row in rows:
        db_game_ids.add(row.game_id)
        home_team = team_lookup.get(row.home_team_id) if row.home_team_id is not None else None
        away_team = team_lookup.get(row.away_team_id) if row.away_team_id is not None else None
        series = series_lookup.get(row.series_id) if row.series_id else None

        top_team = team_lookup.get(series.top_seed_team_id) if series is not None else None
        bottom_team = team_lookup.get(series.bottom_seed_team_id) if series is not None else None

        storyline: Optional[str] = None
        if home_team is not None and away_team is not None:
            try:
                storyline = compute_game_storyline(db, row, home_team, away_team)
            except Exception:  # pragma: no cover - storyline is best-effort, never fatal
                storyline = None

        # Overlay live scoreboard data when the game is happening today and
        # the scoreboard has fresher info (tipoff time, live scores).
        sb_game = scoreboard_lookup.get(row.game_id)
        sb_tipoff = sb_game.get("gameTimeUTC") if sb_game else None
        sb_broadcaster = None
        if sb_game:
            broadcasters = sb_game.get("broadcasters") or {}
            national = broadcasters.get("nationalTvBroadcasters") or []
            if national:
                sb_broadcaster = (
                    national[0].get("broadcasterDisplay")
                    or national[0].get("broadcasterAbbreviation")
                )

        # Live game with no DB scores yet — pull current scores from scoreboard.
        live_home_pts = row.home_score
        live_away_pts = row.away_score
        db_had_score = row.home_score is not None and row.away_score is not None
        sb_status = sb_game.get("gameStatus") if sb_game else None
        if sb_game and (live_home_pts is None or live_away_pts is None):
            if sb_status in (2, 3):  # live or final
                live_home_pts = (sb_game.get("homeTeam") or {}).get("score")
                live_away_pts = (sb_game.get("awayTeam") or {}).get("score")

        games.append(
            PlayoffSeriesGameWithMatchup(
                game_id=row.game_id,
                game_date=row.game_date,
                home_team_id=row.home_team_id,
                home_team_abbr=home_team.abbreviation if home_team is not None else None,
                away_team_id=row.away_team_id,
                away_team_abbr=away_team.abbreviation if away_team is not None else None,
                home_pts=live_home_pts,
                away_pts=live_away_pts,
                winner_team_id=_winner_team_id(row),
                series_game_num=row.series_game_num,
                series_id=row.series_id,
                season=series.season if series is not None else None,
                round=series.round if series is not None else None,
                top_seed_team_abbr=top_team.abbreviation if top_team is not None else None,
                bottom_seed_team_abbr=bottom_team.abbreviation if bottom_team is not None else None,
                # Sprint 90 hotfix — set placeholders here; we'll patch from
                # series_completed_wins in a single post-pass below so the
                # record reflects every win source uniformly (DB-row games,
                # in-flight scoreboard finals not yet ingested into GameLog).
                top_wins=None,
                bottom_wins=None,
                status=series.status if series is not None else None,
                headline_storyline=storyline,
                tipoff_utc=sb_tipoff,
                broadcaster=sb_broadcaster,
            )
        )

    # Append any scoreboard games that weren't already in the DB (true
    # "upcoming" games not yet ingested).
    scoreboard_only_finals: List[PlayoffSeriesGameWithMatchup] = []
    for game_id, sb_game in scoreboard_lookup.items():
        if game_id in db_game_ids:
            continue
        scheduled = _build_scheduled_game_from_scoreboard(sb_game, target, db)
        if scheduled is None:
            continue
        # Sprint 90 hotfix — track scoreboard-only finals so the post-pass
        # below counts them toward the series record (live final → +1 win
        # before the nightly GameLog ingest catches up). Skip live (status=2)
        # and scheduled (status=1): only finals book a win.
        if (
            sb_game.get("gameStatus") == 3
            and scheduled.series_id
            and scheduled.winner_team_id is not None
        ):
            scoreboard_only_finals.append(scheduled)
        games.append(scheduled)

    # ---------------------------------------------------------------------
    # Sprint 90 hotfix — single post-pass that computes the series win
    # record fresh and patches every game's top_wins / bottom_wins. The
    # PlayoffSeries.top_wins/bottom_wins denormalized cache is bypassed
    # entirely on this endpoint; GameLog + live scoreboard finals are
    # authoritative.
    # ---------------------------------------------------------------------

    all_series_ids: Set[str] = {g.series_id for g in games if g.series_id}
    if all_series_ids:
        # Pull every PlayoffSeries we'll need to map team_id → top/bottom seed,
        # which may include series for tonight's scoreboard-only games whose
        # series_id wasn't in the original `series_ids` set.
        all_series_rows = (
            db.query(PlayoffSeries)
            .filter(PlayoffSeries.series_id.in_(all_series_ids))
            .all()
        )
        series_seed_lookup: Dict[str, Dict[str, Optional[int]]] = {
            s.series_id: {"top": s.top_seed_team_id, "bottom": s.bottom_seed_team_id}
            for s in all_series_rows
        }

        # Count wins from completed GameLog rows across every relevant series.
        completed_rows = (
            db.query(GameLog)
            .filter(GameLog.series_id.in_(all_series_ids))
            .all()
        )
        for completed in completed_rows:
            winner_id = _winner_team_id(completed)
            if winner_id is None or completed.series_id is None:
                continue
            bucket = series_completed_wins.setdefault(completed.series_id, {})
            bucket[winner_id] = bucket.get(winner_id, 0) + 1

        # Also count tonight's just-final scoreboard games (no GameLog row yet
        # OR GameLog row exists but has NULL scores). For DB rows whose score
        # was null but the live overlay supplied final scores, we re-detect
        # "final via overlay" by checking the scoreboard status here.
        for db_row in rows:
            sb_game = scoreboard_lookup.get(db_row.game_id)
            if sb_game is None:
                continue
            if db_row.home_score is not None and db_row.away_score is not None:
                continue  # already counted via completed_rows above
            if sb_game.get("gameStatus") != 3:
                continue
            home_pts_sb = (sb_game.get("homeTeam") or {}).get("score")
            away_pts_sb = (sb_game.get("awayTeam") or {}).get("score")
            if home_pts_sb is None or away_pts_sb is None:
                continue
            if home_pts_sb > away_pts_sb:
                live_winner_id = db_row.home_team_id
            elif away_pts_sb > home_pts_sb:
                live_winner_id = db_row.away_team_id
            else:
                live_winner_id = None
            if live_winner_id is not None and db_row.series_id:
                # Sprint 91 — write-through: persist the scoreboard final
                # to GameLog so subsequent /bracket and /series/{id} reads
                # see the fresh winner_team_id (which the new fresh-count
                # in _series_to_response keys off of). Without this, the
                # bracket page would still show yesterday's series record
                # until the 6am daily sync.
                db_row.home_score = home_pts_sb
                db_row.away_score = away_pts_sb
                bucket = series_completed_wins.setdefault(db_row.series_id, {})
                bucket[live_winner_id] = bucket.get(live_winner_id, 0) + 1

        # Scoreboard-only finals (no GameLog row at all yet).
        for scheduled in scoreboard_only_finals:
            bucket = series_completed_wins.setdefault(scheduled.series_id, {})
            bucket[scheduled.winner_team_id] = bucket.get(scheduled.winner_team_id, 0) + 1

        # Patch every game's record.
        for g in games:
            if not g.series_id:
                continue
            seeds = series_seed_lookup.get(g.series_id)
            if not seeds:
                continue
            bucket = series_completed_wins.get(g.series_id, {})
            g.top_wins = bucket.get(seeds["top"], 0) if seeds["top"] is not None else 0
            g.bottom_wins = bucket.get(seeds["bottom"], 0) if seeds["bottom"] is not None else 0

    games.sort(key=lambda g: (g.tipoff_utc or "9999", g.game_id))

    # Sprint 91 — flush any GameLog write-through scoreboard finals from
    # the overlay block above. Wrap so a commit failure can't take down
    # the /today response — the in-memory `games` list is already correct
    # for this request even if the persist fails.
    try:
        db.commit()
    except Exception:  # noqa: BLE001 — defensive; in-memory response still valid
        db.rollback()

    return PlayoffTodayResponse(date=target, games=games)


@router.get("/series-simulation/{series_id}", response_model=SeriesSimulationResponse)
def get_series_simulation(
    series_id: str,
    override_top_wins: Optional[int] = None,
    override_bottom_wins: Optional[int] = None,
    db: Session = Depends(get_db),
) -> SeriesSimulationResponse:
    """Return the Monte-Carlo projection for the requested series."""
    return simulate_series(
        db,
        series_id,
        override_top_wins=override_top_wins,
        override_bottom_wins=override_bottom_wins,
    )


@router.get("/leaders", response_model=PlayoffLeadersResponse)
def get_playoff_leaders(
    season: str = Query(...),
    limit: int = Query(5, ge=1, le=15),
    db: Session = Depends(get_db),
) -> PlayoffLeadersResponse:
    """Return the top-N playoff scoring leaders with trend + recent-grade chips."""
    return PlayoffLeadersResponse(
        season=season,
        leaders=compute_playoff_leaders(db, season, limit),
    )


@router.get("/story-rail", response_model=PlayoffStoryRailResponse)
def get_story_rail(
    season: str = Query(..., description="Season string, e.g. '2025-26'."),
    db: Session = Depends(get_db),
) -> PlayoffStoryRailResponse:
    """Return up to 3 auto-generated story tiles for the broadsheet rail.

    Tiles are computed from current playoff data (heat checks, efficiency
    leaders, x-factor contributors) and link to internal player routes.
    No editorial copy or external content — every tile is data-driven and
    refreshes whenever the underlying stats refresh.
    """
    return PlayoffStoryRailResponse(
        season=season,
        tiles=compute_story_rail(db, season),
        data_as_of=compute_data_as_of(db, season),
        computed_at=datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# Sprint 85 — Per-series detail page (per-team player game-by-game logs)
# ---------------------------------------------------------------------------


@router.get(
    "/series/{series_id}/player-logs",
    response_model=PlayoffSeriesPlayerLogsResponse,
)
def get_series_player_logs(
    series_id: str,
    db: Session = Depends(get_db),
) -> PlayoffSeriesPlayerLogsResponse:
    """Return per-team player game-by-game logs for a single playoff series.

    Backs the per-series tracker page: each player's stat line per game,
    grouped by team, ordered by minutes played in the series. The frontend
    deep-links each game row into ``/games/{game_id}``.
    """
    response = build_series_player_logs(db, series_id)
    if response is None:
        raise HTTPException(
            status_code=404, detail=f"Playoff series '{series_id}' not found"
        )
    return response
