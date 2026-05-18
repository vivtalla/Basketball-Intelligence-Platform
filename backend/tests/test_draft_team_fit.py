"""Sprint 102 (Stream B) — tests for compute_team_fit_for_prospect.

The team-fit v3 algorithm is exercised heavily by the player-side tests
(test_sprint69_team_fit.py). These tests cover the draft-adapter wrapper:
synthetic SeasonStat construction, position-aware fallback values for
NCAA-missing features (par3, ftr), and the top-N + label thresholds.
"""
from __future__ import annotations

from typing import List
from unittest import mock

import pytest

from services.draft_team_fit_service import (
    FIT_LABEL_BETTER,
    FIT_LABEL_SIMILAR,
    METHODOLOGY_VERSION,
    _build_synthetic_season_stat,
    _fit_label,
    compute_team_fit_for_prospect,
)


def _seed_prospect(db, *, position="F", gp=30, pts_pg=18.0, ts_pct=0.58, usg_pct=24.0):
    from db.models import DraftProspect, DraftProspectStat

    p = DraftProspect(
        external_id=f"test-tf-{position}-{pts_pg}",
        full_name=f"Test Prospect {position}",
        draft_year=2026,
        age_on_draft_day=19.5,
        school="Duke",
        school_type="ncaa",
        primary_position=position,
    )
    db.add(p)
    db.flush()
    db.add(DraftProspectStat(
        prospect_id=p.id,
        season="2025-26",
        league="NCAA D-I",
        gp=gp,
        min_pg=32.0,
        pts_pg=pts_pg,
        reb_pg=6.0,
        ast_pg=4.0,
        stl_pg=1.2,
        blk_pg=0.8,
        tov_pg=2.5,
        ts_pct=ts_pct,
        usg_pct=usg_pct,
        fg3_pct=0.36,
        pace=70.0,
    ))
    db.flush()
    return p


# ── Pure unit tests (no DB) ───────────────────────────────────────────


@pytest.mark.parametrize(
    "score,expected_label",
    [
        (75.0, "better_fit"),
        (FIT_LABEL_BETTER, "better_fit"),  # boundary inclusive
        (FIT_LABEL_BETTER - 0.1, "similar_fit"),
        (60.0, "similar_fit"),
        (FIT_LABEL_SIMILAR, "similar_fit"),  # boundary inclusive
        (FIT_LABEL_SIMILAR - 0.1, "different_fit"),
        (30.0, "different_fit"),
    ],
)
def test_fit_label_thresholds(score, expected_label):
    assert _fit_label(score) == expected_label


def test_synthetic_season_stat_fills_position_defaults(test_db_session):
    """par3 + ftr aren't on DraftProspectStat; fallback values must populate."""
    p = _seed_prospect(test_db_session, position="C")
    stat = p.stats[0]
    synth = _build_synthetic_season_stat(p, stat, "2025-26")
    # par3 + ftr should be filled with center-typical values, not 0/None
    assert synth.par3 > 0.0
    assert synth.ftr > 0.0
    # Guard-typical par3 should be higher than center-typical
    p2 = _seed_prospect(test_db_session, position="PG", pts_pg=20.0)
    synth2 = _build_synthetic_season_stat(p2, p2.stats[0], "2025-26")
    assert synth2.par3 > synth.par3
    # Sentinel team_abbreviation so this row never matches a real team
    assert synth.team_abbreviation == "__PROSPECT__"
    # Negative player_id avoids collision with real players
    assert synth.player_id < 0


def test_synthetic_season_stat_carries_through_basic_stats(test_db_session):
    p = _seed_prospect(test_db_session, position="SG", pts_pg=22.5, ts_pct=0.605, usg_pct=27.0)
    synth = _build_synthetic_season_stat(p, p.stats[0], "2025-26")
    assert synth.pts_pg == pytest.approx(22.5)
    assert synth.ts_pct == pytest.approx(0.605)
    assert synth.usg_pct == pytest.approx(27.0)
    assert synth.season == "2025-26"


# ── DB-backed tests ───────────────────────────────────────────────────


def test_compute_team_fit_handles_missing_translation(test_db_session):
    """A prospect with no DraftProspectStat rows returns [] (doesn't raise)."""
    from db.models import DraftProspect

    p = DraftProspect(
        external_id="test-empty",
        full_name="Empty Prospect",
        draft_year=2026,
        primary_position="F",
        school="Duke",
        school_type="ncaa",
    )
    test_db_session.add(p)
    test_db_session.commit()
    result = compute_team_fit_for_prospect(test_db_session, p)
    assert result == []


