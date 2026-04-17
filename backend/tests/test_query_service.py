from __future__ import annotations

import datetime as dt
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GameTeamStat, Player, PlayerGameLog, SeasonStat, Team, TeamSeasonStat, WarehouseGame  # noqa: E402
from models.query import QueryAskRequest  # noqa: E402
from routers.query import ask, examples, metrics  # noqa: E402
from services.query_metric_registry import resolve_metric  # noqa: E402
from services.query_service import answer_query  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def seed_query_data(session):
    teams = [
        Team(id=1610612738, abbreviation="BOS", city="Boston", name="Celtics", conference="East"),
        Team(id=1610612744, abbreviation="GSW", city="Golden State", name="Warriors", conference="West"),
        Team(id=1610612760, abbreviation="OKC", city="Oklahoma City", name="Thunder", conference="West"),
    ]
    session.add_all(teams)
    players = [
        Player(id=1, full_name="Shai Gilgeous-Alexander", first_name="Shai", last_name="Gilgeous-Alexander", team_id=1610612760, is_active=True, position="G"),
        Player(id=2, full_name="Jayson Tatum", first_name="Jayson", last_name="Tatum", team_id=1610612738, is_active=True, position="F"),
        Player(id=3, full_name="Stephen Curry", first_name="Stephen", last_name="Curry", team_id=1610612744, is_active=True, position="G"),
        Player(id=4, full_name="Efficient Wing", first_name="Efficient", last_name="Wing", team_id=1610612738, is_active=True, position="F"),
    ]
    session.add_all(players)
    session.add_all(
        [
            SeasonStat(player_id=1, season="2025-26", team_abbreviation="OKC", is_playoff=False, gp=32, pts_pg=31.4, reb_pg=5.2, ast_pg=6.1, ts_pct=0.625, net_rating=9.3),
            SeasonStat(player_id=2, season="2025-26", team_abbreviation="BOS", is_playoff=False, gp=31, pts_pg=28.2, reb_pg=8.5, ast_pg=4.7, ts_pct=0.604, net_rating=8.7),
            SeasonStat(player_id=3, season="2025-26", team_abbreviation="GSW", is_playoff=False, gp=28, pts_pg=26.1, reb_pg=4.1, ast_pg=6.4, ts_pct=0.598, net_rating=3.1),
            SeasonStat(player_id=4, season="2025-26", team_abbreviation="BOS", is_playoff=False, gp=26, pts_pg=24.5, reb_pg=6.0, ast_pg=3.0, ts_pct=0.640, net_rating=6.0),
            SeasonStat(player_id=1, season="2024-25", team_abbreviation="OKC", is_playoff=False, gp=70, pts_pg=30.1, ts_pct=0.610),
        ]
    )
    session.add_all(
        [
            TeamSeasonStat(team_id=1610612738, season="2025-26", is_playoff=False, gp=34, w=25, l=9, pts_pg=119.0, off_rating=121.1, def_rating=111.8, net_rating=9.3, pace=99.2),
            TeamSeasonStat(team_id=1610612744, season="2025-26", is_playoff=False, gp=34, w=18, l=16, pts_pg=114.2, off_rating=114.9, def_rating=115.1, net_rating=-0.2, pace=101.0),
            TeamSeasonStat(team_id=1610612760, season="2025-26", is_playoff=False, gp=34, w=28, l=6, pts_pg=121.4, off_rating=120.0, def_rating=106.7, net_rating=13.3, pace=100.5),
        ]
    )
    for index, points in enumerate([34, 28, 35, 31, 29], start=1):
        session.add(
            PlayerGameLog(
                player_id=1,
                game_id=f"00225000{index:02d}",
                season="2025-26",
                season_type="Regular Season",
                game_date=dt.date(2025, 11, index),
                matchup="OKC vs BOS",
                wl="W" if index % 2 else "L",
                min=34.0,
                pts=points,
                reb=5,
                ast=6,
                plus_minus=8,
            )
        )
        session.add(
            WarehouseGame(
                game_id=f"00225010{index:02d}",
                season="2025-26",
                game_date=dt.date(2025, 12, index),
                status="final",
                home_team_id=1610612760,
                away_team_id=1610612738,
                home_team_abbreviation="OKC",
                away_team_abbreviation="BOS",
                home_score=120 + index,
                away_score=110,
            )
        )
        session.add(
            GameTeamStat(
                game_id=f"00225010{index:02d}",
                season="2025-26",
                team_id=1610612760,
                team_abbreviation="OKC",
                is_home=True,
                won=True,
                pts=120 + index,
                reb=45,
                ast=28,
            )
        )
    session.commit()


