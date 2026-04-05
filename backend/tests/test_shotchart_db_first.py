from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Optional
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from data.nba_client import _format_shot_clock, _normalize_shot_chart_game_date  # noqa: E402
from db.models import (  # noqa: E402
    GameLog,
    GamePlayerStat,
    IngestionJob,
    PlayByPlay,
    PlayByPlayEvent,
    Player,
    PlayerGameLog,
    PlayerShotChart,
    SeasonStat,
    SourceRun,
    Team,
    WarehouseGame,
)
from routers.advanced import get_pbp_coverage  # noqa: E402
from routers.games import get_game_detail  # noqa: E402
from routers.shotchart import (  # noqa: E402
    get_shot_lab_snapshot_route,
    player_shot_chart,
    player_shot_zones,
    post_shot_lab_snapshot,
    refresh_player_shot_chart,
    refresh_team_defense_shot_chart,
    shot_completeness_report,
    team_defense_shot_chart,
    team_defense_shot_zones,
)
from models.shotchart import ShotLabSnapshotCreateRequest  # noqa: E402
from services.game_visualization_service import build_game_visualization  # noqa: E402
from services.warehouse_service import queue_player_shot_chart_sync, queue_season_shot_charts, run_next_job  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def seed_player(session, player_id: int = 7):
    team = session.query(Team).filter_by(id=1610612737).first()
    if team is None:
        team = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks")
        session.add(team)
        session.flush()
    player = Player(id=player_id, full_name="Test Shooter", team_id=team.id, is_active=True)
    session.add(player)
    session.commit()
    return player


def seed_game(
    session,
    *,
    game_id: str = "0022400001",
    season: str = "2024-25",
    home_team_id: int = 1610612737,
    away_team_id: int = 1610612738,
    home_team_abbreviation: str = "ATL",
    away_team_abbreviation: str = "BOS",
    has_schedule: bool = True,
    has_pbp_payload: bool = True,
    has_parsed_pbp: bool = True,
):
    game = WarehouseGame(
        game_id=game_id,
        season=season,
        game_date=datetime(2025, 1, 1).date(),
        status="final",
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_team_abbreviation=home_team_abbreviation,
        away_team_abbreviation=away_team_abbreviation,
        home_team_name=home_team_abbreviation,
        away_team_name=away_team_abbreviation,
        home_score=110,
        away_score=104,
        has_schedule=has_schedule,
        has_pbp_payload=has_pbp_payload,
        has_parsed_pbp=has_parsed_pbp,
    )
    session.add(game)
    session.commit()
    return game


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
    period: Optional[int] = 1,
    clock: Optional[str] = "11:42",
    minutes_remaining: Optional[int] = 11,
    seconds_remaining: Optional[int] = 42,
    shot_value: Optional[int] = 2,
    shot_event_id: Optional[str] = "101",
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
        "period": period,
        "clock": clock,
        "minutes_remaining": minutes_remaining,
        "seconds_remaining": seconds_remaining,
        "shot_value": shot_value,
        "shot_event_id": shot_event_id,
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
        assert response.shots[0].period == 1
        assert response.shots[0].clock == "11:42"
        assert response.shots[0].minutes_remaining == 11
        assert response.shots[0].seconds_remaining == 42
        assert response.shots[0].shot_value == 2
        assert response.shots[0].shot_event_id == "101"
    finally:
        session.close()


def test_normalize_shot_chart_game_date_accepts_compact_nba_format():
    assert _normalize_shot_chart_game_date("20260119") == "2026-01-19"


def test_format_shot_clock_returns_mm_ss():
    assert _format_shot_clock(3, 7) == "3:07"


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


def test_player_shot_chart_filters_by_period_result_and_shot_value():
    session = make_session()
    try:
        player = seed_player(session)
        session.add(
            PlayerShotChart(
                player_id=player.id,
                season="2024-25",
                season_type="Regular Season",
                shots=[
                    shot_payload(game_id="0022400001", game_date="2025-01-01", period=1, shot_made=True, shot_type="2PT Field Goal", shot_value=2, zone_basic="Restricted Area", distance=2),
                    shot_payload(game_id="0022400002", game_date="2025-01-02", period=1, shot_made=False, shot_type="3PT Field Goal", shot_value=3, zone_basic="Above the Break 3", distance=26),
                    shot_payload(game_id="0022400003", game_date="2025-01-03", period=5, shot_made=False, shot_type="2PT Field Goal", shot_value=2, zone_basic="Mid-Range", distance=15),
                ],
                shot_count=3,
                fetched_at=datetime(2026, 4, 5, 12, 0, 0),
                expires_at=datetime.utcnow() + timedelta(days=1),
            )
        )
        session.commit()

        response = player_shot_chart(
            player.id,
            season="2024-25",
            season_type="Regular Season",
            period_bucket="ot",
            result="missed",
            shot_value="2pt",
            db=session,
        )

        assert response.attempted == 1
        assert response.shots[0].game_id == "0022400003"
        assert response.shots[0].period == 5
        assert response.shots[0].shot_made is False
        assert response.shots[0].shot_value == 2
    finally:
        session.close()


