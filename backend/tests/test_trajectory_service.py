from datetime import date, timedelta
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GamePlayerStat, GameTeamStat, Player, Team  # noqa: E402
from services.trajectory_service import build_trajectory_report  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def seed_trajectory_pool(session):
    atl = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks")
    bos = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
    session.add_all([atl, bos])

    players = [
        (1, "Breakout Guard", "G"),
        (2, "Slumping Wing", "F"),
        (3, "Steady Creator", "G"),
        (4, "Quietly Rising Big", "C"),
        (5, "Minutes Dip Guard", "G"),
        (6, "Low Minute Bench", "G"),
    ]
    for player_id, name, position in players:
        session.add(Player(id=player_id, full_name=name, position=position, team=atl, team_id=atl.id))

    base_date = date(2025, 12, 20)
    for index in range(15):
        game_id = "0022500{0:03d}".format(index)
        game_date = base_date - timedelta(days=index)
        session.add(
            GameTeamStat(
                game_id=game_id,
                season="2025-26",
                team_id=atl.id,
                team_abbreviation="ATL",
                pts=112,
                fga=88,
                fta=23,
                oreb=10,
                tov=13,
            )
        )
        session.add(
            GameTeamStat(
                game_id=game_id,
                season="2025-26",
                team_id=bos.id,
                team_abbreviation="BOS",
                pts=106,
                fga=86,
                fta=21,
                oreb=9,
                tov=12,
            )
        )

        is_recent = index < 5
        player_lines = [
            (1, 33 if is_recent else 26, 27 if is_recent else 17, 6 if is_recent else 4, 6 if is_recent else 4, 0.54 if is_recent else 0.47, 18 if is_recent else 12, 4 if is_recent else 2, 6 if is_recent else 3, 9 if is_recent else 2),
            (2, 28 if is_recent else 33, 14 if is_recent else 24, 5 if is_recent else 7, 4 if is_recent else 6, 0.46 if is_recent else 0.60, 11 if is_recent else 19, 3 if is_recent else 4, 4 if is_recent else 7, -8 if is_recent else 5),
            (3, 30, 18, 5, 7, 0.55, 13, 3, 5, 1),
            (4, 31 if is_recent else 27, 20 if is_recent else 16, 11 if is_recent else 9, 3 if is_recent else 2, 0.63 if is_recent else 0.57, 14 if is_recent else 11, 4 if is_recent else 3, 3 if is_recent else 2, 6 if is_recent else 1),
            (5, 19 if is_recent else 28, 11 if is_recent else 16, 4 if is_recent else 5, 4 if is_recent else 5, 0.49 if is_recent else 0.55, 9 if is_recent else 12, 2 if is_recent else 2, 2 if is_recent else 3, -2 if is_recent else 2),
            (6, 14 if is_recent else 18, 8 if is_recent else 10, 3 if is_recent else 4, 2 if is_recent else 3, 0.50 if is_recent else 0.52, 7 if is_recent else 8, 2 if is_recent else 2, 1 if is_recent else 2, -1),
        ]
        for player_id, minutes, pts, reb, ast, fg_pct, fga, fta, tov, plus_minus in player_lines:
            session.add(
                GamePlayerStat(
                    game_id=game_id,
                    season="2025-26",
                    player_id=player_id,
                    team_id=atl.id,
                    team_abbreviation="ATL",
                    game_date=game_date,
                    matchup="ATL vs. BOS",
                    wl="W" if plus_minus >= 0 else "L",
                    min=minutes,
                    pts=pts,
                    reb=reb,
                    ast=ast,
                    stl=1,
                    blk=1 if player_id == 4 else 0,
                    tov=tov,
                    fgm=max(1, int(round(fga * fg_pct))),
                    fga=fga,
                    fg_pct=fg_pct,
                    fg3m=2,
                    fg3a=5,
                    ftm=max(1, int(round(fta * 0.75))),
                    fta=fta,
                    plus_minus=plus_minus,
                    is_starter=player_id != 6,
                )
            )

    for index in range(12):
        game_id = "0022599{0:03d}".format(index)
        session.add(
            GamePlayerStat(
                game_id=game_id,
                season="2025-26",
                player_id=99,
                team_id=atl.id,
                team_abbreviation="ATL",
                game_date=base_date - timedelta(days=20 + index),
                matchup="ATL vs. BOS",
                wl="W",
                min=25,
                pts=12,
                reb=5,
                ast=3,
                tov=2,
                fga=10,
                fgm=5,
                fg_pct=0.50,
                fta=4,
                ftm=3,
                plus_minus=0,
            )
        )
    session.add(Player(id=99, full_name="Short Sample Guard", position="G", team=atl, team_id=atl.id))
    session.commit()


def test_trajectory_report_ranks_breakouts_and_declines():
    session = make_session()
    try:
        seed_trajectory_pool(session)
        report = build_trajectory_report(
            session,
            season="2025-26",
            last_n_games=5,
            player_pool="all",
            min_minutes_per_game=20.0,
        )

        assert report.window == "Last 5 games"
        assert report.breakout_leaders[0].player_name == "Breakout Guard"
        assert report.breakout_leaders[0].trajectory_label in {"Breaking Out", "Quietly Rising"}
        assert "Role change" in report.breakout_leaders[0].context_flags
        assert report.decline_watch[0].player_name == "Slumping Wing"
        assert any("Short Sample Guard — insufficient sample" == entry for entry in report.excluded_players)
        assert any("Low Minute Bench — below minutes threshold" == entry for entry in report.excluded_players)
    finally:
        session.close()


def test_trajectory_report_enforces_supported_season():
    session = make_session()
    try:
        with pytest.raises(HTTPException) as exc_info:
            build_trajectory_report(
                session,
                season="2024-25",
                last_n_games=5,
                player_pool="all",
                min_minutes_per_game=15.0,
            )
        assert exc_info.value.status_code == 422
    finally:
        session.close()
