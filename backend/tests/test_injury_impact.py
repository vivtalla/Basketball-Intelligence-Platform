"""Tests for FO5 injury impact + duration model (Sprint 78)."""
from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    Player,
    PlayerInjury,
    PlayerInjuryHistory,
    PlayerOnOff,
    SeasonStat,
    Team,
    TeamSeasonStat,
)
from services.availability_impact_service import compute_team_availability_impact  # noqa: E402
from services.injury_duration_model import (  # noqa: E402
    HARDCODED_PRIOR,
    expected_duration,
    find_similar_past_injuries,
)


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _seed_team_with_players(session):
    team = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks", city="Atlanta")
    session.add(team)
    star = Player(
        id=2544, full_name="LeBron James", first_name="LeBron", last_name="James",
        team_id=team.id, is_active=True, position="F", jersey="6", birth_date="1984-12-30",
    )
    starter = Player(
        id=201939, full_name="Stephen Curry", first_name="Stephen", last_name="Curry",
        team_id=team.id, is_active=True, position="G", jersey="30", birth_date="1988-03-14",
    )
    bench = Player(
        id=1628378, full_name="Donovan Mitchell", first_name="Donovan", last_name="Mitchell",
        team_id=team.id, is_active=True, position="G", jersey="45", birth_date="1996-09-07",
    )
    deep_bench = Player(
        id=1629029, full_name="Luka Doncic", first_name="Luka", last_name="Doncic",
        team_id=team.id, is_active=True, position="G", jersey="77", birth_date="1999-02-28",
    )
    session.add_all([star, starter, bench, deep_bench])
    session.add_all([
        SeasonStat(player_id=star.id, season="2024-25", team_abbreviation="ATL",
                   is_playoff=False, gp=50, pts_pg=26.0, min_pg=35.0, bpm=6.0),
        SeasonStat(player_id=starter.id, season="2024-25", team_abbreviation="ATL",
                   is_playoff=False, gp=55, pts_pg=22.0, min_pg=33.0, bpm=4.5),
        SeasonStat(player_id=bench.id, season="2024-25", team_abbreviation="ATL",
                   is_playoff=False, gp=60, pts_pg=14.0, min_pg=24.0, bpm=1.0),
        SeasonStat(player_id=deep_bench.id, season="2024-25", team_abbreviation="ATL",
                   is_playoff=False, gp=58, pts_pg=9.0, min_pg=19.0, bpm=-0.5),
    ])
    session.add_all([
        PlayerOnOff(player_id=star.id, season="2024-25", is_playoff=False,
                    on_minutes=1750.0, off_minutes=1000.0, on_off_net=8.0),
        PlayerOnOff(player_id=starter.id, season="2024-25", is_playoff=False,
                    on_minutes=1815.0, off_minutes=1000.0, on_off_net=5.5),
        PlayerOnOff(player_id=bench.id, season="2024-25", is_playoff=False,
                    on_minutes=1440.0, off_minutes=1100.0, on_off_net=2.0),
        PlayerOnOff(player_id=deep_bench.id, season="2024-25", is_playoff=False,
                    on_minutes=1100.0, off_minutes=1300.0, on_off_net=-1.0),
    ])
    session.add(TeamSeasonStat(team_id=team.id, season="2024-25", is_playoff=False,
                               gp=60, w=40, l=20, w_pct=0.667, net_rating=4.5))
    session.commit()
    return team, star, starter, bench, deep_bench


def _seed_history_cohort(session, body_part: str, count: int, *, age_at_start: float = 30.0):
    """Seed `count` historical knee-style injuries with games_missed in [10, 20]."""
    base_player_id = 9000
    # Need at least one Player row so the FK constraint isn't violated.
    if session.query(Player).filter(Player.id == base_player_id).count() == 0:
        session.add(Player(id=base_player_id, full_name="Cohort Player Zero",
                           is_active=False, position="F"))
    for i in range(count):
        session.add(PlayerInjuryHistory(
            player_id=base_player_id,
            season="2023-24",
            body_part=body_part,
            severity="moderate",
            started_on=date(2024, 1, 1) + timedelta(days=i * 4),
            resolved_on=date(2024, 1, 20) + timedelta(days=i * 4),
            games_missed=10 + i,  # 10, 11, 12, ... — median lands inside cohort
            age_at_start=age_at_start,
            is_recurring=False,
            source="seed_synthetic",
        ))
    session.commit()


def test_expected_duration_returns_sensible_median_from_seeded_cohort():
    session = _make_session()
    try:
        # 8 knee injuries with games_missed 10..17 → median 13/14 (sample-size>5).
        _seed_history_cohort(session, body_part="knee", count=8, age_at_start=30.0)
        estimate = expected_duration(session, body_part="knee", age=30.0, is_recurring=False)
        assert estimate.is_fallback is False, "expected empirical estimate, got fallback"
        assert estimate.sample_size == 8
        # Median of [10,11,12,13,14,15,16,17] is 13 or 14 depending on interpolation.
        assert 12 <= estimate.median_games <= 15
        assert estimate.p25_games < estimate.median_games < estimate.p75_games
        # The mean of 10..17 is 13.5; allow small float drift.
        assert abs(estimate.mean_games - 13.5) < 0.6
        # Cohort metadata should reflect the matched filter.
        assert estimate.cohort_age_low is not None and estimate.cohort_age_high is not None
    finally:
        session.close()


