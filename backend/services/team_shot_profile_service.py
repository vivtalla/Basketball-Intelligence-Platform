from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import Team, TeamShootingSplitStat
from models.styles import StyleShotProfileDriver

_SHOOTING_DRIVER_CANDIDATE_FAMILIES = {
    "ShotAreaTeamDashboard",
    "ShotTypeTeamDashboard",
    "Shot8FTTeamDashboard",
    "Shot5FTTeamDashboard",
    "AssitedShotTeamDashboard",
}

_SHOOTING_FAMILY_LABELS = {
    "ShotAreaTeamDashboard": "Shot Area",
    "ShotTypeTeamDashboard": "Shot Type",
    "Shot8FTTeamDashboard": "Shot Distance (8ft)",
    "Shot5FTTeamDashboard": "Shot Distance (5ft)",
    "AssitedShotTeamDashboard": "Assisted Shot",
    "OverallTeamDashboard": "Overall",
}

_SHOOTING_FAMILY_TRUST = {
    "AssitedShotTeamDashboard": (
        "caution",
        "Official assisted-shot semantics still look ambiguous upstream, so treat this family as directional only.",
    ),
}


def _safe_round(value: Optional[float], digits: int = 2) -> Optional[float]:
    if value is None:
        return None
    return round(value, digits)


def family_label(split_family: str) -> str:
    return _SHOOTING_FAMILY_LABELS.get(split_family, split_family)


def family_trust(split_family: str) -> Tuple[str, Optional[str], bool]:
    level, note = _SHOOTING_FAMILY_TRUST.get(split_family, ("strong", None))
    return level, note, level != "caution"