def test_player_shot_zones_filters_by_context_and_date_window_together():
    session = make_session()
    try:
        player = seed_player(session)
        session.add(
            PlayerShotChart(
                player_id=player.id,
                season="2024-25",
                season_type="Regular Season",
                shots=[
                    shot_payload(game_id="0022400001", game_date="2025-01-01", period=4, shot_made=True, shot_type="3PT Field Goal", shot_value=3, zone_basic="Above the Break 3", distance=25),
                    shot_payload(game_id="0022400002", game_date="2025-01-02", period=4, shot_made=False, shot_type="3PT Field Goal", shot_value=3, zone_basic="Above the Break 3", distance=25),
                    shot_payload(game_id="0022400003", game_date="2025-01-03", period=4, shot_made=True, shot_type="3PT Field Goal", shot_value=3, zone_basic="Above the Break 3", distance=25),
                    shot_payload(game_id="0022400004", game_date="2025-01-03", period=4, shot_made=False, shot_type="3PT Field Goal", shot_value=3, zone_basic="Above the Break 3", distance=25),
                    shot_payload(game_id="0022400005", game_date="2025-01-03", period=4, shot_made=True, shot_type="3PT Field Goal", shot_value=3, zone_basic="Above the Break 3", distance=25),
                    shot_payload(game_id="0022400006", game_date="2025-01-03", period=4, shot_made=True, shot_type="3PT Field Goal", shot_value=3, zone_basic="Above the Break 3", distance=25),
                    shot_payload(game_id="0022400007", game_date="2025-01-03", period=2, shot_made=True, shot_type="2PT Field Goal", shot_value=2, zone_basic="Restricted Area", distance=1),
                ],
                shot_count=7,
                fetched_at=datetime(2026, 4, 5, 12, 0, 0),
                expires_at=datetime.utcnow() + timedelta(days=1),
            )
        )
        session.commit()

        response = player_shot_zones(
            player.id,
            season="2024-25",
            season_type="Regular Season",
            start_date="2025-01-02",
            end_date="2025-01-03",
            period_bucket="q4",
            result="made",
            shot_value="3pt",
            db=session,
        )

        assert response.total_attempts == 3
        assert len(response.zones) == 1
        assert response.zones[0].zone_basic == "Above the Break 3"
        assert response.zones[0].attempts == 3
        assert response.zones[0].made == 3
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


def test_refresh_player_shot_chart_queues_single_player_job():
    session = make_session()
    try:
        player = seed_player(session, player_id=19)

        response = refresh_player_shot_chart(
            player.id,
            season="2024-25",
            season_type="Regular Season",
            force=True,
            db=session,
        )

        assert response.queued == 1
        assert response.jobs[0].job_type == "sync_player_shot_chart"
        assert response.jobs[0].job_key == "19:2024-25:Regular Season"
    finally:
        session.close()


def test_refresh_team_defense_shot_chart_queues_opponent_player_jobs():
    session = make_session()
    try:
        session.add_all(
            [
                Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks"),
                Team(id=1610612738, abbreviation="BOS", name="Boston Celtics"),
                Team(id=1610612739, abbreviation="CLE", name="Cleveland Cavaliers"),
                Player(id=41, full_name="Opponent One", team_id=1610612738, is_active=True),
                Player(id=42, full_name="Opponent Two", team_id=1610612739, is_active=True),
            ]
        )
        session.commit()
        seed_game(session, game_id="0022400110", season="2024-25", home_team_id=1610612737, away_team_id=1610612738)
        seed_game(session, game_id="0022400111", season="2024-25", home_team_id=1610612739, away_team_id=1610612737)
        session.add_all(
            [
                GamePlayerStat(game_id="0022400110", season="2024-25", player_id=41, team_id=1610612738, team_abbreviation="BOS"),
                GamePlayerStat(game_id="0022400111", season="2024-25", player_id=42, team_id=1610612739, team_abbreviation="CLE"),
            ]
        )
        session.commit()

        response = refresh_team_defense_shot_chart(
            1610612737,
            season="2024-25",
            season_type="Regular Season",
            force=True,
            db=session,
        )

        assert response.queued == 2
        assert [job.job_key for job in response.jobs] == [
            "41:2024-25:Regular Season",
            "42:2024-25:Regular Season",
        ]
    finally:
        session.close()


