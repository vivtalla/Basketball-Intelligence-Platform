"""Sprint 100 (Stream C) — translation v2 + comp v2 + analysis tests.

Tests run against the in-memory SQLite fixture from conftest.py. Each
test seeds the minimum data it needs (a DraftProspect + one stat row)
rather than relying on the global seed.
"""
from __future__ import annotations

import pytest

from services.draft_analysis_service import (
    compute_projected_tier,
    compute_risk_indicators,
    compute_historical_baseline,
)
from services.draft_translation_service_v2 import (
    LEAGUE_STRENGTH,
    SHOOTING_HAIRCUTS_NCAA,
    _age_multiplier,
    _league_strength_key,
    translate_prospect_v2,
)


# ── shared helper ─────────────────────────────────────────────────────


def _seed_prospect(
    db,
    *,
    full_name="Test Prospect",
    age=19.0,
    school="Duke",
    school_type="ncaa",
    league="NCAA D-I",
    gp=30,
    pts_pg=20.0,
    reb_pg=7.0,
    ast_pg=4.0,
    ts_pct=0.62,
    usg_pct=28.0,
    fg3_pct=0.38,
    pace=70.0,
    consensus_rank_float=None,
):
    from db.models import DraftProspect, DraftProspectStat

    p = DraftProspect(
        external_id="test-" + full_name.lower().replace(" ", "-"),
        full_name=full_name,
        draft_year=2026,
        age_on_draft_day=age,
        school=school,
        school_type=school_type,
        primary_position="F",
        consensus_rank_float=consensus_rank_float,
    )
    db.add(p)
    db.flush()
    stat = DraftProspectStat(
        prospect_id=p.id,
        season="2025-26",
        league=league,
        gp=gp,
        pts_pg=pts_pg,
        reb_pg=reb_pg,
        ast_pg=ast_pg,
        ts_pct=ts_pct,
        usg_pct=usg_pct,
        fg3_pct=fg3_pct,
        pace=pace,
    )
    db.add(stat)
    db.flush()
    return p


# ── translation v2 ────────────────────────────────────────────────────


def test_league_strength_key_detects_p6():
    assert _league_strength_key("Duke", "NCAA D-I") == "ncaa_p6"
    assert _league_strength_key("Kansas", "NCAA D-I") == "ncaa_p6"


def test_league_strength_key_falls_back_to_mid_ncaa():
    assert _league_strength_key("Cal Poly", "NCAA D-I") == "ncaa_mid"


def test_league_strength_key_g_league():
    assert _league_strength_key("Ignite", "G League") == "g_league"


def test_league_strength_key_euroleague():
    assert _league_strength_key("Real Madrid", "Euroleague") == "euroleague"


def test_age_multiplier_curve():
    assert _age_multiplier(19) == 1.04
    assert _age_multiplier(20) == 1.00
    assert _age_multiplier(23) == 0.91
    # Edge clamps.
    assert _age_multiplier(16) == _age_multiplier(18) == 1.07
    assert _age_multiplier(30) == _age_multiplier(24) == 0.88


def test_translate_v2_returns_point_intervals(test_db_session):
    p = _seed_prospect(test_db_session)
    result = translate_prospect_v2(test_db_session, p.id)
    assert result is not None
    assert result["source_league"] == "NCAA D-I"
    assert result["league_strength_key"] == "ncaa_p6"
    # pts_per100 should be a {point, lower, upper} dict.
    pts = result["pts_per100"]
    assert isinstance(pts, dict)
    assert "point" in pts and "lower" in pts and "upper" in pts
    assert pts["lower"] < pts["point"] < pts["upper"]
    # TS% should reflect the shooting haircut. Tolerance is 1e-2 because
    # _ci() rounds to 2 decimal places.
    ts = result["ts_pct"]
    assert ts["point"] == pytest.approx(0.62 * SHOOTING_HAIRCUTS_NCAA["ts_pct"], abs=0.01)


