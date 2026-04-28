"""Sprint 73 — career response surfaces playoff_seasons alongside seasons."""
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import Player, SeasonStat, Team  # noqa: E402
from routers.stats import career_stats  # noqa: E402


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSession()


def _seed_player_with_seasons(session, player_id: int = 1628369):
    team = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
    session.add(team)
    player = Player(
        id=player_id,
        full_name="Test Player",
        first_name="Test",
        last_name="Player",
        team_id=team.id,
        is_active=True,
    )
    session.add(player)

    # Two regular-season rows
    session.add(
        SeasonStat(
            player_id=player.id,
            season="2024-25",
            team_abbreviation="BOS",
            is_playoff=False,
            gp=72,
            pts=2100,
            pts_pg=29.2,
            reb=560,
            reb_pg=7.8,
            ast=380,
            ast_pg=5.3,
            min_total=2520,
            min_pg=35.0,
        )
    )
    session.add(
        SeasonStat(
            player_id=player.id,
            season="2025-26",
            team_abbreviation="BOS",
            is_playoff=False,
            gp=68,
            pts=2050,
            pts_pg=30.1,
            reb=540,
            reb_pg=7.9,
            ast=360,
            ast_pg=5.3,
            min_total=2380,
            min_pg=35.0,
        )
    )
    # Two playoff rows in different seasons.
    session.add(
        SeasonStat(
            player_id=player.id,
            season="2024-25",
            team_abbreviation="BOS",
            is_playoff=True,
            gp=18,
            pts=520,
            pts_pg=28.9,
            reb=140,
            reb_pg=7.8,
            ast=92,
            ast_pg=5.1,
            min_total=720,
            min_pg=40.0,
        )
    )
    session.add(
        SeasonStat(
            player_id=player.id,
            season="2025-26",
            team_abbreviation="BOS",
            is_playoff=True,
            gp=12,
            pts=360,
            pts_pg=30.0,
            reb=96,
            reb_pg=8.0,
            ast=66,
            ast_pg=5.5,
            min_total=480,
            min_pg=40.0,
        )
    )
    session.commit()
    return player


def test_career_response_includes_playoff_seasons():
    session = _make_session()
    try:
        player = _seed_player_with_seasons(session)

        response = career_stats(player.id, db=session)

        # Regular-season list still populated and ordered ascending.
        assert [s.season for s in response.seasons] == ["2024-25", "2025-26"]
        assert response.seasons[0].team_abbreviation == "BOS"
        assert response.seasons[1].pts_pg == 30.1

        # Playoff list is populated and sorted descending by season.
        assert [s.season for s in response.playoff_seasons] == ["2025-26", "2024-25"]
        assert response.playoff_seasons[0].gp == 12
        assert response.playoff_seasons[1].gp == 18

        # Career totals come from regular-season rows; playoffs do not pollute them.
        assert response.career_totals is not None
        assert response.career_totals.gp == 72 + 68
        assert response.data_status in {"ready", "stale"}
    finally:
        session.close()


def test_career_response_with_only_regular_season_omits_playoff_rows():
    session = _make_session()
    try:
        player = _seed_player_with_seasons(session)
        # Wipe playoff rows.
        session.query(SeasonStat).filter(SeasonStat.is_playoff == True).delete()  # noqa: E712
        session.commit()

        response = career_stats(player.id, db=session)
        assert response.playoff_seasons == []
        assert len(response.seasons) == 2
    finally:
        session.close()


def test_career_response_with_only_playoff_seasons_still_returns_them():
    session = _make_session()
    try:
        player = _seed_player_with_seasons(session)
        # Wipe regular-season rows.
        session.query(SeasonStat).filter(SeasonStat.is_playoff == False).delete()  # noqa: E712
        session.commit()

        response = career_stats(player.id, db=session)
        assert response.seasons == []
        assert [s.season for s in response.playoff_seasons] == ["2025-26", "2024-25"]
        # data_status should still indicate something is available.
        assert response.data_status in {"ready", "stale"}
    finally:
        session.close()
