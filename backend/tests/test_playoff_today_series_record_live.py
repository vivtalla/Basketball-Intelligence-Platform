"""Sprint 90 hotfix — `/api/playoffs/today` must compute the series win
record fresh on every request rather than reading the persisted
`PlayoffSeries.top_wins`/`bottom_wins`, which only updates on the nightly
sync.

Without this, the live scoreboard overlay would show tonight's just-final
score correctly while the series record still rendered yesterday's state
(e.g. score reads "DET 110 - ORL 105 final" but record says "Series tied
3-3" instead of "DET leads 4-3").
"""
from pathlib import Path
from datetime import date
import sys
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GameLog, PlayoffSeries, Team  # noqa: E402
from routers.playoffs import get_today  # noqa: E402


SEASON = "2024-25"


def _make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _seed_det_orl_series_through_g6(session, target_date):
    """Seed a DET-ORL series with games 1-6 completed, 3-3 split. Game 7 is
    today; DB row exists but home/away_score is still None (the live overlay
    will supply them)."""
    det = Team(id=1610612765, abbreviation="DET", name="Detroit Pistons", city="Detroit")
    orl = Team(id=1610612753, abbreviation="ORL", name="Orlando Magic", city="Orlando")
    session.add_all([det, orl])
    session.commit()

    series_id = "{0}-E-R1-DET-ORL".format(SEASON)
    session.add(
        PlayoffSeries(
            season=SEASON,
            round=1,
            series_id=series_id,
            top_seed_team_id=det.id,
            bottom_seed_team_id=orl.id,
            top_seed=4,
            bottom_seed=5,
            top_wins=3,
            bottom_wins=3,
            status="active",
        )
    )
    # Six completed games, alternating winners so the series is tied 3-3.
    # Odd-numbered games go to DET, even to ORL → 3 wins each.
    for game_num in range(1, 7):
        det_home = game_num % 2 == 1
        det_won = game_num % 2 == 1
        home_id = det.id if det_home else orl.id
        away_id = orl.id if det_home else det.id
        if det_won:
            home_score, away_score = (115, 108) if det_home else (108, 115)
        else:
            home_score, away_score = (108, 115) if det_home else (115, 108)
        session.add(
            GameLog(
                game_id="00425{0:05d}".format(game_num),
                season=SEASON,
                game_date=date(2026, 5, game_num),  # arbitrary past dates
                home_team_id=home_id,
                away_team_id=away_id,
                home_score=home_score,
                away_score=away_score,
                season_type="Playoffs",
                series_id=series_id,
                series_game_num=game_num,
            )
        )
    # Game 7 today, no score persisted yet.
    session.add(
        GameLog(
            game_id="0042500007",
            season=SEASON,
            game_date=target_date,
            home_team_id=det.id,
            away_team_id=orl.id,
            home_score=None,
            away_score=None,
            season_type="Playoffs",
            series_id=series_id,
            series_game_num=7,
        )
    )
    session.commit()
    return series_id, det, orl


def test_today_series_record_pre_game_reads_from_completed_gamelogs():
    """Before tipoff, the slate should show 3-3 from the 6 completed
    GameLog rows even if PlayoffSeries.top_wins is stale."""
    session = _make_session()
    try:
        target = date(2026, 5, 13)
        _seed_det_orl_series_through_g6(session, target)

        with patch("routers.playoffs._scoreboard_games_for_today", return_value={}):
            response = get_today(date_param=target.isoformat(), db=session)

        assert len(response.games) == 1
        game = response.games[0]
        assert game.top_wins == 3
        assert game.bottom_wins == 3
        # Game 7 hasn't been played yet — no score on the row.
        assert game.home_pts is None
        assert game.away_pts is None
    finally:
        session.close()


def test_today_series_record_updates_when_scoreboard_finalizes_game():
    """When tonight's game goes final on the scoreboard before the DB row
    is updated, the series record must reflect the new win count — not
    the stale persisted PlayoffSeries.top_wins.
    Reproduces the user-reported DET-ORL Game 7 scenario.
    """
    session = _make_session()
    try:
        target = date(2026, 5, 13)
        _seed_det_orl_series_through_g6(session, target)

        scoreboard = {
            "0042500007": {
                "gameStatus": 3,  # final
                "gameTimeUTC": "2026-05-14T01:30:00Z",
                "homeTeam": {"score": 110},
                "awayTeam": {"score": 105},
                "broadcasters": {"nationalTvBroadcasters": []},
            }
        }
        # Force the endpoint's is_today gate open so the overlay branch runs
        # against our fixture date rather than wall-clock today.
        with patch("routers.playoffs._scoreboard_games_for_today", return_value=scoreboard), \
             patch("routers.playoffs._today_pacific", return_value=target):
            response = get_today(date_param=target.isoformat(), db=session)

        game = response.games[0]
        # Live overlay carried the final score
        assert game.home_pts == 110
        assert game.away_pts == 105
        # Series record bumped to 4-3 DET (top seed) — the actual bug fix
        assert game.top_wins == 4
        assert game.bottom_wins == 3
    finally:
        session.close()


def test_today_series_record_does_not_count_in_progress_game():
    """A game that's live (gameStatus=2) but not yet final must NOT
    increment the series record — the win isn't booked until the final."""
    session = _make_session()
    try:
        target = date(2026, 5, 13)
        _seed_det_orl_series_through_g6(session, target)

        scoreboard = {
            "0042500007": {
                "gameStatus": 2,  # in progress, not final
                "gameTimeUTC": "2026-05-14T01:30:00Z",
                "homeTeam": {"score": 87},
                "awayTeam": {"score": 81},
                "broadcasters": {"nationalTvBroadcasters": []},
            }
        }
        # Force the endpoint's is_today gate open so the overlay branch runs
        # against our fixture date rather than wall-clock today.
        with patch("routers.playoffs._scoreboard_games_for_today", return_value=scoreboard), \
             patch("routers.playoffs._today_pacific", return_value=target):
            response = get_today(date_param=target.isoformat(), db=session)

        game = response.games[0]
        # In-progress score is shown
        assert game.home_pts == 87
        assert game.away_pts == 81
        # But series record stays at 3-3 — DET hasn't won the game yet
        assert game.top_wins == 3
        assert game.bottom_wins == 3
    finally:
        session.close()


def test_today_series_record_ignores_stale_playoffseries_topwins():
    """Even if PlayoffSeries.top_wins claims 7-3 (corrupted/stale), the
    fresh GameLog count of 3-3 should win. Locks down the regression
    direction: GameLog is now authoritative, not the denormalized table."""
    session = _make_session()
    try:
        target = date(2026, 5, 13)
        series_id, _, _ = _seed_det_orl_series_through_g6(session, target)
        # Simulate stale denormalized state
        s = session.query(PlayoffSeries).filter_by(series_id=series_id).first()
        s.top_wins = 7
        s.bottom_wins = 0
        session.commit()

        with patch("routers.playoffs._scoreboard_games_for_today", return_value={}):
            response = get_today(date_param=target.isoformat(), db=session)

        game = response.games[0]
        assert game.top_wins == 3, "GameLog must be authoritative, not denormalized PlayoffSeries"
        assert game.bottom_wins == 3
    finally:
        session.close()
