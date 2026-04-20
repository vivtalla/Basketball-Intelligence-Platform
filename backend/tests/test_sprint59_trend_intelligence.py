from datetime import date, datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    GamePlayerStat,
    GameTeamStat,
    LineupStats,
    Player,
    PlayerOnOff,
    PlayerShotChart,
    PlayByPlayEvent,
    SeasonStat,
    Team,
    WarehouseGame,
)
from main import app  # noqa: E402
from services.trend_card_service import build_trend_cards_report  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def seed_trends(session):
    today = date(2026, 4, 19)
    team = Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder", city="Oklahoma City", conference="West")
    opponent = Team(id=1610612743, abbreviation="DEN", name="Denver Nuggets", city="Denver", conference="West")
    session.add_all([team, opponent])
    session.add_all(
        [
            Player(id=101, full_name="Rising Guard", first_name="Rising", last_name="Guard", team_id=team.id, position="G", is_active=True),
            Player(id=102, full_name="Surging Wing", first_name="Surging", last_name="Wing", team_id=team.id, position="F", is_active=True),
        ]
    )
    session.add_all(
        [
            SeasonStat(
                player_id=101,
                season="2025-26",
                team_abbreviation=team.abbreviation,
                is_playoff=False,
                gp=4,
                min_pg=24.0,
                pts_pg=11.0,
                ts_pct=0.55,
                clutch_plus_minus=2.0,
            ),
            SeasonStat(
                player_id=102,
                season="2025-26",
                team_abbreviation=team.abbreviation,
                is_playoff=False,
                gp=4,
                min_pg=28.0,
                pts_pg=14.0,
                ts_pct=0.56,
                clutch_plus_minus=1.0,
            ),
        ]
    )

    game_specs = [
        ("0025900001", today - timedelta(days=8), 104, 108, 10, 14),
        ("0025900002", today - timedelta(days=6), 108, 110, 12, 16),
        ("0025900003", today - timedelta(days=3), 121, 111, 18, 28),
        ("0025900004", today - timedelta(days=1), 126, 109, 17, 31),
    ]
    for index, (game_id, game_date, okc_pts, den_pts, p1_pts, p2_pts) in enumerate(game_specs):
        session.add(
            WarehouseGame(
                game_id=game_id,
                season="2025-26",
                game_date=game_date,
                status="final",
                home_team_id=team.id,
                away_team_id=opponent.id,
                home_team_abbreviation=team.abbreviation,
                away_team_abbreviation=opponent.abbreviation,
                home_score=okc_pts,
                away_score=den_pts,
                has_parsed_pbp=True,
            )
        )
        session.add_all(
            [
                GameTeamStat(
                    game_id=game_id,
                    season="2025-26",
                    team_id=team.id,
                    team_abbreviation=team.abbreviation,
                    is_home=True,
                    won=okc_pts > den_pts,
                    pts=okc_pts,
                    reb=42,
                    ast=26,
                    tov=9 if index >= 2 else 14,
                    fgm=43,
                    fga=88,
                    fg3m=15 if index >= 2 else 9,
                    fg3a=38 if index >= 2 else 28,
                    ftm=20,
                    fta=25,
                    oreb=11,
                    dreb=31,
                    pf=18,
                    minutes=240.0,
                    plus_minus=okc_pts - den_pts,
                ),
                GameTeamStat(
                    game_id=game_id,
                    season="2025-26",
                    team_id=opponent.id,
                    team_abbreviation=opponent.abbreviation,
                    is_home=False,
                    won=den_pts > okc_pts,
                    pts=den_pts,
                    reb=39,
                    ast=23,
                    tov=12,
                    fgm=40,
                    fga=86,
                    fg3m=11,
                    fg3a=31,
                    ftm=18,
                    fta=22,
                    oreb=8,
                    dreb=31,
                    pf=20,
                    minutes=240.0,
                    plus_minus=den_pts - okc_pts,
                ),
            ]
        )
        session.add_all(
            [
                GamePlayerStat(
                    game_id=game_id,
                    season="2025-26",
                    player_id=101,
                    team_id=team.id,
                    team_abbreviation=team.abbreviation,
                    game_date=game_date,
                    min=26.0,
                    pts=p1_pts,
                    fga=10,
                    fta=3,
                    fg3a=4,
                    tov=1,
                    plus_minus=5 if index >= 2 else -2,
                    is_starter=True,
                ),
                GamePlayerStat(
                    game_id=game_id,
                    season="2025-26",
                    player_id=102,
                    team_id=team.id,
                    team_abbreviation=team.abbreviation,
                    game_date=game_date,
                    min=31.0,
                    pts=p2_pts,
                    fga=14,
                    fta=5,
                    fg3a=7,
                    tov=1,
                    plus_minus=12 if index >= 2 else -1,
                    is_starter=True,
                ),
                PlayByPlayEvent(
                    game_id=game_id,
                    season="2025-26",
                    order_index=1,
                    action_number=1,
                    period=1,
                    team_id=team.id,
                    player_id=102,
                    action_type="3pt",
                    action_family="spot_up",
                    description="Surging Wing catch and shoot three",
                ),
                PlayByPlayEvent(
                    game_id=game_id,
                    season="2025-26",
                    order_index=2,
                    action_number=2,
                    period=2,
                    team_id=team.id,
                    player_id=101,
                    action_type="turnover",
                    action_family="live_ball_turnover",
                    description="Rising Guard turnover",
                ),
                PlayByPlayEvent(
                    game_id=game_id,
                    season="2025-26",
                    order_index=3,
                    action_number=3,
                    period=3,
                    team_id=team.id,
                    action_type="substitution",
                    action_family="substitution",
                    description="OKC substitution",
                ),
            ]
        )
    session.add_all(
        [
            PlayerOnOff(player_id=101, season="2025-26", is_playoff=False, on_off_net=3.0, on_minutes=96, off_minutes=96),
            PlayerOnOff(player_id=102, season="2025-26", is_playoff=False, on_off_net=9.0, on_minutes=124, off_minutes=68),
            LineupStats(lineup_key="101-102-201-202-203", season="2025-26", team_id=team.id, minutes=80.0, possessions=160, net_rating=14.2),
            PlayerShotChart(
                player_id=102,
                season="2025-26",
                season_type="Regular Season",
                shots=[
                    {"shot_made": True, "shot_value": 3, "shot_type": "3PT Field Goal", "zone_basic": "Above the Break 3", "zone_area": "Center", "distance": 25},
                    {"shot_made": True, "shot_value": 2, "shot_type": "2PT Field Goal", "zone_basic": "Restricted Area", "zone_area": "Center", "distance": 2},
                    {"shot_made": False, "shot_value": 3, "shot_type": "3PT Field Goal", "zone_basic": "Corner 3", "zone_area": "Right", "distance": 23},
                ],
                shot_count=3,
                fetched_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=1),
            ),
        ]
    )
    session.commit()
    return team


