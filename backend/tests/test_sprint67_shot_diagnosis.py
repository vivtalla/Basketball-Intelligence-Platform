"""Sprint 67 (B5/B9b) — shot diagnosis service tests.

Covers:
  - minimum-sample gate (<50 shots => insufficient_sample fallback)
  - sustainability derivation (Sustainable / Hot Streak / Cold Streak / Insufficient)
  - creation burden (Assisted Heavy / Self-Created Heavy / Balanced)
  - each tag fires on a synthetic input meeting its spec trigger
  - tag ranking caps at 4 and drops red-low-confidence noise
  - headline template
"""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.shot_diagnosis import ShotDiagnosisResponse  # noqa: E402
from models.shotchart import (  # noqa: E402
    ShotCreationResponse,
    ShotCreationSplit,
    ShotIntelligenceCoverage,
    ShotLabFilterEcho,
    ShotQualityResponse,
    ShotQualitySummary,
    ShotQualityZone,
)
from services.shot_diagnosis_service import (  # noqa: E402
    METHODOLOGY_VERSION,
    MIN_SHOTS_FOR_DIAGNOSIS,
    build_shot_diagnosis,
)


def _coverage(state: str = "ready") -> ShotIntelligenceCoverage:
    return ShotIntelligenceCoverage(
        state=state,
        data_status="fresh" if state == "ready" else "stale",
        total_shots=100,
        contextual_shots=100,
        linked_shots=80,
        exact_linked_shots=60,
        derived_linked_shots=20,
        completeness_pct=1.0,
        linked_pct=0.8,
        missing_context_fields=[],
        note="mock",
    )


def _filters() -> ShotLabFilterEcho:
    return ShotLabFilterEcho(
        start_date=None, end_date=None, period_bucket="all", result="all", shot_value="all",
    )


def _summary(shots: int, actual_pps: float, expected_pps: float, confidence: str = "high") -> ShotQualitySummary:
    return ShotQualitySummary(
        shots=shots,
        actual_fg_pct=0.48,
        expected_fg_pct=0.47,
        fg_pct_delta=0.01,
        actual_efg_pct=0.55,
        expected_efg_pct=0.54,
        efg_pct_delta=0.01,
        actual_pps=actual_pps,
        expected_pps=expected_pps,
        pps_delta=actual_pps - expected_pps,
        confidence=confidence,
    )


def _zone(
    zone_basic: str, zone_area: str = "Center(C)", attempts: int = 50,
    frequency: float = 0.2, fg_pct_delta: float = 0.02, pps_delta: float = 0.02,
    sample_confidence: str = "high",
) -> ShotQualityZone:
    return ShotQualityZone(
        zone_basic=zone_basic, zone_area=zone_area,
        attempts=attempts, made=int(attempts * 0.5),
        frequency=frequency,
        actual_fg_pct=0.52, expected_fg_pct=0.52 - fg_pct_delta, fg_pct_delta=fg_pct_delta,
        actual_pps=1.05, expected_pps=1.05 - pps_delta, pps_delta=pps_delta,
        sample_confidence=sample_confidence,
    )


def _quality(
    shots: int = 300, zones=None, coverage_state: str = "ready",
    summary_pps_delta: float = 0.02, summary_confidence: str = "high",
) -> ShotQualityResponse:
    if zones is None:
        zones = [_zone("Restricted Area", frequency=0.35)]
    return ShotQualityResponse(
        subject_type="player", subject_id=1, season="2024-25", season_type="Regular Season",
        filters=_filters(), methodology_version="shot_quality_v1",
        coverage_state=coverage_state, coverage=_coverage(coverage_state),
        methodology=[],
        summary=_summary(shots, 1.0 + summary_pps_delta, 1.0, summary_confidence),
        bins=[],
        zones=zones,
    )


def _creation(assisted_freq: float, self_freq: float, assisted_efg: float = 0.58) -> ShotCreationResponse:
    return ShotCreationResponse(
        subject_type="player", subject_id=1, season="2024-25", season_type="Regular Season",
        filters=_filters(), methodology_version="shot_quality_v1",
        coverage_state="ready", coverage=_coverage("ready"),
        methodology=[],
        summary={"note": "mock"},
        splits=[
            ShotCreationSplit(
                split_key="assisted", label="Assisted", description="",
                attempts=100, made=55, frequency=assisted_freq,
                fg_pct=0.52, efg_pct=assisted_efg, pps=1.05,
                precision="linked", coverage_note="mock",
            ),
            ShotCreationSplit(
                split_key="self_created", label="Self-Created", description="",
                attempts=100, made=45, frequency=self_freq,
                fg_pct=0.45, efg_pct=0.49, pps=0.95,
                precision="linked", coverage_note="mock",
            ),
        ],
    )


