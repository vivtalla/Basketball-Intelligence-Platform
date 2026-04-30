"""Sprint 78 FO4 — Tests for the multi-year team arc + aging-curve services."""
from __future__ import annotations

from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    DraftPickAsset,
    Player,
    PlayerContract,
    SeasonStat,
    Team,
)
from models.team_arc import IncomingPick, TeamArcLevers  # noqa: E402
from services.aging_curve_service import (  # noqa: E402
    clear_aging_curve_cache,
    compute_aging_curve,
    project_player_next_n,
)
from services.team_arc_projection_service import project_team_arc  # noqa: E402


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSession()


def _seed_team_with_roster(session, abbr: str = "BOS"):
    team = Team(id=1610612738, abbreviation=abbr, name="Boston Celtics")
    session.add(team)

    # Three rostered players, varied positions and ages.
    players_data = [
        # (id, name, pos, birth_year)
        # _player_age_at_season uses season_start_year + 1 - birth_year.
        (1001, "Alpha Guard", "PG", 1996),       # age 29 in 2024-25
        (1002, "Bravo Forward", "SF", 1998),     # age 27 in 2024-25
        (1003, "Charlie Center", "C", 1992),     # age 33 in 2024-25
    ]
    for pid, name, pos, by in players_data:
        session.add(Player(
            id=pid,
            full_name=name,
            first_name=name.split(" ")[0],
            last_name=name.split(" ")[1],
            team_id=team.id,
            is_active=True,
            position=pos,
            birth_date="{0}-06-15".format(by),
        ))

    # Seed many years of league-wide SeasonStat history so the aging curve has
    # samples at every age. We synthesize stats for 100 synthetic players.
    for synth_id in range(2000, 2100):
        # Assign each synthetic player to a position bucket cycle.
        pos_cycle = ["PG", "SF", "C", "PF", "SG"][synth_id % 5]
        birth_year = 1990 + (synth_id % 10)
        session.add(Player(
            id=synth_id,
            full_name="Synth {0}".format(synth_id),
            first_name="Synth",
            last_name=str(synth_id),
            is_active=False,
            position=pos_cycle,
            birth_date="{0}-04-15".format(birth_year),
        ))
        for season_year in range(2010, 2025):
            age = season_year + 1 - birth_year
            if age < 19 or age > 38:
                continue
            # Simple arc: peak at 27.
            peak_factor = 1.0 - abs(age - 27) * 0.03
            session.add(SeasonStat(
                player_id=synth_id,
                season="{0}-{1:02d}".format(season_year, (season_year + 1) % 100),
                team_abbreviation="ZZZ",
                is_playoff=False,
                gp=70,
                pts_pg=18.0 * peak_factor,
                ts_pct=0.55 * peak_factor,
                usg_pct=22.0 * peak_factor,
                min_pg=30.0 * peak_factor,
                ws=6.0 * peak_factor,
                min_total=2100.0 * peak_factor,
            ))

    # Seed 2024-25 SeasonStat rows for the actual roster.
    roster_stats = [
        # (id, pts, ts, ws, min_total, min_pg, usg)
        (1001, 24.0, 0.58, 8.0, 2400, 33.0, 28.0),
        (1002, 18.0, 0.55, 5.0, 2100, 30.0, 22.0),
        (1003, 14.0, 0.60, 4.5, 1800, 26.0, 19.0),
    ]
    for pid, pts, ts, ws, mtot, mpg, usg in roster_stats:
        session.add(SeasonStat(
            player_id=pid,
            season="2024-25",
            team_abbreviation=abbr,
            is_playoff=False,
            gp=72,
            pts_pg=pts,
            ts_pct=ts,
            ws=ws,
            min_total=mtot,
            min_pg=mpg,
            usg_pct=usg,
        ))

    session.commit()
    return team


def test_compute_aging_curve_returns_position_bucket_with_samples():
    """Aging curve has points across the expected age range with samples."""
    session = _make_session()
    try:
        clear_aging_curve_cache()
        _seed_team_with_roster(session)
        curve = compute_aging_curve(session, position="PG")

        # Curve should be either the G bucket or fall back to "all" if sparse.
        assert curve.position_bucket in {"G", "all"}
        assert len(curve.points) >= 5
        # At least one point should sit in the prime age range.
        prime_points = [p for p in curve.points if 24 <= p.age <= 30]
        assert prime_points, "expected aging curve to cover prime ages"
        for point in prime_points:
            assert point.sample_size >= 1
            assert point.pts_pg is not None and point.pts_pg > 0
    finally:
        session.close()


