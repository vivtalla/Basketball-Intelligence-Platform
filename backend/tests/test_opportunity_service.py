from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import LineupStats, Player, PlayerOnOff, SeasonStat, Team  # noqa: E402
from services.opportunity_service import (  # noqa: E402
    METHODOLOGY_VERSION,
    MIN_LINEUP_POSSESSIONS,
    WEIGHTS,
    Z_CAP,
    build_opportunity_report,
)


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def seed_pool(session, season="2025-26"):
    """Seed a 12-player pool across three teams spanning guards/forwards/centers."""
    okc = Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder")
    bos = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
    session.add_all([okc, bos])

    specs = [
        # (id, name, position, team_abbr, min_pg, usg_pct, ts_pct, off_rating, def_rating,
        #  net_rating, pts_pg, ast_pg, tov_pg, par3, ftr, efg_pct, gp)
        (1, "OKC Efficient Guard", "SG", "OKC", 32.0, 18.0, 0.62, 118.0, 108.0, 10.0, 17.0, 4.0, 2.0, 0.42, 0.28, 0.58, 62),
        (2, "OKC Heavy Guard", "PG", "OKC", 35.0, 31.0, 0.56, 115.0, 110.0, 5.0, 28.0, 8.0, 3.0, 0.35, 0.30, 0.54, 60),
        (3, "OKC Forward", "SF", "OKC", 30.0, 22.0, 0.58, 114.0, 109.0, 5.0, 18.0, 3.0, 1.5, 0.40, 0.25, 0.55, 58),
        (4, "OKC Center", "C", "OKC", 28.0, 20.0, 0.60, 120.0, 106.0, 14.0, 16.0, 2.0, 1.3, 0.08, 0.35, 0.62, 60),
        (5, "OKC Bench Guard", "SG", "OKC", 18.0, 17.0, 0.50, 108.0, 112.0, -4.0, 10.0, 2.5, 1.5, 0.44, 0.20, 0.50, 50),
        (6, "BOS Star Guard", "PG", "BOS", 34.0, 28.0, 0.61, 119.0, 107.0, 12.0, 24.0, 6.0, 2.5, 0.43, 0.30, 0.58, 60),
        (7, "BOS Wing", "SF", "BOS", 32.0, 25.0, 0.59, 116.0, 108.0, 8.0, 22.0, 4.0, 2.0, 0.42, 0.27, 0.56, 60),
        (8, "BOS Big", "C", "BOS", 30.0, 23.0, 0.57, 115.0, 109.0, 6.0, 15.0, 2.0, 1.5, 0.10, 0.33, 0.58, 59),
        (9, "BOS Sixth", "SG", "BOS", 22.0, 19.0, 0.54, 112.0, 110.0, 2.0, 13.0, 3.0, 1.8, 0.40, 0.22, 0.52, 58),
        (10, "BOS Reserve PF", "PF", "BOS", 20.0, 16.0, 0.52, 110.0, 111.0, -1.0, 9.0, 1.5, 1.2, 0.33, 0.23, 0.51, 55),
        (11, "OKC Sub-threshold", "SG", "OKC", 8.0, 15.0, 0.48, 104.0, 114.0, -10.0, 4.0, 1.0, 0.8, 0.40, 0.18, 0.48, 25),
        (12, "OKC Other", "G-F", "OKC", 24.0, 21.0, 0.57, 112.0, 110.0, 2.0, 14.0, 3.0, 2.0, 0.42, 0.24, 0.53, 55),
    ]

    for (
        pid, name, pos, team_abbr, mpg, usg, ts, off, drtg, nr, pts, ast, tov,
        par3, ftr, efg, gp,
    ) in specs:
        team = okc if team_abbr == "OKC" else bos
        session.add(Player(id=pid, full_name=name, position=pos, team=team, team_id=team.id))
        session.add(SeasonStat(
            player_id=pid,
            season=season,
            team_abbreviation=team_abbr,
            is_playoff=False,
            gp=gp,
            min_pg=mpg,
            usg_pct=usg,
            ts_pct=ts,
            off_rating=off,
            def_rating=drtg,
            net_rating=nr,
            pts_pg=pts,
            ast_pg=ast,
            tov_pg=tov,
            par3=par3,
            ftr=ftr,
            efg_pct=efg,
        ))

    # On/off data: OKC Efficient Guard (id=1) has a strong on/off swing.
    session.add(PlayerOnOff(
        player_id=1, season=season, is_playoff=False,
        on_minutes=1400.0, off_minutes=500.0,
        on_net_rating=12.0, off_net_rating=3.0, on_off_net=9.0,
        on_ortg=118.0, on_drtg=106.0, off_ortg=110.0, off_drtg=107.0,
    ))
    # OKC Heavy Guard (id=2) — smaller on/off swing.
    session.add(PlayerOnOff(
        player_id=2, season=season, is_playoff=False,
        on_minutes=1600.0, off_minutes=300.0,
        on_net_rating=7.0, off_net_rating=6.0, on_off_net=1.0,
    ))
    # OKC Center (id=4) — negative on/off (team plays slightly worse with him).
    session.add(PlayerOnOff(
        player_id=4, season=season, is_playoff=False,
        on_minutes=1100.0, off_minutes=700.0,
        on_net_rating=5.0, off_net_rating=8.0, on_off_net=-3.0,
    ))
    # BOS Star Guard (id=6) — strong.
    session.add(PlayerOnOff(
        player_id=6, season=season, is_playoff=False,
        on_minutes=1500.0, off_minutes=450.0,
        on_net_rating=11.0, off_net_rating=4.0, on_off_net=7.0,
    ))

    # Lineup stats: 5-man lineup with OKC core (1,2,3,4,5) — 300 possessions.
    session.add(LineupStats(
        lineup_key="-".join(str(p) for p in sorted([1, 2, 3, 4, 5])),
        season=season, team_id=okc.id,
        minutes=220.0, net_rating=11.0, ortg=118.0, drtg=107.0, possessions=300,
    ))
    # A 4-man slice 1,2,3,4 — 200 poss (not in real NBA but we use for synergy test).
    session.add(LineupStats(
        lineup_key="-".join(str(p) for p in sorted([1, 2, 3, 4])),
        season=season, team_id=okc.id,
        minutes=130.0, net_rating=13.5, ortg=120.0, drtg=106.5, possessions=200,
    ))
    # A weak-sample lineup that should be excluded (50 poss).
    session.add(LineupStats(
        lineup_key="-".join(str(p) for p in sorted([1, 5, 11])),
        season=season, team_id=okc.id,
        minutes=30.0, net_rating=-5.0, ortg=100.0, drtg=105.0, possessions=50,
    ))
    # BOS lineup.
    session.add(LineupStats(
        lineup_key="-".join(str(p) for p in sorted([6, 7, 8, 9, 10])),
        season=season, team_id=bos.id,
        minutes=200.0, net_rating=8.0, ortg=115.0, drtg=107.0, possessions=280,
    ))

    session.commit()


