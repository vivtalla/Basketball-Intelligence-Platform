from datetime import datetime, timedelta
from pathlib import Path
import sys
from unittest.mock import patch
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GamePlayerStat, IngestionJob, Player, PlayerGameLog, SeasonStat, Team  # noqa: E402
from routers.gamelogs import player_game_logs  # noqa: E402
from routers.players import get_player  # noqa: E402
from routers.stats import career_stats  # noqa: E402
from services.warehouse_service import (  # noqa: E402
    _get_or_create_player,
    get_readiness_summary,
    player_profile_needs_enrichment,
    queue_player_career_sync,
    queue_player_gamelogs_sync,
    queue_player_profile_sync,
    run_next_job,
)


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def seed_player(session, player_id: int = 21, updated_at: Optional[datetime] = None) -> Player:
    team = session.query(Team).filter_by(id=1610612738).first()
    if not team:
        team = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
        session.add(team)
    player = Player(
        id=player_id,
        full_name="DB First",
        first_name="DB",
        last_name="First",
        team_id=team.id,
        is_active=True,
        updated_at=updated_at,
    )
    session.add(player)
    session.commit()
    return player


def test_player_route_returns_missing_profile_without_sync():
    session = make_session()
    try:
        response = get_player(404, db=session)

        assert response.id == 404
        assert response.data_status == "missing"
        assert response.full_name == ""
        assert response.last_synced_at is None
    finally:
        session.close()


def test_career_route_returns_stale_cached_rows_without_sync():
    session = make_session()
    try:
        player = seed_player(session, updated_at=datetime.utcnow() - timedelta(days=3))
        session.add(
            SeasonStat(
                player_id=player.id,
                season="2025-26",
                team_abbreviation="BOS",
                is_playoff=False,
                gp=10,
                pts=220,
                pts_pg=22.0,
                reb=50,
                reb_pg=5.0,
                ast=40,
                ast_pg=4.0,
                min_total=320,
                min_pg=32.0,
                updated_at=datetime.utcnow() - timedelta(days=2),
            )
        )
        session.commit()

        response = career_stats(player.id, db=session)

        assert response.data_status == "stale"
        assert response.last_synced_at is not None
        assert len(response.seasons) == 1
        assert response.seasons[0].season == "2025-26"
    finally:
        session.close()


def test_gamelogs_route_returns_missing_without_remote_fetch():
    session = make_session()
    try:
        player = seed_player(session, player_id=31)

        response = player_game_logs(player.id, season="2025-26", season_type="Regular Season", db=session)

        assert response.data_status == "missing"
        assert response.gp == 0
        assert response.games == []
        assert response.last_synced_at is None
    finally:
        session.close()


def test_readiness_summary_counts_ready_stale_and_missing_domains():
    session = make_session()
    try:
        ready = seed_player(session, player_id=51, updated_at=datetime.utcnow())
        stale = seed_player(session, player_id=52, updated_at=datetime.utcnow() - timedelta(days=30))
        missing = seed_player(session, player_id=53, updated_at=datetime.utcnow())

        session.add_all(
            [
                GamePlayerStat(game_id="0022500001", season="2025-26", player_id=ready.id, team_id=ready.team_id),
                GamePlayerStat(game_id="0022500002", season="2025-26", player_id=stale.id, team_id=stale.team_id),
                GamePlayerStat(game_id="0022500003", season="2025-26", player_id=missing.id, team_id=missing.team_id),
                SeasonStat(
                    player_id=ready.id,
                    season="2025-26",
                    team_abbreviation="BOS",
                    is_playoff=False,
                    gp=12,
                    pts=240,
                    pts_pg=20.0,
                    min_total=360,
                    min_pg=30.0,
                    updated_at=datetime.utcnow(),
                ),
                SeasonStat(
                    player_id=stale.id,
                    season="2025-26",
                    team_abbreviation="BOS",
                    is_playoff=False,
                    gp=12,
                    pts=180,
                    pts_pg=15.0,
                    min_total=300,
                    min_pg=25.0,
                    updated_at=datetime.utcnow() - timedelta(days=3),
                ),
                PlayerGameLog(
                    player_id=ready.id,
                    game_id="0022500001",
                    season="2025-26",
                    season_type="Regular Season",
                    synced_at=datetime.utcnow(),
                ),
                PlayerGameLog(
                    player_id=stale.id,
                    game_id="0022500002",
                    season="2025-26",
                    season_type="Regular Season",
                    synced_at=datetime.utcnow() - timedelta(days=3),
                ),
            ]
        )
        session.commit()

        summary = get_readiness_summary(session, "2025-26")
        by_domain = {row["domain"]: row for row in summary["domains"]}

        assert by_domain["player_profile"] == {
            "domain": "player_profile",
            "eligible_count": 3,
            "ready_count": 2,
            "stale_count": 1,
            "missing_count": 0,
        }
        assert by_domain["career_stats"]["eligible_count"] == 2
        assert by_domain["career_stats"]["ready_count"] == 1
        assert by_domain["career_stats"]["stale_count"] == 1
        assert by_domain["game_logs"]["eligible_count"] == 3
        assert by_domain["game_logs"]["ready_count"] == 1
        assert by_domain["game_logs"]["stale_count"] == 1
        assert by_domain["game_logs"]["missing_count"] == 1
    finally:
        session.close()


