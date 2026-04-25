"""Shot Profile Diagnosis — Sprint 67 / Stream B (B5).

Pure layer over `shot_intelligence_service` outputs. Given pre-built
`ShotQualityResponse`, `ShotCreationResponse`, and (optionally) archetype z-scores,
produces a structured diagnosis with graded tags, sustainability + creation-burden
labels, and a one-sentence headline.

Taxonomy lives in `specs/sprint-67-archetype-rules.md` §2.2–§2.6. No new DB
tables; no changes to `shot_quality_baselines` or Alembic 0008.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from models.shot_diagnosis import (
    CreationBurden,
    ShotDiagnosisEvidence,
    ShotDiagnosisGrade,
    ShotDiagnosisResponse,
    ShotDiagnosisSentiment,
    ShotDiagnosisTag,
    ShotSampleConfidence,
    Sustainability,
)
from models.shotchart import ShotCreationResponse, ShotQualityResponse


METHODOLOGY_VERSION = "shot_diagnosis_v1"
MIN_SHOTS_FOR_DIAGNOSIS = 50

# Per-tag ranking weights (spec §2.3).
_CONFIDENCE_WEIGHT: Dict[str, float] = {"high": 1.0, "medium": 0.7, "low": 0.4}

# Corner-3 detection
_CORNER_ZONES = {"Left Corner 3", "Right Corner 3"}


def _safe_abs(value: Optional[float]) -> float:
    return abs(value) if value is not None and math.isfinite(value) else 0.0


def _grade_from_confidence(sentiment: ShotDiagnosisSentiment, confidence: ShotSampleConfidence) -> ShotDiagnosisGrade:
    """Spec §2.3 grade cutoffs. Neutral tags never emit red."""
    if confidence == "high":
        return "green" if sentiment != "risk" else "red"
    if confidence == "medium":
        return "yellow" if sentiment != "risk" else "red"
    # low confidence
    return "yellow" if sentiment != "risk" else "yellow"


def _zones_by_basic(quality: ShotQualityResponse, zone_basic: str) -> List:
    return [z for z in quality.zones if z.zone_basic == zone_basic]


def _zone_totals(quality: ShotQualityResponse, zone_basics: set) -> Tuple[int, float]:
    """Return (total_attempts, total_frequency) across named zone_basics."""
    rows = [z for z in quality.zones if z.zone_basic in zone_basics]
    attempts = sum(z.attempts for z in rows)
    frequency = sum(z.frequency for z in rows)
    return attempts, frequency


def _creation_split(creation: Optional[ShotCreationResponse], split_key: str):
    if creation is None:
        return None
    for split in creation.splits:
        if split.split_key == split_key:
            return split
    return None


# --- Tag rules --------------------------------------------------------------
# Each rule returns an Optional[ShotDiagnosisTag]. A rule that doesn't fire
# returns None; its evidence was not present.


def _tag_elite_corner_gravity(quality: ShotQualityResponse) -> Optional[ShotDiagnosisTag]:
    best = None
    for zone in quality.zones:
        if zone.zone_basic not in _CORNER_ZONES:
            continue
        if zone.attempts < 15:
            continue
        if zone.pps_delta is None or zone.pps_delta < 0.10:
            continue
        if best is None or (zone.pps_delta or 0) > (best.pps_delta or 0):
            best = zone
    if best is None:
        return None
    conf: ShotSampleConfidence = best.sample_confidence if best.sample_confidence in ("high", "medium", "low") else "low"  # type: ignore[assignment]
    return ShotDiagnosisTag(
        key="elite_corner_gravity",
        label="Elite corner gravity",
        sentiment="strength",
        grade=_grade_from_confidence("strength", conf),
        sample_confidence=conf,
        evidence=[ShotDiagnosisEvidence(
            metric="zone.pps_delta", value=best.actual_pps, delta=best.pps_delta,
            zone=best.zone_basic, note="Corner 3s going down well above league expected.",
        )],
    )


def _tag_dead_corners(quality: ShotQualityResponse, size_inches: Optional[int]) -> Optional[ShotDiagnosisTag]:
    # Bigs aren't expected to take corner 3s; only flag when a perimeter player.
    if size_inches is not None and size_inches >= 80:
        return None
    _, corner_freq = _zone_totals(quality, _CORNER_ZONES)
    if corner_freq > 0.04:
        return None
    # Need at least some signal from a non-trivial 3PT sample to be meaningful.
    _, three_freq = _zone_totals(quality, {"Above the Break 3", "Left Corner 3", "Right Corner 3"})
    if three_freq < 0.15:
        return None
    return ShotDiagnosisTag(
        key="dead_corners",
        label="Dead corners",
        sentiment="risk",
        grade="red",
        sample_confidence="medium",
        evidence=[ShotDiagnosisEvidence(
            metric="corner_frequency", value=corner_freq,
            note="Rarely attempts corner 3s despite being a perimeter player.",
        )],
    )


def _tag_midrange_dependency(quality: ShotQualityResponse) -> Optional[ShotDiagnosisTag]:
    _, mid_freq = _zone_totals(quality, {"Mid-Range"})
    if mid_freq < 0.25:
        return None
    return ShotDiagnosisTag(
        key="midrange_dependency",
        label="Mid-range heavy",
        sentiment="risk",
        grade="yellow" if mid_freq < 0.35 else "red",
        sample_confidence="medium",
        evidence=[ShotDiagnosisEvidence(
            metric="midrange_frequency", value=mid_freq,
            note="Over a quarter of his attempts come from the mid-range.",
        )],
    )


def _tag_rim_pressure_elite(quality: ShotQualityResponse) -> Optional[ShotDiagnosisTag]:
    restricted = [z for z in quality.zones if z.zone_basic == "Restricted Area"]
    if not restricted:
        return None
    total_attempts = sum(z.attempts for z in restricted)
    total_freq = sum(z.frequency for z in restricted)
    if total_attempts < 40 or total_freq < 0.30:
        return None
    # Weighted average of fg_pct_delta across the restricted-area rows
    deltas = [z.fg_pct_delta for z in restricted if z.fg_pct_delta is not None]
    if not deltas:
        return None
    avg_delta = sum(deltas) / len(deltas)
    if avg_delta < 0.03:
        return None
    # Prefer "high" zone confidence if any zone is high; else average.
    confidences = [z.sample_confidence for z in restricted]
    conf: ShotSampleConfidence = "high" if "high" in confidences else ("medium" if "medium" in confidences else "low")  # type: ignore[assignment]
    return ShotDiagnosisTag(
        key="rim_pressure_elite",
        label="Elite rim pressure",
        sentiment="strength",
        grade=_grade_from_confidence("strength", conf),
        sample_confidence=conf,
        evidence=[ShotDiagnosisEvidence(
            metric="restricted_area.fg_pct_delta", value=total_freq, delta=avg_delta,
            zone="Restricted Area",
            note="Heavy rim diet, finishing above what the sample expects.",
        )],
    )


def _tag_rim_finishing_variance(quality: ShotQualityResponse) -> Optional[ShotDiagnosisTag]:
    restricted = [z for z in quality.zones if z.zone_basic == "Restricted Area"]
    total_attempts = sum(z.attempts for z in restricted)
    if total_attempts < 40:
        return None
    deltas = [z.fg_pct_delta for z in restricted if z.fg_pct_delta is not None]
    if not deltas:
        return None
    avg_delta = sum(deltas) / len(deltas)
    if avg_delta > -0.05:
        return None
    return ShotDiagnosisTag(
        key="rim_finishing_variance",
        label="Finishing below average at the rim",
        sentiment="risk",
        grade="red",
        sample_confidence="medium",
        evidence=[ShotDiagnosisEvidence(
            metric="restricted_area.fg_pct_delta", delta=avg_delta,
            zone="Restricted Area",
            note="Finishing at the rim below what the sample expects.",
        )],
    )


def _tag_three_point_volume_low(quality: ShotQualityResponse, size_inches: Optional[int]) -> Optional[ShotDiagnosisTag]:
    if size_inches is not None and size_inches >= 80:
        return None
    _, three_freq = _zone_totals(quality, {"Above the Break 3", "Left Corner 3", "Right Corner 3"})
    if three_freq > 0.20:
        return None
    return ShotDiagnosisTag(
        key="three_point_volume_low",
        label="Won't pull from 3",
        sentiment="risk",
        grade="yellow",
        sample_confidence="medium",
        evidence=[ShotDiagnosisEvidence(
            metric="three_point_frequency", value=three_freq,
            note="Under 20% of his attempts come from 3 despite being a perimeter player.",
        )],
    )


def _tag_long_two_diet_problem(quality: ShotQualityResponse) -> Optional[ShotDiagnosisTag]:
    mids = [z for z in quality.zones if z.zone_basic == "Mid-Range"]
    if not mids:
        return None
    total_freq = sum(z.frequency for z in mids)
    if total_freq < 0.15:
        return None
    deltas = [z.pps_delta for z in mids if z.pps_delta is not None]
    if not deltas:
        return None
    avg_delta = sum(deltas) / len(deltas)
    if avg_delta > -0.05:
        return None
    return ShotDiagnosisTag(
        key="long_two_diet_problem",
        label="Long-two habit",
        sentiment="risk",
        grade="red",
        sample_confidence="medium",
        evidence=[ShotDiagnosisEvidence(
            metric="midrange.pps_delta", value=total_freq, delta=avg_delta,
            zone="Mid-Range",
            note="High mid-range volume with efficiency below what the sample expects.",
        )],
    )


def _tag_high_ftr_creator(ftr_z: Optional[float]) -> Optional[ShotDiagnosisTag]:
    if ftr_z is None or ftr_z < 0.7:
        return None
    return ShotDiagnosisTag(
        key="high_ftr_creator",
        label="Gets to the line",
        sentiment="strength",
        grade="green" if ftr_z >= 1.0 else "yellow",
        sample_confidence="high" if ftr_z >= 1.0 else "medium",
        evidence=[ShotDiagnosisEvidence(
            metric="ftr_z", value=ftr_z,
            note="FTA/FGA ranks in the league's top tier.",
        )],
    )


def _tag_low_ftr_floor_spacer(ftr_z: Optional[float], par3_z: Optional[float]) -> Optional[ShotDiagnosisTag]:
    if ftr_z is None or par3_z is None:
        return None
    if ftr_z > -0.5 or par3_z < 0.5:
        return None
    return ShotDiagnosisTag(
        key="low_ftr_floor_spacer",
        label="Floor spacer",
        sentiment="neutral",
        grade="yellow",
        sample_confidence="medium",
        evidence=[
            ShotDiagnosisEvidence(metric="ftr_z", value=ftr_z),
            ShotDiagnosisEvidence(metric="par3_z", value=par3_z,
                                  note="Shoots threes at volume but barely gets to the line."),
        ],
    )


def _tag_catch_and_shoot_specialist(creation: Optional[ShotCreationResponse]) -> Optional[ShotDiagnosisTag]:
    assisted = _creation_split(creation, "assisted")
    if assisted is None or assisted.frequency < 0.55:
        return None
    # efg_pct_delta isn't part of ShotCreationSplit today; use raw efg_pct as a proxy
    # above ~0.55 as a "shooting well" signal. Spec says we can re-tune once the split
    # carries an explicit delta field.
    if assisted.efg_pct is None or assisted.efg_pct < 0.55:
        return None
    return ShotDiagnosisTag(
        key="catch_and_shoot_specialist",
        label="Catch-and-shoot specialist",
        sentiment="strength",
        grade="green",
        sample_confidence="high",
        evidence=[ShotDiagnosisEvidence(
            metric="assisted.efg_pct", value=assisted.efg_pct,
            note=f"{assisted.frequency:.0%} of shots are assisted, eFG {assisted.efg_pct:.0%}.",
        )],
    )


def _tag_off_dribble_heavy(creation: Optional[ShotCreationResponse]) -> Optional[ShotDiagnosisTag]:
    self_made = _creation_split(creation, "self_created")
    if self_made is None or self_made.frequency < 0.55:
        return None
    return ShotDiagnosisTag(
        key="off_dribble_heavy",
        label="Off-dribble heavy",
        sentiment="neutral",
        grade="yellow",
        sample_confidence="medium",
        evidence=[ShotDiagnosisEvidence(
            metric="self_created.frequency", value=self_made.frequency,
            note=f"{self_made.frequency:.0%} of shots are self-created off the dribble.",
        )],
    )


def _tag_heat_check_overperformance(quality: ShotQualityResponse) -> Optional[ShotDiagnosisTag]:
    pps_delta = quality.summary.pps_delta
    conf = quality.summary.confidence
    if pps_delta is None or pps_delta < 0.08:
        return None
    if conf not in ("medium", "low"):
        return None
    return ShotDiagnosisTag(
        key="heat_check_overperformance",
        label="Running hot",
        sentiment="risk",
        grade="yellow",
        sample_confidence=conf,  # type: ignore[arg-type]
        evidence=[ShotDiagnosisEvidence(
            metric="summary.pps_delta", delta=pps_delta,
            note="Running ahead of expected PPS on a thin sample — likely to regress.",
        )],
    )


# --- Sustainability + creation burden --------------------------------------


def _sustainability(quality: ShotQualityResponse) -> Sustainability:
    shots = quality.summary.shots
    if shots < MIN_SHOTS_FOR_DIAGNOSIS or quality.coverage_state in ("legacy", "missing"):
        return "Insufficient Sample"
    pps_delta = quality.summary.pps_delta or 0.0
    zone_deltas = [z.pps_delta for z in quality.zones if z.pps_delta is not None]
    # stdev across zone deltas
    if len(zone_deltas) >= 3:
        mean = sum(zone_deltas) / len(zone_deltas)
        var = sum((d - mean) ** 2 for d in zone_deltas) / len(zone_deltas)
        stdev = math.sqrt(var)
    else:
        stdev = 0.0
    noisy = stdev >= 0.10
    mean_conf = quality.summary.confidence
    if pps_delta >= 0.08 and noisy and mean_conf == "low":
        return "Hot Streak"
    if pps_delta <= -0.08 and noisy and mean_conf == "low":
        return "Cold Streak"
    return "Sustainable"


def _creation_burden(creation: Optional[ShotCreationResponse]) -> CreationBurden:
    if creation is None:
        return "Balanced"
    assisted = _creation_split(creation, "assisted")
    self_made = _creation_split(creation, "self_created")
    if assisted and assisted.frequency >= 0.55:
        return "Assisted Heavy"
    if self_made and self_made.frequency >= 0.55:
        return "Self-Created Heavy"
    return "Balanced"


def _headline(
    top_tag: Optional[ShotDiagnosisTag],
    sustainability: Sustainability,
    creation_burden: CreationBurden,
) -> str:
    if sustainability == "Insufficient Sample":
        return "Not enough tracked shots to diagnose yet."
    if top_tag is None:
        return "Balanced shot profile — nothing loud either way."
    return f"{top_tag.label} · {sustainability} · {creation_burden.lower()}."


# --- Tag ranking (spec §2.3) -----------------------------------------------


def _rank_tag_score(tag: ShotDiagnosisTag) -> float:
    """|delta| × confidence_weight. Higher = surface sooner."""
    delta_mag = 0.0
    for ev in tag.evidence:
        delta_mag = max(delta_mag, _safe_abs(ev.delta), _safe_abs(ev.value) if ev.delta is None else 0.0)
    return delta_mag * _CONFIDENCE_WEIGHT.get(tag.sample_confidence, 0.4)


def _cull_tags(tags: List[ShotDiagnosisTag], limit: int = 4) -> List[ShotDiagnosisTag]:
    # Drop noisy red risk tags; keep at most `limit` total.
    filtered = [
        t for t in tags
        if not (t.grade == "red" and t.sample_confidence == "low")
    ]
    filtered.sort(key=_rank_tag_score, reverse=True)
    return filtered[:limit]


# --- Public entry point -----------------------------------------------------


def build_shot_diagnosis(
    *,
    player_id: int,
    season: str,
    season_type: str,
    quality: ShotQualityResponse,
    creation: Optional[ShotCreationResponse] = None,
    size_inches: Optional[int] = None,
    ftr_z: Optional[float] = None,
    par3_z: Optional[float] = None,
) -> ShotDiagnosisResponse:
    """Build the diagnosis from already-computed Shot Lab responses.

    `size_inches`, `ftr_z`, and `par3_z` come from the archetype engine when
    available and gate the dead-corners, three-point-volume-low, high-ftr-creator,
    and low-ftr-floor-spacer tags. When None, those tags simply don't fire.
    """
    total_shots = quality.summary.shots
    sample_conf = quality.summary.confidence if quality.summary.confidence in ("high", "medium", "low") else "low"  # type: ignore[assignment]

    # Minimum-sample gate (spec §2.2)
    if total_shots < MIN_SHOTS_FOR_DIAGNOSIS or quality.coverage_state in ("legacy", "missing"):
        fallback = ShotDiagnosisTag(
            key="insufficient_sample",
            label="Insufficient sample",
            sentiment="risk",
            grade="red",
            sample_confidence="low",
            evidence=[ShotDiagnosisEvidence(
                metric="summary.shots", value=float(total_shots),
                note=f"Needs ≥ {MIN_SHOTS_FOR_DIAGNOSIS} tracked shots with usable coverage.",
            )],
        )
        return ShotDiagnosisResponse(
            player_id=player_id,
            season=season,
            season_type=season_type,
            methodology_version=METHODOLOGY_VERSION,
            headline="Not enough tracked shots to diagnose.",
            sustainability="Insufficient Sample",
            creation_burden=_creation_burden(creation),
            tags=[fallback],
            sample_confidence=sample_conf,
            coverage_state=quality.coverage_state,
            total_shots=total_shots,
        )

    # Run every tag rule. `None` return = rule didn't fire.
    raw_tags: List[Optional[ShotDiagnosisTag]] = [
        _tag_elite_corner_gravity(quality),
        _tag_dead_corners(quality, size_inches),
        _tag_midrange_dependency(quality),
        _tag_rim_pressure_elite(quality),
        _tag_rim_finishing_variance(quality),
        _tag_three_point_volume_low(quality, size_inches),
        _tag_long_two_diet_problem(quality),
        _tag_high_ftr_creator(ftr_z),
        _tag_low_ftr_floor_spacer(ftr_z, par3_z),
        _tag_catch_and_shoot_specialist(creation),
        _tag_off_dribble_heavy(creation),
        _tag_heat_check_overperformance(quality),
    ]
    fired = [t for t in raw_tags if t is not None]
    tags = _cull_tags(fired)

    sustainability = _sustainability(quality)
    creation_burden = _creation_burden(creation)
    headline = _headline(tags[0] if tags else None, sustainability, creation_burden)

    return ShotDiagnosisResponse(
        player_id=player_id,
        season=season,
        season_type=season_type,
        methodology_version=METHODOLOGY_VERSION,
        headline=headline,
        sustainability=sustainability,
        creation_burden=creation_burden,
        tags=tags,
        sample_confidence=sample_conf,
        coverage_state=quality.coverage_state,
        total_shots=total_shots,
    )