def attempt_share_text(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return "{0:.1f}%".format(value * 100.0)


def pct_text(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return "{0:.1f}%".format(value * 100.0)


def signed_points_text(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return "{0}{1:.1f} pts".format("+" if value >= 0 else "", value * 100.0)


def build_team_shot_profile_drivers(
    db: Session,
    season: str,
    team_id: int,
    limit: int = 4,
) -> Tuple[List[StyleShotProfileDriver], List[Dict[str, Any]]]:
    rows = (
        db.query(TeamShootingSplitStat)
        .filter(
            TeamShootingSplitStat.season == season,
            TeamShootingSplitStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    if not rows:
        return [], []

    overall_attempts: Dict[int, float] = {}
    for row in rows:
        if row.split_family == "OverallTeamDashboard" and row.fga is not None:
            overall_attempts[row.team_id] = float(row.fga)

    current_candidates: List[Dict[str, Any]] = []
    for row in rows:
        if row.team_id != team_id or row.split_family not in _SHOOTING_DRIVER_CANDIDATE_FAMILIES:
            continue
        team_total = overall_attempts.get(team_id)
        if not team_total or team_total <= 0 or row.fga is None or row.fga < 40:
            continue
        peer_rows = [
            other
            for other in rows
            if other.team_id != team_id
            and other.split_family == row.split_family
            and other.split_value == row.split_value
            and other.fga is not None
            and overall_attempts.get(other.team_id, 0.0) > 0
        ]
        if not peer_rows:
            continue
        attempt_share = float(row.fga) / team_total
        league_attempt_shares = [
            float(other.fga) / overall_attempts[other.team_id]
            for other in peer_rows
            if overall_attempts.get(other.team_id)
        ]
        league_efg_values = [float(other.efg_pct) for other in peer_rows if other.efg_pct is not None]
        if not league_attempt_shares:
            continue
        league_attempt_share = statistics.mean(league_attempt_shares)
        league_efg_pct = statistics.mean(league_efg_values) if league_efg_values else None
        volume_delta = attempt_share - league_attempt_share
        efg_delta = None
        if row.efg_pct is not None and league_efg_pct is not None:
            efg_delta = float(row.efg_pct) - league_efg_pct
        trust_level, trust_note, strong_claim = family_trust(row.split_family)
        current_candidates.append(
            {
                "key": (row.split_family, row.split_value),
                "split_family": row.split_family,
                "split_value": row.split_value,
                "label": row.label,
                "attempt_share": attempt_share,
                "efg_pct": float(row.efg_pct) if row.efg_pct is not None else None,
                "league_attempt_share": league_attempt_share,
                "league_efg_pct": league_efg_pct,
                "volume_delta": volume_delta,
                "efg_delta": efg_delta,
                "fga": float(row.fga),
                "pct_ast_fgm": float(row.pct_ast_fgm) if row.pct_ast_fgm is not None else None,
                "pct_uast_fgm": float(row.pct_uast_fgm) if row.pct_uast_fgm is not None else None,
                "trust_level": trust_level,
                "trust_note": trust_note,
                "strong_claim": strong_claim,
                "row": row,
            }
        )

    if not current_candidates:
        return [], []

    selected: List[Dict[str, Any]] = []
    seen = set()
    volume_sorted = sorted(
        current_candidates,
        key=lambda item: (abs(item["volume_delta"]), item["fga"]),
        reverse=True,
    )
    efficiency_sorted = sorted(
        [item for item in current_candidates if item["efg_delta"] is not None],
        key=lambda item: (abs(item["efg_delta"]), item["fga"]),
        reverse=True,
    )
    for candidate_list in (volume_sorted[:2], efficiency_sorted[:2], volume_sorted[2:], efficiency_sorted[2:]):
        for candidate in candidate_list:
            if candidate["key"] in seen:
                continue
            seen.add(candidate["key"])
            selected.append(candidate)
            if len(selected) >= limit:
                break
        if len(selected) >= limit:
            break

    drivers: List[StyleShotProfileDriver] = []
    for candidate in selected:
        volume_delta = candidate["volume_delta"]
        efg_delta = candidate["efg_delta"]
        if efg_delta is not None and abs(efg_delta) >= abs(volume_delta):
            league_delta = efg_delta
        else:
            league_delta = volume_delta
        summary_parts = [
            "{0} shots".format(family_label(candidate["split_family"])),
            "take {0} of attempts vs league {1}".format(
                attempt_share_text(candidate["attempt_share"]),
                attempt_share_text(candidate["league_attempt_share"]),
            ),
        ]
        if candidate["efg_pct"] is not None and candidate["league_efg_pct"] is not None:
            summary_parts.append(
                "and post {0} eFG vs league {1}".format(
                    pct_text(candidate["efg_pct"]),
                    pct_text(candidate["league_efg_pct"]),
                )
            )
        drivers.append(
            StyleShotProfileDriver(
                split_family=candidate["split_family"],
                family_label=family_label(candidate["split_family"]),
                split_value=candidate["split_value"],
                label=candidate["label"],
                attempt_share=_safe_round(candidate["attempt_share"], 3),
                efg_pct=_safe_round(candidate["efg_pct"], 3) if candidate["efg_pct"] is not None else None,
                league_delta=_safe_round(league_delta, 3),
                summary=" ".join(summary_parts) + ".",
                trust_level=candidate["trust_level"],
                trust_note=candidate["trust_note"],
                strong_claim=candidate["strong_claim"],
            )
        )
    return drivers, selected


def summarize_neighbor_shot_profile(
    current_team_abbr: str,
    neighbor: Team,
    candidate: Dict[str, Any],
    neighbor_row: Optional[TeamShootingSplitStat],
    neighbor_total_attempts: Optional[float],
) -> Optional[str]:
    if not neighbor_row or not neighbor_total_attempts or neighbor_row.fga is None:
        return None
    current_share = candidate["attempt_share"]
    neighbor_share = float(neighbor_row.fga) / neighbor_total_attempts
    share_gap = current_share - neighbor_share
    current_efg = candidate["efg_pct"]
    neighbor_efg = float(neighbor_row.efg_pct) if neighbor_row.efg_pct is not None else None
    efg_gap = None
    if current_efg is not None and neighbor_efg is not None:
        efg_gap = current_efg - neighbor_efg

    if abs(share_gap) <= 0.02 and (efg_gap is None or abs(efg_gap) <= 0.02):
        return "Shared shot-profile note: both teams sit near each other on {0} volume and efficiency.".format(candidate["label"])
    if abs(share_gap) >= (abs(efg_gap) if efg_gap is not None else 0.0):
        return "{0} leans {1} harder into {2} than {3} ({4} vs {5} of attempts).".format(
            current_team_abbr,
            "more" if share_gap > 0 else "less",
            candidate["label"],
            neighbor.abbreviation,
            attempt_share_text(current_share),
            attempt_share_text(neighbor_share),
        )
    if efg_gap is not None:
        return "{0} is {1} efficient than {2} on {3} ({4} vs {5} eFG).".format(
            current_team_abbr,
            "more" if efg_gap > 0 else "less",
            neighbor.abbreviation,
            candidate["label"],
            pct_text(current_efg),
            pct_text(neighbor_efg),
        )
    return None