def test_project_player_next_n_applies_aging_decline():
    """A 32-year-old center should not project as young as a 26-year-old wing."""
    session = _make_session()
    try:
        clear_aging_curve_cache()
        _seed_team_with_roster(session)

        center_proj = project_player_next_n(session, player_id=1003, n_years=3)
        guard_proj = project_player_next_n(session, player_id=1001, n_years=3)

        assert len(center_proj) == 4  # year 0..3
        assert len(guard_proj) == 4

        # Year 0 must mirror the seeded base stats.
        assert center_proj[0].pts_pg == pytest.approx(14.0, abs=0.01)
        assert guard_proj[0].pts_pg == pytest.approx(24.0, abs=0.01)

        # Ages advance correctly.
        assert center_proj[0].age == 33
        assert center_proj[3].age == 36
        assert guard_proj[3].age == 32

        # By year 3 the 36-year-old center should be at-or-below his year-0
        # pts_pg (modest decline expected, never massive growth).
        assert center_proj[3].pts_pg is not None
        assert center_proj[3].pts_pg <= center_proj[0].pts_pg + 0.5
    finally:
        session.close()


def test_project_team_arc_returns_n_year_projection():
    """`project_team_arc` returns 4 year-objects (year 0..3) with rosters."""
    session = _make_session()
    try:
        clear_aging_curve_cache()
        _seed_team_with_roster(session)
        response = project_team_arc(session, team_abbr="BOS", n_years=3)

        assert response.team_abbreviation == "BOS"
        assert len(response.years) == 4
        for year_idx, year in enumerate(response.years):
            assert year.year_offset == year_idx
            assert year.season_label.startswith("20")
            # Every roster summary row must have a player_id.
            assert all(row.player_id for row in year.roster_summary) or year.roster_summary == []

        # Year 0 should be near a sensible WS aggregate (>0).
        assert response.years[0].win_share_total is not None
        assert response.years[0].win_share_total > 0.0
        # No PlayerContract data was seeded so cap_state is placeholder.
        assert all(state.has_data is False for state in response.cap_state)
        assert any("PlayerContract" in w for w in response.warnings)
    finally:
        session.close()


def test_project_team_arc_with_levers_adds_pick_and_release():
    """Levers: dropping a player and adding a pick changes year-1 roster size."""
    session = _make_session()
    try:
        clear_aging_curve_cache()
        team = _seed_team_with_roster(session)

        # Add a contract to verify cap_state.has_data flips on for 2025-26.
        session.add(PlayerContract(
            player_id=1001,
            team_id=team.id,
            season="2025-26",
            salary=42_000_000,
            years_remaining=2,
        ))
        # Add an owned pick we can verify auto-loads.
        session.add(DraftPickAsset(
            draft_year=2025,
            round=1,
            owner_team_id=team.id,
            origin_team_id=team.id,
            expected_slot_low=14,
            expected_slot_high=18,
        ))
        session.commit()

        levers = TeamArcLevers(
            outgoing_releases=[1003],
            incoming_picks=[
                IncomingPick(
                    draft_year=2025,
                    round=1,
                    expected_slot_low=8,
                    expected_slot_high=12,
                ),
            ],
        )
        response = project_team_arc(
            session,
            team_abbr="BOS",
            n_years=3,
            levers=levers,
        )

        # Year 0 still includes the released player.
        year0_ids = {row.player_id for row in response.years[0].roster_summary}
        assert 1003 in year0_ids
        # Year 1 should NOT include the released player.
        year1_ids = {row.player_id for row in response.years[1].roster_summary}
        assert 1003 not in year1_ids
        # Year 1 should include a synthetic pick row (negative id).
        assert any(pid < 0 for pid in year1_ids)

        # Cap state for 2025-26 should now report has_data=True.
        cap_2025 = next(c for c in response.cap_state if c.season == "2025-26")
        assert cap_2025.has_data is True
        assert cap_2025.total_committed == 42_000_000

        # Levers applied list captured the release + pick.
        assert any("release" in label for label in response.levers_applied)
        assert any("pick" in label for label in response.levers_applied)
    finally:
        session.close()