def test_shot_completeness_report_counts_ready_legacy_and_missing():
    session = make_session()
    try:
        seed_player(session, player_id=21)
        seed_player(session, player_id=22)
        seed_player(session, player_id=23)
        seed_game(session, game_id="0022400100", has_schedule=True, has_pbp_payload=True, has_parsed_pbp=True)
        seed_game(session, game_id="0022400101", has_schedule=True, has_pbp_payload=True, has_parsed_pbp=False)
        seed_game(session, game_id="0022400102", has_schedule=True, has_pbp_payload=False, has_parsed_pbp=False)
        session.add_all(
            [
                GamePlayerStat(game_id="0022400100", season="2024-25", player_id=21, team_id=1610612737, team_abbreviation="ATL"),
                GamePlayerStat(game_id="0022400101", season="2024-25", player_id=22, team_id=1610612737, team_abbreviation="ATL"),
                GamePlayerStat(game_id="0022400102", season="2024-25", player_id=23, team_id=1610612737, team_abbreviation="ATL"),
                PlayerShotChart(
                    player_id=21,
                    season="2024-25",
                    season_type="Regular Season",
                    shots=[dict(shot_payload(), team_id=1610612737, opponent_team_id=1610612738, event_order_index=1, linkage_mode="exact")],
                    shot_count=1,
                    fetched_at=datetime(2026, 4, 5, 12, 0, 0),
                    expires_at=datetime.utcnow() + timedelta(days=1),
                ),
                PlayerShotChart(
                    player_id=22,
                    season="2024-25",
                    season_type="Regular Season",
                    shots=[{
                        "loc_x": 0,
                        "loc_y": 0,
                        "shot_made": True,
                        "shot_type": "2PT Field Goal",
                        "action_type": "Jump Shot",
                        "zone_basic": "Mid-Range",
                        "zone_area": "Center(C)",
                        "distance": 12,
                    }],
                    shot_count=1,
                    fetched_at=datetime(2026, 4, 5, 12, 0, 0),
                    expires_at=datetime.utcnow() + timedelta(days=1),
                ),
            ]
        )
        session.commit()

        response = shot_completeness_report("2024-25", season_type="Regular Season", db=session)
        domains = {domain.domain: domain for domain in response.domains}

        assert domains["player_shot_chart"].ready_count == 1
        assert domains["player_shot_chart"].legacy_count == 1
        assert domains["player_shot_chart"].missing_count == 1
        assert domains["game_event_stream"].ready_count == 1
        assert domains["game_event_stream"].partial_count == 1
        assert domains["game_event_stream"].legacy_count == 0
        assert domains["game_event_stream"].missing_count == 1
    finally:
        session.close()


def test_shot_lab_snapshot_roundtrip_preserves_payload():
    session = make_session()
    try:
        snapshot = post_shot_lab_snapshot(
            payload=ShotLabSnapshotCreateRequest(
                subject_type="player",
                subject_id=7,
                season="2024-25",
                season_type="Regular Season",
                active_view="sprawl",
                route_path="/players/7",
                filters={
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-10",
                    "period_bucket": "q4",
                    "result": "made",
                    "shot_value": "3pt",
                },
                metadata={"label": "Test Snapshot"},
            ),
            db=session,
        )

        fetched = get_shot_lab_snapshot_route(snapshot.snapshot_id, db=session)

        assert snapshot.snapshot_id == fetched.snapshot_id
        assert "shot_snapshot_id=" in snapshot.share_url
        assert fetched.payload.active_view == "sprawl"
        assert fetched.payload.filters.period_bucket == "q4"
        assert fetched.payload.metadata["label"] == "Test Snapshot"
    finally:
        session.close()


