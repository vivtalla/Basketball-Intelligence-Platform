from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import Player, SeasonStat, Team  # noqa: E402
from models.leaderboard import CustomMetricComponent, CustomMetricRequest  # noqa: E402
from services.custom_metric_service import build_custom_metric_report  # noqa: E402
from services.methodology_registry_service import list_methodologies  # noqa: E402
from services.methodology_validation_service import methodology_validation_report  # noqa: E402
from services.reliability_service import (  # noqa: E402
    _z_for_level,
    collinearity_warnings,
    empirical_bayes_rate,
    normal_uncertainty_band,
    pearson_correlation,
    wilson_interval,
)


# ---------- z-value level mapping ----------


def test_z_for_level_resolves_documented_levels_exactly():
    assert _z_for_level(0.80) == (0.80, 1.282)
    assert _z_for_level(0.90) == (0.90, 1.645)
    assert _z_for_level(0.95) == (0.95, 1.960)
    assert _z_for_level(0.99) == (0.99, 2.576)


def test_z_for_level_snaps_unsupported_level_to_nearest_documented():
    resolved_level, z_value = _z_for_level(0.97)
    assert resolved_level in {0.95, 0.99}
    # Snapped level should report the level it actually used, not the requester's.
    assert z_value == (1.960 if resolved_level == 0.95 else 2.576)


def test_wilson_interval_widens_with_higher_confidence_level():
    narrower = wilson_interval(successes=12, attempts=40, level=0.80)
    wider = wilson_interval(successes=12, attempts=40, level=0.99)

    assert narrower.level == 0.80
    assert wider.level == 0.99
    narrow_width = narrower.upper - narrower.lower
    wide_width = wider.upper - wider.lower
    assert wide_width > narrow_width


def test_normal_uncertainty_band_returns_resolved_level_for_unsupported_input():
    band = normal_uncertainty_band(mean=2.0, sample_size=50, std_dev=0.5, level=0.93)
    assert band.level in {0.90, 0.95}
    assert band.lower < 2.0 < band.upper


# ---------- empirical_bayes_rate hardening ----------


def test_empirical_bayes_rate_rejects_prior_rate_outside_unit_interval():
    with pytest.raises(ValueError):
        empirical_bayes_rate(successes=2, attempts=4, prior_rate=1.2, prior_weight=10)
    with pytest.raises(ValueError):
        empirical_bayes_rate(successes=2, attempts=4, prior_rate=-0.1, prior_weight=10)


def test_empirical_bayes_rate_rejects_more_successes_than_attempts():
    with pytest.raises(ValueError):
        empirical_bayes_rate(successes=5, attempts=4, prior_rate=0.5, prior_weight=10)


def test_empirical_bayes_rate_returns_value_inside_unit_interval():
    posterior = empirical_bayes_rate(successes=4, attempts=4, prior_rate=0.0, prior_weight=0.0)
    assert 0.0 <= posterior <= 1.0


# ---------- correlation primitives ----------


def test_pearson_correlation_handles_perfect_pairs_and_uncorrelated_pairs():
    assert pearson_correlation([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)
    assert pearson_correlation([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert pearson_correlation([1, 1, 1, 1], [2, 4, 6, 8]) is None


def test_pearson_correlation_returns_none_with_too_few_complete_pairs():
    assert pearson_correlation([1, None, None], [None, 2, 3]) is None


def test_collinearity_warnings_flags_high_correlation_pairs_only():
    series = {
        "Points": [10, 20, 30, 40, 50],
        "Scoring Volume": [11, 21, 29, 41, 51],
        "Free Throws": [3, 1, 4, 2, 5],
    }
    warnings_out = collinearity_warnings(series, threshold=0.85)
    assert any("Points" in note and "Scoring Volume" in note for note in warnings_out)
    assert not any("Free Throws" in note for note in warnings_out)


# ---------- custom metric collinearity wiring ----------


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return SessionLocal()


def _seed_collinear_pool(session):
    team = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks")
    session.add(team)
    # PTS and TS% intentionally co-move so the collinearity warning should fire.
    rows = [
        (1, "Alpha", 28.0, 0.60, 5.0),
        (2, "Bravo", 24.0, 0.58, 4.5),
        (3, "Charlie", 22.0, 0.56, 4.0),
        (4, "Delta", 18.0, 0.54, 3.0),
        (5, "Echo", 14.0, 0.52, 2.0),
        (6, "Foxtrot", 10.0, 0.50, 1.5),
    ]
    for player_id, name, pts_pg, ts_pct, ast_pg in rows:
        session.add(Player(id=player_id, full_name=name, team=team, team_id=team.id, position="G"))
        session.add(
            SeasonStat(
                player_id=player_id,
                season="2024-25",
                team_abbreviation="ATL",
                is_playoff=False,
                gp=50,
                pts_pg=pts_pg,
                ts_pct=ts_pct,
                ast_pg=ast_pg,
            )
        )
    session.commit()


def test_custom_metric_warns_when_components_are_highly_correlated():
    session = _make_session()
    try:
        _seed_collinear_pool(session)
        report = build_custom_metric_report(
            session,
            CustomMetricRequest(
                metric_name="Scoring Twins",
                player_pool="all",
                season="2024-25",
                components=[
                    CustomMetricComponent(stat_id="pts_pg", label="Points", weight=0.5, inverse=False),
                    CustomMetricComponent(stat_id="ts_pct", label="True Shooting", weight=0.5, inverse=False),
                ],
            ),
        )
        assert any("highly correlated" in warning for warning in report.validation_warnings)
    finally:
        session.close()


def test_custom_metric_does_not_warn_for_uncorrelated_components():
    session = _make_session()
    try:
        # Independent dimensions: pts_pg increases, ast_pg decreases.
        team = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks")
        session.add(team)
        for player_id, pts_pg, ast_pg in [
            (1, 28.0, 1.0),
            (2, 24.0, 4.0),
            (3, 22.0, 2.0),
            (4, 18.0, 6.0),
            (5, 14.0, 3.0),
            (6, 10.0, 8.0),
        ]:
            session.add(
                Player(id=player_id, full_name="P{}".format(player_id), team=team, team_id=team.id, position="G")
            )
            session.add(
                SeasonStat(
                    player_id=player_id,
                    season="2024-25",
                    team_abbreviation="ATL",
                    is_playoff=False,
                    gp=50,
                    pts_pg=pts_pg,
                    ast_pg=ast_pg,
                )
            )
        session.commit()
        report = build_custom_metric_report(
            session,
            CustomMetricRequest(
                metric_name="Mixed",
                player_pool="all",
                season="2024-25",
                components=[
                    CustomMetricComponent(stat_id="pts_pg", label="Points", weight=0.5, inverse=False),
                    CustomMetricComponent(stat_id="ast_pg", label="Assists", weight=0.5, inverse=False),
                ],
            ),
        )
        assert not any("highly correlated" in warning for warning in report.validation_warnings)
    finally:
        session.close()


# ---------- expanded validation fixture coverage ----------


def test_validation_fixtures_cover_every_registered_domain():
    registry_domains = {domain.domain for domain in list_methodologies().domains}
    fixture_domains = {fixture.domain for fixture in methodology_validation_report().fixtures}
    missing = registry_domains - fixture_domains
    assert not missing, "Methodology domains missing validation fixtures: {0}".format(sorted(missing))


def test_validation_fixture_keys_are_unique():
    keys = [fixture.fixture_key for fixture in methodology_validation_report().fixtures]
    assert len(keys) == len(set(keys))
