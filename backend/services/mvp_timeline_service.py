from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import MvpRaceSnapshot, MvpRaceSnapshotCandidate, Player, PlayerGameLog
from models.mvp import (
    MvpTimelineMover,
    MvpTimelinePlayer,
    MvpTimelinePoint,
    MvpTimelineResponse,
)
from services.mvp_service import AVAILABLE_PROFILES, DEFAULT_PROFILE, build_mvp_race


DEFAULT_SNAPSHOT_TOP = 15
DEFAULT_MIN_GP = 20
TIMELINE_METHODOLOGY = (
    "The Voter Timeline currently runs as a value-driven weekly reconstruction from regular-season game logs. "
    "Each cutoff scores production, true shooting, availability, candidate game W-L, and last-five momentum. "
    "A future voter-style ballot simulation can layer 10-7-5-3-1 points on top of the same dated cutoffs. "
    "Impact Consensus, Gravity, clutch, and opponent-adjusted context remain current-case annotations because "
    "the platform does not yet persist dated historical source rows for those metrics."
)


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _iso(value: Optional[date]) -> str:
    return value.isoformat() if value else ""


def _round(value: Optional[float], digits: int = 1) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


def _avg(values: Iterable[Optional[float]]) -> Optional[float]:
    filtered = [float(value) for value in values if value is not None]
    return statistics.mean(filtered) if filtered else None


def _zscore_pool(values: List[Optional[float]]) -> List[float]:
    filtered = [float(value) for value in values if value is not None]
    if len(filtered) < 2:
        return [0.0 for _ in values]
    mean = statistics.mean(filtered)
    stdev = statistics.pstdev(filtered) or 1.0
    return [((float(value) - mean) / stdev) if value is not None else 0.0 for value in values]


def _display_score(raw: float) -> float:
    return round(max(0.0, min(100.0, 50.0 + raw * 16.0)), 1)


def _log_ts(row: PlayerGameLog) -> Optional[float]:
    fga = row.fga or 0
    fta = row.fta or 0
    denom = 2 * (fga + 0.44 * fta)
    return (float(row.pts or 0) / denom) if denom > 0 else None


def _played(row: PlayerGameLog) -> bool:
    return float(row.min or 0.0) > 0.0


def _weekly_cutoffs(db: Session, season: str) -> List[date]:
    start, end = (
        db.query(func.min(PlayerGameLog.game_date), func.max(PlayerGameLog.game_date))
        .filter(
            PlayerGameLog.season == season,
            PlayerGameLog.season_type == "Regular Season",
            PlayerGameLog.game_date.isnot(None),
        )
        .one()
    )
    if start is None or end is None:
        return []
    current = start + timedelta(days=6)
    cutoffs: List[date] = []
    while current < end:
        cutoffs.append(current)
        current += timedelta(days=7)
    if not cutoffs or cutoffs[-1] != end:
        cutoffs.append(end)
    return cutoffs


def _trend_label(value: Optional[float], suffix: str = "") -> Optional[str]:
    if value is None or abs(value) < 0.05:
        return None
    return "{0:+.1f}{1}".format(value, suffix)


def _build_reasons(row: dict, previous: Optional[dict]) -> List[str]:
    reasons: List[str] = []
    if previous is None:
        reasons.append("entry/exit: Entered the voter pool at #{0}.".format(row["rank"]))
    elif previous["rank"] != row["rank"]:
        direction = "rose" if row["rank"] < previous["rank"] else "fell"
        reasons.append("entry/exit: {0} from #{1} to #{2}.".format(direction.capitalize(), previous["rank"], row["rank"]))
    pts_label = _trend_label(row.get("last5_pts_delta"), " PPG over last 5")
    if pts_label:
        reasons.append("scoring load: {0}".format(pts_label))
    if previous is not None and row.get("ts_pct") is not None and previous.get("ts_pct") is not None:
        ts_label = _trend_label((row["ts_pct"] - previous["ts_pct"]) * 100.0, " TS pct pts")
        if ts_label:
            reasons.append("efficiency: {0}".format(ts_label))
    if row.get("last5_wins") is not None and row.get("last5_losses") is not None:
        reasons.append("team value: Team went {0}-{1} in last 5.".format(row["last5_wins"], row["last5_losses"]))
    if len(reasons) < 2 and row.get("games"):
        reasons.append("availability: {0} games played through cutoff.".format(row["games"]))
    return reasons[:3]