def test_team_defense_routes_filter_opponent_attempts():
    session = make_session()
    try:
        home_team = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks")
        away_team = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
        opponent = Player(id=30, full_name="Opponent Shooter", team_id=away_team.id, is_active=True)
        session.add_all([home_team, away_team, opponent])
        session.commit()
        seed_game(session, game_id="0022400200", home_team_id=home_team.id, away_team_id=away_team.id)
        session.add(
            GamePlayerStat(
                game_id="0022400200",
                season="2024-25",
                player_id=opponent.id,
                team_id=away_team.id,
                team_abbreviation="BOS",
            )
        )
        session.add(
            PlayerShotChart(
                player_id=opponent.id,
                season="2024-25",
                season_type="Regular Season",
                shots=[
                    dict(
                        shot_payload(
                            game_id="0022400200",
                            game_date="2025-01-11",
                            period=4,
                            shot_made=True,
                            shot_type="3PT Field Goal",
                            shot_value=3,
                            zone_basic="Above the Break 3",
                            distance=27,
                        ),
                        team_id=away_team.id,
                        opponent_team_id=home_team.id,
                    ),
                    dict(
                        shot_payload(
                            game_id="0022400200",
                            game_date="2025-01-11",
                            period=2,
                            shot_made=False,
                            shot_type="2PT Field Goal",
                            shot_value=2,
                            zone_basic="Mid-Range",
                            distance=14,
                        ),
                        team_id=away_team.id,
                        opponent_team_id=home_team.id,
                    ),
                ],
                shot_count=2,
                fetched_at=datetime(2026, 4, 5, 12, 0, 0),
                expires_at=datetime.utcnow() + timedelta(days=1),
            )
        )
        session.commit()

        chart = team_defense_shot_chart(
            home_team.id,
            season="2024-25",
            season_type="Regular Season",
            period_bucket="q4",
            shot_value="3pt",
            db=session,
        )
        zones = team_defense_shot_zones(
            home_team.id,
            season="2024-25",
            season_type="Regular Season",
            period_bucket="q4",
            shot_value="3pt",
            db=session,
        )

        assert chart.team_abbreviation == "ATL"
        assert chart.attempted == 1
        assert chart.shots[0].team_abbreviation == "BOS"
        assert chart.completeness_status in {"partial", "ready"}
        assert zones.total_attempts == 1
        assert zones.zones[0].zone_basic == "Above the Break 3"
    finally:
        session.close()


def test_build_game_visualization_marks_exact_and_timeline_elements():
    session = make_session()
    try:
        home_team = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks")
        away_team = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
        shooter = Player(id=40, full_name="Visualizer Shooter", team_id=away_team.id, is_active=True)
        session.add_all([home_team, away_team, shooter])
        session.commit()
        seed_game(session, game_id="0022400300", home_team_id=home_team.id, away_team_id=away_team.id)
        session.add_all(
            [
                PlayByPlayEvent(
                    game_id="0022400300",
                    season="2024-25",
                    source_event_id="evt-1",
                    action_number=101,
                    order_index=1,
                    period=4,
                    clock="1:22",
                    team_id=away_team.id,
                    player_id=shooter.id,
                    action_type="3pt",
                    action_family="jump_shot",
                    sub_type="made",
                    description="Visualizer Shooter makes 3-pt jump shot",
                    score_home=100,
                    score_away=103,
                ),
                PlayByPlayEvent(
                    game_id="0022400300",
                    season="2024-25",
                    source_event_id="evt-2",
                    action_number=102,
                    order_index=2,
                    period=4,
                    clock="1:05",
                    team_id=home_team.id,
                    action_type="turnover",
                    action_family="live_ball_turnover",
                    description="Turnover by ATL",
                    score_home=100,
                    score_away=103,
                ),
                PlayerShotChart(
                    player_id=shooter.id,
                    season="2024-25",
                    season_type="Regular Season",
                    shots=[
                        dict(
                            shot_payload(
                                game_id="0022400300",
                                game_date="2025-01-12",
                                period=4,
                                clock="1:22",
                                shot_type="3PT Field Goal",
                                shot_value=3,
                                shot_event_id="evt-1",
                            ),
                            event_order_index=1,
                            action_number=101,
                            team_id=away_team.id,
                            opponent_team_id=home_team.id,
                            linkage_mode="exact",
                        )
                    ],
                    shot_count=1,
                    fetched_at=datetime(2026, 4, 5, 12, 0, 0),
                    expires_at=datetime.utcnow() + timedelta(days=1),
                ),
            ]
        )
        session.commit()

        response = build_game_visualization(
            session,
            game_id="0022400300",
            shot_event_id="evt-1",
            source="shot-lab",
        )

        assert response is not None
        assert response.exact_shot_match is True
        assert response.steps[0].exact_shot_match is True
        assert response.steps[0].elements[0].kind == "shot_arc"
        assert response.steps[0].elements[0].exactness == "exact"
        assert response.steps[1].elements[0].kind == "context_token"
        assert response.steps[1].elements[0].exactness == "timeline"
    finally:
        session.close()


