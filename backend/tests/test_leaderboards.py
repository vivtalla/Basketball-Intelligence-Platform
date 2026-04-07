from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import Player, SeasonStat, Team  # noqa: E402
from routers.leaderboards import leaderboard  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_leaderboard_supports_total_box_score_stats():
    session = make_session()
    try:
        team = Team(id=1610612747, abbreviation="LAL", name="Los Angeles Lakers")
        player_a = Player(id=1, full_name="Alpha Scorer", first_name="Alpha", last_name="Scorer", team_id=team.id, is_active=True)
        player_b = Player(id=2, full_name="Beta Scorer", first_name="Beta", last_name="Scorer", team_id=team.id, is_active=True)
        session.add_all([team, player_a, player_b])
        session.flush()

        session.add_all(
            [
                SeasonStat(
                    player_id=player_a.id,
                    season="2025-26",
                    team_abbreviation="LAL",
                    is_playoff=False,
                    gp=60,
                    pts=1800,
                    pts_pg=30.0,
                ),
                SeasonStat(
                    player_id=player_b.id,
                    season="2025-26",
                    team_abbreviation="LAL",
                    is_playoff=False,
                    gp=62,
                    pts=1500,
                    pts_pg=24.2,
                ),
            ]
        )
        session.commit()

        response = leaderboard(season="2025-26", stat="pts", season_type="Regular Season", limit=25, min_gp=15, team=None, db=session)

        assert response.stat == "pts"
        assert len(response.entries) == 2
        assert response.entries[0].player_name == "Alpha Scorer"
        assert response.entries[0].stat_value == 1800.0
    finally:
        session.close()
