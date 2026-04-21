from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import Player, PlayerShotChart, ShotQualityBaseline, Team
from models.shotchart import (
    ShotIntelligenceOpsBaseline,
    ShotIntelligenceOpsPlayer,
    ShotIntelligenceOpsResponse,
    ShotIntelligenceOpsTeam,
)
from services.shot_intelligence_service import METHODOLOGY_VERSION
from services.shot_lab_service import summarize_shot_completeness

STALE_AFTER_HOURS = 36


def _iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _player_state(summary_status: str, data_status: str) -> str:
    if data_status == "missing":
        return "missing"
    if data_status == "stale":
        return "stale"
    return summary_status  # "ready" | "partial" | "legacy"


def _team_readiness(counts: Dict[str, int]) -> str:
    if counts["total"] == 0:
        return "missing"
    if counts["ready"] == counts["total"]:
        return "ready"
    if counts["ready"] + counts["partial"] >= max(1, counts["total"] // 2):
        return "partial"
    if counts["stale"] > 0:
        return "stale"
    return "missing"


def build_shot_intelligence_ops(
    db: Session,
    season: str,
    season_type: str = "Regular Season",
    methodology_version: str = METHODOLOGY_VERSION,
    stale_after_hours: int = STALE_AFTER_HOURS,
) -> ShotIntelligenceOpsResponse:
    """Aggregate shot intelligence readiness across rostered players.

    Joins rostered Players (team_id not null) to their PlayerShotChart row for
    (season, season_type). Summarizes completeness per player, rolls up to teams,
    and reports baseline materialization state.
    """
    now = datetime.utcnow()
    stale_cutoff = now - timedelta(hours=stale_after_hours)

    team_rows = {t.id: t for t in db.query(Team).all()}
    players = (
        db.query(Player)
        .filter(Player.team_id.isnot(None))
        .filter(Player.is_active.is_(True))
        .all()
    )
    shot_rows = {
        row.player_id: row
        for row in db.query(PlayerShotChart)
        .filter(
            PlayerShotChart.season == season,
            PlayerShotChart.season_type == season_type,
        )
        .all()
    }

    team_buckets: Dict[int, Dict[str, int]] = defaultdict(
        lambda: {
            "total": 0,
            "ready": 0,
            "partial": 0,
            "legacy": 0,
            "stale": 0,
            "missing": 0,
        }
    )
    stale_players: List[ShotIntelligenceOpsPlayer] = []
    missing_histogram: Counter = Counter()
    totals = {
        "roster": 0,
        "ready": 0,
        "partial": 0,
        "legacy": 0,
        "stale": 0,
        "missing": 0,
    }

    for player in players:
        team = team_rows.get(player.team_id)
        row = shot_rows.get(player.id)
        shots = (row.shots or []) if row is not None else []
        summary = summarize_shot_completeness(shots)

        if row is None:
            data_status = "missing"
        elif row.fetched_at and row.fetched_at < stale_cutoff:
            data_status = "stale"
        else:
            data_status = "fresh"

        state = _player_state(summary.status, data_status)
        bucket = team_buckets[player.team_id]
        bucket["total"] += 1
        bucket[state] = bucket.get(state, 0) + 1
        totals["roster"] += 1
        totals[state] = totals.get(state, 0) + 1

        for field in summary.missing_context_fields or []:
            missing_histogram[field] += 1

        if state in ("stale", "missing") or summary.status != "ready":
            ops_player = ShotIntelligenceOpsPlayer(
                player_id=player.id,
                player_name=player.full_name,
                team_id=player.team_id,
                team_abbreviation=team.abbreviation if team else None,
                state=state,
                data_status=data_status,
                total_shots=summary.total_shots,
                linked_shots=summary.linked_shots,
                exact_linked_shots=summary.exact_linked_shots,
                missing_context_fields=summary.missing_context_fields,
                last_synced_at=_iso(row.fetched_at) if row else None,
            )
            if state in ("stale", "missing"):
                stale_players.append(ops_player)

    teams: List[ShotIntelligenceOpsTeam] = []
    for team_id, counts in team_buckets.items():
        team = team_rows.get(team_id)
        if team is None:
            continue
        teams.append(
            ShotIntelligenceOpsTeam(
                team_id=team_id,
                team_abbreviation=team.abbreviation,
                team_name=team.name,
                readiness=_team_readiness(counts),
                roster_size=counts["total"],
                ready_count=counts.get("ready", 0),
                partial_count=counts.get("partial", 0),
                legacy_count=counts.get("legacy", 0),
                stale_count=counts.get("stale", 0),
                missing_count=counts.get("missing", 0),
            )
        )
    teams.sort(key=lambda t: t.team_abbreviation)
    stale_players.sort(key=lambda p: (p.team_abbreviation or "", p.player_name))

    baseline_row = (
        db.query(ShotQualityBaseline)
        .filter(
            ShotQualityBaseline.season == season,
            ShotQualityBaseline.season_type == season_type,
            ShotQualityBaseline.methodology_version == methodology_version,
        )
        .one_or_none()
    )
    if baseline_row is None:
        baseline_status = "missing"
        sample_n = 0
        computed_at: Optional[str] = None
    elif baseline_row.computed_at and baseline_row.computed_at < stale_cutoff:
        baseline_status = "stale"
        sample_n = baseline_row.sample_n
        computed_at = _iso(baseline_row.computed_at)
    else:
        baseline_status = "ready"
        sample_n = baseline_row.sample_n
        computed_at = _iso(baseline_row.computed_at)

    baseline = ShotIntelligenceOpsBaseline(
        season=season,
        season_type=season_type,
        methodology_version=methodology_version,
        status=baseline_status,
        sample_n=sample_n,
        computed_at=computed_at,
    )

    return ShotIntelligenceOpsResponse(
        season=season,
        season_type=season_type,
        methodology_version=methodology_version,
        teams=teams,
        stale_players=stale_players,
        missing_context_histogram=dict(missing_histogram),
        baseline=baseline,
        totals=totals,
    )
