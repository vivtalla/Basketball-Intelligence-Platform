"""Sprint 73 — season-phase auto-detection tests.

Three scenarios:

1. Mid-January with no recent playoff GameLog rows → ``regular_season``.
2. Late April with five playoff GameLog rows in the last 7 days plus a
   `PlayoffSeries` row marked active in round 1 → ``playoff_round_1``.
3. Mid-August with no playoff GameLog rows → ``offseason``.
"""
from pathlib import Path
import sys
from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GameLog, PlayoffSeries, Team  # noqa: E402
from services import season_phase_service  # noqa: E402


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSession()


def _seed_teams(session):
    session.add_all(
        [
            Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder"),
            Team(id=1610612750, abbreviation="MIN", name="Minnesota Timberwolves"),
        ]
    )
    session.commit()


def test_phase_is_regular_season_in_january():
    session = _make_session()
    season_phase_service._clear_cache()
    try:
        _seed_teams(session)
        # No playoff games anywhere; date is firmly in regular season.
        fixed_date = date(2026, 1, 15)
        phase = season_phase_service._detect_phase(session, fixed_date)
        assert phase == "regular_season"

        # Sanity: a regular-season GameLog row should not flip the phase.
        session.add(
            GameLog(
                game_id="0022500001",
                season="2025-26",
                game_date=fixed_date - timedelta(days=2),
                home_team_id=1610612760,
                away_team_id=1610612750,
                home_score=110,
                away_score=99,
                season_type="Regular Season",
            )
        )
        session.commit()
        assert season_phase_service._detect_phase(session, fixed_date) == "regular_season"
    finally:
        session.close()
        season_phase_service._clear_cache()


def test_phase_is_playoff_round_1_in_april_with_playoff_games():
    session = _make_session()
    season_phase_service._clear_cache()
    try:
        _seed_teams(session)
        fixed_date = date(2026, 4, 25)

        # Five playoff GameLog rows within the last 7 days.
        for i in range(5):
            session.add(
                GameLog(
                    game_id=f"00425001{i:02d}",
                    season="2025-26",
                    game_date=fixed_date - timedelta(days=i + 1),
                    home_team_id=1610612760,
                    away_team_id=1610612750,
                    home_score=110 + i,
                    away_score=99 + i,
                    season_type="Playoffs",
                    series_id="2025-26-W-R1-OKC-MIN",
                    series_game_num=i + 1,
                )
            )
        session.add(
            PlayoffSeries(
                season="2025-26",
                round=1,
                series_id="2025-26-W-R1-OKC-MIN",
                top_seed_team_id=1610612760,
                bottom_seed_team_id=1610612750,
                top_seed=1,
                bottom_seed=8,
                top_wins=3,
                bottom_wins=2,
                status="active",
            )
        )
        session.commit()

        phase = season_phase_service._detect_phase(session, fixed_date)
        assert phase == "playoff_round_1"
    finally:
        session.close()
        season_phase_service._clear_cache()


def test_phase_is_offseason_in_august():
    session = _make_session()
    season_phase_service._clear_cache()
    try:
        _seed_teams(session)
        fixed_date = date(2026, 8, 10)
        phase = season_phase_service._detect_phase(session, fixed_date)
        assert phase == "offseason"
    finally:
        session.close()
        season_phase_service._clear_cache()
