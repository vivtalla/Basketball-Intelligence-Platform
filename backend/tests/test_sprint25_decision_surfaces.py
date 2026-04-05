from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GameTeamStat, Team, WarehouseGame  # noqa: E402
from services.compare_service import build_team_comparison_report  # noqa: E402
from services.pre_read_service import build_pre_read_deck  # noqa: E402
from services.team_focus_service import build_team_focus_levers_report  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def seed_team_pair(session):
    team_a = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks")
    team_b = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
    session.add_all([team_a, team_b])

    base_date = date(2025, 12, 20)
    for index in range(6):
        game_id = f"0022500{index:03d}"
        game_date = base_date - timedelta(days=index)
        session.add(
            WarehouseGame(
                game_id=game_id,
                season="2025-26",
                game_date=game_date,
                home_team_id=team_a.id,
                away_team_id=team_b.id,
                home_score=112 + index,
                away_score=104 + index,
            )
        )
        session.add(
            GameTeamStat(
                game_id=game_id,
                season="2025-26",
                team_id=team_a.id,
                team_abbreviation=team_a.abbreviation,
                pts=112 + index,
                fgm=42 + index,
                fga=86,
                fg3m=13,
                fg3a=36,
                ftm=18,
                fta=22,
                oreb=11,
                dreb=31,
                reb=42,
                ast=27,
                tov=11 - (index // 2),
                pf=18,
                minutes=240.0,
                plus_minus=8 + index,
                won=True,
                is_home=True,
            )
        )
        session.add(
            GameTeamStat(
                game_id=game_id,
                season="2025-26",
                team_id=team_b.id,
                team_abbreviation=team_b.abbreviation,
                pts=104 + index,
                fgm=39,
                fga=88,
                fg3m=11,
                fg3a=34,
                ftm=14,
                fta=18,
                oreb=9,
                dreb=28,
                reb=37,
                ast=22,
                tov=14 + (index // 2),
                pf=20,
                minutes=240.0,
                plus_minus=-8 - index,
                won=False,
                is_home=False,
            )
        )

    session.commit()
    return team_a, team_b


def test_team_comparison_report_surfaces_coach_readable_edges():
    session = make_session()
    try:
        team_a, team_b = seed_team_pair(session)
        report = build_team_comparison_report(
            session,
            team_a.abbreviation,
            team_b.abbreviation,
            "2025-26",
            source_context={"source_type": "scouting-report", "reason": "play-type scouting"},
        )

        assert report.team_a.abbreviation == "ATL"
        assert report.team_b.abbreviation == "BOS"
        assert report.rows[0].stat_id == "efg_pct"
        assert any(story.label == "Wins turnover battle" for story in report.stories)
        assert any(story.label == "More efficient shooting team" for story in report.stories)
        assert any(story.label == "Stronger glass profile" for story in report.stories)
        assert any(story.label == "Faster tempo team" for story in report.stories)
        assert report.stories[0].edge in {"team_a", "team_b", "even"}
        assert report.source_context == {"source_type": "scouting-report", "reason": "play-type scouting"}
    finally:
        session.close()


def test_team_focus_levers_report_prioritizes_four_factor_pressure_points():
    session = make_session()
    try:
        team_a, _team_b = seed_team_pair(session)
        report = build_team_focus_levers_report(session, team_a.abbreviation, "2025-26")

        assert report.team_abbreviation == "ATL"
        assert len(report.factor_rows) == 4
        assert len(report.focus_levers) == 3
        assert {row.factor_id for row in report.factor_rows} == {"shooting", "turnovers", "rebounding", "free_throws"}
        assert report.focus_levers[0].factor_id in {"shooting", "turnovers", "rebounding", "free_throws"}
        assert report.focus_levers[0].impact_label in {
            "protect current edge",
            "lift scoring efficiency",
            "recover possessions",
            "win second balls",
            "manufacture easier points",
            "monitor",
        }
    finally:
        session.close()


def test_pre_read_deck_composes_focus_levers_and_matchup_edges():
    session = make_session()
    try:
        team_a, team_b = seed_team_pair(session)
        deck = build_pre_read_deck(session, team_a.abbreviation, team_b.abbreviation, "2025-26")

        assert deck.team_abbreviation == "ATL"
        assert deck.opponent_abbreviation == "BOS"
        assert len(deck.slides) == 4
        assert deck.slides[0].eyebrow == "Tonight"
        assert deck.focus_levers
        assert deck.matchup_advantages
        assert any("focus levers" in bullet.lower() for bullet in deck.slides[0].bullets)
    finally:
        session.close()
