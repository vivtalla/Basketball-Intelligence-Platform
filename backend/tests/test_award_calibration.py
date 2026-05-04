"""Sprint 79 Stream A1 — award case calibration math tests.

Methodology: specs/methodology-future-modeling.md#1.

These tests exercise the pure-math primitives (coordinate descent, LOO-CV,
Spearman, constraint projection) against synthetic data with known ground-truth
weights. Once historical Basketball Value + modifier vectors are materialized
in a future sprint, the integration is a one-liner.
"""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.migrations import upgrade_database  # noqa: E402
from db.models import AwardVote, Player  # noqa: E402
from services.award_calibration_service import (  # noqa: E402
    DEFAULT_AWARD_CASE_WEIGHTS,
    MAX_PILLAR_DRIFT,
    MODIFIER_KEYS,
    WEIGHT_SUM_CAP,
    _award_case_score,
    _enforce_drift_cap,
    _project_to_constraints,
    _spearman_correlation,
    calibrate_award_case_weights,
    coordinate_descent_fit,
    leave_one_season_out_cv,
)


@pytest.fixture
def db_session():
    with TemporaryDirectory() as tmpdir:
        database_url = "sqlite:///{0}".format(Path(tmpdir) / "award.db")
        upgrade_database(database_url)
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            yield session
        finally:
            session.close()
            engine.dispose()


def _candidate(basketball_value, modifier_vector, observed_share):
    return {
        "basketball_value": basketball_value,
        "modifier_vector": modifier_vector,
        "observed_share": observed_share,
    }


def test_spearman_perfect_correlation():
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    b = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert abs(_spearman_correlation(a, b) - 1.0) < 1e-9


def test_spearman_perfect_inverse():
    a = [1.0, 2.0, 3.0, 4.0, 5.0]
    b = [50.0, 40.0, 30.0, 20.0, 10.0]
    assert abs(_spearman_correlation(a, b) - (-1.0)) < 1e-9


def test_spearman_zero_correlation_on_constant_input():
    a = [1.0, 1.0, 1.0]
    b = [10.0, 20.0, 30.0]
    assert _spearman_correlation(a, b) == 0.0


def test_project_to_constraints_clips_negatives():
    weights = [-0.05, 0.10, -0.02, 0.05, 0.03]
    result = _project_to_constraints(weights)
    assert all(w >= 0 for w in result)


def test_project_to_constraints_scales_when_sum_exceeds_cap():
    # Sum = 0.50, cap = 0.40 → uniform scale by 0.8
    weights = [0.10, 0.10, 0.10, 0.10, 0.10]
    result = _project_to_constraints(weights)
    assert abs(sum(result) - WEIGHT_SUM_CAP) < 1e-9
    assert all(abs(r - 0.08) < 1e-9 for r in result)


def test_project_to_constraints_passes_through_valid():
    weights = [0.08, 0.08, 0.06, 0.05, 0.05]  # sum = 0.32
    result = _project_to_constraints(weights)
    assert result == weights


def test_award_case_score_combines_basketball_value_and_modifiers():
    score = _award_case_score(0.50, [1.0, 1.0, 1.0, 1.0, 1.0], [0.08, 0.08, 0.06, 0.05, 0.05])
    # 0.50 + 0.08 + 0.08 + 0.06 + 0.05 + 0.05 = 0.82
    assert abs(score - 0.82) < 1e-9


def test_coordinate_descent_recovers_known_weights():
    """Synthetic ground truth: candidates whose ranking is driven by a known weight vector
    should have the fit converge near those weights."""
    true_weights = [0.10, 0.05, 0.03, 0.02, 0.04]  # sum = 0.24, valid

    # Build 30 candidates with diverse modifier vectors and a small range of basketball values.
    candidates = []
    for i in range(30):
        bv = 0.50 + (i % 7) * 0.02
        mv = [
            (i * 0.13 % 1) - 0.5,
            (i * 0.27 % 1) - 0.5,
            (i * 0.41 % 1) - 0.5,
            (i * 0.57 % 1) - 0.5,
            (i * 0.71 % 1) - 0.5,
        ]
        observed = bv + sum(true_weights[k] * mv[k] for k in range(5))
        candidates.append(_candidate(bv, mv, observed))

    fit_weights, score = coordinate_descent_fit(candidates)

    # When the true generating model is in-class, Spearman should be very high
    assert score >= 0.95, "expected near-perfect rank correlation, got {0}".format(score)


