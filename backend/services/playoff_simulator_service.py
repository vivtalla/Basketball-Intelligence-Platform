"""Playoff series Monte-Carlo simulator (Sprint 73).

Given a `PlayoffSeries.series_id`, project the per-game home-team win
probability for every remaining game in the best-of-7, and aggregate to a
series-level win probability via 1000 deterministic Monte-Carlo trials.

Strength model::

    team_strength = 0.5 * net_rating_z
                  + 0.3 * mean_top_5_player_BPM_z
                  + 0.2 * pace_adjusted_TS%_z

`P(home_wins) = sigmoid((home_strength - away_strength) + 0.06)` where 0.06 is
the home-court advantage adjustment.

If any of the inputs cannot be computed for both sides, we fall back to a
50/50 coin-flip baseline so the API stays tolerant to missing data.
"""
from __future__ import annotations

import math
import random
import statistics
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import GameLog, SeasonStat, Team, TeamSeasonStat
from models.game import SeriesOddsPoint
from models.playoffs import (
    SeriesProjectionEntry,
    SeriesSimulationCurrentState,
    SeriesSimulationResponse,
)


HOME_COURT_ADJUSTMENT = 0.06
TRIALS = 1000
SERIES_LENGTH = 7  # best-of-7
DEFAULT_HOME_WIN_PROB = 0.5

# Standard NBA Finals / playoff round home-court allocation: top seed hosts
# 1, 2, 5, 7; bottom seed hosts 3, 4, 6.
_TOP_SEED_HOME_GAMES = {1, 2, 5, 7}


# ---------------------------------------------------------------------------
# Strength model
# ---------------------------------------------------------------------------


def _zscore(value: Optional[float], pool: List[float]) -> float:
    if value is None or not pool:
        return 0.0
    if len(pool) < 2:
        return 0.0
    mean = statistics.mean(pool)
    try:
        stdev = statistics.pstdev(pool)
    except statistics.StatisticsError:
        return 0.0
    if not stdev:
        return 0.0
    return (value - mean) / stdev


def _sigmoid(x: float) -> float:
    if x > 50:
        return 1.0
    if x < -50:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def _team_season_stat(db: Session, team_id: int, season: str) -> Optional[TeamSeasonStat]:
    return (
        db.query(TeamSeasonStat)
        .filter(
            TeamSeasonStat.team_id == team_id,
            TeamSeasonStat.season == season,
            TeamSeasonStat.is_playoff == False,  # noqa: E712
        )
        .first()
    )


def _top5_bpm_mean(db: Session, team_id: int, season: str) -> Optional[float]:
    team = db.query(Team).filter(Team.id == team_id).first()
    abbr = team.abbreviation if team is not None else None
    if not abbr:
        return None
    rows = (
        db.query(SeasonStat.bpm)
        .filter(SeasonStat.season == season)
        .filter(SeasonStat.team_abbreviation == abbr)
        .filter(SeasonStat.is_playoff == False)  # noqa: E712
        .all()
    )
    bpms = [float(r[0]) for r in rows if r[0] is not None]
    if not bpms:
        return None
    bpms.sort(reverse=True)
    top = bpms[:5]
    if not top:
        return None
    return sum(top) / len(top)


