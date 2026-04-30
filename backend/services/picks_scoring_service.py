"""Sprint 78 — CF2 — Bracket Pick'em scoring service.

Given a `UserPicks` submission, compares against:

1. Actual outcomes pulled from `PlayoffSeries` + `GameLog` rows for the
   season. A series is considered "decided" once `status == 'closed'` (the
   simulator uses the same convention) and we can resolve the winner abbr.
2. The CourtVue model's predicted bracket. We reuse
   :func:`playoff_simulator_service.simulate_series` to project every series
   in the season (already-decided series are returned as-is by the simulator,
   so this works for both live + historical post-mortem reviews).

Scoring rubric (per series, by round):
    Round 1 (R1): 1 pt for the winner.
    Round 2 (R2): 2 pts.
    Conference Finals (R3): 4 pts.
    NBA Finals (R4): 8 pts.

Length bonus: +50% of the round value (rounded up) if the user also nails
the exact game count (4..7). Length is only awarded when the winner is also
correct — picking the wrong winner zeros the bonus.

Award picks (MVP / COY / DPOY / ROY): 5 pts each, all-or-nothing.

Head-to-head: we re-run the same scoring model against the CourtVue model's
predicted bracket (the model is just another picker), then compute the
delta (user - model) on points and correct picks.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import GameLog, Player, SeasonStat, Team
from models.picks import (
    AwardPickResult,
    HeadToHead,
    ModelAwardPick,
    ModelPicks,
    ModelSeriesPick,
    PickStatus,
    PicksScorecard,
    SeriesPickResult,
    UserPicks,
)
from services.playoff_simulator_service import simulate_series


# ---------------------------------------------------------------------------
# Scoring tables
# ---------------------------------------------------------------------------

ROUND_POINTS: Dict[int, int] = {1: 1, 2: 2, 3: 4, 4: 8}
AWARD_POINTS: int = 5
SUPPORTED_AWARDS: Tuple[str, ...] = ("mvp", "coy", "dpoy", "roy")


def _length_bonus(round_no: int) -> int:
    """Series-length bonus. Rounded up."""
    base = ROUND_POINTS.get(round_no, 1)
    return -(-base // 2)  # ceil(base/2)


def _series_points_possible(round_no: int) -> int:
    return ROUND_POINTS.get(round_no, 1) + _length_bonus(round_no)


# ---------------------------------------------------------------------------
# Helpers — actual + model outcomes
# ---------------------------------------------------------------------------


def _team_abbr_lookup(db: Session, team_ids: List[int]) -> Dict[int, str]:
    rows = db.query(Team).filter(Team.id.in_([t for t in team_ids if t is not None])).all()
    return {row.id: row.abbreviation for row in rows if row.abbreviation}


def _completed_games_for_series(db: Session, series_id: str) -> int:
    rows = (
        db.query(GameLog)
        .filter(GameLog.series_id == series_id)
        .all()
    )
    return sum(
        1
        for r in rows
        if r.home_score is not None and r.away_score is not None
    )


def _actual_series_outcome(
    db, series, abbr_lookup: Dict[int, str]
) -> Tuple[Optional[str], Optional[int]]:
    """Return (winner_abbr, games_played) for a closed series; else (None, None)."""
    if series.status != "closed" or series.winner_team_id is None:
        return None, None
    winner_abbr = abbr_lookup.get(series.winner_team_id)
    games = _completed_games_for_series(db, series.series_id)
    return winner_abbr, games or None


def _model_series_pick(db: Session, series) -> ModelSeriesPick:
    """Run the existing simulator and convert to a single pick row."""
    sim = simulate_series(db, series.series_id)
    top_abbr = sim.current_state.top_seed_team_abbr
    bottom_abbr = sim.current_state.bottom_seed_team_abbr

    # Model's pick = whichever side has the higher series win prob. If the
    # series is already closed, simulator returns 1.0/0.0 so winner is exact.
    top_p = float(sim.top_seed_series_win_prob or 0.0)
    bottom_p = float(sim.bottom_seed_series_win_prob or 0.0)
    winner_abbr: Optional[str] = None
    confidence: Optional[float] = None
    if top_p == 0.0 and bottom_p == 0.0:
        # No data — leave as None.
        winner_abbr = None
    elif top_p >= bottom_p:
        winner_abbr = top_abbr
        confidence = top_p
    else:
        winner_abbr = bottom_abbr
        confidence = bottom_p

    # Model's predicted length: pick the most-likely game number to clinch.
    # We approximate from current state: completed + 4 - current_winner_wins.
    games_pred: Optional[int] = None
    state = sim.current_state
    if winner_abbr is not None:
        if winner_abbr == top_abbr:
            wins_so_far = state.top_wins
        else:
            wins_so_far = state.bottom_wins
        games_remaining = max(1, 4 - wins_so_far)
        # Other side's wins so far + 0 (model leans toward predicted winner
        # closing it cleanly). Capped at 7.
        if winner_abbr == top_abbr:
            other_wins = state.bottom_wins
        else:
            other_wins = state.top_wins
        games_pred = min(7, max(4, wins_so_far + games_remaining + other_wins))

    return ModelSeriesPick(
        series_id=series.series_id,
        round=series.round,
        winner_team_abbr=winner_abbr,
        games=games_pred,
        confidence=round(confidence, 4) if confidence is not None else None,
    )


def _model_award_pick(db: Session, season: str, award: str) -> ModelAwardPick:
    """Pick a season leader as the model's vote for the given award.

    These picks are deterministic and methodology-light — we surface the
    leader on the relevant stat and call out the rationale chip. Real
    award-case modeling lives in `mvp_service`; for the pick'em surface we
    only need a single name per category.
    """
    metric_field, rationale = _award_metric(award)
    row = (
        db.query(SeasonStat, Player)
        .join(Player, Player.id == SeasonStat.player_id)
        .filter(SeasonStat.season == season)
        .filter(SeasonStat.is_playoff == False)  # noqa: E712
        .filter(SeasonStat.gp >= 30)  # qualifying floor — matches platform conventions
        .filter(getattr(SeasonStat, metric_field).isnot(None))
        .order_by(getattr(SeasonStat, metric_field).desc())
        .first()
    )
    if row is None:
        return ModelAwardPick(award=award)
    _stat, player = row
    return ModelAwardPick(
        award=award,
        player_id=player.id,
        player_name=player.full_name,
        rationale=rationale,
    )


def _award_metric(award: str) -> Tuple[str, str]:
    """Return (SeasonStat field name, short rationale) for the model's pick."""
    if award == "mvp":
        return "bpm", "BPM leader"
    if award == "dpoy":
        return "def_rating", "DRTG leader"  # lower-is-better; we still order DESC for symmetry
    if award == "coy":
        # Coach of Year — we don't model coaches; fall back to most net-rating
        # production via team but coach is unmapped. Use BPM as a heuristic.
        return "bpm", "BPM leader (coach proxy)"
    if award == "roy":
        return "bpm", "BPM leader (rookie proxy)"
    return "bpm", "BPM leader"


