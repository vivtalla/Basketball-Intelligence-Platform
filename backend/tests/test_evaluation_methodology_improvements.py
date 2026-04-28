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
    covariance_matrix,
    empirical_bayes_rate,
    invert_matrix,
    mahalanobis_distance,
    normal_uncertainty_band,
    pearson_correlation,
    shrunk_covariance,
    weight_sensitivity_analysis,
    wilson_interval,
)
from services.scouting_brief_service import _detect_contradictions  # noqa: E402
from services.similarity_service import find_similar_players_with_archetype  # noqa: E402


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


# ---------- Mahalanobis primitives (similarity_v3) ----------


def test_covariance_matrix_recovers_known_relationship():
    # a and b move together (correlation +1), c is independent and constant.
    vectors = [
        [1.0, 2.0, 5.0],
        [2.0, 4.0, 5.0],
        [3.0, 6.0, 5.0],
        [4.0, 8.0, 5.0],
    ]
    cov = covariance_matrix(vectors)
    # Off-diagonal cov(a, b) is positive and equal to cov(b, a); cov(c, *) = 0.
    assert cov[0][1] > 0
    assert cov[0][1] == pytest.approx(cov[1][0])
    assert cov[0][2] == pytest.approx(0.0)
    assert cov[2][2] == pytest.approx(0.0)


def test_shrunk_covariance_blends_toward_diagonal():
    cov = [[2.0, 1.5], [1.5, 3.0]]
    full = shrunk_covariance(cov, 0.0)
    diag_only = shrunk_covariance(cov, 1.0)
    half = shrunk_covariance(cov, 0.5)

    assert full == [[2.0, 1.5], [1.5, 3.0]]
    assert diag_only == [[2.0, 0.0], [0.0, 3.0]]
    assert half[0][1] == pytest.approx(0.75)
    assert half[1][0] == pytest.approx(0.75)
    # Diagonal is preserved at every shrinkage level.
    assert half[0][0] == 2.0
    assert half[1][1] == 3.0


def test_shrunk_covariance_rejects_out_of_range_shrinkage():
    with pytest.raises(ValueError):
        shrunk_covariance([[1.0]], -0.1)
    with pytest.raises(ValueError):
        shrunk_covariance([[1.0]], 1.1)


def test_invert_matrix_returns_none_on_singular_matrix():
    # Two identical rows → rank-deficient.
    assert invert_matrix([[1.0, 2.0], [1.0, 2.0]]) is None


def test_invert_matrix_recovers_identity():
    matrix = [[4.0, 7.0], [2.0, 6.0]]
    inverse = invert_matrix(matrix)
    assert inverse is not None
    # M * M^-1 ≈ I for a 2x2.
    product_00 = matrix[0][0] * inverse[0][0] + matrix[0][1] * inverse[1][0]
    product_01 = matrix[0][0] * inverse[0][1] + matrix[0][1] * inverse[1][1]
    assert product_00 == pytest.approx(1.0)
    assert product_01 == pytest.approx(0.0)


def test_mahalanobis_with_identity_inverse_equals_euclidean():
    a = [1.0, 2.0, 3.0]
    b = [4.0, 6.0, 3.0]
    identity = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    euclid = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5
    assert mahalanobis_distance(a, b, identity) == pytest.approx(euclid)


def test_mahalanobis_shrinks_distance_along_correlated_dimensions():
    # Two strongly-correlated features. Inverse-covariance off-diagonals are
    # negative, so a delta that moves both features together gets a SMALLER
    # contribution under Mahalanobis than under Euclidean — exactly the
    # double-counting fix the upgrade is meant to deliver.
    cov = [[1.0, 0.9], [0.9, 1.0]]
    inverse = invert_matrix(cov)
    assert inverse is not None
    a = [0.0, 0.0]
    b = [1.0, 1.0]
    euclidean = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    mahal = mahalanobis_distance(a, b, inverse)
    assert mahal < euclidean


# ---------- similarity_v3 integration ----------


def _add_similarity_row(db, *, pid, name, season, **stats):
    from db.models import Player, SeasonStat
    if db.query(Player).filter(Player.id == pid).first() is None:
        db.add(Player(id=pid, full_name=name, height="6-6", birth_date="1998-01-01"))
    defaults = dict(
        player_id=pid, season=season, team_abbreviation="TOT", is_playoff=False,
        gp=70, min_pg=32.0,
        pts_pg=18.0, reb_pg=5.0, ast_pg=4.5, stl_pg=1.0, blk_pg=0.5, tov_pg=2.2,
        fgm=6.5, fga=14.0, fg_pct=0.464,
        fg3m=2.0, fg3a=5.5, fg3_pct=0.363,
        ftm=3.0, fta=4.0, ft_pct=0.750,
        oreb=1.0, dreb=4.0, pf=2.5,
        usg_pct=22.0, ts_pct=0.570, efg_pct=0.540, per=16.0, bpm=0.0,
        off_rating=112.0, def_rating=112.0, net_rating=0.0,
        pace=100.0, pie=0.12, darko=0.0, epm=0.0, rapm=0.0, obpm=0.0, dbpm=0.0,
        ftr=0.29, par3=0.40, ast_tov=2.0, oreb_pct=4.0,
    )
    defaults.update(stats)
    db.add(SeasonStat(**defaults))


