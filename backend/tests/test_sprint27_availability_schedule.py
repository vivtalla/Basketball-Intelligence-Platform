from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GameTeamStat, Player, PlayerInjury, SeasonStat, Team, WarehouseGame  # noqa: E402
from services.pre_read_service import build_pre_read_deck  # noqa: E402
from services.schedule_service import list_upcoming_games  # noqa: E402
from services.team_availability_service import build_team_availability  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def seed_core_context(session):
    atl = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks", city="Atlanta")
    bos = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics", city="Boston")
    nyk = Team(id=1610612752, abbreviation="NYK", name="New York Knicks", city="New York")
    session.add_all([atl, bos, nyk])

    atl_players = [
        Player(id=1, full_name="Alpha Guard", first_name="Alpha", last_name="Guard", team_id=atl.id, team=atl, is_active=True, position="G", jersey="1"),
        Player(id=2, full_name="Bravo Wing", first_name="Bravo", last_name="Wing", team_id=atl.id, team=atl, is_active=True, position="F", jersey="2"),
        Player(id=3, full_name="Charlie Big", first_name="Charlie", last_name="Big", team_id=atl.id, team=atl, is_active=True, position="C", jersey="3"),
    ]
    bos_players = [
        Player(id=11, full_name="Delta Guard", first_name="Delta", last_name="Guard", team_id=bos.id, team=bos, is_active=True, position="G", jersey="4"),
        Player(id=12, full_name="Echo Wing", first_name="Echo", last_name="Wing", team_id=bos.id, team=bos, is_active=True, position="F", jersey="5"),
    ]
    session.add_all(atl_players + bos_players)

    stat_rows = [
        SeasonStat(player_id=1, season="2025-26", team_abbreviation="ATL", is_playoff=False, gp=40, pts_pg=24.5, bpm=4.6),
        SeasonStat(player_id=2, season="2025-26", team_abbreviation="ATL", is_playoff=False, gp=38, pts_pg=13.1, bpm=1.8),
        SeasonStat(player_id=3, season="2025-26", team_abbreviation="ATL", is_playoff=False, gp=36, pts_pg=7.4, bpm=0.4),
        SeasonStat(player_id=11, season="2025-26", team_abbreviation="BOS", is_playoff=False, gp=42, pts_pg=26.2, bpm=5.2),
        SeasonStat(player_id=12, season="2025-26", team_abbreviation="BOS", is_playoff=False, gp=41, pts_pg=15.0, bpm=2.4),
    ]
    session.add_all(stat_rows)

    recent_start = date.today() - timedelta(days=6)
    for index in range(6):
        game_id = "002250{0:04d}".format(index)
        game_date = recent_start + timedelta(days=index)
        session.add(
            WarehouseGame(
                game_id=game_id,
                season="2025-26",
                game_date=game_date,
                status="final",
                home_team_id=atl.id if index % 2 == 0 else bos.id,
                away_team_id=bos.id if index % 2 == 0 else atl.id,
                home_team_abbreviation="ATL" if index % 2 == 0 else "BOS",
                away_team_abbreviation="BOS" if index % 2 == 0 else "ATL",
                home_team_name="Atlanta Hawks" if index % 2 == 0 else "Boston Celtics",
                away_team_name="Boston Celtics" if index % 2 == 0 else "Atlanta Hawks",
                home_score=112 + index,
                away_score=105 + index,
            )
        )
        session.add(
            GameTeamStat(
                game_id=game_id,
                season="2025-26",
                team_id=atl.id,
                team_abbreviation="ATL",
                pts=112 + index,
                fgm=41 + index,
                fga=86,
                fg3m=13,
                fg3a=35,
                ftm=17,
                fta=22,
                oreb=10,
                dreb=30,
                reb=40,
                ast=26,
                tov=11,
                pf=18,
                minutes=240.0,
                plus_minus=6 + index,
                won=True,
                is_home=index % 2 == 0,
            )
        )
        session.add(
            GameTeamStat(
                game_id=game_id,
                season="2025-26",
                team_id=bos.id,
                team_abbreviation="BOS",
                pts=105 + index,
                fgm=39,
                fga=88,
                fg3m=12,
                fg3a=34,
                ftm=15,
                fta=19,
                oreb=9,
                dreb=29,
                reb=38,
                ast=23,
                tov=14,
                pf=19,
                minutes=240.0,
                plus_minus=-(6 + index),
                won=False,
                is_home=index % 2 != 0,
            )
        )

    future_games = [
        WarehouseGame(
            game_id="0022590001",
            season="2025-26",
            game_date=date.today() + timedelta(days=1),
            status="scheduled",
            home_team_id=atl.id,
            away_team_id=bos.id,
            home_team_abbreviation="ATL",
            away_team_abbreviation="BOS",
            home_team_name="Atlanta Hawks",
            away_team_name="Boston Celtics",
        ),
        WarehouseGame(
            game_id="0022590002",
            season="2025-26",
            game_date=date.today() + timedelta(days=3),
            status="scheduled",
            home_team_id=nyk.id,
            away_team_id=atl.id,
            home_team_abbreviation="NYK",
            away_team_abbreviation="ATL",
            home_team_name="New York Knicks",
            away_team_name="Atlanta Hawks",
        ),
        WarehouseGame(
            game_id="0022590003",
            season="2025-26",
            game_date=date.today() + timedelta(days=9),
            status="scheduled",
            home_team_id=bos.id,
            away_team_id=nyk.id,
            home_team_abbreviation="BOS",
            away_team_abbreviation="NYK",
            home_team_name="Boston Celtics",
            away_team_name="New York Knicks",
        ),
        WarehouseGame(
            game_id="0022590004",
            season="2025-26",
            game_date=date.today() + timedelta(days=2),
            status="final",
            home_team_id=bos.id,
            away_team_id=atl.id,
            home_team_abbreviation="BOS",
            away_team_abbreviation="ATL",
            home_team_name="Boston Celtics",
            away_team_name="Atlanta Hawks",
        ),
    ]
    session.add_all(future_games)

    report_date = date.today()
    session.add_all(
        [
            PlayerInjury(
                player_id=1,
                team_id=atl.id,
                report_date=report_date,
                season="2025-26",
                injury_status="Out",
                injury_type="Hamstring",
                detail="Left hamstring tightness",
                return_date=report_date + timedelta(days=5),
            ),
            PlayerInjury(
                player_id=2,
                team_id=atl.id,
                report_date=report_date,
                season="2025-26",
                injury_status="Questionable",
                injury_type="Ankle",
                detail="Right ankle soreness",
            ),
            PlayerInjury(
                player_id=12,
                team_id=bos.id,
                report_date=report_date,
                season="2025-26",
                injury_status="Probable",
                injury_type="Illness",
                detail="Available if needed",
            ),
        ]
    )

    session.commit()
    return atl, bos, nyk


