from datetime import date, timedelta
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import Player, PlayerGameLog, SeasonStat, Team  # noqa: E402
from routers.leaderboards import leaderboard_trends  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _seed_player(session, player_id: int, full_name: str, team_abbr: str) -> Player:
    team = session.query(Team).filter(Team.abbreviation == team_abbr).one_or_none()
    if team is None:
        team = Team(id=1610612747, abbreviation=team_abbr, name="Los Angeles Lakers")
        session.add(team)
        session.flush()
    player = Player(
        id=player_id,
        full_name=full_name,
        first_name=full_name.split()[0],
        last_name=full_name.split()[-1],
        team_id=team.id,
        is_active=True,
    )
    session.add(player)
    session.flush()
    return player


def _seed_game_logs(session, player_id: int, season: str, pts_sequence):
    base_date = date(2024, 10, 22)
    for idx, pts in enumerate(pts_sequence):
        session.add(
            PlayerGameLog(
                player_id=player_id,
                game_id=f"00{player_id}{idx:03d}",
                season=season,
                season_type="Regular Season",
                game_date=base_date + timedelta(days=idx * 2),
                pts=pts,
                reb=5,
                ast=3,
                fgm=int(pts // 2),
                fga=int(pts // 2) + 5,
                fg3m=2,
                fg3a=5,
                ftm=2,
                fta=3,
                min=32.0,
            )
        )


def test_trends_returns_rolling_values_for_pts_pg():
    session = make_session()
    try:
        player = _seed_player(session, player_id=101, full_name="Alpha Scorer", team_abbr="LAL")
        pts_sequence = [20, 22, 18, 24, 28, 30, 25, 26, 21, 23, 27, 32]
        _seed_game_logs(session, player.id, season="2024-25", pts_sequence=pts_sequence)
        session.add(
            SeasonStat(
                player_id=player.id,
                season="2024-25",
                team_abbreviation="LAL",
                is_playoff=False,
                gp=12,
                pts_pg=24.7,
                pts=296,
            )
        )
        session.commit()

        response = leaderboard_trends(
            stat="pts_pg",
            player_ids=str(player.id),
            season="2024-25",
            window=10,
            db=session,
        )

        assert response.season == "2024-25"
        assert response.stat == "pts_pg"
        assert response.window == 10
        assert len(response.entries) == 1
        entry = response.entries[0]
        assert entry.player_id == player.id
        assert entry.team_abbreviation == "LAL"
        assert entry.sample_size == 10
        assert len(entry.rolling_values) == 10
        assert all(v is not None for v in entry.rolling_values)
        # Last value of the window equals the 12th game's pts (32).
        assert entry.latest_value == 32.0
        # Baseline = season pts_pg (24.7); latest_value = 32 → delta ≈ +7.3
        assert entry.delta_vs_baseline is not None
        assert round(entry.delta_vs_baseline, 1) == 7.3
    finally:
        session.close()


def test_trends_handles_player_with_few_games():
    session = make_session()
    try:
        player = _seed_player(session, player_id=202, full_name="Sparse Sub", team_abbr="LAL")
        _seed_game_logs(session, player.id, season="2024-25", pts_sequence=[14, 16])
        session.add(
            SeasonStat(
                player_id=player.id,
                season="2024-25",
                team_abbreviation="LAL",
                is_playoff=False,
                gp=2,
                pts_pg=15.0,
                pts=30,
            )
        )
        session.commit()

        response = leaderboard_trends(
            stat="pts_pg",
            player_ids=str(player.id),
            season="2024-25",
            window=10,
            db=session,
        )

        assert len(response.entries) == 1
        entry = response.entries[0]
        assert entry.sample_size == 0
        assert entry.rolling_values == []
        assert entry.latest_value is None
        assert entry.delta_vs_baseline is None
    finally:
        session.close()


def test_trends_endpoint_400_when_too_many_player_ids():
    session = make_session()
    try:
        too_many = ",".join(str(i) for i in range(1, 22))  # 21 IDs

        with pytest.raises(HTTPException) as exc_info:
            leaderboard_trends(
                stat="pts_pg",
                player_ids=too_many,
                season="2024-25",
                window=10,
                db=session,
            )

        assert exc_info.value.status_code == 400
        assert "at most 20" in exc_info.value.detail
    finally:
        session.close()