def _rank_weekly_cutoff(logs_by_player: Dict[int, List[PlayerGameLog]], cutoff: date, min_gp: int) -> List[dict]:
    rows: List[dict] = []
    for player_id, logs in logs_by_player.items():
        current_logs = [row for row in logs if row.game_date and row.game_date <= cutoff and _played(row)]
        if len(current_logs) < min_gp:
            continue
        current_logs.sort(key=lambda row: row.game_date or cutoff)
        recent = current_logs[-5:]
        games = len(current_logs)
        wins = sum(1 for row in current_logs if (row.wl or "").upper() == "W")
        losses = sum(1 for row in current_logs if (row.wl or "").upper() == "L")
        pts_pg = _avg([row.pts for row in current_logs]) or 0.0
        reb_pg = _avg([row.reb for row in current_logs]) or 0.0
        ast_pg = _avg([row.ast for row in current_logs]) or 0.0
        ts_pct = _avg([_log_ts(row) for row in current_logs])
        recent_pts = _avg([row.pts for row in recent])
        recent_ts = _avg([_log_ts(row) for row in recent])
        rows.append(
            {
                "player_id": player_id,
                "games": games,
                "wins": wins,
                "losses": losses,
                "pts_pg": pts_pg,
                "reb_pg": reb_pg,
                "ast_pg": ast_pg,
                "ts_pct": ts_pct,
                "win_pct": wins / games if games else 0.0,
                "last5_pts_delta": (recent_pts - pts_pg) if recent_pts is not None else None,
                "last5_ts_delta": (recent_ts - ts_pct) if recent_ts is not None and ts_pct is not None else None,
                "last5_wins": sum(1 for row in recent if (row.wl or "").upper() == "W"),
                "last5_losses": sum(1 for row in recent if (row.wl or "").upper() == "L"),
            }
        )
    if not rows:
        return []

    z_pts = _zscore_pool([row["pts_pg"] for row in rows])
    z_reb = _zscore_pool([row["reb_pg"] for row in rows])
    z_ast = _zscore_pool([row["ast_pg"] for row in rows])
    z_ts = _zscore_pool([row["ts_pct"] for row in rows])
    z_games = _zscore_pool([row["games"] for row in rows])
    z_win = _zscore_pool([row["win_pct"] for row in rows])
    z_momentum = _zscore_pool([
        _avg([
            row.get("last5_pts_delta"),
            (row.get("last5_ts_delta") or 0.0) * 100.0 if row.get("last5_ts_delta") is not None else None,
        ])
        for row in rows
    ])
    for index, row in enumerate(rows):
        raw_score = (
            0.32 * (_avg([z_pts[index], z_reb[index], z_ast[index]]) or 0.0)
            + 0.18 * z_ts[index]
            + 0.16 * z_games[index]
            + 0.22 * z_win[index]
            + 0.12 * z_momentum[index]
        )
        row["raw_score"] = raw_score
        row["score"] = _display_score(raw_score)
    ranked = sorted(rows, key=lambda row: row["raw_score"], reverse=True)
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    return ranked


def _pillar_scores(candidate) -> Dict[str, float]:
    return {
        key: pillar.display_score
        for key, pillar in (candidate.score_pillars or {}).items()
    }


def materialize_mvp_timeline_snapshot(
    db: Session,
    *,
    season: str,
    snapshot_date: Optional[date] = None,
    profile: str = DEFAULT_PROFILE,
    top: int = DEFAULT_SNAPSHOT_TOP,
    min_gp: int = DEFAULT_MIN_GP,
) -> MvpRaceSnapshot:
    """Persist one MVP race snapshot for a profile/date.

    The write is idempotent: rerunning a profile for the same season/date/min_gp
    updates the snapshot header and replaces candidate rows.
    """
    run_date = snapshot_date or date.today()
    response = build_mvp_race(db, season=season, top=top, min_gp=min_gp, profile=profile)
    as_of = _parse_date(response.as_of_date)
    snapshot = (
        db.query(MvpRaceSnapshot)
        .filter(
            MvpRaceSnapshot.season == season,
            MvpRaceSnapshot.snapshot_date == run_date,
            MvpRaceSnapshot.profile == profile,
            MvpRaceSnapshot.min_gp == min_gp,
        )
        .first()
    )
    if snapshot is None:
        snapshot = MvpRaceSnapshot(
            season=season,
            snapshot_date=run_date,
            profile=profile,
            min_gp=min_gp,
        )
        db.add(snapshot)
        db.flush()

    snapshot.as_of_date = as_of
    snapshot.top = top
    snapshot.scoring_profile = response.scoring_profile or ""
    snapshot.payload_summary = {
        "candidate_count": len(response.candidates),
        "weights": response.weights,
        "available_profiles": response.available_profiles,
    }

    db.query(MvpRaceSnapshotCandidate).filter(
        MvpRaceSnapshotCandidate.snapshot_id == snapshot.id
    ).delete(synchronize_session=False)

    for candidate in response.candidates:
        db.add(
            MvpRaceSnapshotCandidate(
                snapshot_id=snapshot.id,
                player_id=candidate.player_id,
                player_name=candidate.player_name,
                team_abbreviation=candidate.team_abbreviation,
                rank=candidate.rank,
                composite_score=float(candidate.composite_score),
                context_adjusted_score=_round(candidate.context_adjusted_score, 1),
                momentum=candidate.momentum,
                eligibility_status=(
                    candidate.eligibility.eligibility_status
                    if candidate.eligibility
                    else "unknown"
                ),
                impact_consensus_score=(
                    _round(candidate.impact_consensus.consensus_score, 1)
                    if candidate.impact_consensus
                    else None
                ),
                clutch_confidence=(
                    candidate.clutch_profile.confidence
                    if candidate.clutch_profile
                    else None
                ),
                gravity_score=(
                    _round(candidate.gravity_profile.overall_gravity, 1)
                    if candidate.gravity_profile
                    else None
                ),
                coverage_warning_count=(
                    len(candidate.data_coverage.warnings)
                    if candidate.data_coverage
                    else 0
                ),
                pillar_scores=_pillar_scores(candidate),
                case_summary=list((candidate.case_summary or [])[:3]),
            )
        )

    db.flush()
    return snapshot