def test_similarity_v3_uses_shrunk_mahalanobis_when_pool_is_large_enough():
    from services.player_archetype_service import clear_archetype_cache
    clear_archetype_cache()
    db = _make_session()
    try:
        # Subject + 50 distinct same-season peers — enough rows for the 13-feature
        # covariance to invert reliably (3 * 13 = 39).
        _add_similarity_row(db, pid=1, name="Subject", season="2023-24",
                            usg_pct=30.0, ast_pg=8.0, pts_pg=28.0, per=24.0)
        for i in range(50):
            _add_similarity_row(db, pid=100 + i, name="Peer {0}".format(i), season="2023-24",
                                usg_pct=18.0 + i * 0.2,
                                ast_pg=3.0 + i * 0.1,
                                pts_pg=12.0 + i * 0.4,
                                per=12.0 + i * 0.2,
                                ts_pct=0.50 + i * 0.002,
                                reb_pg=4.0 + i * 0.1)
        db.commit()
        comps = find_similar_players_with_archetype(
            db, 1, "2023-24", mode="season", n=5,
            distance_method="shrunk_mahalanobis",
        )
        assert comps, "expected at least one comp"
        assert all(c["distance_method_used"] == "shrunk_mahalanobis" for c in comps)
    finally:
        db.close()


def test_similarity_v3_falls_back_to_euclidean_on_thin_pool():
    from services.player_archetype_service import clear_archetype_cache
    clear_archetype_cache()
    db = _make_session()
    try:
        # Subject + only 5 peers — well below the 39-row floor for a 13-feature
        # covariance. The service must auto-fall back to weighted Euclidean.
        _add_similarity_row(db, pid=1, name="Subject", season="2023-24",
                            usg_pct=30.0, ast_pg=8.0, pts_pg=28.0)
        for i in range(5):
            _add_similarity_row(db, pid=100 + i, name="Peer {0}".format(i), season="2023-24",
                                usg_pct=18.0 + i * 0.5,
                                ast_pg=3.0 + i * 0.3,
                                pts_pg=12.0 + i)
        db.commit()
        comps = find_similar_players_with_archetype(
            db, 1, "2023-24", mode="season", n=5,
            distance_method="shrunk_mahalanobis",
        )
        assert comps, "expected at least one comp"
        assert all(c["distance_method_used"] == "weighted_euclidean" for c in comps)
    finally:
        db.close()


# ---------- weight sensitivity primitive ----------


def test_weight_sensitivity_zero_change_when_one_feature_dominates():
    # Subject 1 dominates on every feature; perturbing weights cannot dethrone.
    contributions = {
        1: [3.0, 3.0, 3.0],
        2: [1.0, 1.0, 1.0],
        3: [0.5, 0.5, 0.5],
        4: [0.0, 0.0, 0.0],
        5: [-1.0, -1.0, -1.0],
        6: [-2.0, -2.0, -2.0],
    }
    weights = [0.4, 0.3, 0.3]
    max_change, jaccard = weight_sensitivity_analysis(
        contributions, weights, perturbation=0.10, top_n=5,
    )
    assert max_change == 0
    assert jaccard == pytest.approx(1.0)


def test_weight_sensitivity_flags_unstable_top_set():
    # Two players have nearly-tied composites that flip under tiny weight
    # changes — sensitivity must report a non-zero rank change.
    contributions = {
        1: [1.0, -0.9],
        2: [-0.9, 1.0],
        3: [0.5, 0.5],
        4: [0.0, 0.0],
        5: [-0.5, -0.5],
        6: [-1.0, -1.0],
    }
    weights = [0.5, 0.5]
    max_change, jaccard = weight_sensitivity_analysis(
        contributions, weights, perturbation=0.40, top_n=2,
    )
    assert max_change >= 1
    assert jaccard <= 0.999  # something flipped


def test_weight_sensitivity_validates_inputs():
    with pytest.raises(ValueError):
        weight_sensitivity_analysis({}, [1.0], perturbation=0.1, top_n=3)
    with pytest.raises(ValueError):
        weight_sensitivity_analysis({1: [1.0, 2.0]}, [1.0, 2.0], perturbation=-0.1, top_n=1)
    with pytest.raises(ValueError):
        weight_sensitivity_analysis({1: [1.0]}, [1.0, 2.0], perturbation=0.1, top_n=1)


# ---------- custom metric sensitivity wiring ----------