def test_leave_one_season_out_cv_reports_fold_count():
    # 6 seasons of synthetic data
    candidates_by_season = {}
    true_weights = [0.10, 0.05, 0.03, 0.02, 0.04]
    for season_idx in range(6):
        season_key = "20{0:02d}-{1:02d}".format(20 + season_idx, 21 + season_idx)
        rows = []
        for cand_idx in range(5):
            bv = 0.50 + (cand_idx + season_idx) * 0.02
            mv = [
                (cand_idx * 0.13 + season_idx * 0.07) % 1 - 0.5,
                (cand_idx * 0.27 + season_idx * 0.11) % 1 - 0.5,
                (cand_idx * 0.41 + season_idx * 0.13) % 1 - 0.5,
                (cand_idx * 0.57 + season_idx * 0.17) % 1 - 0.5,
                (cand_idx * 0.71 + season_idx * 0.19) % 1 - 0.5,
            ]
            observed = bv + sum(true_weights[k] * mv[k] for k in range(5))
            rows.append(_candidate(bv, mv, observed))
        candidates_by_season[season_key] = rows

    weights, mean_spearman, fold_count = leave_one_season_out_cv(candidates_by_season)
    assert fold_count == 6
    assert mean_spearman >= 0.5
    # Returned weights pass constraints
    assert all(w >= 0 for w in weights)
    assert sum(weights) <= WEIGHT_SUM_CAP + 1e-9


def test_loo_cv_returns_defaults_when_below_min_folds():
    # Only 3 seasons → below MIN_FOLDS_REQUIRED (5) → return defaults
    candidates_by_season = {
        "2020-21": [_candidate(0.5, [0.0]*5, 0.6)],
        "2021-22": [_candidate(0.5, [0.0]*5, 0.6)],
        "2022-23": [_candidate(0.5, [0.0]*5, 0.6)],
    }
    weights, mean_spearman, fold_count = leave_one_season_out_cv(candidates_by_season)
    expected = list(DEFAULT_AWARD_CASE_WEIGHTS.values())
    assert weights == expected
    assert fold_count == 3
    assert mean_spearman == 0.0


def test_drift_cap_clamps_runaway_calibration():
    """Per spec: each pillar must move <= 0.04 absolute from the prior."""
    prior = [0.08, 0.08, 0.06, 0.05, 0.05]
    calibrated = [0.20, 0.00, 0.10, 0.05, 0.05]  # 1st and 3rd have huge swings
    capped = _enforce_drift_cap(calibrated, prior, cap=MAX_PILLAR_DRIFT)
    assert capped[0] == 0.12  # 0.08 + 0.04 cap
    assert capped[1] == 0.04  # 0.08 - 0.04 cap
    assert capped[2] == 0.10  # 0.06 + 0.04 cap (matches calibrated)
    assert capped[3] == 0.05  # unchanged
    assert capped[4] == 0.05  # unchanged


def test_calibrate_returns_pending_when_voting_table_empty(db_session):
    """No award_voting rows → return defaults with calibration_pending=True."""
    result = calibrate_award_case_weights(db_session)
    assert result["calibration_pending"] is True
    assert result["fold_count"] == 0
    assert result["weights"] == DEFAULT_AWARD_CASE_WEIGHTS
    assert "empty" in result["notes"][0]


def test_calibrate_reports_pending_with_voting_data_but_no_modifier_vectors(db_session):
    """When award_voting has rows but historical modifier vectors aren't materialized,
    the response signals pending status and surfaces the last season seen."""
    # Seed one player + one ballot row
    p = Player(id=2544, full_name="LeBron James", first_name="LeBron", last_name="James", is_active=True)
    db_session.add(p)
    db_session.flush()
    db_session.add(AwardVote(
        player_id=2544, season="2012-13", award_type="MVP",
        ballot_position=1, voter_count=121, total_award_points=0.998,
    ))
    db_session.commit()

    result = calibrate_award_case_weights(db_session)
    assert result["calibration_pending"] is True
    assert result["last_calibrated_season"] == "2012-13"
    assert result["fold_count"] == 0
    # Default weights stand in until materialization lands
    assert result["weights"] == DEFAULT_AWARD_CASE_WEIGHTS


def test_modifier_keys_match_spec():
    """Lock down the 5 modifier names in the order the math expects."""
    expected = ("team_framing", "eligibility_pressure", "clutch", "momentum", "signature_games")
    assert MODIFIER_KEYS == expected
    assert set(DEFAULT_AWARD_CASE_WEIGHTS.keys()) == set(expected)


# ---------------------------------------------------------------------------
# Sprint 90 — activation integration tests
# ---------------------------------------------------------------------------