def test_player_jobs_queue_and_run_through_workers():
    session = make_session()
    try:
        player = seed_player(session, player_id=61, updated_at=datetime.utcnow() - timedelta(days=20))

        queue_player_profile_sync(session, player.id, force=True)
        queue_player_career_sync(session, player.id, force=True)
        queue_player_gamelogs_sync(session, player.id, season="2025-26", force=True)
        session.commit()

        def fake_sync_player(db, player_id):
            row = db.query(Player).filter(Player.id == player_id).first()
            row.full_name = "Queued Worker"
            row.updated_at = datetime.utcnow()
            existing = (
                db.query(SeasonStat)
                .filter(
                    SeasonStat.player_id == player_id,
                    SeasonStat.season == "2025-26",
                    SeasonStat.is_playoff == False,  # noqa: E712
                )
                .first()
            )
            if not existing:
                db.add(
                    SeasonStat(
                        player_id=player_id,
                        season="2025-26",
                        team_abbreviation="BOS",
                        is_playoff=False,
                        gp=8,
                        pts=144,
                        pts_pg=18.0,
                        min_total=256,
                        min_pg=32.0,
                        updated_at=datetime.utcnow(),
                    )
                )
            else:
                existing.updated_at = datetime.utcnow()
            db.flush()
            return row

        with patch("services.warehouse_service.sync_player", side_effect=fake_sync_player), patch(
            "services.warehouse_service.get_player_game_logs",
            return_value=[
                {
                    "game_id": "0022500099",
                    "game_date": "2025-11-01",
                    "matchup": "BOS vs NYK",
                    "wl": "W",
                    "min": 31,
                    "pts": 24,
                    "reb": 6,
                    "ast": 5,
                    "stl": 1,
                    "blk": 0,
                    "tov": 2,
                    "fgm": 8,
                    "fga": 16,
                    "fg_pct": 0.5,
                    "fg3m": 3,
                    "fg3a": 7,
                    "fg3_pct": 0.429,
                    "ftm": 5,
                    "fta": 6,
                    "ft_pct": 0.833,
                    "oreb": 1,
                    "dreb": 5,
                    "pf": 2,
                    "plus_minus": 9,
                }
            ],
        ):
            first = run_next_job(session)
            second = run_next_job(session)
            third = run_next_job(session)

        assert first["status"] == "ok"
        assert second["status"] == "ok"
        assert third["status"] == "ok"

        refreshed_player = session.query(Player).filter_by(id=player.id).first()
        refreshed_log = (
            session.query(PlayerGameLog)
            .filter_by(player_id=player.id, season="2025-26", season_type="Regular Season")
            .first()
        )
        refreshed_career = (
            session.query(SeasonStat)
            .filter_by(player_id=player.id, season="2025-26", is_playoff=False)
            .first()
        )

        assert refreshed_player is not None
        assert refreshed_player.full_name == "Queued Worker"
        assert refreshed_career is not None
        assert refreshed_log is not None
        assert refreshed_log.game_id == "0022500099"
    finally:
        session.close()


def test_incomplete_player_rows_queue_profile_enrichment():
    session = make_session()
    try:
        team = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks")
        session.add(team)
        session.commit()

        player = _get_or_create_player(
            session,
            player_id=901,
            full_name="Rookie Lastname",
            team_id=team.id,
        )
        session.commit()

        assert player is not None
        assert player_profile_needs_enrichment(player) is True

        queued = session.query(IngestionJob).filter_by(
            job_type="sync_player_profile",
            job_key="901",
        ).one_or_none()
        assert queued is not None
        assert queued.status == "queued"
    finally:
        session.close()