def test_translate_v2_widens_intervals_for_small_sample(test_db_session):
    """A 10-GP prospect should get wider CIs than a 30-GP prospect with the same line."""
    small = _seed_prospect(test_db_session, full_name="Small Sample", gp=10)
    big = _seed_prospect(test_db_session, full_name="Big Sample", gp=30)
    r_small = translate_prospect_v2(test_db_session, small.id)
    r_big = translate_prospect_v2(test_db_session, big.id)
    width_small = r_small["pts_per100"]["upper"] - r_small["pts_per100"]["lower"]
    width_big = r_big["pts_per100"]["upper"] - r_big["pts_per100"]["lower"]
    assert width_small > width_big


def test_translate_v2_age_multiplier_affects_volume(test_db_session):
    """A 19-year-old produces a higher projected volume than a 23-year-old
    with identical college line."""
    young = _seed_prospect(test_db_session, full_name="Young Prospect", age=19.0)
    old = _seed_prospect(test_db_session, full_name="Older Prospect", age=23.0)
    r_y = translate_prospect_v2(test_db_session, young.id)
    r_o = translate_prospect_v2(test_db_session, old.id)
    assert r_y["pts_per100"]["point"] > r_o["pts_per100"]["point"]


# ── risk indicators ──────────────────────────────────────────────────


def test_risk_indicators_returns_five_axes_in_range(test_db_session):
    p = _seed_prospect(test_db_session)
    risk = compute_risk_indicators(test_db_session, p)
    for axis in ("age_risk", "sample_risk", "level_risk", "athleticism_risk", "shooting_risk"):
        assert axis in risk
        assert 0.0 <= risk[axis] <= 1.0


def test_age_risk_higher_for_older_prospect(test_db_session):
    young = _seed_prospect(test_db_session, full_name="Young", age=19.0)
    old = _seed_prospect(test_db_session, full_name="Old", age=23.0)
    assert compute_risk_indicators(test_db_session, young)["age_risk"] < \
        compute_risk_indicators(test_db_session, old)["age_risk"]


def test_sample_risk_higher_for_thin_sample(test_db_session):
    thin = _seed_prospect(test_db_session, full_name="Thin", gp=8)
    healthy = _seed_prospect(test_db_session, full_name="Healthy", gp=30)
    assert compute_risk_indicators(test_db_session, thin)["sample_risk"] > \
        compute_risk_indicators(test_db_session, healthy)["sample_risk"]


def test_level_risk_higher_for_weak_conference(test_db_session):
    p6 = _seed_prospect(test_db_session, full_name="P6 Prospect", school="Duke")
    mid = _seed_prospect(test_db_session, full_name="Mid Prospect", school="Some Mid-Major U")
    assert compute_risk_indicators(test_db_session, mid)["level_risk"] > \
        compute_risk_indicators(test_db_session, p6)["level_risk"]


# ── projected tier ───────────────────────────────────────────────────


def test_projected_tier_uses_consensus_rank_when_present(test_db_session):
    lottery = _seed_prospect(test_db_session, full_name="Lottery Pick", consensus_rank_float=4.5)
    second = _seed_prospect(test_db_session, full_name="Second-Round Pick", consensus_rank_float=42.0)
    assert compute_projected_tier(test_db_session, lottery) == "lottery"
    assert compute_projected_tier(test_db_session, second) == "second_round"


def test_projected_tier_undrafted_for_very_deep_rank(test_db_session):
    deep = _seed_prospect(test_db_session, full_name="Deep Sleeper", consensus_rank_float=75.0)
    assert compute_projected_tier(test_db_session, deep) == "undrafted"


def test_projected_tier_unknown_when_no_signal(test_db_session):
    """No consensus rank + no comps in DB → tier is unknown (no false signal)."""
    p = _seed_prospect(test_db_session, full_name="No Signal")
    assert compute_projected_tier(test_db_session, p) == "unknown"


# ── historical baseline ──────────────────────────────────────────────


def test_historical_baseline_insufficient_without_outcomes(test_db_session):
    p = _seed_prospect(test_db_session, full_name="Lonely Prospect")
    baseline = compute_historical_baseline(test_db_session, p, top_k=5)
    assert baseline["insufficient"] is True
    assert baseline["n_with_outcome"] == 0
