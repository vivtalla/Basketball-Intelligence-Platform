from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    GameLog,
    GameTeamStat,
    LineupStats,
    PlayByPlay,
    PlayByPlayEvent,
    Player,
    PlayerInjury,
    PlayerOnOff,
    SeasonStat,
    Team,
    TeamStanding,
    WarehouseGame,
)
from services.team_intelligence_service import build_team_intelligence  # noqa: E402
from services.team_prep_service import build_team_prep_queue  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def seed_modern_context(session):
    today = date.today()
    atl = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks", city="Atlanta", conference="East")
    bos = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics", city="Boston", conference="East")
    nyk = Team(id=1610612752, abbreviation="NYK", name="New York Knicks", city="New York", conference="East")
    session.add_all([atl, bos, nyk])

    players = [
        Player(id=1, full_name="Alpha Guard", first_name="Alpha", last_name="Guard", team_id=atl.id, is_active=True),
        Player(id=2, full_name="Bravo Wing", first_name="Bravo", last_name="Wing", team_id=atl.id, is_active=True),
        Player(id=11, full_name="Delta Guard", first_name="Delta", last_name="Guard", team_id=bos.id, is_active=True),
        Player(id=12, full_name="Echo Wing", first_name="Echo", last_name="Wing", team_id=bos.id, is_active=True),
    ]
    session.add_all(players)

    session.add_all(
        [
            SeasonStat(player_id=1, season="2025-26", team_abbreviation="ATL", is_playoff=False, gp=5, pts_pg=24.5, bpm=4.4, clutch_pts=18),
            SeasonStat(player_id=2, season="2025-26", team_abbreviation="ATL", is_playoff=False, gp=5, pts_pg=14.2, bpm=1.7),
            SeasonStat(player_id=11, season="2025-26", team_abbreviation="BOS", is_playoff=False, gp=5, pts_pg=25.1, bpm=5.0),
            SeasonStat(player_id=12, season="2025-26", team_abbreviation="BOS", is_playoff=False, gp=5, pts_pg=16.1, bpm=2.5),
        ]
    )

    session.add_all(
        [
            PlayerOnOff(player_id=1, season="2025-26", is_playoff=False, on_minutes=150.0, off_minutes=80.0, on_off_net=7.2),
            PlayerOnOff(player_id=2, season="2025-26", is_playoff=False, on_minutes=120.0, off_minutes=70.0, on_off_net=2.4),
        ]
    )

    session.add(
        LineupStats(
            lineup_key="1-2-11-12-99",
            season="2025-26",
            team_id=atl.id,
            minutes=45.0,
            net_rating=8.3,
            ortg=118.4,
            drtg=110.1,
            plus_minus=12.0,
            possessions=95,
        )
    )

    final_games = [
        ("0022600001", today - timedelta(days=3), atl, bos, 112, 104),
        ("0022600002", today - timedelta(days=1), nyk, atl, 106, 111),
        ("0022600003", today, atl, bos, 118, 110),
    ]
    for game_id, game_date, home, away, home_score, away_score in final_games:
        session.add(
            WarehouseGame(
                game_id=game_id,
                season="2025-26",
                game_date=game_date,
                status="final",
                home_team_id=home.id,
                away_team_id=away.id,
                home_team_abbreviation=home.abbreviation,
                away_team_abbreviation=away.abbreviation,
                home_team_name=home.name,
                away_team_name=away.name,
                home_score=home_score,
                away_score=away_score,
                has_parsed_pbp=True,
            )
        )
        for team in (home, away):
            pts = home_score if team.id == home.id else away_score
            won = (team.id == home.id and home_score > away_score) or (team.id == away.id and away_score > home_score)
            session.add(
                GameTeamStat(
                    game_id=game_id,
                    season="2025-26",
                    team_id=team.id,
                    team_abbreviation=team.abbreviation,
                    is_home=team.id == home.id,
                    won=won,
                    pts=pts,
                    reb=42,
                    ast=25,
                    tov=12,
                    fgm=40,
                    fga=85,
                    fg3m=13,
                    fg3a=35,
                    ftm=19,
                    fta=24,
                    oreb=10,
                    dreb=31,
                    pf=18,
                    minutes=240.0,
                    plus_minus=8.0 if won else -8.0,
                )
            )
        session.add(
            PlayByPlayEvent(
                game_id=game_id,
                season="2025-26",
                order_index=1,
                action_number=1,
                period=1,
                team_id=home.id,
                player_id=1,
                action_type="tip",
                action_family="start",
                description="Opening tip",
            )
        )

    upcoming_games = [
        ("0022690001", today + timedelta(days=1), atl, bos, "scheduled"),
        ("0022690002", today + timedelta(days=3), nyk, atl, "scheduled"),
    ]
    for game_id, game_date, home, away, status in upcoming_games:
        session.add(
            WarehouseGame(
                game_id=game_id,
                season="2025-26",
                game_date=game_date,
                status=status,
                home_team_id=home.id,
                away_team_id=away.id,
                home_team_abbreviation=home.abbreviation,
                away_team_abbreviation=away.abbreviation,
                home_team_name=home.name,
                away_team_name=away.name,
            )
        )

    session.add_all(
        [
            TeamStanding(team_id=atl.id, season="2025-26", snapshot_date=today, wins=4, losses=1, last_10_wins=4, last_10_losses=1, current_streak=2, streak_type="W", conference="East", division="Southeast"),
            TeamStanding(team_id=bos.id, season="2025-26", snapshot_date=today, wins=3, losses=2, last_10_wins=3, last_10_losses=2, current_streak=-1, streak_type="L", conference="East", division="Atlantic"),
            TeamStanding(team_id=nyk.id, season="2025-26", snapshot_date=today, wins=2, losses=3, last_10_wins=2, last_10_losses=3, current_streak=1, streak_type="W", conference="East", division="Atlantic"),
        ]
    )

    session.add(
        PlayerInjury(
            player_id=12,
            team_id=bos.id,
            report_date=today,
            season="2025-26",
            injury_status="Probable",
            injury_type="Illness",
            detail="Expected to play",
        )
    )

    session.commit()
    return atl, bos, nyk


