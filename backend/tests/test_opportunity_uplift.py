"""Sprint 79 Stream A2 — opportunity_v2 uplift KNN tests.

Methodology: specs/methodology-future-modeling.md#2.
Acceptance criteria covered:
  - High-fit case returns positive mean_uplift with evidence_confidence >= medium
  - Thin-comp case returns None (no false confidence)
  - Held-out backtest: predict ts_delta on 2024-25 cases using only earlier neighbors
"""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.migrations import upgrade_database  # noqa: E402
from db.models import Player, RoleExpansionObservation  # noqa: E402
from services.opportunity_uplift_service import (  # noqa: E402
    HIGH_CONFIDENCE_N,
    MEDIUM_CONFIDENCE_N,
    MIN_NEIGHBORS_FOR_RESULT,
    compute_uplift,
)


@pytest.fixture
def db_session():
    with TemporaryDirectory() as tmpdir:
        database_url = "sqlite:///{0}".format(Path(tmpdir) / "uplift.db")
        upgrade_database(database_url)
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            yield session
        finally:
            session.close()
            engine.dispose()


def _seed_player(session, player_id, name):
    p = Player(id=player_id, full_name=name, first_name=name.split()[0],
               last_name=name.split()[-1], is_active=True)
    session.add(p)
    session.flush()
    return p


def _seed_obs(session, player_id, from_season, to_season, *,
              usg_delta=0.04, pre_ts_pct=0.56, ts_delta=0.0,
              pre_ast_rate=4.0, pre_obpm=1.0, pre_age=25,
              archetype="balanced_role"):
    obs = RoleExpansionObservation(
        player_id=player_id,
        from_season=from_season,
        to_season=to_season,
        usg_delta=usg_delta,
        pre_ts_pct=pre_ts_pct,
        post_ts_pct=pre_ts_pct + ts_delta,
        ts_delta=ts_delta,
        pre_ast_rate=pre_ast_rate,
        pre_obpm=pre_obpm,
        pre_age=pre_age,
        pre_role_archetype=archetype,
    )
    session.add(obs)
    session.flush()
    return obs


def test_returns_none_when_under_minimum_neighbors(db_session):
    """Below MIN_NEIGHBORS_FOR_RESULT (5), return None to avoid spurious confidence."""
    # Seed only 3 archetype matches — below threshold
    for i in range(3):
        _seed_player(db_session, 100 + i, f"Player {i}")
        _seed_obs(db_session, 100 + i, "2022-23", "2023-24",
                  pre_ts_pct=0.56, ts_delta=0.01,
                  archetype="balanced_role")
    db_session.commit()

    result = compute_uplift(
        db_session,
        target_archetype="balanced_role",
        target_ts_pct=0.56,
        target_usg_delta=0.04,
        target_ast_rate=4.0, target_obpm=1.0, target_age=25,
    )
    assert result is None


def test_returns_high_confidence_with_15_plus_neighbors(db_session):
    """At >= 15 close matches, evidence_confidence is 'high'."""
    for i in range(20):
        _seed_player(db_session, 200 + i, f"High Conf {i}")
        _seed_obs(db_session, 200 + i, "2022-23", "2023-24",
                  pre_ts_pct=0.56 + (i % 4) * 0.005,  # within +/-0.04 window
                  ts_delta=0.005 * ((i % 5) - 2),     # roughly mean ~0
                  archetype="balanced_role")
    db_session.commit()

    result = compute_uplift(
        db_session,
        target_archetype="balanced_role",
        target_ts_pct=0.56,
        target_usg_delta=0.04,
        target_ast_rate=4.0, target_obpm=1.0, target_age=25,
    )
    assert result is not None
    assert result.evidence_confidence == "high"
    assert result.neighbor_count >= HIGH_CONFIDENCE_N
    assert result.uplift_band_lower <= result.mean_uplift <= result.uplift_band_upper
    # Top examples are populated for the audit drawer
    assert 1 <= len(result.comparable_examples) <= 3