def materialize_mvp_timeline_snapshots(
    db: Session,
    *,
    season: str,
    snapshot_date: Optional[date] = None,
    profiles: Optional[Iterable[str]] = None,
    top: int = DEFAULT_SNAPSHOT_TOP,
    min_gp: int = DEFAULT_MIN_GP,
) -> List[MvpRaceSnapshot]:
    profile_names = list(profiles or AVAILABLE_PROFILES)
    snapshots = [
        materialize_mvp_timeline_snapshot(
            db,
            season=season,
            snapshot_date=snapshot_date,
            profile=profile,
            top=top,
            min_gp=min_gp,
        )
        for profile in profile_names
    ]
    db.commit()
    return snapshots


def _snapshots_for_timeline(
    db: Session,
    *,
    season: str,
    profile: str,
    days: int,
    min_gp: int,
) -> List[MvpRaceSnapshot]:
    cutoff = date.today() - timedelta(days=max(days, 1) - 1)
    rows = (
        db.query(MvpRaceSnapshot)
        .filter(
            MvpRaceSnapshot.season == season,
            MvpRaceSnapshot.profile == profile,
            MvpRaceSnapshot.min_gp == min_gp,
            MvpRaceSnapshot.snapshot_date >= cutoff,
        )
        .order_by(MvpRaceSnapshot.snapshot_date.asc(), MvpRaceSnapshot.id.asc())
        .all()
    )
    if len(rows) >= 2:
        return rows

    # Fresh dev databases often seed snapshots with explicit historical dates.
    # Fall back to the latest N snapshots so the endpoint remains useful there.
    return (
        db.query(MvpRaceSnapshot)
        .filter(
            MvpRaceSnapshot.season == season,
            MvpRaceSnapshot.profile == profile,
            MvpRaceSnapshot.min_gp == min_gp,
        )
        .order_by(MvpRaceSnapshot.snapshot_date.desc(), MvpRaceSnapshot.id.desc())
        .limit(max(days, 2))
        .all()
    )[::-1]


