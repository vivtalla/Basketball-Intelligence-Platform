from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    Player,
    PlayerGravityStat,
    PlayerHustleStat,
    PlayerPlayTypeStat,
    PlayerTrackingStat,
    SeasonStat,
    Team,
)
from services import gravity_sync_service  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _seed_player(session):
    team = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
    player = Player(id=1, full_name="Alpha Star", first_name="Alpha", last_name="Star", team_id=team.id)
    session.add_all([team, player])
    session.add(
        SeasonStat(
            player_id=player.id,
            season="2025-26",
            team_abbreviation="BOS",
            is_playoff=False,
            gp=25,
            min_total=850,
            pts=800,
            pts_pg=32.0,
            ast_pg=8.0,
            fg3a=250,
            fta=200,
            usg_pct=31.0,
            ts_pct=0.640,
        )
    )
    session.commit()
    return player


def test_sync_play_type_hustle_and_tracking_upsert(monkeypatch):
    session = make_session()
    try:
        player = _seed_player(session)
        def fake_synergy(*args, **kwargs):
            grouping = kwargs.get("type_grouping", "offensive")
            return [
                {
                    "PLAYER_ID": player.id,
                    "PLAY_TYPE": "Isolation" if grouping == "offensive" else "Spot Up",
                    "TYPE_GROUPING": grouping,
                    "TEAM_ID": 1610612738,
                    "TEAM_ABBREVIATION": "BOS",
                    "GP": 25,
                    "POSS": 120,
                    "PPP": 1.08,
                }
            ]

        monkeypatch.setattr(gravity_sync_service, "get_synergy_player_play_types", fake_synergy)
        monkeypatch.setattr(
            gravity_sync_service,
            "get_league_hustle_player_stats",
            lambda *args, **kwargs: [
                {
                    "PLAYER_ID": player.id,
                    "TEAM_ID": 1610612738,
                    "TEAM_ABBREVIATION": "BOS",
                    "GP": 25,
                    "SCREEN_ASSISTS": 42,
                    "DEFLECTIONS": 38,
                }
            ],
        )
        monkeypatch.setattr(
            gravity_sync_service,
            "get_player_tracking_dashboard",
            lambda *args, **kwargs: [
                {
                    "family": "touches",
                    "split_key": "overall",
                    "raw": {"GP": 25, "TOUCHES": 84, "PASS": 52},
                }
            ],
        )

        play_result = gravity_sync_service.sync_player_play_type_stats(session, "2025-26", player_ids=[player.id])
        hustle_result = gravity_sync_service.sync_player_hustle_stats(session, "2025-26")
        tracking_result = gravity_sync_service.sync_player_tracking_stats(session, "2025-26", [player.id])

        assert play_result["rows_synced"] == 2
        assert hustle_result["rows_synced"] == 1
        assert tracking_result["rows_synced"] == 1
        assert session.query(PlayerPlayTypeStat).filter_by(player_id=player.id).count() == 2
        assert session.query(PlayerHustleStat).filter_by(player_id=player.id).one().screen_assists == 42.0
        assert session.query(PlayerTrackingStat).filter_by(player_id=player.id).one().touches == 84.0
    finally:
        session.close()


def test_official_gravity_fallback_persists_proxy_without_failure(monkeypatch):
    session = make_session()
    try:
        player = _seed_player(session)
        monkeypatch.setattr(gravity_sync_service, "get_inside_game_gravity_rows", lambda *args, **kwargs: [])

        result = gravity_sync_service.sync_official_gravity_stats(
            session,
            "2025-26",
            fallback_player_ids=[player.id],
        )

        assert result["status"] == "fallback"
        row = session.query(PlayerGravityStat).filter_by(player_id=player.id, source="courtvue_proxy").one()
        assert row.overall_gravity is not None
        assert row.gravity_confidence in {"low", "medium", "high"}
        assert row.warnings
    finally:
        session.close()