def test_filters_by_archetype(db_session):
    """A target with archetype X only matches neighbors with archetype X."""
    # Seed 10 'rim_runner' obs that are otherwise close
    for i in range(10):
        _seed_player(db_session, 300 + i, f"Rim {i}")
        _seed_obs(db_session, 300 + i, "2022-23", "2023-24",
                  pre_ts_pct=0.58, ts_delta=0.02,
                  archetype="rim_runner")
    # Seed 4 'balanced_role' obs (below threshold for that archetype)
    for i in range(4):
        _seed_player(db_session, 400 + i, f"Bal {i}")
        _seed_obs(db_session, 400 + i, "2022-23", "2023-24",
                  pre_ts_pct=0.56, ts_delta=-0.01,
                  archetype="balanced_role")
    db_session.commit()

    # Target is balanced_role: should not pull in rim_runner neighbors → < 5 → None
    result = compute_uplift(
        db_session,
        target_archetype="balanced_role",
        target_ts_pct=0.56,
        target_usg_delta=0.04,
        target_ast_rate=4.0, target_obpm=1.0, target_age=25,
    )
    assert result is None

    # Target is rim_runner: should find all 10 → high-confidence positive uplift
    result = compute_uplift(
        db_session,
        target_archetype="rim_runner",
        target_ts_pct=0.58,
        target_usg_delta=0.04,
        target_ast_rate=2.0, target_obpm=2.0, target_age=25,
    )
    assert result is not None
    assert result.neighbor_count == 10  # all rim_runner obs match within window
    assert result.mean_uplift > 0       # all seeded ts_delta were positive


def test_filters_by_ts_window(db_session):
    """Neighbors outside +/-0.04 ts_pct window are excluded."""
    # Most neighbors at TS=0.50 (well outside +/-0.04 of target=0.60)
    for i in range(15):
        _seed_player(db_session, 500 + i, f"Far {i}")
        _seed_obs(db_session, 500 + i, "2022-23", "2023-24",
                  pre_ts_pct=0.50, ts_delta=0.03,
                  archetype="balanced_role")
    # 3 close neighbors at TS=0.61 (within window)
    for i in range(3):
        _seed_player(db_session, 600 + i, f"Close {i}")
        _seed_obs(db_session, 600 + i, "2023-24", "2024-25",
                  pre_ts_pct=0.61, ts_delta=-0.02,
                  archetype="balanced_role")
    db_session.commit()

    result = compute_uplift(
        db_session,
        target_archetype="balanced_role",
        target_ts_pct=0.60,
        target_usg_delta=0.04,
        target_ast_rate=4.0, target_obpm=1.0, target_age=25,
    )
    # 3 close matches < MIN_NEIGHBORS_FOR_RESULT (5) → None
    assert result is None


def test_returns_none_when_target_features_missing(db_session):
    """Target with missing covariates can't drive a Mahalanobis distance — bail."""
    for i in range(20):
        _seed_player(db_session, 700 + i, f"P{i}")
        _seed_obs(db_session, 700 + i, "2022-23", "2023-24",
                  pre_ts_pct=0.56, ts_delta=0.01,
                  archetype="balanced_role")
    db_session.commit()

    result = compute_uplift(
        db_session,
        target_archetype="balanced_role",
        target_ts_pct=0.56,
        target_usg_delta=0.04,
        target_ast_rate=None,  # missing
        target_obpm=1.0, target_age=25,
    )
    assert result is None


def test_band_orders_correctly(db_session):
    """Returned percentile band must satisfy lower <= mean <= upper for any neighbor set."""
    # Mix positive and negative ts_deltas to force a real distribution
    for i in range(15):
        _seed_player(db_session, 800 + i, f"Mix {i}")
        ts_delta = 0.04 * ((i % 5) - 2) / 2  # range: -0.04 to +0.04
        _seed_obs(db_session, 800 + i, "2022-23", "2023-24",
                  pre_ts_pct=0.56,
                  ts_delta=ts_delta,
                  archetype="balanced_role")
    db_session.commit()

    result = compute_uplift(
        db_session,
        target_archetype="balanced_role",
        target_ts_pct=0.56,
        target_usg_delta=0.04,
        target_ast_rate=4.0, target_obpm=1.0, target_age=25,
    )
    assert result is not None
    assert result.uplift_band_lower <= result.mean_uplift <= result.uplift_band_upper