def test_report_returns_methodology_and_ranked_rows():
    session = make_session()
    try:
        seed_pool(session)
        report = build_opportunity_report(session, season="2025-26", team=None, min_minutes=15.0)
        assert report.methodology.version == METHODOLOGY_VERSION
        assert report.methodology.weights == WEIGHTS
        assert report.methodology.z_score_cap == Z_CAP
        assert report.methodology.min_lineup_possessions == MIN_LINEUP_POSSESSIONS
        assert len(report.rows) > 0
        # Top rows are sorted by opportunity_score desc.
        scores = [r.opportunity_score for r in report.rows]
        assert scores == sorted(scores, reverse=True)
    finally:
        session.close()


def test_min_minutes_gate_excludes_low_sample_players():
    session = make_session()
    try:
        seed_pool(session)
        report = build_opportunity_report(session, season="2025-26", team=None, min_minutes=15.0)
        ids = {r.player_id for r in report.rows}
        # Player 11 has 8 MPG, below 15 cutoff.
        assert 11 not in ids
    finally:
        session.close()


def test_team_filter_and_team_rollup():
    session = make_session()
    try:
        seed_pool(session)
        report = build_opportunity_report(session, season="2025-26", team="OKC", min_minutes=15.0)
        assert report.team == "OKC"
        assert all(r.team_abbreviation == "OKC" for r in report.rows)
        assert report.team_rollup is not None
        assert report.team_rollup.team_abbreviation == "OKC"
        assert report.team_rollup.sample_size == len(report.rows)
        # Team-context score is present when team is filtered.
        assert all(r.team_opportunity_score is not None for r in report.rows)
    finally:
        session.close()