def _seed_calibration_dataset(db_session, n_seasons: int = 6, candidates_per_season: int = 5):
    """Seed award_voting + award_case_candidates with synthetic data that has
    a strong signal in the modifier vector — calibration should converge and
    flip ``calibration_pending`` to False.

    Generating model: observed_share = basketball_value + W . modifier_vector,
    with W skewed toward team_framing + clutch so the calibrator has signal
    to lean on.
    """
    from db.models import AwardCaseCandidate as _AwardCaseCandidate
    from db.models import AwardVote as _AwardVote
    from db.models import Player as _Player

    true_w = [0.10, 0.04, 0.07, 0.02, 0.03]  # sum = 0.26 < cap

    pid = 5000
    for season_idx in range(n_seasons):
        season = "20{0:02d}-{1:02d}".format(20 + season_idx, 21 + season_idx)
        for cand_idx in range(candidates_per_season):
            player_id = pid
            pid += 1
            db_session.add(_Player(
                id=player_id,
                full_name="Test {0} {1}".format(season_idx, cand_idx),
                first_name="Test",
                last_name="{0}-{1}".format(season_idx, cand_idx),
                is_active=True,
            ))
            bv = 0.50 + (cand_idx + season_idx) * 0.02
            mv = [
                ((cand_idx * 0.13 + season_idx * 0.07) % 1) - 0.5,
                ((cand_idx * 0.27 + season_idx * 0.11) % 1) - 0.5,
                ((cand_idx * 0.41 + season_idx * 0.13) % 1) - 0.5,
                ((cand_idx * 0.57 + season_idx * 0.17) % 1) - 0.5,
                ((cand_idx * 0.71 + season_idx * 0.19) % 1) - 0.5,
            ]
            observed = bv + sum(true_w[k] * mv[k] for k in range(5))
            db_session.add(_AwardVote(
                player_id=player_id, season=season, award_type="MVP",
                ballot_position=cand_idx + 1, voter_count=100,
                total_award_points=observed,
            ))
            db_session.add(_AwardCaseCandidate(
                player_id=player_id, season=season, award_type="MVP",
                basketball_value=bv,
                modifier_team_framing=mv[0],
                modifier_eligibility_pressure=mv[1],
                modifier_clutch=mv[2],
                modifier_momentum=mv[3],
                modifier_signature_games=mv[4],
            ))
    db_session.commit()


def test_calibration_activates_when_dataset_has_signal(db_session):
    """End-to-end: with materialized AwardCaseCandidate rows that follow a
    known generating model, calibrate flips calibration_pending → False and
    returns fitted weights different from the hand-tuned defaults."""
    _seed_calibration_dataset(db_session, n_seasons=6, candidates_per_season=5)

    result = calibrate_award_case_weights(db_session)
    assert result["calibration_pending"] is False, "expected calibration to clear pending; notes={0}".format(result["notes"])
    assert result["fold_count"] == 6
    assert result["cross_validated_spearman"] >= 0.7
    # Fitted weights should differ from the defaults on at least one pillar
    fitted = result["weights"]
    differs = any(abs(fitted[k] - DEFAULT_AWARD_CASE_WEIGHTS[k]) > 1e-6 for k in MODIFIER_KEYS)
    assert differs, "expected at least one fitted weight to move from defaults; got {0}".format(fitted)
    # Drift cap holds: every pillar within 0.04 of its prior
    for k in MODIFIER_KEYS:
        assert abs(fitted[k] - DEFAULT_AWARD_CASE_WEIGHTS[k]) <= MAX_PILLAR_DRIFT + 1e-9


def test_get_calibration_state_caches_result(db_session, monkeypatch):
    """The mvp_service helper should hit the SQLite cache on the second call;
    a sentinel value injected into the cache must short-circuit the live
    calibrate function entirely."""
    from data.cache import CacheManager
    from services import mvp_service

    CacheManager.initialize()
    CacheManager.delete(mvp_service.CALIBRATION_CACHE_KEY)

    sentinel = {
        "weights": dict(DEFAULT_AWARD_CASE_WEIGHTS),
        "cross_validated_spearman": 0.42,
        "fold_count": 99,
        "last_calibrated_season": "2099-00",
        "calibration_pending": False,
        "notes": ["sentinel"],
    }
    CacheManager.set(mvp_service.CALIBRATION_CACHE_KEY, sentinel, ttl_seconds=60)

    # Patch calibrate to fail loudly if called — proves the cache short-circuits it
    def _explode(*args, **kwargs):
        raise AssertionError("calibrate should not have been called when cache is warm")
    monkeypatch.setattr(mvp_service, "calibrate_award_case_weights", _explode)

    state = mvp_service._get_calibration_state(db_session)
    assert state["fold_count"] == 99
    assert state["notes"] == ["sentinel"]

    CacheManager.delete(mvp_service.CALIBRATION_CACHE_KEY)


def test_methodology_registry_augments_mvp_with_runtime_calibration(db_session):
    """get_methodology_detail('mvp', db) must surface live calibration state
    in the response's runtime_calibration field."""
    from services.methodology_registry_service import get_methodology_detail

    detail = get_methodology_detail("mvp", db=db_session)
    assert detail.runtime_calibration is not None
    rc = detail.runtime_calibration
    # Empty DB = pending; weights match defaults
    assert rc["calibration_pending"] is True
    assert rc["weights_source"] == "default"
    assert rc["fold_count"] == 0
    assert set(rc["weights"].keys()) == set(MODIFIER_KEYS)


def test_methodology_registry_passes_through_other_domains(db_session):
    """Non-mvp domains must NOT have runtime_calibration populated."""
    from services.methodology_registry_service import get_methodology_detail

    detail = get_methodology_detail("archetype", db=db_session)
    assert detail.runtime_calibration is None
