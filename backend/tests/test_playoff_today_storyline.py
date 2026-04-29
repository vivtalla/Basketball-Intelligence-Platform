"""Sprint 77 — Playoff today endpoint surfaces a headline storyline for each
game when the two teams have a clear stat differential.
"""
from pathlib import Path
import sys
from datetime import date
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GameLog, PlayoffSeries, Team, TeamSeasonStat  # noqa: E402
from routers.playoffs import get_today  # noqa: E402


def _make_session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _seed_storyline_fixture(session, season: str = "2024-25", target_date=date(2026, 4, 28)):
    bos = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics", city="Boston")
    mia = Team(id=1610612748, abbreviation="MIA", name="Miami Heat", city="Miami")
    # Filler teams give the league sample enough variance for a meaningful z-score.
    nyk = Team(id=1610612752, abbreviation="NYK", name="New York Knicks", city="New York")
    phi = Team(id=1610612755, abbreviation="PHI", name="Philadelphia 76ers", city="Philadelphia")
    mil = Team(id=1610612749, abbreviation="MIL", name="Milwaukee Bucks", city="Milwaukee")
    cle = Team(id=1610612739, abbreviation="CLE", name="Cleveland Cavaliers", city="Cleveland")
    session.add_all([bos, mia, nyk, phi, mil, cle])
    session.commit()

    # BOS scores ~120; MIA scores ~105; the rest cluster around the middle so
    # the BOS↔MIA gap is the largest pts_pg differential in the league sample.
    league_pts = [
        (bos.id, 120.0),
        (mia.id, 105.0),
        (nyk.id, 113.0),
        (phi.id, 112.0),
        (mil.id, 114.0),
        (cle.id, 111.0),
    ]
    for team_id, pts in league_pts:
        session.add(
            TeamSeasonStat(
                team_id=team_id,
                season=season,
                is_playoff=False,
                gp=82,
                pts_pg=pts,
                off_rating=110.0 + (pts - 113.0) * 0.3,
                def_rating=110.0,
                pace=99.0,
                ts_pct=0.575,
            )
        )
    session.commit()

    series_id = "{0}-E-R1-BOS-MIA".format(season)
    session.add(
        PlayoffSeries(
            season=season,
            round=1,
            series_id=series_id,
            top_seed_team_id=bos.id,
            bottom_seed_team_id=mia.id,
            top_seed=1,
            bottom_seed=8,
            top_wins=1,
            bottom_wins=0,
            status="active",
        )
    )
    session.add(
        GameLog(
            game_id="0042500001",
            season=season,
            game_date=target_date,
            home_team_id=bos.id,
            away_team_id=mia.id,
            home_score=None,
            away_score=None,
            season_type="Playoffs",
            series_id=series_id,
            series_game_num=2,
        )
    )
    session.commit()
    return target_date


def test_storyline_non_empty_when_clear_stat_edge():
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        target_date = _seed_storyline_fixture(session)
        # Stub the live CDN scoreboard so the test stays hermetic — without
        # this, when the fixture date matches the system date, the endpoint
        # would merge in real games from the live scoreboard.
        with patch("routers.playoffs._scoreboard_games_for_today", return_value={}):
            response = get_today(date_param=target_date.isoformat(), db=session)
    finally:
        session.close()

    assert response.date == target_date
    assert len(response.games) == 1
    storyline = response.games[0].headline_storyline
    assert storyline, "expected a non-empty storyline for a clear stat-edge fixture"
    lowered = storyline.lower()
    # Storyline phrases the pts_pg edge in any of several offense-related
    # ways ("scoring", "score", "offensive", "offense", "firepower"). All
    # read as a scoring-volume narrative; accept any of them.
    assert any(needle in lowered for needle in ("scoring", "score", "offensive", "offense", "firepower")), (
        "expected a scoring/offense storyline for the BOS-vs-MIA pts_pg gap; got: {0!r}".format(storyline)
    )