# --- Sample gate ------------------------------------------------------------


def test_insufficient_sample_returns_fallback_tag():
    q = _quality(shots=30)
    result: ShotDiagnosisResponse = build_shot_diagnosis(
        player_id=1, season="2024-25", season_type="Regular Season", quality=q,
    )
    assert result.methodology_version == METHODOLOGY_VERSION
    assert result.sustainability == "Insufficient Sample"
    assert len(result.tags) == 1
    assert result.tags[0].key == "insufficient_sample"
    assert "tracked shots" in result.headline.lower()


def test_legacy_coverage_treated_as_insufficient_even_with_shots():
    q = _quality(shots=500, coverage_state="legacy")
    result = build_shot_diagnosis(player_id=1, season="2024-25", season_type="Regular Season", quality=q)
    assert result.sustainability == "Insufficient Sample"
    assert result.tags[0].key == "insufficient_sample"


# --- Tag firing -------------------------------------------------------------


def test_elite_corner_gravity_fires_on_corner_overperformance():
    zones = [
        _zone("Left Corner 3", attempts=40, frequency=0.12, pps_delta=0.14),
        _zone("Restricted Area", frequency=0.30),
    ]
    q = _quality(shots=300, zones=zones)
    result = build_shot_diagnosis(player_id=1, season="2024-25", season_type="Regular Season", quality=q)
    keys = {t.key for t in result.tags}
    assert "elite_corner_gravity" in keys


def test_dead_corners_fires_for_perimeter_player():
    # 3PT volume present (above-the-break) but corners empty
    zones = [
        _zone("Above the Break 3", attempts=120, frequency=0.30, pps_delta=0.00),
        _zone("Restricted Area", frequency=0.30),
    ]
    q = _quality(shots=400, zones=zones)
    result = build_shot_diagnosis(
        player_id=1, season="2024-25", season_type="Regular Season",
        quality=q, size_inches=76,  # guard
    )
    assert "dead_corners" in {t.key for t in result.tags}


def test_dead_corners_suppressed_for_big():
    zones = [
        _zone("Above the Break 3", attempts=120, frequency=0.30),
        _zone("Restricted Area", frequency=0.30),
    ]
    q = _quality(shots=400, zones=zones)
    result = build_shot_diagnosis(
        player_id=1, season="2024-25", season_type="Regular Season",
        quality=q, size_inches=84,  # big
    )
    assert "dead_corners" not in {t.key for t in result.tags}


def test_midrange_dependency_fires_when_mid_share_over_25():
    zones = [_zone("Mid-Range", attempts=120, frequency=0.28, pps_delta=0.00)]
    q = _quality(shots=400, zones=zones)
    result = build_shot_diagnosis(player_id=1, season="2024-25", season_type="Regular Season", quality=q)
    assert "midrange_dependency" in {t.key for t in result.tags}


def test_rim_pressure_elite_requires_volume_and_overperformance():
    zones = [_zone("Restricted Area", attempts=180, frequency=0.40, fg_pct_delta=0.06)]
    q = _quality(shots=450, zones=zones)
    result = build_shot_diagnosis(player_id=1, season="2024-25", season_type="Regular Season", quality=q)
    assert "rim_pressure_elite" in {t.key for t in result.tags}


def test_rim_finishing_variance_fires_on_underperformance():
    zones = [_zone("Restricted Area", attempts=100, frequency=0.35, fg_pct_delta=-0.07)]
    q = _quality(shots=300, zones=zones)
    result = build_shot_diagnosis(player_id=1, season="2024-25", season_type="Regular Season", quality=q)
    assert "rim_finishing_variance" in {t.key for t in result.tags}


def test_long_two_diet_problem_fires():
    zones = [_zone("Mid-Range", attempts=120, frequency=0.25, pps_delta=-0.08)]
    q = _quality(shots=450, zones=zones)
    result = build_shot_diagnosis(player_id=1, season="2024-25", season_type="Regular Season", quality=q)
    assert "long_two_diet_problem" in {t.key for t in result.tags}


def test_catch_and_shoot_specialist_requires_high_assist_and_efg():
    q = _quality(shots=300)
    creation = _creation(assisted_freq=0.65, self_freq=0.25, assisted_efg=0.60)
    result = build_shot_diagnosis(
        player_id=1, season="2024-25", season_type="Regular Season",
        quality=q, creation=creation,
    )
    assert "catch_and_shoot_specialist" in {t.key for t in result.tags}