def build_mvp_timeline(
    db: Session,
    *,
    season: str,
    profile: str = DEFAULT_PROFILE,
    days: int = 30,
    top: int = 8,
    min_gp: int = DEFAULT_MIN_GP,
) -> MvpTimelineResponse:
    resolved_profile = profile if profile in AVAILABLE_PROFILES else DEFAULT_PROFILE
    cutoffs = _weekly_cutoffs(db, season)
    if len(cutoffs) < 2:
        return MvpTimelineResponse(
            season=season,
            profile=resolved_profile,
            as_of_date=date.today().isoformat(),
            snapshot_count=len(cutoffs),
            horizon_start=_iso(cutoffs[0]) if cutoffs else None,
            horizon_end=_iso(cutoffs[-1]) if cutoffs else None,
            timeline_grain="weekly",
            methodology=TIMELINE_METHODOLOGY,
            players=[],
            biggest_movers=[],
            coverage_note="The voter timeline needs at least two weekly cutoffs with game-log data.",
        )

    if days:
        horizon_cutoff = cutoffs[-1] - timedelta(days=max(days, 2) - 1)
        cutoffs = [cutoff for cutoff in cutoffs if cutoff >= horizon_cutoff]
        if len(cutoffs) < 2:
            cutoffs = _weekly_cutoffs(db, season)[-2:]

    logs = (
        db.query(PlayerGameLog)
        .filter(
            PlayerGameLog.season == season,
            PlayerGameLog.season_type == "Regular Season",
            PlayerGameLog.game_date.isnot(None),
        )
        .order_by(PlayerGameLog.player_id.asc(), PlayerGameLog.game_date.asc())
        .all()
    )
    logs_by_player: Dict[int, List[PlayerGameLog]] = defaultdict(list)
    for row in logs:
        logs_by_player[row.player_id].append(row)

    ranked_by_date: Dict[date, List[dict]] = {
        cutoff: _rank_weekly_cutoff(logs_by_player, cutoff, min_gp)
        for cutoff in cutoffs
    }
    latest_date = cutoffs[-1]
    previous_date = cutoffs[-2]
    latest_rows = ranked_by_date.get(latest_date, [])[:top]
    previous_by_player = {
        row["player_id"]: row
        for row in ranked_by_date.get(previous_date, [])
    }
    player_ids = {row["player_id"] for row in latest_rows}
    players_by_id = {
        player.id: player
        for player in db.query(Player).filter(Player.id.in_(list(player_ids))).all()
    } if player_ids else {}
    current_case = {
        candidate.player_id: candidate
        for candidate in build_mvp_race(
            db,
            season=season,
            top=max(top, 15),
            min_gp=min_gp,
            profile=resolved_profile,
        ).candidates
    }

    players: List[MvpTimelinePlayer] = []
    movers: List[MvpTimelineMover] = []
    for current in latest_rows:
        player = players_by_id.get(current["player_id"])
        case = current_case.get(current["player_id"])
        previous_row = previous_by_player.get(current["player_id"])
        rank_delta = previous_row["rank"] - current["rank"] if previous_row else None
        score_delta = (
            _round(current["score"] - previous_row["score"], 1)
            if previous_row
            else None
        )
        reasons = _build_reasons(current, previous_row)
        series: List[MvpTimelinePoint] = []
        for cutoff in cutoffs:
            point = next(
                (row for row in ranked_by_date.get(cutoff, []) if row["player_id"] == current["player_id"]),
                None,
            )
            if point is None:
                continue
            series.append(
                MvpTimelinePoint(
                    date=cutoff.isoformat(),
                    rank=point["rank"],
                    score=_round(point["score"], 1) or 0.0,
                    context_adjusted_score=_round(case.context_adjusted_score, 1) if case else None,
                    pts_pg=_round(point["pts_pg"], 1),
                    reb_pg=_round(point["reb_pg"], 1),
                    ast_pg=_round(point["ast_pg"], 1),
                    ts_pct=_round(point["ts_pct"], 3),
                    wins=point["wins"],
                    losses=point["losses"],
                )
            )

        players.append(
            MvpTimelinePlayer(
                player_id=current["player_id"],
                player_name=(player.full_name if player else "Unknown Player"),
                team_abbreviation=(case.team_abbreviation if case else ""),
                current_rank=current["rank"],
                previous_rank=previous_row["rank"] if previous_row else None,
                rank_delta=rank_delta,
                current_score=_round(current["score"], 1) or 0.0,
                previous_score=_round(previous_row["score"], 1) if previous_row else None,
                score_delta=score_delta,
                current_context_adjusted_score=_round(case.context_adjusted_score, 1) if case else None,
                momentum=(case.momentum if case else "steady"),
                eligibility_status=(case.eligibility.eligibility_status if case and case.eligibility else "unknown"),
                impact_consensus_score=(
                    _round(case.impact_consensus.consensus_score, 1)
                    if case and case.impact_consensus
                    else None
                ),
                clutch_confidence=(case.clutch_profile.confidence if case and case.clutch_profile else None),
                gravity_score=(
                    _round(case.gravity_profile.overall_gravity, 1)
                    if case and case.gravity_profile
                    else None
                ),
                coverage_warning_count=(len(case.data_coverage.warnings) if case and case.data_coverage else 0),
                reasons=reasons,
                series=series,
            )
        )
        if previous_row and rank_delta:
            movers.append(
                MvpTimelineMover(
                    player_id=current["player_id"],
                    player_name=(player.full_name if player else "Unknown Player"),
                    team_abbreviation=(case.team_abbreviation if case else ""),
                    current_rank=current["rank"],
                    previous_rank=previous_row["rank"],
                    rank_delta=rank_delta,
                    score_delta=score_delta,
                    reasons=reasons,
                )
            )

    movers.sort(key=lambda row: (abs(row.rank_delta), abs(row.score_delta or 0.0)), reverse=True)
    return MvpTimelineResponse(
        season=season,
        profile=resolved_profile,
        as_of_date=latest_date.isoformat(),
        snapshot_count=len(cutoffs),
        horizon_start=cutoffs[0].isoformat(),
        horizon_end=latest_date.isoformat(),
        timeline_grain="weekly",
        methodology=TIMELINE_METHODOLOGY,
        players=players,
        biggest_movers=movers[:5],
        coverage_note=(
            "Weekly history is reconstructed from game logs. Current impact, Gravity, clutch, and coverage notes "
            "are shown as present-day context rather than historical inputs."
        ),
    )
