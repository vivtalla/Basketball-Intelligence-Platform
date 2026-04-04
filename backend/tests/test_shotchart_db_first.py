from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Optional
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import IngestionJob, Player, PlayerGameLog, PlayerShotChart, SourceRun, Team  # noqa: E402
from routers.shotchart import player_shot_chart, player_shot_zones  # noqa: E402
from services.warehouse_service import queue_player_shot_chart_sync, queue_season_shot_charts, run_next_job  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def seed_player(session, player_id: int = 7):
    team = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks")
    player = Player(id=player_id, full_name="Test Shooter", team_id=team.id, is_active=True)
    session.add_all([team, player])
    session.commit()
    return player


def shot_payload(
    *,
    loc_x: int = 0,
    loc_y: int = 0,
    shot_made: bool = True,
    shot_type: str = "2PT Field Goal",
    action_type: str = "Jump Shot",
    zone_basic: str = "Mid-Range",
    zone_area: str = "Center(C)",
    distance: int = 12,
    game_id: Optional[str] = "0022400001",
    game_date: Optional[str] = "2025-01-01",
):
    return {
        "loc_x": loc_x,
        "loc_y": loc_y,
        "shot_made": shot_made,
        "shot_type": shot_type,
        "action_type": action_type,
        "zone_basic": zone_basic,
        "zone_area": zone_area,
        "distance": distance,
        "game_id": game_id,
        "game_date": game_date,
    }


def test_player_shot_chart_returns_ready_from_fresh_db_row():
    session = make_session()
    try:
        player = seed_player(session)
        session.add(
            PlayerShotChart(
                player_id=player.id,
                season="2024-25",
                season_type="Regular Season",
                shots=[shot_payload()],
                shot_count=1,
                fetched_at=datetime(2026, 4, 2, 12, 0, 0),
                expires_at=datetime.utcnow() + timedelta(days=1),
            )
        )
        session.commit()

        response = player_shot_chart(player.id, season="2024-25", season_type="Regular Season", db=session)

        assert response.data_status == "ready"
        assert response.attempted == 1
        assert response.last_synced_at == "2026-04-02T12:00:00"
        assert response.shots[0].game_id == "0022400001"
        assert response.shots[0].game_date == "2025-01-01"
    finally:
        session.close()


def test_player_shot_chart_returns_stale_cached_row_without_remote_fetch():
    session = make_session()
    try:
        player = seed_player(session)
        session.add(
            PlayerShotChart(
                player_id=player.id,
                season="2024-25",
                season_type="Regular Season",
                shots=[shot_payload(
                    loc_x=10,
                    loc_y=5,
                    shot_made=False,
                    shot_type="3PT Field Goal",
                    action_type="Pullup Jump Shot",
                    zone_basic="Above the Break 3",
                    distance=27,
                )],
                shot_count=1,
                fetched_at=datetime(2026, 4, 1, 9, 30, 0),
                expires_at=datetime.utcnow() - timedelta(hours=2),
            )
        )
        session.commit()

        response = player_shot_chart(player.id, season="2024-25", season_type="Regular Season", db=session)

        assert response.data_status == "stale"
        assert response.attempted == 1
        assert response.shots[0].zone_basic == "Above the Break 3"
    finally:
        session.close()


def test_player_shot_chart_returns_missing_when_unsynced():
    session = make_session()
    try:
        player = seed_player(session)

        response = player_shot_chart(player.id, season="2024-25", season_type="Regular Season", db=session)

        assert response.data_status == "missing"
        assert response.attempted == 0
        assert response.last_synced_at is None
    finally:
        session.close()


def test_player_shot_zones_returns_missing_metadata_when_unsynced():
    session = make_session()
    try:
        player = seed_player(session)

        response = player_shot_zones(player.id, season="2024-25", season_type="Regular Season", db=session)

        assert response.data_status == "missing"
        assert response.total_attempts == 0
        assert response.zones == []
    finally:
        session.close()


def test_player_shot_chart_filters_by_date_window_and_preserves_available_bounds():
    session = make_session()
    try:
        player = seed_player(session)
        session.add(
            PlayerShotChart(
                player_id=player.id,
                season="2024-25",
                season_type="Regular Season",
                shots=[
                    shot_payload(game_id="0022400001", game_date="2025-01-01", shot_made=True),
                    shot_payload(game_id="0022400002", game_date="2025-01-05", shot_made=False),
                    shot_payload(game_id="0022400003", game_date="2025-01-10", shot_made=True),
                ],
                shot_count=3,
                fetched_at=datetime(2026, 4, 2, 12, 0, 0),
                expires_at=datetime.utcnow() + timedelta(days=1),
            )
        )
        session.commit()

        response = player_shot_chart(
            player.id,
            season="2024-25",
            season_type="Regular Season",
            start_date="2025-01-04",
            end_date="2025-01-08",
            db=session,
        )

        assert response.attempted == 1
        assert response.made == 0
        assert response.shots[0].game_date == "2025-01-05"
        assert response.start_date == "2025-01-04"
        assert response.end_date == "2025-01-08"
        assert response.available_start_date == "2025-01-01"
        assert response.available_end_date == "2025-01-10"
        assert response.available_game_dates == ["2025-01-01", "2025-01-05", "2025-01-10"]
    finally:
        session.close()