def test_off_dribble_heavy_fires_on_self_created_majority():
    q = _quality(shots=300)
    creation = _creation(assisted_freq=0.30, self_freq=0.60)
    result = build_shot_diagnosis(
        player_id=1, season="2024-25", season_type="Regular Season",
        quality=q, creation=creation,
    )
    assert "off_dribble_heavy" in {t.key for t in result.tags}


def test_heat_check_overperformance_requires_low_confidence():
    q = _quality(shots=200, summary_pps_delta=0.10, summary_confidence="low")
    result = build_shot_diagnosis(player_id=1, season="2024-25", season_type="Regular Season", quality=q)
    assert "heat_check_overperformance" in {t.key for t in result.tags}


def test_high_ftr_creator_uses_archetype_gate():
    q = _quality(shots=300)
    result = build_shot_diagnosis(
        player_id=1, season="2024-25", season_type="Regular Season",
        quality=q, ftr_z=1.5,
    )
    assert "high_ftr_creator" in {t.key for t in result.tags}


def test_low_ftr_floor_spacer_requires_both_gates():
    q = _quality(shots=300)
    result = build_shot_diagnosis(
        player_id=1, season="2024-25", season_type="Regular Season",
        quality=q, ftr_z=-0.8, par3_z=1.0,
    )
    assert "low_ftr_floor_spacer" in {t.key for t in result.tags}


# --- Sustainability + creation burden ---------------------------------------


def test_sustainability_hot_streak_when_noisy_small_sample():
    # Large pps_delta + low summary confidence + noisy zone deltas
    zones = [
        _zone("Restricted Area", frequency=0.30, pps_delta=0.20, sample_confidence="low"),
        _zone("Above the Break 3", frequency=0.25, pps_delta=-0.05, sample_confidence="low"),
        _zone("Mid-Range", frequency=0.15, pps_delta=0.18, sample_confidence="low"),
    ]
    q = _quality(shots=80, zones=zones, summary_pps_delta=0.10, summary_confidence="low")
    result = build_shot_diagnosis(player_id=1, season="2024-25", season_type="Regular Season", quality=q)
    assert result.sustainability == "Hot Streak"


def test_sustainability_sustainable_by_default():
    q = _quality(shots=400, summary_pps_delta=0.03, summary_confidence="high")
    result = build_shot_diagnosis(player_id=1, season="2024-25", season_type="Regular Season", quality=q)
    assert result.sustainability == "Sustainable"


def test_creation_burden_assisted_heavy():
    q = _quality(shots=300)
    creation = _creation(assisted_freq=0.65, self_freq=0.25)
    result = build_shot_diagnosis(
        player_id=1, season="2024-25", season_type="Regular Season",
        quality=q, creation=creation,
    )
    assert result.creation_burden == "Assisted Heavy"


def test_creation_burden_balanced_when_no_split():
    q = _quality(shots=300)
    result = build_shot_diagnosis(player_id=1, season="2024-25", season_type="Regular Season", quality=q)
    assert result.creation_burden == "Balanced"


# --- Tag ranking + culling --------------------------------------------------


def test_tag_list_capped_at_four():
    zones = [
        _zone("Left Corner 3", attempts=50, frequency=0.10, pps_delta=0.15),
        _zone("Right Corner 3", attempts=50, frequency=0.10, pps_delta=0.15),
        _zone("Restricted Area", attempts=200, frequency=0.40, fg_pct_delta=0.08),
        _zone("Mid-Range", attempts=80, frequency=0.28, pps_delta=-0.06),
        _zone("Above the Break 3", attempts=100, frequency=0.20),
    ]
    q = _quality(shots=500, zones=zones)
    creation = _creation(assisted_freq=0.65, self_freq=0.25, assisted_efg=0.60)
    result = build_shot_diagnosis(
        player_id=1, season="2024-25", season_type="Regular Season",
        quality=q, creation=creation, ftr_z=1.2,
    )
    assert len(result.tags) <= 4


# --- Headline ---------------------------------------------------------------


def test_headline_mentions_top_tag_and_sustainability():
    zones = [_zone("Left Corner 3", attempts=50, frequency=0.12, pps_delta=0.15)]
    q = _quality(shots=300, zones=zones)
    result = build_shot_diagnosis(player_id=1, season="2024-25", season_type="Regular Season", quality=q)
    assert "Elite corner gravity" in result.headline
    assert "Sustainable" in result.headline