def test_expected_duration_falls_back_to_prior_when_sample_too_small():
    session = _make_session()
    try:
        # Only 3 hamstring rows — below MIN_SAMPLE=5 with the strict cohort.
        # We additionally target a body_part that has no rows at all so the
        # tier-3 (drop age band) cohort is also empty and we hit the prior.
        estimate = expected_duration(session, body_part="hamstring", age=27.0, is_recurring=False)
        assert estimate.is_fallback is True
        assert estimate.fallback_reason == "hardcoded_prior"
        assert estimate.sample_size == 0
        assert estimate.median_games == HARDCODED_PRIOR["hamstring"]
        assert estimate.p25_games < estimate.median_games < estimate.p75_games
    finally:
        session.close()


def test_team_availability_impact_returns_negative_net_delta_when_starter_is_out():
    session = _make_session()
    try:
        team, star, starter, bench, deep_bench = _seed_team_with_players(session)
        # LeBron is OUT with a hamstring strain. He has on_off_net=8.0
        # weighted by minute share, so removing him should be a clearly
        # negative net-rating delta.
        report_date = date(2025, 4, 1)
        session.add(PlayerInjury(
            player_id=star.id,
            team_id=team.id,
            report_date=report_date,
            return_date=report_date + timedelta(days=10),
            injury_type="Hamstring",
            injury_status="Out",
            detail="Left hamstring strain",
            season="2024-25",
        ))
        # Curry is questionable — should also be flagged but not OUT.
        session.add(PlayerInjury(
            player_id=starter.id,
            team_id=team.id,
            report_date=report_date,
            injury_type="Ankle",
            injury_status="Questionable",
            detail="Right ankle soreness",
            season="2024-25",
        ))
        # Seed enough hamstring history rows to force an empirical estimate
        # for the LeBron projection (so the test also exercises the
        # duration-model passthrough on the impact response).
        _seed_history_cohort(session, body_part="hamstring", count=8, age_at_start=39.0)
        session.commit()

        impact = compute_team_availability_impact(session, team_id=team.id, season="2024-25")
        assert impact.out_count == 1
        assert impact.questionable_count == 1
        assert impact.sidelined_minutes_per_game > 0
        assert impact.net_rating_delta is not None
        assert impact.net_rating_delta < 0, "expected negative swing when star is out"
        # Healthy net rating from TeamSeasonStat survives the projection.
        assert impact.healthy_net_rating == 4.5
        assert impact.projected_net_rating is not None
        assert impact.projected_net_rating < impact.healthy_net_rating
        # Highest-impact sidelined player surfaces first.
        assert impact.sidelined_players[0].player_id == star.id
        # LeBron's projection should carry an empirical (non-fallback) duration
        # estimate because we seeded the hamstring cohort.
        assert impact.sidelined_players[0].expected_duration is not None
        assert impact.sidelined_players[0].expected_duration.is_fallback is False
        # Rotation replacement should pick a non-injured roster player.
        rep_ids = {rep.replacement_player_id for rep in impact.rotation_replacements}
        assert star.id not in rep_ids
        assert starter.id not in rep_ids  # questionable is also sidelined
    finally:
        session.close()


def test_find_similar_past_injuries_excludes_self_and_prefers_age_match():
    session = _make_session()
    try:
        # Seed a Player row so FK is happy.
        session.add(Player(id=2544, full_name="LeBron James", is_active=True,
                           position="F", birth_date="1984-12-30"))
        session.commit()
        # 4 historical entries — closest age match should sort first.
        for player_id, age in [(7001, 25.0), (7002, 30.0), (7003, 39.0), (7004, 21.0)]:
            session.add(Player(id=player_id, full_name="Cohort {0}".format(player_id),
                               is_active=False, position="F"))
            session.add(PlayerInjuryHistory(
                player_id=player_id,
                season="2023-24",
                body_part="knee",
                severity="moderate",
                started_on=date(2024, 1, 10),
                resolved_on=date(2024, 1, 24),
                games_missed=12,
                age_at_start=age,
                is_recurring=False,
                source="seed_synthetic",
            ))
        # Self-injury that must be excluded.
        session.add(PlayerInjuryHistory(
            player_id=2544,
            season="2023-24",
            body_part="knee",
            severity="moderate",
            started_on=date(2024, 1, 5),
            resolved_on=date(2024, 1, 15),
            games_missed=8,
            age_at_start=39.0,
            is_recurring=False,
            source="seed_synthetic",
        ))
        session.commit()

        results = find_similar_past_injuries(
            session, body_part="knee", age=39.0, limit=3, exclude_player_id=2544
        )
        assert all(r.player_id != 2544 for r in results)
        assert len(results) == 3
        # Closest age (39 vs 39) should win first slot.
        assert results[0].age_at_start == 39.0
    finally:
        session.close()
