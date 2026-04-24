"""Scouting Summary Brief composer — Sprint 67 / Stream B (B7).

Composes five cards from the existing analytics services (archetype,
opportunity, shot diagnosis, trajectory) into a single coach-readable
payload rendered at the top of the player page.

Any source service that raises or returns no usable data causes its card to
be skipped entirely — sparse-state is worse than no card at this density.
Composition is fully server-side so confidence language stays consistent
across cards.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from db.models import Player as PlayerOrm
from models.scouting_brief import (
    ScoutingBriefCard,
    ScoutingBriefResponse,
    ScoutingCardConfidence,
)

logger = logging.getLogger(__name__)

METHODOLOGY_VERSION = "scouting_brief_v1"

# Human-readable feature labels for the Strengths/Weaknesses card.
_FEATURE_PROSE: dict = {
    "usg_z": "usage",
    "ast_rate_z": "playmaking volume",
    "par3_z": "3-point attempt rate",
    "ftr_z": "free-throw generation",
    "ts_z": "shooting efficiency",
    "stl_rate_z": "perimeter disruption",
    "blk_rate_z": "rim protection",
    "oreb_z": "offensive rebounding",
    "dbpm_z": "defensive impact",
    "obpm_z": "offensive impact",
    "fg3_pct_z": "3-point accuracy",
}


def _fmt_pct(value: Optional[float], digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.{digits}f}%"


def _fmt_float(value: Optional[float], digits: int = 1) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}"


# --- Card 1: Role ----------------------------------------------------------


def _role_card(archetype) -> Optional[ScoutingBriefCard]:
    if archetype is None or archetype.archetype_key == "developmental":
        return None
    confidence: ScoutingCardConfidence = archetype.confidence
    evidence = []
    for contributor in archetype.contributors[:3]:
        evidence.append(
            f"{contributor.label}: z={'+' if contributor.z >= 0 else ''}{contributor.z:.2f}"
            f" ({'above' if contributor.direction == 'above' else 'below'} league)"
        )
    return ScoutingBriefCard(
        card_type="role",
        title="Role",
        summary=f"{archetype.label} — {archetype.confidence} confidence",
        evidence=evidence,
        confidence=confidence,
        deep_link=f"/players/{archetype.player_id}#archetype",
    )


# --- Card 2: Strengths / Weaknesses ----------------------------------------


def _strengths_card(archetype) -> Optional[ScoutingBriefCard]:
    if archetype is None or not archetype.contributors:
        return None
    # Partition contributors by direction.
    above = [c for c in archetype.contributors if c.direction == "above"]
    below = [c for c in archetype.contributors if c.direction == "below"]
    # Pick the strongest-magnitude pair.
    above.sort(key=lambda c: abs(c.z), reverse=True)
    below.sort(key=lambda c: abs(c.z), reverse=True)
    top_up = above[0] if above else None
    top_down = below[0] if below else None
    if top_up is None and top_down is None:
        return None
    parts: List[str] = []
    if top_up is not None:
        prose = _FEATURE_PROSE.get(top_up.feature_key, top_up.label.lower())
        parts.append(f"Leans into {prose} (z={top_up.z:+.2f})")
    if top_down is not None:
        prose = _FEATURE_PROSE.get(top_down.feature_key, top_down.label.lower())
        parts.append(f"{prose.capitalize()} lags (z={top_down.z:+.2f})")
    summary = " · ".join(parts)
    evidence: List[str] = []
    for c in above[:2]:
        evidence.append(f"+ {c.label} (z={c.z:+.2f})")
    for c in below[:2]:
        evidence.append(f"− {c.label} (z={c.z:+.2f})")
    # Confidence inherits from the archetype confidence band.
    return ScoutingBriefCard(
        card_type="strengths",
        title="Strengths & weaknesses",
        summary=summary,
        evidence=evidence,
        confidence=archetype.confidence,
        deep_link=f"/players/{archetype.player_id}#archetype",
    )


# --- Card 3: Usage & Efficiency --------------------------------------------


def _usage_efficiency_card(player_id: int, opportunity_response) -> Optional[ScoutingBriefCard]:
    if opportunity_response is None:
        return None
    row = next((r for r in opportunity_response.rows if r.player_id == player_id), None)
    if row is None:
        return None
    summary = (
        f"Usage {_fmt_pct((row.usg_pct or 0) / 100.0 if row.usg_pct else None)}, "
        f"TS {_fmt_pct(row.ts_pct)} "
        f"({_fmt_float(row.cohort_percentile, 0)} pct cohort)"
    )
    evidence: List[str] = []
    evidence.append(f"Opportunity score {row.opportunity_score:+.2f}")
    if row.top_driver:
        evidence.append(f"Top driver: {row.top_driver.replace('_', ' ')}")
    if row.on_off_net is not None:
        evidence.append(f"On/off net {row.on_off_net:+.1f}")
    confidence_raw = (row.confidence or "low").lower()
    if confidence_raw not in ("high", "medium", "low"):
        confidence_raw = "low"
    return ScoutingBriefCard(
        card_type="usage_efficiency",
        title="Usage & efficiency",
        summary=summary,
        evidence=evidence,
        confidence=confidence_raw,  # type: ignore[arg-type]
        deep_link=f"/insights?tab=usage&player_id={player_id}",
    )


# --- Card 4: Shot Profile --------------------------------------------------


def _shot_profile_card(player_id: int, diagnosis) -> Optional[ScoutingBriefCard]:
    if diagnosis is None or diagnosis.sustainability == "Insufficient Sample":
        return None
    top_tags = [t for t in diagnosis.tags if t.key != "insufficient_sample"][:2]
    if not top_tags:
        return None
    summary = (
        f"{top_tags[0].label}"
        + (f" · {top_tags[1].label}" if len(top_tags) > 1 else "")
        + f" — {diagnosis.sustainability}"
    )
    evidence: List[str] = [f"Creation burden: {diagnosis.creation_burden}"]
    for tag in top_tags:
        if tag.evidence:
            ev = tag.evidence[0]
            if ev.delta is not None:
                evidence.append(f"{tag.label}: Δ{ev.delta:+.2f}")
            elif ev.value is not None:
                evidence.append(f"{tag.label}: {ev.value:.2f}")
    confidence: ScoutingCardConfidence = diagnosis.sample_confidence
    return ScoutingBriefCard(
        card_type="shot_profile",
        title="Shot profile",
        summary=summary,
        evidence=evidence,
        confidence=confidence,
        deep_link=f"/players/{player_id}#shot-lab",
    )


# --- Card 5: Trajectory ----------------------------------------------------


def _trajectory_card(player_id: int, trajectory_response) -> Optional[ScoutingBriefCard]:
    if trajectory_response is None:
        return None
    rows = list(trajectory_response.breakout_leaders) + list(trajectory_response.decline_watch)
    row = next((r for r in rows if r.player_id == player_id), None)
    if row is None:
        return None
    summary = f"{row.trajectory_label} — {row.narrative}"
    evidence: List[str] = []
    for driver in row.driver_contributions[:2]:
        evidence.append(f"{driver.signal.replace('_', ' ')}: {driver.weighted_contribution:+.2f}")
    # Trajectory doesn't surface a per-player confidence; use position-percentile
    # magnitude as a loose stand-in.
    pct = row.position_percentile or 50.0
    conf: ScoutingCardConfidence = "high" if pct >= 80 or pct <= 20 else "medium"
    return ScoutingBriefCard(
        card_type="trajectory",
        title="Trajectory",
        summary=summary,
        evidence=evidence,
        confidence=conf,
        deep_link=f"/insights?tab=trajectory&player_id={player_id}",
    )


# --- Entry point -----------------------------------------------------------


def build_scouting_brief(
    db: Session,
    player_id: int,
    season: str,
) -> ScoutingBriefResponse:
    """Compose the five-card brief for a single player-season.

    Each card is built independently — failures of one source service don't
    propagate. Warnings list captures any skipped cards for debugging.
    """
    warnings: List[str] = []
    cards: List[ScoutingBriefCard] = []

    # 1 + 2 — Archetype powers both Role and Strengths cards.
    archetype = None
    try:
        from services.player_archetype_service import classify_player_archetype
        archetype = classify_player_archetype(db, player_id, season)
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("scouting-brief: archetype load failed for player %s", player_id)
        warnings.append(f"archetype: {exc}")

    role_card = _role_card(archetype)
    if role_card is not None:
        cards.append(role_card)
    else:
        warnings.append("role: archetype unavailable or developmental")

    strengths_card = _strengths_card(archetype)
    if strengths_card is not None:
        cards.append(strengths_card)
    else:
        warnings.append("strengths: no contributors available")

    # 3 — Opportunity (whole-league report; filter to subject).
    opportunity_response = None
    try:
        from services.opportunity_service import build_opportunity_report
        # Pull the subject's team to keep the pool small; fall back to ALL if missing.
        player = db.query(PlayerOrm).filter(PlayerOrm.id == player_id).first()
        team_abbr = None
        if player is not None and player.team is not None:
            team_abbr = player.team.abbreviation
        opportunity_response = build_opportunity_report(
            db=db, season=season, team=team_abbr, min_minutes=15.0,
        )
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("scouting-brief: opportunity load failed for player %s", player_id)
        warnings.append(f"usage_efficiency: {exc}")

    usage_card = _usage_efficiency_card(player_id, opportunity_response)
    if usage_card is not None:
        cards.append(usage_card)
    else:
        warnings.append("usage_efficiency: player not in opportunity pool")

    # 4 — Shot diagnosis.
    diagnosis = None
    try:
        from db.models import PlayerShotChart
        from services.shot_diagnosis_service import build_shot_diagnosis
        from services.shot_intelligence_service import (
            build_shot_creation_response,
            build_shot_quality_response,
        )
        from services.shot_lab_service import enrich_player_shot_payload

        cached = (
            db.query(PlayerShotChart)
            .filter(
                PlayerShotChart.player_id == player_id,
                PlayerShotChart.season == season,
                PlayerShotChart.season_type == "Regular Season",
            )
            .first()
        )
        if cached is not None:
            available_shots = enrich_player_shot_payload(db, player_id, cached.shots or [])
            from datetime import datetime
            quality = build_shot_quality_response(
                db,
                subject_type="player",
                subject_id=player_id,
                season=season,
                season_type="Regular Season",
                filtered_shots=available_shots,
                available_shots=available_shots,
                data_status=(
                    "fresh" if cached.last_synced_at and (datetime.utcnow() - cached.last_synced_at).days < 2
                    else "stale"
                ),
                start_date=None,
                end_date=None,
                period_bucket="all",
                result="all",
                shot_value="all",
            )
            creation = build_shot_creation_response(
                db,
                subject_type="player",
                subject_id=player_id,
                season=season,
                season_type="Regular Season",
                filtered_shots=available_shots,
                available_shots=available_shots,
                data_status=(
                    "fresh" if cached.last_synced_at and (datetime.utcnow() - cached.last_synced_at).days < 2
                    else "stale"
                ),
                start_date=None,
                end_date=None,
                period_bucket="all",
                result="all",
                shot_value="all",
            )
            size_inches = None
            ftr_z = None
            par3_z = None
            if archetype is not None:
                from services.player_archetype_service import parse_height_to_inches
                size_inches = parse_height_to_inches(player.height) if player else None
                for c in archetype.contributors:
                    if c.feature_key == "ftr_z":
                        ftr_z = c.z
                    elif c.feature_key == "par3_z":
                        par3_z = c.z
            diagnosis = build_shot_diagnosis(
                player_id=player_id,
                season=season,
                season_type="Regular Season",
                quality=quality,
                creation=creation,
                size_inches=size_inches,
                ftr_z=ftr_z,
                par3_z=par3_z,
            )
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("scouting-brief: shot diagnosis failed for player %s", player_id)
        warnings.append(f"shot_profile: {exc}")

    shot_card = _shot_profile_card(player_id, diagnosis)
    if shot_card is not None:
        cards.append(shot_card)
    else:
        warnings.append("shot_profile: insufficient shot sample or no tags fired")

    # 5 — Trajectory (season-restricted in the current service).
    trajectory_response = None
    try:
        from services.trajectory_service import build_trajectory_report
        trajectory_response = build_trajectory_report(
            db=db,
            season=season,
            last_n_games=10,
            player_pool="all",
            min_minutes_per_game=15.0,
        )
    except Exception as exc:  # pragma: no cover — trajectory service raises HTTPException for old seasons
        warnings.append(f"trajectory: {exc}")

    trajectory_card = _trajectory_card(player_id, trajectory_response)
    if trajectory_card is not None:
        cards.append(trajectory_card)
    else:
        if not any(w.startswith("trajectory:") for w in warnings):
            warnings.append("trajectory: player not in breakout/decline lists")

    return ScoutingBriefResponse(
        player_id=player_id,
        season=season,
        methodology_version=METHODOLOGY_VERSION,
        cards=cards,
        warnings=warnings,
    )