def test_custom_metric_attaches_weight_sensitivity_to_response():
    from db.models import Player, SeasonStat, Team
    from models.leaderboard import CustomMetricComponent, CustomMetricRequest
    from services.custom_metric_service import build_custom_metric_report

    session = _make_session()
    try:
        team = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks")
        session.add(team)
        # Spread players widely so the top-5 ranking is stable under +/-10%.
        rows = [
            (1, "Alpha", 30.0, 8.0),
            (2, "Bravo", 28.0, 7.0),
            (3, "Charlie", 26.0, 6.0),
            (4, "Delta", 24.0, 5.0),
            (5, "Echo", 22.0, 4.0),
            (6, "Foxtrot", 20.0, 3.0),
            (7, "Golf", 18.0, 2.0),
        ]
        for player_id, name, pts_pg, ast_pg in rows:
            session.add(Player(id=player_id, full_name=name, team=team, team_id=team.id, position="G"))
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
                metric_name="Volume Composite",
                player_pool="all",
                season="2024-25",
                components=[
                    CustomMetricComponent(stat_id="pts_pg", label="Points", weight=0.6, inverse=False),
                    CustomMetricComponent(stat_id="ast_pg", label="Assists", weight=0.4, inverse=False),
                ],
            ),
        )
        assert report.weight_sensitivity is not None
        assert report.weight_sensitivity.top_n == 5
        assert report.weight_sensitivity.perturbation == pytest.approx(0.10)
        assert report.weight_sensitivity.max_rank_change == 0
        assert report.weight_sensitivity.top_set_jaccard == pytest.approx(1.0)
        assert "stable" in report.weight_sensitivity.interpretation.lower()
    finally:
        session.close()


# ---------- scouting brief contradiction detector ----------


class _StubContributor:
    def __init__(self, feature_key, direction, z=1.0, label=""):
        self.feature_key = feature_key
        self.direction = direction
        self.z = z
        self.label = label or feature_key


class _StubArchetype:
    def __init__(self, key, label, confidence, contributors=None):
        self.archetype_key = key
        self.label = label
        self.confidence = confidence
        self.contributors = contributors or []


class _StubOpportunityRow:
    def __init__(self, usg_pct):
        self.usg_pct = usg_pct


class _StubDiagnosis:
    def __init__(self, sustainability):
        self.sustainability = sustainability


class _StubTrajectoryRow:
    def __init__(self, trajectory_label):
        self.trajectory_label = trajectory_label


def test_contradiction_detector_flags_high_usage_archetype_at_low_usage():
    archetype = _StubArchetype(
        key="lead_ball_handler",
        label="Lead Ball-Handler",
        confidence="high",
        contributors=[_StubContributor("usg_z", "above")],
    )
    opportunity_row = _StubOpportunityRow(usg_pct=0.15)
    contradictions = _detect_contradictions(
        archetype=archetype, opportunity_row=opportunity_row,
        diagnosis=None, trajectory_row=None,
    )
    assert any("Lead Ball-Handler" in c.summary for c in contradictions)
    assert any(set(c.card_types) == {"role", "usage_efficiency"} for c in contradictions)


def test_contradiction_detector_flags_role_versus_decline_trajectory():
    archetype = _StubArchetype(
        key="iso_scorer", label="Iso Scorer", confidence="high",
        contributors=[_StubContributor("usg_z", "above")],
    )
    trajectory_row = _StubTrajectoryRow(trajectory_label="Slumping")
    contradictions = _detect_contradictions(
        archetype=archetype, opportunity_row=None,
        diagnosis=None, trajectory_row=trajectory_row,
    )
    assert any(set(c.card_types) == {"role", "trajectory"} for c in contradictions)


def test_contradiction_detector_flags_shooting_strength_versus_hot_streak():
    archetype = _StubArchetype(
        key="movement_shooter", label="Movement Shooter", confidence="high",
        contributors=[
            _StubContributor("par3_z", "above", z=1.4, label="3-point attempt rate"),
        ],
    )
    diagnosis = _StubDiagnosis(sustainability="Hot Streak")
    contradictions = _detect_contradictions(
        archetype=archetype, opportunity_row=None,
        diagnosis=diagnosis, trajectory_row=None,
    )
    assert any(set(c.card_types) == {"strengths", "shot_profile"} for c in contradictions)


def test_contradiction_detector_skips_low_confidence_archetypes():
    # Even with downward trajectory + low usage, low-confidence archetype
    # shouldn't trigger contradictions — they'd just be noise.
    archetype = _StubArchetype(
        key="iso_scorer", label="Iso Scorer", confidence="low",
        contributors=[_StubContributor("usg_z", "above")],
    )
    contradictions = _detect_contradictions(
        archetype=archetype,
        opportunity_row=_StubOpportunityRow(usg_pct=0.15),
        diagnosis=_StubDiagnosis(sustainability="Hot Streak"),
        trajectory_row=_StubTrajectoryRow(trajectory_label="Collapsing"),
    )
    assert contradictions == []


def test_contradiction_detector_skips_developmental_archetype():
    archetype = _StubArchetype(
        key="developmental", label="Developmental", confidence="high",
    )
    contradictions = _detect_contradictions(
        archetype=archetype, opportunity_row=_StubOpportunityRow(usg_pct=0.15),
        diagnosis=None, trajectory_row=_StubTrajectoryRow("Collapsing"),
    )
    assert contradictions == []
