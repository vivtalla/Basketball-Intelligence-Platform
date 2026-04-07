from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import Player, SeasonStat, Team  # noqa: E402
from services.sync_service import sync_official_season_stats  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_sync_official_season_stats_replaces_stale_current_season_rows(monkeypatch):
    session = make_session()
    try:
        team = Team(id=1610612747, abbreviation="LAL", name="Los Angeles Lakers")
        player = Player(id=1629029, full_name="Luka Doncic", first_name="Luka", last_name="Doncic", team_id=team.id, is_active=True)
        session.add_all([team, player])
        session.add(
            SeasonStat(
                player_id=player.id,
                season="2025-26",
                team_abbreviation="DAL",
                is_playoff=False,
                gp=75,
                pts=2089,
                pts_pg=27.9,
            )
        )
        session.commit()

        base_rows = [
            {
                "PLAYER_ID": 1629029,
                "PLAYER_NAME": "Luka Doncic",
                "TEAM_ID": 1610612747,
                "TEAM_ABBREVIATION": "LAL",
                "AGE": 27.0,
                "GP": 64,
                "GS": 64,
                "MIN": 2304.0,
                "PTS": 2143,
                "REB": 493,
                "AST": 531,
                "STL": 112,
                "BLK": 36,
                "TOV": 210,
                "FGM": 710,
                "FGA": 1490,
                "FG_PCT": 0.477,
                "FG3M": 236,
                "FG3A": 654,
                "FG3_PCT": 0.361,
                "FTM": 487,
                "FTA": 569,
                "FT_PCT": 0.856,
                "OREB": 64,
                "DREB": 429,
                "PF": 144,
            }
        ]
        advanced_rows = [
            {
                "PLAYER_ID": 1629029,
                "E_OFF_RATING": 118.2,
                "E_DEF_RATING": 109.8,
                "E_NET_RATING": 8.4,
                "E_PACE": 99.2,
                "PIE": 0.2,
                "WS": 11.3,
                "AST_RATIO": 21.1,
                "REB_PCT": 11.4,
                "TM_TOV_PCT": 13.4,
                "USG_PCT": 36.2,
            }
        ]

        def fake_league_dash(season: str, measure_type: str = "Advanced"):
            assert season == "2025-26"
            return base_rows if measure_type == "Base" else advanced_rows

        monkeypatch.setattr("services.sync_service.get_league_dash_player_stats", fake_league_dash)

        result = sync_official_season_stats(session, "2025-26")
        assert result["status"] == "ok"
        assert result["players_synced"] == 1
        assert result["stale_rows_deleted"] == 1

        rows = session.query(SeasonStat).filter_by(player_id=1629029, season="2025-26", is_playoff=False).all()
        assert len(rows) == 1
        assert rows[0].team_abbreviation == "LAL"
        assert rows[0].gp == 64
        assert rows[0].pts == 2143
        assert rows[0].pts_pg == 33.5
    finally:
        session.close()