def test_game_detail_reports_legacy_event_stream_when_only_legacy_rows_exist():
    session = make_session()
    try:
        home_team = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks")
        away_team = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
        shooter = Player(id=77, full_name="Legacy Guard", team_id=away_team.id, is_active=True)
        session.add_all([home_team, away_team, shooter])
        session.commit()
        session.add(
            GameLog(
                game_id="0022400400",
                season="2024-25",
                game_date=datetime(2025, 1, 14).date(),
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_score=98,
                away_score=101,
            )
        )
        seed_game(
            session,
            game_id="0022400400",
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            has_schedule=True,
            has_pbp_payload=False,
            has_parsed_pbp=False,
        )
        session.add(
            PlayByPlay(
                game_id="0022400400",
                action_number=11,
                period=4,
                clock="1:11",
                team_id=away_team.id,
                player_id=shooter.id,
                action_type="3pt",
                sub_type="made",
                description="Legacy Guard makes 3-pt jump shot",
                score_home=98,
                score_away=101,
            )
        )
        session.commit()

        response = get_game_detail("0022400400", db=session)

        assert response.data_status == "ready"
        assert response.completeness_status == "legacy"
        assert response.canonical_source == "legacy-play-by-play"
        assert response.events[0].source_event_id == "11"
    finally:
        session.close()


def test_shot_completeness_report_distinguishes_legacy_vs_missing_game_events():
    session = make_session()
    try:
        seed_game(
            session,
            game_id="0022400500",
            season="2024-25",
            has_schedule=True,
            has_pbp_payload=False,
            has_parsed_pbp=False,
        )
        seed_game(
            session,
            game_id="0022400501",
            season="2024-25",
            has_schedule=True,
            has_pbp_payload=False,
            has_parsed_pbp=False,
        )
        session.add(
            PlayByPlay(
                game_id="0022400500",
                action_number=1,
                period=1,
                clock="12:00",
                team_id=1610612737,
                player_id=None,
                action_type="jumpball",
                sub_type=None,
                description="Jump ball",
                score_home=0,
                score_away=0,
            )
        )
        session.commit()

        response = shot_completeness_report("2024-25", season_type="Regular Season", db=session)
        rows = {
            row.entity_id: row
            for row in response.rows
            if row.entity_type == "game_event_stream"
        }

        assert rows["0022400500"].completeness_status == "legacy"
        assert rows["0022400500"].data_status == "ready"
        assert rows["0022400501"].completeness_status == "missing"
        assert rows["0022400501"].data_status == "missing"
    finally:
        session.close()


def test_pbp_coverage_reports_legacy_when_only_legacy_rows_exist():
    session = make_session()
    try:
        player = seed_player(session, player_id=88)
        session.add(
            SeasonStat(
                player_id=player.id,
                season="2024-25",
                team_abbreviation="ATL",
                is_playoff=False,
                gp=1,
            )
        )
        session.add(
            PlayerGameLog(
                player_id=player.id,
                game_id="0022400600",
                season="2024-25",
                season_type="Regular Season",
                game_date=datetime(2025, 1, 20).date(),
                matchup="ATL vs BOS",
            )
        )
        session.add(
            GameLog(
                game_id="0022400600",
                season="2024-25",
                game_date=datetime(2025, 1, 20).date(),
                home_team_id=1610612737,
                away_team_id=1610612738,
                home_score=102,
                away_score=99,
            )
        )
        seed_game(
            session,
            game_id="0022400600",
            season="2024-25",
            has_schedule=True,
            has_pbp_payload=False,
            has_parsed_pbp=False,
        )
        session.add(
            PlayByPlay(
                game_id="0022400600",
                action_number=7,
                period=1,
                clock="8:20",
                team_id=1610612737,
                player_id=player.id,
                action_type="2pt",
                sub_type="made",
                description="Legacy Guard makes 2-pt shot",
                score_home=2,
                score_away=0,
            )
        )
        session.commit()

        response = get_pbp_coverage(player.id, season="2024-25", db=session)

        assert response.status == "partial"
        assert response.data_status == "ready"
        assert response.completeness_status == "legacy"
        assert response.canonical_source == "legacy-play-by-play"
    finally:
        session.close()