def test_list_upcoming_games_filters_window_and_team():
    session = make_session()
    try:
        atl, _bos, _nyk = seed_core_context(session)

        games = list_upcoming_games(session, season="2025-26", days=7, today=date.today())
        assert [game.game_id for game in games] == ["0022590001", "0022590002"]

        atl_games = list_upcoming_games(session, season="2025-26", days=7, team_abbreviation=atl.abbreviation, today=date.today())
        assert [game.game_id for game in atl_games] == ["0022590001", "0022590002"]
        assert atl_games[0].home_team_abbreviation == "ATL"
    finally:
        session.close()


def test_team_availability_groups_players_and_surfaces_next_game():
    session = make_session()
    try:
        atl, _bos, _nyk = seed_core_context(session)
        report = build_team_availability(session, atl.abbreviation, "2025-26", today=date.today())

        assert report.overall_status == "shorthanded"
        assert report.unavailable_count == 1
        assert report.questionable_count == 1
        assert report.probable_count == 0
        assert report.key_absences[0].player_name == "Alpha Guard"
        assert report.key_absences[0].impact_label == "high impact"
        assert report.questionable_players[0].return_date is None
        assert report.next_game is not None
        assert report.next_game.opponent_abbreviation == "BOS"
        assert report.next_game.is_home is True
    finally:
        session.close()


def test_team_availability_returns_healthy_when_latest_report_skips_team():
    session = make_session()
    try:
        _atl, bos, _nyk = seed_core_context(session)
        report = build_team_availability(session, bos.abbreviation, "2025-26", today=date.today())

        assert report.report_date == date.today()
        assert report.unavailable_count == 0
        assert report.questionable_count == 0
        assert report.probable_count == 1
        assert report.overall_status == "monitor"

        session.query(PlayerInjury).delete()
        session.add(
            PlayerInjury(
                player_id=1,
                team_id=1610612737,
                report_date=date.today(),
                season="2025-26",
                injury_status="Out",
                injury_type="Hamstring",
            )
        )
        session.commit()

        healthy_report = build_team_availability(session, bos.abbreviation, "2025-26", today=date.today())
        assert healthy_report.report_date == date.today()
        assert healthy_report.unavailable_count == 0
        assert healthy_report.questionable_count == 0
        assert healthy_report.probable_count == 0
        assert healthy_report.overall_status == "healthy"
    finally:
        session.close()


def test_pre_read_deck_includes_structured_availability_blocks():
    session = make_session()
    try:
        atl, bos, _nyk = seed_core_context(session)
        deck = build_pre_read_deck(session, atl.abbreviation, bos.abbreviation, "2025-26")

        assert deck.team_availability.abbreviation == "ATL"
        assert deck.opponent_availability.abbreviation == "BOS"
        assert deck.team_availability.unavailable_count == 1
        assert deck.opponent_availability.probable_count == 1
        assert any(bullet.startswith("ATL: ") for bullet in deck.slides[0].bullets)
        assert any(bullet.startswith("BOS: ") for bullet in deck.slides[0].bullets)
    finally:
        session.close()