def _league_pool(db: Session, season: str) -> Tuple[List[float], List[float], List[float]]:
    rows = (
        db.query(TeamSeasonStat)
        .filter(
            TeamSeasonStat.season == season,
            TeamSeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    net_pool = [r.net_rating for r in rows if r.net_rating is not None]
    pace_pool = [r.pace for r in rows if r.pace is not None]
    ts_pool = [r.ts_pct for r in rows if r.ts_pct is not None]
    league_pace = statistics.mean(pace_pool) if pace_pool else None
    pace_adj_ts: List[float] = []
    for r in rows:
        if r.ts_pct is None:
            continue
        if r.pace is not None and league_pace:
            pace_adj_ts.append(float(r.ts_pct) * (league_pace / float(r.pace)))
        else:
            pace_adj_ts.append(float(r.ts_pct))
    return net_pool, pace_adj_ts, ts_pool


def _team_strength(
    db: Session,
    team_id: int,
    season: str,
    net_pool: List[float],
    pace_adj_ts_pool: List[float],
) -> Optional[float]:
    """Weighted z-score composite. Returns `None` if no signal at all."""
    season_stat = _team_season_stat(db, team_id, season)
    if season_stat is None:
        return None

    components: List[Tuple[float, float]] = []  # (weight, z_value)

    if season_stat.net_rating is not None:
        components.append((0.5, _zscore(float(season_stat.net_rating), net_pool)))

    bpm_mean = _top5_bpm_mean(db, team_id, season)
    if bpm_mean is not None:
        # Build the BPM pool across all teams in the season for normalization.
        team_rows = (
            db.query(Team.id)
            .join(TeamSeasonStat, TeamSeasonStat.team_id == Team.id)
            .filter(
                TeamSeasonStat.season == season,
                TeamSeasonStat.is_playoff == False,  # noqa: E712
            )
            .all()
        )
        bpm_pool: List[float] = []
        for (other_team_id,) in team_rows:
            other_mean = _top5_bpm_mean(db, other_team_id, season)
            if other_mean is not None:
                bpm_pool.append(other_mean)
        components.append((0.3, _zscore(bpm_mean, bpm_pool)))

    if season_stat.ts_pct is not None:
        league_pace_pool = [
            r.pace for r in db.query(TeamSeasonStat).filter(
                TeamSeasonStat.season == season,
                TeamSeasonStat.is_playoff == False,  # noqa: E712
            ).all()
            if r.pace is not None
        ]
        league_pace = statistics.mean(league_pace_pool) if league_pace_pool else None
        if season_stat.pace is not None and league_pace:
            pace_adj_ts = float(season_stat.ts_pct) * (league_pace / float(season_stat.pace))
        else:
            pace_adj_ts = float(season_stat.ts_pct)
        components.append((0.2, _zscore(pace_adj_ts, pace_adj_ts_pool)))

    if not components:
        return None

    return sum(weight * value for weight, value in components)


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


def _home_team_for_game(game_num: int, top_seed_team_id: int, bottom_seed_team_id: int) -> Tuple[int, int]:
    """Return (home_team_id, away_team_id) for game number `game_num` (1..7)."""
    if game_num in _TOP_SEED_HOME_GAMES:
        return top_seed_team_id, bottom_seed_team_id
    return bottom_seed_team_id, top_seed_team_id


def _team_abbr(db: Session, team_id: Optional[int]) -> Optional[str]:
    if team_id is None:
        return None
    team = db.query(Team).filter(Team.id == team_id).first()
    return team.abbreviation if team is not None else None


def _games_played(db: Session, series_id: str) -> int:
    """Count completed games in this series (rows with both scores present)."""
    rows = (
        db.query(GameLog)
        .filter(GameLog.series_id == series_id)
        .all()
    )
    completed = 0
    for row in rows:
        if row.home_score is not None and row.away_score is not None:
            completed += 1
    return completed


def _win_prob_top_seed_at_home(
    db: Session,
    season: str,
    top_seed_team_id: int,
    bottom_seed_team_id: int,
    net_pool: List[float],
    pace_adj_ts_pool: List[float],
) -> Optional[float]:
    """Probability that the top seed wins a single game played at top-seed home."""
    top_strength = _team_strength(db, top_seed_team_id, season, net_pool, pace_adj_ts_pool)
    bottom_strength = _team_strength(db, bottom_seed_team_id, season, net_pool, pace_adj_ts_pool)
    if top_strength is None or bottom_strength is None:
        return None
    return _sigmoid((top_strength - bottom_strength) + HOME_COURT_ADJUSTMENT)


def _per_game_top_seed_win_prob(
    home_prob_top_seed: float,
    bottom_prob_top_seed_on_road: float,
    game_num: int,
) -> float:
    """Probability that the top seed wins game `game_num`."""
    if game_num in _TOP_SEED_HOME_GAMES:
        return home_prob_top_seed
    return bottom_prob_top_seed_on_road


def _monte_carlo(
    rng: random.Random,
    top_wins: int,
    bottom_wins: int,
    per_game_top_seed_win_prob: Dict[int, float],
    total_trials: int = TRIALS,
) -> Tuple[float, float, Dict[int, Tuple[int, int]]]:
    """Run MC trials starting from current state and return:

    - top_seed_series_win_prob
    - bottom_seed_series_win_prob
    - per remaining game: (top_seed_win_count, total_simulations_that_played_it)
    """
    top_series_wins = 0
    bottom_series_wins = 0
    per_game_counter: Dict[int, Tuple[int, int]] = {
        gn: (0, 0) for gn in per_game_top_seed_win_prob
    }

    for _ in range(total_trials):
        cur_top = top_wins
        cur_bottom = bottom_wins
        for game_num in sorted(per_game_top_seed_win_prob):
            if cur_top >= 4 or cur_bottom >= 4:
                break
            top_seed_win_prob = per_game_top_seed_win_prob[game_num]
            outcome_top_wins = rng.random() < top_seed_win_prob
            top_w, total_p = per_game_counter[game_num]
            per_game_counter[game_num] = (
                top_w + (1 if outcome_top_wins else 0),
                total_p + 1,
            )
            if outcome_top_wins:
                cur_top += 1
            else:
                cur_bottom += 1
        if cur_top >= 4:
            top_series_wins += 1
        elif cur_bottom >= 4:
            bottom_series_wins += 1

    if total_trials == 0:
        return 0.0, 0.0, per_game_counter

    return (
        top_series_wins / total_trials,
        bottom_series_wins / total_trials,
        per_game_counter,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def _clamp_wins(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    return max(0, min(4, int(value)))


def simulate_series(
    db: Session,
    series_id: str,
    override_top_wins: Optional[int] = None,
    override_bottom_wins: Optional[int] = None,
) -> SeriesSimulationResponse:
    """Project remaining games + series win probability for `series_id`.

    The output is deterministic for a given series_id (we seed from a hash
    of the id) so successive calls produce identical numbers.
    """
    # Local import — see season_phase_service for the rationale.
    from db.models import PlayoffSeries  # type: ignore

    series = (
        db.query(PlayoffSeries)
        .filter(PlayoffSeries.series_id == series_id)
        .first()
    )
    if series is None:
        # Empty response — caller can decide how to surface "not found".
        return SeriesSimulationResponse(
            series_id=series_id,
            current_state=SeriesSimulationCurrentState(
                top_wins=0,
                bottom_wins=0,
                games_played=0,
                status="scheduled",
            ),
            projection=[],
            top_seed_series_win_prob=0.0,
            bottom_seed_series_win_prob=0.0,
            trials=0,
        )

    season = series.season
    top_id = series.top_seed_team_id
    bottom_id = series.bottom_seed_team_id
    top_abbr = _team_abbr(db, top_id)
    bottom_abbr = _team_abbr(db, bottom_id)

    games_played = _games_played(db, series_id)
    top_wins = int(series.top_wins or 0)
    bottom_wins = int(series.bottom_wins or 0)
    top_override = _clamp_wins(override_top_wins)
    bottom_override = _clamp_wins(override_bottom_wins)
    using_override = top_override is not None or bottom_override is not None
    if top_override is not None:
        top_wins = top_override
    if bottom_override is not None:
        bottom_wins = bottom_override
    if top_wins + bottom_wins > SERIES_LENGTH:
        # Keep hypothetical states possible but never impossible.
        overflow = top_wins + bottom_wins - SERIES_LENGTH
        if bottom_override is not None and top_override is None:
            bottom_wins = max(0, bottom_wins - overflow)
        else:
            top_wins = max(0, top_wins - overflow)
    if using_override:
        games_played = min(SERIES_LENGTH, top_wins + bottom_wins)

    state_status = series.status
    if using_override:
        if top_wins >= 4 or bottom_wins >= 4:
            state_status = "closed"
        elif top_wins == 0 and bottom_wins == 0 and series.status == "scheduled":
            state_status = "scheduled"
        else:
            state_status = "active"

    current_state = SeriesSimulationCurrentState(
        top_seed_team_abbr=top_abbr,
        bottom_seed_team_abbr=bottom_abbr,
        top_wins=top_wins,
        bottom_wins=bottom_wins,
        games_played=games_played,
        status=state_status,
    )

    # Series already over — short circuit.
    if top_wins >= 4 or bottom_wins >= 4 or (series.status == "closed" and not using_override):
        return SeriesSimulationResponse(
            series_id=series_id,
            current_state=current_state,
            projection=[],
            top_seed_series_win_prob=1.0 if top_wins >= 4 else 0.0,
            bottom_seed_series_win_prob=1.0 if bottom_wins >= 4 else 0.0,
            trials=0,
        )

    # Strength model.
    net_pool, pace_adj_ts_pool, _ts_pool = _league_pool(db, season)
    home_top_prob = _win_prob_top_seed_at_home(
        db, season, top_id, bottom_id, net_pool, pace_adj_ts_pool
    )
    if home_top_prob is None:
        # Coin-flip fallback when strength inputs are missing.
        home_top_prob = DEFAULT_HOME_WIN_PROB
        away_top_prob = DEFAULT_HOME_WIN_PROB
    else:
        # On the road the top seed faces the home-court adjustment in reverse:
        # Pr(top wins on road) = sigmoid((top - bottom) - 0.06).
        bottom_strength = _team_strength(db, bottom_id, season, net_pool, pace_adj_ts_pool)
        top_strength = _team_strength(db, top_id, season, net_pool, pace_adj_ts_pool)
        if bottom_strength is None or top_strength is None:
            away_top_prob = 1.0 - home_top_prob
        else:
            away_top_prob = _sigmoid((top_strength - bottom_strength) - HOME_COURT_ADJUSTMENT)

    # Determine which game numbers are still to be played.
    remaining_game_nums: List[int] = []
    for game_num in range(1, SERIES_LENGTH + 1):
        if game_num <= games_played:
            continue
        remaining_game_nums.append(game_num)

    per_game_top_seed_prob: Dict[int, float] = {}
    for gn in remaining_game_nums:
        per_game_top_seed_prob[gn] = _per_game_top_seed_win_prob(
            home_top_prob, away_top_prob, gn
        )

    # Deterministic seeded RNG.
    rng = random.Random()
    rng.seed(hash(series_id))

    top_series_prob, bottom_series_prob, per_game_counter = _monte_carlo(
        rng,
        top_wins,
        bottom_wins,
        per_game_top_seed_prob,
        total_trials=TRIALS,
    )

    projection: List[SeriesProjectionEntry] = []
    for gn in remaining_game_nums:
        home_team_id, away_team_id = _home_team_for_game(gn, top_id, bottom_id)
        home_abbr = top_abbr if home_team_id == top_id else bottom_abbr
        away_abbr = bottom_abbr if away_team_id == bottom_id else top_abbr
        top_w, total_p = per_game_counter.get(gn, (0, 0))
        if total_p > 0:
            top_seed_win_share = top_w / total_p
        else:
            top_seed_win_share = per_game_top_seed_prob.get(gn, DEFAULT_HOME_WIN_PROB)
        if home_team_id == top_id:
            home_win_prob = top_seed_win_share
        else:
            home_win_prob = 1.0 - top_seed_win_share

        projection.append(
            SeriesProjectionEntry(
                game_num=gn,
                home_team_abbr=home_abbr,
                away_team_abbr=away_abbr,
                home_win_prob=round(home_win_prob, 4),
            )
        )

    return SeriesSimulationResponse(
        series_id=series_id,
        current_state=current_state,
        projection=projection,
        top_seed_series_win_prob=round(top_series_prob, 4),
        bottom_seed_series_win_prob=round(bottom_series_prob, 4),
        trials=TRIALS,
    )


# ---------------------------------------------------------------------------
# Sprint 77 — Post-game series odds history
# ---------------------------------------------------------------------------


def compute_series_odds_history(
    db: Session,
    series_id: str,
) -> List[SeriesOddsPoint]:
    """Build a per-game post-game series-odds curve for a playoff series.

    For each completed game in the series (ordered by ``series_game_num``):

    1. Resolve the winner from ``home_team_id``/``away_team_id`` + scores.
    2. Compute the post-game snapshot ``(top_wins_after, bottom_wins_after)``.
    3. Re-run :func:`simulate_series` with the snapshot supplied via
       ``override_top_wins`` / ``override_bottom_wins`` and capture the
       resulting ``top_seed_series_win_prob``.
    4. Compare against the previous game's snapshot odds (or against the
       pre-series prior — i.e. ``simulate_series`` with no overrides — for
       Game 1) to derive ``swing_pp``.

    Returns an empty list if the series doesn't exist or no games are
    completed.
    """
    # Local import — keeps this module compatible with the same lazy-import
    # pattern used by ``simulate_series``.
    from db.models import PlayoffSeries  # type: ignore

    series = (
        db.query(PlayoffSeries)
        .filter(PlayoffSeries.series_id == series_id)
        .first()
    )
    if series is None:
        return []

    games = (
        db.query(GameLog)
        .filter(GameLog.series_id == series_id)
        .order_by(GameLog.series_game_num.asc(), GameLog.game_date.asc())
        .all()
    )

    completed_games: List[GameLog] = [
        g
        for g in games
        if g.home_score is not None
        and g.away_score is not None
        and g.series_game_num is not None
    ]
    if not completed_games:
        return []

    top_id = series.top_seed_team_id
    bottom_id = series.bottom_seed_team_id
    top_abbr = _team_abbr(db, top_id)
    bottom_abbr = _team_abbr(db, bottom_id)

    # Pre-series prior — overrides 0/0 forces the simulator to project the
    # series from scratch regardless of the row's persisted ``top_wins`` /
    # ``bottom_wins`` (which already reflect completed games).
    prior_sim = simulate_series(
        db,
        series_id,
        override_top_wins=0,
        override_bottom_wins=0,
    )
    previous_odds = float(prior_sim.top_seed_series_win_prob)

    points: List[SeriesOddsPoint] = []
    top_wins_after = 0
    bottom_wins_after = 0

    for game in completed_games:
        # Determine which side won this game.
        home_won = (game.home_score or 0) > (game.away_score or 0)
        winner_team_id = game.home_team_id if home_won else game.away_team_id
        if winner_team_id == top_id:
            top_wins_after += 1
            winner_abbr = top_abbr or ""
        elif winner_team_id == bottom_id:
            bottom_wins_after += 1
            winner_abbr = bottom_abbr or ""
        else:
            # Game references a team not part of the series — skip rather than
            # corrupt the snapshot.
            continue

        # Snapshot simulator: re-project AS IF only games up to here had been
        # played. ``simulate_series`` clamps wins and short-circuits when one
        # side has already reached 4 — it returns the deterministic terminal
        # 1.0/0.0 in that case, which is exactly what we want.
        snapshot = simulate_series(
            db,
            series_id,
            override_top_wins=top_wins_after,
            override_bottom_wins=bottom_wins_after,
        )
        odds_after = float(snapshot.top_seed_series_win_prob)
        swing_pp = odds_after - previous_odds

        points.append(
            SeriesOddsPoint(
                game_num=int(game.series_game_num or 0),
                date=game.game_date.isoformat() if game.game_date else "",
                winner_team_abbr=winner_abbr,
                top_seed_post_game_odds=round(odds_after, 4),
                swing_pp=round(swing_pp, 4),
            )
        )

        previous_odds = odds_after

    return points