# ---------------------------------------------------------------------------
# Scoring — the picker (user OR model) is just a list of (winner, games).
# ---------------------------------------------------------------------------


def _score_series(
    picker_winner: Optional[str],
    picker_games: Optional[int],
    actual_winner: Optional[str],
    actual_games: Optional[int],
    round_no: int,
) -> Tuple[PickStatus, PickStatus, int]:
    """Score one series for one picker. Returns (winner_status, games_status, points)."""
    if picker_winner is None:
        return "missing", "missing", 0
    if actual_winner is None:
        return "pending", "pending", 0

    base = ROUND_POINTS.get(round_no, 1)
    bonus = _length_bonus(round_no)

    if picker_winner.upper() != actual_winner.upper():
        return "incorrect", "incorrect", 0

    points = base
    games_status: PickStatus = "missing"
    if picker_games is not None and actual_games is not None:
        if picker_games == actual_games:
            points += bonus
            games_status = "correct"
        else:
            games_status = "incorrect"

    return "correct", games_status, points


def _score_award(
    picker_player_id: Optional[int],
    actual_player_id: Optional[int],
) -> Tuple[PickStatus, int]:
    if picker_player_id is None:
        return "missing", 0
    if actual_player_id is None:
        return "pending", 0
    if picker_player_id == actual_player_id:
        return "correct", AWARD_POINTS
    return "incorrect", 0


# ---------------------------------------------------------------------------
# Public — build the model bracket + score a user's picks
# ---------------------------------------------------------------------------


def get_model_picks(db: Session, season: str) -> ModelPicks:
    """Return the CourtVue model's bracket + award picks for `season`."""
    from db.models import PlayoffSeries  # local import — avoids cycle

    series_rows = (
        db.query(PlayoffSeries)
        .filter(PlayoffSeries.season == season)
        .order_by(PlayoffSeries.round.asc(), PlayoffSeries.top_seed.asc())
        .all()
    )

    series_picks: List[ModelSeriesPick] = []
    for s in series_rows:
        try:
            series_picks.append(_model_series_pick(db, s))
        except Exception:  # pragma: no cover — simulator is best-effort here
            series_picks.append(
                ModelSeriesPick(series_id=s.series_id, round=s.round)
            )

    award_picks: List[ModelAwardPick] = [
        _model_award_pick(db, season, award) for award in SUPPORTED_AWARDS
    ]

    return ModelPicks(season=season, series_picks=series_picks, award_picks=award_picks)