def seed_historical_context(session):
    atl = Team(id=7001, abbreviation="ATL", name="Atlanta Hawks", city="Atlanta", conference="East")
    bos = Team(id=7002, abbreviation="BOS", name="Boston Celtics", city="Boston", conference="East")
    session.add_all([atl, bos])
    session.add_all(
        [
            Player(id=701, full_name="Legacy Guard", first_name="Legacy", last_name="Guard", team_id=atl.id, is_active=True),
            Player(id=702, full_name="Legacy Wing", first_name="Legacy", last_name="Wing", team_id=atl.id, is_active=True),
        ]
    )
    session.add_all(
        [
            SeasonStat(player_id=701, season="2023-24", team_abbreviation="ATL", is_playoff=False, gp=2, pts_pg=18.0, bpm=2.1),
            PlayerOnOff(player_id=701, season="2023-24", is_playoff=False, on_minutes=60.0, off_minutes=20.0, on_off_net=3.5),
        ]
    )
    session.add(
        LineupStats(
            lineup_key="701-702-800-801-802",
            season="2023-24",
            team_id=atl.id,
            minutes=20.0,
            net_rating=1.2,
            ortg=110.0,
            drtg=108.8,
            plus_minus=3.0,
            possessions=40,
        )
    )
    session.add(
        GameLog(
            game_id="9000000001",
            season="2023-24",
            game_date=date.today() - timedelta(days=30),
            home_team_id=atl.id,
            away_team_id=bos.id,
            home_score=108,
            away_score=101,
        )
    )
    session.add(
        PlayByPlay(
            game_id="9000000001",
            action_number=1,
            period=1,
            team_id=atl.id,
            player_id=701,
            action_type="shot",
            sub_type="made",
            description="Legacy bucket",
        )
    )
    session.commit()
    return atl


def test_team_intelligence_modern_season_uses_warehouse_and_standings():
    session = make_session()
    try:
        atl, _bos, _nyk = seed_modern_context(session)
        response = build_team_intelligence(session, atl.abbreviation, "2025-26")

        assert response.canonical_source == "warehouse"
        assert response.data_status == "partial"
        assert response.conference == "East"
        assert response.playoff_rank == 1
        assert response.pbp_coverage.synced_games == 3
        assert response.pbp_coverage.eligible_games == 5
        assert response.recent_games[0].game_id == "0022690002"
        assert response.last_synced_at is not None
    finally:
        session.close()


def test_team_intelligence_historical_season_degrades_to_limited():
    session = make_session()
    try:
        atl = seed_historical_context(session)
        response = build_team_intelligence(session, atl.abbreviation, "2023-24")

        assert response.canonical_source == "legacy-plus-derived"
        assert response.data_status == "limited"
        assert response.pbp_coverage.synced_games == 1
        assert response.recent_games[0].game_id == "9000000001"
    finally:
        session.close()


def test_prep_queue_orders_games_and_surfaces_context():
    session = make_session()
    try:
        atl, _bos, _nyk = seed_modern_context(session)
        response = build_team_prep_queue(session, atl.abbreviation, "2025-26", days=7, today=date.today())

        assert response.canonical_source == "warehouse"
        assert response.data_status == "ready"
        assert [item.game_id for item in response.items] == ["0022690001", "0022690002"]

        first = response.items[0]
        assert first.opponent_abbreviation == "BOS"
        assert first.team_rest_days == 0
        assert first.schedule_pressure == "back-to-back"
        assert first.opponent_record == "3-2"
        assert first.probable_count == 1
        assert first.prep_urgency == "medium"
        assert first.prep_headline is not None
        assert first.urgency_rationale is not None
        assert first.best_edge_summary is not None
        assert first.best_edge_rationale is not None
        assert first.best_edge_factor_id in {"shooting", "turnovers", "rebounding", None}
        assert first.first_adjustment_summary is not None
        assert first.first_adjustment_rationale is not None
        assert first.first_adjustment_factor_id in {"shooting", "turnovers", "rebounding", "free_throws"}
        assert "team=ATL" in first.pre_read_url
        assert "source_view=team-prep" in first.pre_read_url
        assert "mode=scouting" in first.scouting_url
        assert "source_type=prep-queue" in first.compare_url
        assert "return_to=%2Fteams%2FATL%3Ftab%3Dprep" in first.compare_url
        assert "team_a=ATL" in first.compare_url
        assert "opponent=BOS" in first.follow_through_url
    finally:
        session.close()
