import math
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.methodology_registry_service import get_methodology_detail, list_methodologies
from services.reliability_service import (
    confidence_from_reliability,
    empirical_bayes_delta,
    empirical_bayes_rate,
    normal_uncertainty_band,
    reliability_score,
    robust_zscores,
    wilson_interval,
    winsorized_zscores,
)


def test_empirical_bayes_rate_shrinks_small_samples_toward_prior():
    posterior = empirical_bayes_rate(
        successes=2,
        attempts=4,
        prior_rate=0.35,
        prior_weight=20,
    )

    assert posterior == pytest.approx(0.375)
    assert 0.35 < posterior < 0.50


def test_empirical_bayes_delta_shrinks_small_samples():
    posterior_delta = empirical_bayes_delta(
        observed_value=1.4,
        expected_value=1.0,
        sample_size=10,
        prior_weight=90,
    )

    assert posterior_delta == pytest.approx(0.04)


def test_reliability_score_and_confidence_labels():
    assert reliability_score(0, 300) == 0.0
    assert reliability_score(300, 300) == 50.0
    assert confidence_from_reliability(25) == "low"
    assert confidence_from_reliability(50) == "medium"
    assert confidence_from_reliability(75) == "high"


def test_uncertainty_helpers_return_ordered_bands():
    wilson = wilson_interval(successes=10, attempts=20)
    normal = normal_uncertainty_band(mean=1.05, sample_size=100, std_dev=0.4)

    assert wilson.lower < 0.5 < wilson.upper
    assert wilson.level == 0.90
    assert normal.lower < 1.05 < normal.upper
    assert normal.method == "normal_approximation"


def test_robust_zscores_and_winsorized_zscores_handle_outliers():
    values = [1.0, 2.0, 2.0, 3.0, 100.0]

    robust = robust_zscores(values)
    winsorized = winsorized_zscores(values)

    assert robust[2] == pytest.approx(0.0)
    assert robust[-1] > 60
    assert len(winsorized) == len(values)
    assert all(math.isfinite(score) for score in winsorized)


def test_methodology_registry_exposes_core_domains_and_normalizes_lookup():
    registry = list_methodologies()
    domains = {domain.domain for domain in registry.domains}

    assert registry.version == "methodology_registry_v2"
    assert {"shot_lab", "team_fit", "similarity", "opportunity", "mvp"}.issubset(domains)

    team_fit = get_methodology_detail("team-fit")
    assert team_fit.domain == "team_fit"
    assert team_fit.methodology_version == "team_fit_v3"
    assert "Playoffs" in team_fit.season_type_support
    assert team_fit.last_validation_date == "2026-04-28"
    assert "specs/platform-methodology.md" == team_fit.docs_path


def test_methodology_registry_unknown_domain_raises_404():
    with pytest.raises(HTTPException) as exc:
        get_methodology_detail("not-real")

    assert exc.value.status_code == 404