def test_position_filter_keeps_only_that_bucket():
    session = make_session()
    try:
        seed_pool(session)
        report = build_opportunity_report(
            session, season="2025-26", team=None, min_minutes=15.0, position="G",
        )
        assert report.position_filter == "G"
        assert all(r.position_bucket == "G" for r in report.rows)
    finally:
        session.close()


def test_z_scores_are_capped_at_cap():
    session = make_session()
    try:
        seed_pool(session)
        report = build_opportunity_report(session, season="2025-26", team=None, min_minutes=15.0)
        for row in report.rows:
            for driver in row.driver_contributions:
                assert -Z_CAP - 1e-6 <= driver.z_score <= Z_CAP + 1e-6, (
                    "signal {0} z-score {1} exceeds cap ±{2}".format(
                        driver.signal, driver.z_score, Z_CAP
                    )
                )
    finally:
        session.close()


def test_driver_contributions_cover_all_signals_sorted_by_magnitude():
    session = make_session()
    try:
        seed_pool(session)
        report = build_opportunity_report(session, season="2025-26", team=None, min_minutes=15.0)
        expected_signals = set(WEIGHTS.keys())
        for row in report.rows:
            emitted = {d.signal for d in row.driver_contributions}
            assert emitted == expected_signals
            # Sorted by absolute weighted contribution desc.
            mags = [abs(d.weighted_contribution) for d in row.driver_contributions]
            assert mags == sorted(mags, reverse=True)
    finally:
        session.close()


def test_top_driver_is_highest_positive_contribution():
    session = make_session()
    try:
        seed_pool(session)
        report = build_opportunity_report(session, season="2025-26", team="OKC", min_minutes=15.0)
        for row in report.rows:
            positive = [d for d in row.driver_contributions if d.weighted_contribution > 0]
            if positive:
                top = max(positive, key=lambda d: d.weighted_contribution)
                assert row.top_driver == top.signal
            else:
                assert row.top_driver is None
    finally:
        session.close()


def test_cohort_percentile_within_0_100():
    session = make_session()
    try:
        seed_pool(session)
        report = build_opportunity_report(session, season="2025-26", team=None, min_minutes=15.0)
        for row in report.rows:
            assert row.cohort_percentile is not None
            assert 0.0 <= row.cohort_percentile <= 100.0
    finally:
        session.close()


def test_top_teammate_and_synergy_lift_respect_possession_gate():
    session = make_session()
    try:
        seed_pool(session)
        report = build_opportunity_report(session, season="2025-26", team="OKC", min_minutes=15.0)
        okc_guard = next(r for r in report.rows if r.player_id == 1)
        # Weak-sample lineup (50 poss) would have teammate 11; must be excluded.
        if okc_guard.top_teammate is not None:
            assert okc_guard.top_teammate.shared_possessions >= MIN_LINEUP_POSSESSIONS
    finally:
        session.close()


def test_directional_hint_only_fires_with_confidence_and_signals():
    session = make_session()
    try:
        seed_pool(session)
        report = build_opportunity_report(session, season="2025-26", team=None, min_minutes=15.0)
        hinted = [r for r in report.rows if r.directional_hint is not None]
        for row in hinted:
            assert row.confidence in ("high", "medium")
            assert "efficiency_load_gap" in row.hint_basis
            assert "team_impact_swing" in row.hint_basis
    finally:
        session.close()


def test_empty_pool_yields_empty_rows_with_warning():
    session = make_session()
    try:
        seed_pool(session)
        report = build_opportunity_report(
            session, season="2020-21", team=None, min_minutes=15.0
        )
        assert report.rows == []
        assert any("No qualifying players" in w for w in report.warnings)
        assert report.methodology is not None
    finally:
        session.close()


def test_confidence_reflects_minutes_and_on_off_sample():
    session = make_session()
    try:
        seed_pool(session)
        report = build_opportunity_report(session, season="2025-26", team="OKC", min_minutes=15.0)
        guard = next(r for r in report.rows if r.player_id == 1)
        # 32 MPG + 1400 on-minutes → high confidence.
        assert guard.confidence == "high"
    finally:
        session.close()


def test_role_fit_includes_cohort_reference_values():
    session = make_session()
    try:
        seed_pool(session)
        report = build_opportunity_report(session, season="2025-26", team=None, min_minutes=15.0)
        for row in report.rows:
            assert row.role_fit is not None
            # Cohort averages are always populated, even if player attrs are None.
            assert row.role_fit.par3_bucket_avg is not None
            assert row.role_fit.efg_bucket_avg is not None
    finally:
        session.close()
