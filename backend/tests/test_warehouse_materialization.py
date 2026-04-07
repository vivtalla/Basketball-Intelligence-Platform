from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GamePlayerStat, Player, SeasonStat, Team  # noqa: E402
from services.warehouse_service import materialize_season_aggregates  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_materialize_season_aggregates_ignores_future_dated_game_rows():
    session = make_session()
    try:
        team = Team(id=1610612747, abbreviation="LAL", name="Los Angeles Lakers")
        player = Player(id=1629029, full_name="Luka Doncic", first_name="Luka", last_name="Doncic", team_id=team.id, is_active=True)
        session.add_all([team, player])
        session.flush()

        session.add(
            GamePlayerStat(
                game_id="0022500001",
                season="2025-26",
                player_id=player.id,
                team_id=team.id,
                team_abbreviation=team.abbreviation,
                game_date=date.today() - timedelta(days=1),
                min=35.0,
                pts=40,
                reb=8,
                ast=9,
                stl=2,
                blk=1,
                tov=4,
                fgm=14,
                fga=24,
                fg3m=5,
                fg3a=11,
                ftm=7,
                fta=8,
                oreb=1,
                dreb=7,
                pf=2,
            )
        )
        session.add(
            GamePlayerStat(
                game_id="0022500002",
                season="2025-26",
                player_id=player.id,
                team_id=team.id,
                team_abbreviation=team.abbreviation,
                game_date=date.today() + timedelta(days=3),
                min=35.0,
                pts=10,
                reb=3,
                ast=4,
                stl=0,
                blk=0,
                tov=3,
                fgm=3,
                fga=14,
                fg3m=1,
                fg3a=6,
                ftm=3,
                fta=4,
                oreb=0,
                dreb=3,
                pf=2,
            )
        )
        session.commit()

        result = materialize_season_aggregates(session, "2025-26")
        assert result["status"] == "ok"

        row = session.query(SeasonStat).filter_by(player_id=player.id, season="2025-26", team_abbreviation="LAL", is_playoff=False).first()
        assert row is not None
        assert row.gp == 1
        assert row.pts == 40
        assert row.pts_pg == 40.0
        assert row.reb_pg == 8.0
        assert row.ast_pg == 9.0
    finally:
        session.close()