def test_trend_intelligence_returns_team_cards_sorted_movers_and_pinned_player():
    session = make_session()
    try:
        team = seed_trends(session)
        response = build_trend_cards_report(
            session,
            team.abbreviation,
            "2025-26",
            2,
            player_id=101,
        )

        assert response.data_status in {"ready", "partial"}
        assert response.overview is not None
        assert response.cards
        assert response.player_movers
        assert abs(response.player_movers[0].trend_score) >= abs(response.player_movers[-1].trend_score)
        assert response.pinned_player is not None
        assert response.pinned_player.row.player_id == 101
        assert response.pinned_player.foundation
    finally:
        session.close()


def test_trend_intelligence_keeps_replay_targets_and_partial_coverage_warnings():
    session = make_session()
    try:
        team = seed_trends(session)
        response = build_trend_cards_report(session, team.abbreviation, "2025-26", 2)

        replayable = {card.card_id: card.replay_target for card in response.cards if card.replay_target is not None}
        assert replayable["shot-profile-drift"] is not None
        assert replayable["turnover-pressure"] is not None
        assert replayable["rotation-drift"] is not None
        assert "source_surface=insights-trends" in replayable["shot-profile-drift"].deep_link_url
        assert "return_to=%2Finsights%3Ftab%3Dtrends" in replayable["shot-profile-drift"].deep_link_url
        assert any("coverage is partial" in warning for warning in response.warnings)
    finally:
        session.close()


def test_usage_efficiency_route_is_hard_deleted():
    paths = {route.path for route in app.routes}
    assert "/api/insights/usage-efficiency" not in paths