def test_player_shot_zones_filters_by_date_window():
    session = make_session()
    try:
        player = seed_player(session)
        session.add(
            PlayerShotChart(
                player_id=player.id,
                season="2024-25",
                season_type="Regular Season",
                shots=[
                    shot_payload(game_id="0022400001", game_date="2025-01-01", shot_made=True, zone_basic="Restricted Area", distance=2),
                    shot_payload(game_id="0022400002", game_date="2025-01-07", shot_made=False, zone_basic="Restricted Area", distance=2),
                    shot_payload(game_id="0022400003", game_date="2025-01-07", shot_made=True, zone_basic="Restricted Area", distance=2),
                    shot_payload(game_id="0022400004", game_date="2025-01-07", shot_made=False, zone_basic="Restricted Area", distance=2),
                    shot_payload(game_id="0022400005", game_date="2025-01-07", shot_made=True, zone_basic="Restricted Area", distance=2),
                    shot_payload(game_id="0022400006", game_date="2025-01-07", shot_made=True, zone_basic="Restricted Area", distance=2),
                ],
                shot_count=6,
                fetched_at=datetime(2026, 4, 2, 12, 0, 0),
                expires_at=datetime.utcnow() + timedelta(days=1),
            )
        )
        session.commit()

        response = player_shot_zones(
            player.id,
            season="2024-25",
            season_type="Regular Season",
            start_date="2025-01-07",
            end_date="2025-01-07",
            db=session,
        )

        assert response.total_attempts == 5
        assert response.start_date == "2025-01-07"
        assert response.available_start_date == "2025-01-01"
        assert response.available_end_date == "2025-01-07"
        assert len(response.zones) == 1
        assert response.zones[0].attempts == 5
        assert response.zones[0].made == 3
        assert response.zones[0].fg_pct == 0.6
    finally:
        session.close()


def test_season_shot_chart_job_enqueues_and_player_job_persists_rows():
    session = make_session()
    try:
        player = seed_player(session, player_id=11)
        session.add(
            PlayerGameLog(
                player_id=player.id,
                game_id="0022400001",
                season="2024-25",
                season_type="Regular Season",
            )
        )
        session.commit()

        queued = queue_season_shot_charts(session, "2024-25", season_type="Regular Season")
        session.commit()
        assert len(queued) == 1
        assert queued[0].job_type == "sync_season_shot_charts"

        season_result = run_next_job(session, season="2024-25")
        assert season_result["status"] == "ok"

        player_job = (
            session.query(IngestionJob)
            .filter_by(job_type="sync_player_shot_chart", season="2024-25")
            .first()
        )
        assert player_job is not None

        with patch(
            "services.warehouse_service.get_shot_chart_data",
            return_value=[
                shot_payload(
                    loc_x=15,
                    loc_y=20,
                    shot_type="2PT Field Goal",
                    action_type="Driving Layup Shot",
                    zone_basic="Restricted Area",
                    distance=2,
                )
            ],
        ):
            player_result = run_next_job(session, season="2024-25")

        assert player_result["status"] == "ok"
        persisted = (
            session.query(PlayerShotChart)
            .filter_by(player_id=player.id, season="2024-25", season_type="Regular Season")
            .first()
        )
        assert persisted is not None
        assert persisted.shot_count == 1
        assert persisted.shots[0]["game_id"] == "0022400001"
        assert persisted.shots[0]["game_date"] == "2025-01-01"

        source_run = (
            session.query(SourceRun)
            .filter_by(job_type="sync_player_shot_chart", entity_id="11:2024-25:Regular Season")
            .first()
        )
        assert source_run is not None
        assert source_run.status == "complete"
    finally:
        session.close()


def test_player_shot_chart_force_sync_overwrites_minimal_cached_payload_with_enriched_fields():
    session = make_session()
    try:
        player = seed_player(session, player_id=14)
        session.add(
            PlayerShotChart(
                player_id=player.id,
                season="2024-25",
                season_type="Regular Season",
                shots=[{
                    "loc_x": 4,
                    "loc_y": 9,
                    "shot_made": False,
                    "shot_type": "2PT Field Goal",
                    "action_type": "Jump Shot",
                    "zone_basic": "Mid-Range",
                    "zone_area": "Center(C)",
                    "distance": 9,
                }],
                shot_count=1,
                fetched_at=datetime(2026, 4, 1, 12, 0, 0),
                expires_at=datetime.utcnow() - timedelta(days=1),
            )
        )
        session.commit()

        queue_player_shot_chart_sync(session, player.id, "2024-25", season_type="Regular Season", force=True)
        session.commit()

        with patch(
            "services.warehouse_service.get_shot_chart_data",
            return_value=[shot_payload(game_id="0022400999", game_date="2025-02-01", zone_basic="Above the Break 3", shot_type="3PT Field Goal", distance=26)],
        ):
            result = run_next_job(session, season="2024-25")

        assert result["status"] == "ok"
        persisted = (
            session.query(PlayerShotChart)
            .filter_by(player_id=player.id, season="2024-25", season_type="Regular Season")
            .first()
        )
        assert persisted is not None
        assert persisted.shots[0]["game_id"] == "0022400999"
        assert persisted.shots[0]["game_date"] == "2025-02-01"
        assert persisted.shots[0]["zone_basic"] == "Above the Break 3"
    finally:
        session.close()