def test_compute_team_fit_empty_pool_returns_empty(test_db_session):
    """No qualified NBA rows in the pool → returns [] (doesn't raise)."""
    p = _seed_prospect(test_db_session)
    test_db_session.commit()
    # SQLite test DB has no NBA season_stats; the function should return [].
    result = compute_team_fit_for_prospect(test_db_session, p)
    assert result == []


def test_compute_team_fit_attribution_when_pool_present(test_db_session):
    """When `_qualified_rows_v2` returns rows, every result carries the
    Sprint 102 methodology version. Mocked so the test doesn't need
    a fully-populated NBA season_stats table.
    """
    p = _seed_prospect(test_db_session)
    test_db_session.commit()

    fake_results = [
        # (score, value, overlap, role, value_drivers, role_drivers, overlap_flags)
        (78.0, 60.0, 70.0, 65.0, [], [], []),
    ]
    with (
        mock.patch(
            "services.draft_team_fit_service._qualified_rows_v2",
            return_value=[mock.MagicMock(player_id=1, season="2025-26", team_abbreviation="LAL")],
        ),
        mock.patch(
            "services.draft_team_fit_service._season_norms_v2",
            return_value={},
        ),
        mock.patch(
            "services.draft_team_fit_service._team_rows",
            return_value={"LAL": [mock.MagicMock() for _ in range(8)]},
        ),
        mock.patch(
            "services.draft_team_fit_service._score_team_fit",
            return_value=fake_results[0],
        ),
    ):
        result = compute_team_fit_for_prospect(test_db_session, p, limit=5)

    assert len(result) == 1
    assert result[0].methodology_version == METHODOLOGY_VERSION
    assert result[0].fit_label == "better_fit"  # 78 > FIT_LABEL_BETTER (70)
    assert result[0].team_abbreviation == "LAL"


def test_compute_team_fit_ranks_by_score_desc(test_db_session):
    """Multiple teams scored → results sorted high → low."""
    p = _seed_prospect(test_db_session)
    test_db_session.commit()

    # Map (team_abbr) → (fit_score, ...) — we'll vary score per call.
    scores_iter = iter([
        (45.0, 40.0, 50.0, 45.0, [], [], []),  # PHX
        (82.0, 70.0, 80.0, 75.0, [], [], []),  # LAL
        (65.0, 55.0, 60.0, 58.0, [], [], []),  # BOS
    ])
    with (
        mock.patch(
            "services.draft_team_fit_service._qualified_rows_v2",
            return_value=[mock.MagicMock(player_id=1, season="2025-26", team_abbreviation="LAL")],
        ),
        mock.patch("services.draft_team_fit_service._season_norms_v2", return_value={}),
        mock.patch(
            "services.draft_team_fit_service._team_rows",
            return_value={
                "PHX": [mock.MagicMock() for _ in range(8)],
                "LAL": [mock.MagicMock() for _ in range(8)],
                "BOS": [mock.MagicMock() for _ in range(8)],
            },
        ),
        mock.patch("services.draft_team_fit_service._score_team_fit", side_effect=lambda *a, **k: next(scores_iter)),
    ):
        result = compute_team_fit_for_prospect(test_db_session, p, limit=5)

    # Three teams returned, sorted high → low regardless of call order.
    scores: List[float] = [r.fit_score for r in result]
    assert scores == sorted(scores, reverse=True)


def test_compute_team_fit_respects_limit(test_db_session):
    """limit=2 returns only the top 2 results."""
    p = _seed_prospect(test_db_session)
    test_db_session.commit()

    scores_iter = iter([
        (75.0, 60.0, 70.0, 65.0, [], [], []),
        (65.0, 55.0, 60.0, 58.0, [], [], []),
        (55.0, 45.0, 50.0, 50.0, [], [], []),
        (45.0, 40.0, 45.0, 42.0, [], [], []),
    ])
    with (
        mock.patch(
            "services.draft_team_fit_service._qualified_rows_v2",
            return_value=[mock.MagicMock(player_id=1, season="2025-26", team_abbreviation="LAL")],
        ),
        mock.patch("services.draft_team_fit_service._season_norms_v2", return_value={}),
        mock.patch(
            "services.draft_team_fit_service._team_rows",
            return_value={
                "A": [mock.MagicMock() for _ in range(8)],
                "B": [mock.MagicMock() for _ in range(8)],
                "C": [mock.MagicMock() for _ in range(8)],
                "D": [mock.MagicMock() for _ in range(8)],
            },
        ),
        mock.patch("services.draft_team_fit_service._score_team_fit", side_effect=lambda *a, **k: next(scores_iter)),
    ):
        result = compute_team_fit_for_prospect(test_db_session, p, limit=2)

    assert len(result) == 2
    assert result[0].fit_score >= result[1].fit_score