def test_metric_registry_resolves_alias_metadata_and_sort_behavior():
    ppg = resolve_metric("top 10 players in ppg", entity_type="player")
    assert ppg is not None
    assert ppg.key == "pts_pg"
    assert ppg.format == "number"
    assert ppg.supports("player")

    defensive_rating = resolve_metric("lowest defensive rating by team", entity_type="team")
    assert defensive_rating is not None
    assert defensive_rating.key == "def_rating"
    assert defensive_rating.higher_is_better is False
    assert defensive_rating.supports("team")


def test_query_answers_player_ppg_leaderboard():
    session = make_session()
    try:
        seed_query_data(session)
        response = answer_query(session, QueryAskRequest(question="top 10 players in ppg this season"))

        assert response.status == "ready"
        assert response.intent.entity_type == "player"
        assert response.intent.metric_key == "pts_pg"
        assert response.rows[0].name == "Shai Gilgeous-Alexander"
        assert response.rows[0].formatted_value == "31.4"
    finally:
        session.close()


def test_query_answers_team_net_rating_and_lowest_defense():
    session = make_session()
    try:
        seed_query_data(session)
        net = answer_query(session, QueryAskRequest(question="best teams by net rating in 2025-26"))
        assert net.status == "ready"
        assert net.intent.entity_type == "team"
        assert net.rows[0].abbreviation == "OKC"
        assert net.rows[0].formatted_value == "13.3"

        defense = answer_query(session, QueryAskRequest(question="lowest defensive rating by a team this season"))
        assert defense.status == "ready"
        assert defense.intent.sort_direction == "asc"
        assert defense.rows[0].abbreviation == "OKC"
        assert defense.rows[0].formatted_value == "106.7"
    finally:
        session.close()


def test_query_answers_player_threshold_filters():
    session = make_session()
    try:
        seed_query_data(session)
        response = answer_query(session, QueryAskRequest(question="players with at least 25 ppg and 60 ts%"))

        assert response.status == "ready"
        assert [row.name for row in response.rows] == ["Shai Gilgeous-Alexander", "Jayson Tatum"]
        assert {filter_item.metric_key for filter_item in response.intent.filters} == {"pts_pg", "ts_pct"}
    finally:
        session.close()


def test_query_answers_recent_player_form():
    session = make_session()
    try:
        seed_query_data(session)
        response = answer_query(session, QueryAskRequest(question="How has Shai played recently?"))

        assert response.status == "ready"
        assert response.intent.intent_type == "player_recent"
        assert response.answer.primary_value == "31.4 PPG"
        assert len(response.rows) == 5
        assert response.rows[0].detail_url == "/games/0022500005"
    finally:
        session.close()


def test_query_answers_recent_team_form():
    session = make_session()
    try:
        seed_query_data(session)
        response = answer_query(session, QueryAskRequest(question="How has OKC played recently?"))

        assert response.status == "ready"
        assert response.intent.intent_type == "team_recent"
        assert response.answer.primary_value == "+13.0"
        assert len(response.rows) == 5
        assert response.rows[0].detail_url == "/games/0022501005"
    finally:
        session.close()


def test_query_returns_suggestions_for_unsupported_question():
    session = make_session()
    try:
        seed_query_data(session)
        response = answer_query(session, QueryAskRequest(question="what should I eat before the game?"))

        assert response.status == "needs_clarification"
        assert response.rows == []
        assert response.suggestions
        assert response.warnings
    finally:
        session.close()


def test_query_router_exposes_examples_metrics_and_ask_response():
    session = make_session()
    try:
        seed_query_data(session)
        assert any(example["prompt"].startswith("Who leads") for example in examples())
        assert any(metric["key"] == "net_rating" and "team" in metric["entity_types"] for metric in metrics())

        response = ask(QueryAskRequest(question="best teams by net rating in 2025-26"), db=session)
        assert response.status == "ready"
        assert response.rows[0].abbreviation == "OKC"
    finally:
        session.close()
