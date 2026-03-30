from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GamePlayerStat, Player, PlayerGameLog, SeasonStat, Team  # noqa: E402
from services.player_trend_service import build_player_trend_report  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def seed_player(session, season: str) -> Player:
    team = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks")
    player = Player(id=101, full_name="Test Player", team=team, team_id=team.id)
    session.add(team)
    session.add(player)
    session.add(
        SeasonStat(
            player_id=player.id,
            season=season,
            team_abbreviation=team.abbreviation,
            is_playoff=False,
            gp=10,
            min_pg=28.0,
            pts_pg=17.2,
            reb_pg=5.1,
            ast_pg=4.3,
            bpm=2.8,
            per=16.4,
            ts_pct=0.587,
        )
    )
    session.commit()
    return player


def test_player_trend_report_handles_missing_on_off_row():
    session = make_session()
    try:
        season = "2024-25"
        player = seed_player(session, season)
        base_date = date(2025, 3, 1)

        for index in range(10):
            game_id = "0022400{0:03d}".format(index)
            session.add(
                PlayerGameLog(
                    player_id=player.id,
                    season=season,
                    season_type="Regular Season",
                    game_id=game_id,
                    game_date=base_date - timedelta(days=index),
                    matchup="ATL vs. BOS",
                    wl="W" if index % 2 == 0 else "L",
                    min=24.0 + index,
                    pts=12 + index,
                    reb=4 + (index % 3),
                    ast=3 + (index % 4),
                    fg_pct=0.45 + (index * 0.005),
                    fg3_pct=0.34 + (index * 0.004),
                    plus_minus=(-4 + index),
                )
            )
            session.add(
                GamePlayerStat(
                    game_id=game_id,
                    season=season,
                    player_id=player.id,
                    team_id=player.team_id,
                    team_abbreviation="ATL",
                    game_date=base_date - timedelta(days=index),
                    matchup="ATL vs. BOS",
                    wl="W" if index % 2 == 0 else "L",
                    min=24.0 + index,
                    pts=12 + index,
                    reb=4 + (index % 3),
                    ast=3 + (index % 4),
                    fg_pct=0.45 + (index * 0.005),
                    fg3_pct=0.34 + (index * 0.004),
                    plus_minus=float(-4 + index),
                    is_starter=index < 7,
                )
            )

        session.commit()

        report = build_player_trend_report(session, player, season)

        assert report.status == "ready"
        assert report.window_games == 10
        assert report.impact_snapshot.pbp_coverage_status == "none"
        assert report.impact_snapshot.on_off_net is None
        assert report.impact_snapshot.on_minutes is None
        assert report.trust_signals.starts_last_10 == 7
        assert len(report.recommended_games) == 5
    finally:
        session.close()


def test_player_trend_report_returns_sparse_limited_shape():
    session = make_session()
    try:
        season = "2025-26"
        player = seed_player(session, season)
        base_date = date(2025, 11, 1)

        for index in range(4):
            session.add(
                PlayerGameLog(
                    player_id=player.id,
                    season=season,
                    season_type="Regular Season",
                    game_id="0022500{0:03d}".format(index),
                    game_date=base_date - timedelta(days=index),
                    matchup="ATL @ NYK",
                    wl="W",
                    min=18.0 + index,
                    pts=10 + index,
                    reb=3,
                    ast=2,
                    fg_pct=0.44,
                    fg3_pct=0.31,
                    plus_minus=2 + index,
                )
            )

        session.commit()

        report = build_player_trend_report(session, player, season)

        assert report.status == "limited"
        assert report.window_games == 4
        assert report.recent_form.games == 0
        assert report.season_baseline.games == 0
        assert report.trust_signals.minutes_delta is None
        assert report.recommended_games == []
    finally:
        session.close()