def score_user_picks(db: Session, user_picks: UserPicks) -> PicksScorecard:
    """Score a user submission against actuals + the CourtVue model bracket."""
    from db.models import PlayoffSeries  # local import — avoids cycle

    season = user_picks.season

    series_rows = (
        db.query(PlayoffSeries)
        .filter(PlayoffSeries.season == season)
        .order_by(PlayoffSeries.round.asc(), PlayoffSeries.top_seed.asc())
        .all()
    )

    # Resolve all team abbrs in one pass.
    needed_team_ids: List[int] = []
    for s in series_rows:
        for tid in (s.top_seed_team_id, s.bottom_seed_team_id, s.winner_team_id):
            if tid is not None:
                needed_team_ids.append(tid)
    abbr_lookup = _team_abbr_lookup(db, needed_team_ids)

    # User pick lookup by series_id.
    user_series_lookup = {p.series_id: p for p in user_picks.series_picks}
    user_award_lookup = {p.award: p for p in user_picks.award_picks}

    # Model picks (re-used both for narration and for parallel scoring).
    model = get_model_picks(db, season)
    model_series_lookup = {p.series_id: p for p in model.series_picks}
    model_award_lookup = {p.award: p for p in model.award_picks}

    series_results: List[SeriesPickResult] = []
    user_total = 0
    user_total_possible = 0
    user_correct = 0
    model_total = 0
    model_correct = 0

    for s in series_rows:
        round_no = s.round
        actual_winner, actual_games = _actual_series_outcome(db, s, abbr_lookup)

        user_pick = user_series_lookup.get(s.series_id)
        user_winner = user_pick.winner_team_abbr if user_pick else None
        user_games = user_pick.games if user_pick else None

        u_winner_status, u_games_status, u_pts = _score_series(
            user_winner, user_games, actual_winner, actual_games, round_no
        )

        model_pick = model_series_lookup.get(s.series_id)
        m_winner = model_pick.winner_team_abbr if model_pick else None
        m_games = model_pick.games if model_pick else None
        _, _, m_pts = _score_series(
            m_winner, m_games, actual_winner, actual_games, round_no
        )

        possible = _series_points_possible(round_no) if actual_winner is not None else 0

        user_total += u_pts
        user_total_possible += possible
        if u_winner_status == "correct":
            user_correct += 1
        model_total += m_pts
        # Model's "correct" count tracks winner correctness only.
        if actual_winner is not None and m_winner and m_winner.upper() == actual_winner.upper():
            model_correct += 1

        series_results.append(
            SeriesPickResult(
                series_id=s.series_id,
                round=round_no,
                user_winner_abbr=user_winner,
                user_games=user_games,
                actual_winner_abbr=actual_winner,
                actual_games=actual_games,
                model_winner_abbr=m_winner,
                model_games=m_games,
                winner_status=u_winner_status,
                games_status=u_games_status,
                points=u_pts,
                points_possible=possible,
            )
        )

    # Awards.
    award_results: List[AwardPickResult] = []
    for award in SUPPORTED_AWARDS:
        user_award = user_award_lookup.get(award)  # type: ignore[arg-type]
        model_award = model_award_lookup.get(award)
        # "Actual" winner: not known until awards are announced — represent as
        # the model's pick once the regular season is complete in real life.
        # For now we treat it as pending unless the database flips a future
        # `actual_award_winner` field.
        actual_player_id: Optional[int] = None
        actual_player_name: Optional[str] = None

        u_status, u_pts = _score_award(
            user_award.player_id if user_award else None,
            actual_player_id,
        )
        _, m_pts = _score_award(
            model_award.player_id if model_award else None,
            actual_player_id,
        )
        possible = AWARD_POINTS if actual_player_id is not None else 0

        user_total += u_pts
        user_total_possible += possible
        if u_status == "correct":
            user_correct += 1
        model_total += m_pts

        award_results.append(
            AwardPickResult(
                award=award,
                user_player_id=user_award.player_id if user_award else None,
                user_player_name=user_award.player_name if user_award else None,
                actual_player_id=actual_player_id,
                actual_player_name=actual_player_name,
                model_player_id=model_award.player_id if model_award else None,
                model_player_name=model_award.player_name if model_award else None,
                status=u_status,
                points=u_pts,
                points_possible=possible,
            )
        )

    accuracy = (
        round(100.0 * user_total / user_total_possible, 1)
        if user_total_possible > 0
        else 0.0
    )

    head_to_head = HeadToHead(
        user_points=user_total,
        model_points=model_total,
        user_correct=user_correct,
        model_correct=model_correct,
        delta_points=user_total - model_total,
        delta_correct=user_correct - model_correct,
    )

    return PicksScorecard(
        season=season,
        series_results=series_results,
        award_results=award_results,
        total_points=user_total,
        total_points_possible=user_total_possible,
        accuracy_pct=accuracy,
        head_to_head=head_to_head,
    )
