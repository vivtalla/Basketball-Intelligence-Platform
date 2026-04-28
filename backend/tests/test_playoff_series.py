"""Sprint 73 — playoffs data-layer schema tests."""
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import PlayoffSeries, Team  # noqa: E402


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSession()


def _seed_teams(session):
    session.add(Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder"))
    session.add(Team(id=1610612750, abbreviation="MIN", name="Minnesota Timberwolves"))
    session.commit()


def test_playoff_series_can_be_created():
    session = _make_session()
    try:
        _seed_teams(session)

        series = PlayoffSeries(
            season="2025-26",
            round=1,
            series_id="2025-26-W-R1-OKC-MIN",
            top_seed_team_id=1610612760,
            bottom_seed_team_id=1610612750,
            top_seed=1,
            bottom_seed=8,
            top_wins=4,
            bottom_wins=2,
            status="closed",
            winner_team_id=1610612760,
        )
        session.add(series)
        session.commit()

        round_trip = (
            session.query(PlayoffSeries)
            .filter(PlayoffSeries.series_id == "2025-26-W-R1-OKC-MIN")
            .one()
        )
        assert round_trip.season == "2025-26"
        assert round_trip.round == 1
        assert round_trip.top_seed_team_id == 1610612760
        assert round_trip.bottom_seed_team_id == 1610612750
        assert round_trip.top_seed == 1
        assert round_trip.bottom_seed == 8
        assert round_trip.top_wins == 4
        assert round_trip.bottom_wins == 2
        assert round_trip.status == "closed"
        assert round_trip.winner_team_id == 1610612760
        assert round_trip.created_at is not None
        assert round_trip.updated_at is not None
    finally:
        session.close()


def test_playoff_series_unique_constraint():
    session = _make_session()
    try:
        _seed_teams(session)

        first = PlayoffSeries(
            season="2025-26",
            round=1,
            series_id="2025-26-W-R1-OKC-MIN",
            top_seed_team_id=1610612760,
            bottom_seed_team_id=1610612750,
            top_seed=1,
            bottom_seed=8,
            top_wins=0,
            bottom_wins=0,
            status="scheduled",
        )
        session.add(first)
        session.commit()

        # Same (season, series_id) is forbidden, even if other fields differ.
        duplicate = PlayoffSeries(
            season="2025-26",
            round=2,
            series_id="2025-26-W-R1-OKC-MIN",
            top_seed_team_id=1610612760,
            bottom_seed_team_id=1610612750,
            top_seed=1,
            bottom_seed=8,
            top_wins=0,
            bottom_wins=0,
            status="active",
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        # A different season with the same series_id is allowed.
        next_season = PlayoffSeries(
            season="2026-27",
            round=1,
            series_id="2025-26-W-R1-OKC-MIN",
            top_seed_team_id=1610612760,
            bottom_seed_team_id=1610612750,
            top_seed=1,
            bottom_seed=8,
            top_wins=0,
            bottom_wins=0,
            status="scheduled",
        )
        session.add(next_season)
        session.commit()
        assert (
            session.query(PlayoffSeries)
            .filter(PlayoffSeries.series_id == "2025-26-W-R1-OKC-MIN")
            .count()
            == 2
        )
    finally:
        session.close()


def test_lineup_stats_unique_constraint_includes_is_playoff():
    """Same lineup_key+season can coexist for regular season and playoffs."""
    from db.models import LineupStats

    session = _make_session()
    try:
        session.add(Team(id=1610612738, abbreviation="BOS", name="Boston Celtics"))
        session.commit()

        regular = LineupStats(
            lineup_key="100-101-102-103-104",
            season="2025-26",
            team_id=1610612738,
            is_playoff=False,
            minutes=120.0,
            net_rating=8.5,
        )
        playoffs = LineupStats(
            lineup_key="100-101-102-103-104",
            season="2025-26",
            team_id=1610612738,
            is_playoff=True,
            minutes=45.0,
            net_rating=14.2,
        )
        session.add_all([regular, playoffs])
        session.commit()

        rows = (
            session.query(LineupStats)
            .filter(LineupStats.lineup_key == "100-101-102-103-104")
            .order_by(LineupStats.is_playoff)
            .all()
        )
        assert len(rows) == 2
        assert rows[0].is_playoff is False
        assert rows[1].is_playoff is True

        # Inserting another regular-season row with the same key collides.
        dup = LineupStats(
            lineup_key="100-101-102-103-104",
            season="2025-26",
            team_id=1610612738,
            is_playoff=False,
            minutes=10.0,
        )
        session.add(dup)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    finally:
        session.close()


def test_game_logs_have_playoff_metadata_columns():
    """game_logs.season_type / series_id / series_game_num / playoff_seed roundtrip."""
    from datetime import date

    from db.models import GameLog

    session = _make_session()
    try:
        session.add(Team(id=1, abbreviation="OKC", name="Oklahoma City Thunder"))
        session.add(Team(id=2, abbreviation="MIN", name="Minnesota Timberwolves"))
        session.commit()

        playoff_game = GameLog(
            game_id="0042500101",
            season="2025-26",
            game_date=date(2026, 4, 18),
            home_team_id=1,
            away_team_id=2,
            home_score=110,
            away_score=99,
            season_type="Playoffs",
            series_id="2025-26-W-R1-OKC-MIN",
            series_game_num=1,
            playoff_seed=1,
        )
        session.add(playoff_game)
        session.commit()

        row = session.query(GameLog).filter(GameLog.game_id == "0042500101").one()
        assert row.season_type == "Playoffs"
        assert row.series_id == "2025-26-W-R1-OKC-MIN"
        assert row.series_game_num == 1
        assert row.playoff_seed == 1
    finally:
        session.close()
