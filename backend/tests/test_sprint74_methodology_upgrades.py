from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.shot_intelligence_service import (
    _Baseline,
    _BaselineStore,
    _expected_baseline,
    _quality_summary,
)
from services.team_fit_service import _alternative_label
from services.methodology_validation_service import methodology_validation_report


def _shot():
    return {
        "zone_basic": "Above the Break 3",
        "zone_area": "Center",
        "distance": 26,
        "shot_value": 3,
        "shot_type": "3PT Field Goal",
        "action_type": "Jump Shot",
        "period": 1,
        "minutes_remaining": 6,
        "seconds_remaining": 0,
        "score_margin": 0,
        "team_id": 1,
        "opponent_team_id": 2,
        "shot_made": True,
    }


def test_hierarchical_baseline_blends_thin_exact_context():
    store = _BaselineStore()
    shot = _shot()
    store.league = _Baseline(attempts=1000, made=450, points=990)
    store.value[("3", "Regular Season")] = _Baseline(attempts=500, made=180, points=540)
    store.zone_value[("Above the Break 3", "3", "Regular Season")] = _Baseline(attempts=200, made=70, points=210)
    store.zone_distance_value[("Above the Break 3", "24-27", "3", "Regular Season")] = _Baseline(attempts=100, made=38, points=114)
    store.exact[(
        "Above the Break 3",
        "Center",
        "24-27",
        "3",
        "perimeter_jumper",
        "q1",
        "middle",
        "close",
        "available",
        "Regular Season",
    )] = _Baseline(attempts=5, made=4, points=12)

    baseline, label = _expected_baseline(shot, "Regular Season", store)

    assert label == "exact_context_blended"
    assert baseline.pps < 12 / 5
    assert baseline.attempts == 30


def test_stabilized_pps_delta_shrinks_low_attempt_extremes():
    summary = _quality_summary(
        attempts=10,
        made=8,
        points=24,
        expected_points=10,
        expected_makes=4,
        prior_weight=90,
        point_std=1.0,
    )

    assert summary.pps_delta == pytest.approx(1.4)
    assert abs(summary.stabilized_pps_delta or 0) < abs(summary.pps_delta or 0)
    assert summary.sustainability_label in {"sample too thin", "likely hot streak"}


def test_validation_report_and_reliability_gated_team_fit_labels():
    report = methodology_validation_report()
    assert report.version == "methodology_validation_v1"
    assert {fixture.domain for fixture in report.fixtures} >= {"team_fit", "shot_lab"}
    assert _alternative_label(6.0, "high") == "better_fit"
    assert _alternative_label(6.0, "medium") == "similar_fit"
    assert _alternative_label(20.0, "low") == "similar_fit"
