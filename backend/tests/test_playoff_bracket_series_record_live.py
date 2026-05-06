"""Sprint 91 — `/api/playoffs/bracket` and `/api/playoffs/series/{id}` must
compute the series win record fresh on every read instead of returning the
stale `PlayoffSeries.top_wins` / `bottom_wins` denormalized cache (only
updated by the 6am daily sync).

Companion to `test_playoff_today_series_record_live.py`, which locks down
the same behavior on `/today`. Without this, the LiveTicker showed a fresh
record while the bracket page sat on yesterday's count for up to a day
after a game finished.

Also covers the write-through behavior on `/today`: when the live
scoreboard reports a final for a `GameLog` row whose scores are still
NULL, `/today` now persists the scores to the row so subsequent
`/bracket` and `/series/{id}` reads see the fresh `winner_team_id`.
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
from routers.playoffs import get_bracket, get_series, get_today  # noqa: E402


SEASON = "2024-25"


def _make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _seed_det_orl_series_3_2(session, persisted_top_wins=2, persisted_bottom_wins=3):
    """Seed a DET-ORL series with 5 completed games (DET 2 - ORL 3) but
    persisted PlayoffSeries.top_wins/bottom_wins set to whatever the caller
    passes in — defaults to the same 2-3 so callers can override to mimic
    a stale denormalized cache."""
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
            top_wins=persisted_top_wins,
            bottom_wins=persisted_bottom_wins,
            status="active",
        )
    )
    # 5 completed games: DET wins 2, ORL wins 3.
    outcomes = [
        ("ORL", det.id, orl.id, 101, 112),  # G1 ORL wins
        ("DET", det.id, orl.id,  98,  83),  # G2 DET wins
        ("ORL", orl.id, det.id, 113, 105),  # G3 ORL wins
        ("ORL", orl.id, det.id,  94,  88),  # G4 ORL wins
        ("DET", det.id, orl.id, 116, 109),  # G5 DET wins
    ]
    for i, (_, home_id, away_id, home_pts, away_pts) in enumerate(outcomes, start=1):
        session.add(
            GameLog(
                game_id="00425001{0:02d}".format(i),
                season=SEASON,
                game_date=date(2026, 4, 18 + i),
                home_team_id=home_id,
                away_team_id=away_id,
                home_score=home_pts,
                away_score=away_pts,
                season_type="Playoffs",
                series_id=series_id,
                series_game_num=i,
            )
        )
    session.commit()
    return series_id, det, orl


def test_bracket_uses_fresh_count_not_stale_topwins():
    """Even if PlayoffSeries.top_wins is stale (4-1) the bracket should
    return the fresh GameLog count of 2-3."""
    session = _make_session()
    try:
        series_id, _, _ = _seed_det_orl_series_3_2(
            session, persisted_top_wins=4, persisted_bottom_wins=1
        )

        response = get_bracket(season=SEASON, db=session)

        # The DET-ORL series is round 1 East — find it across the bracket.
        all_series = response.east + response.west + ([response.finals] if response.finals else [])
        match = next((s for s in all_series if s.series_id == series_id), None)
        assert match is not None, "DET-ORL series should appear in the bracket"
        assert match.top_wins == 2, (
            "GameLog must be authoritative — fresh count is 2 DET wins, "
            "not the stale persisted 4"
        )
        assert match.bottom_wins == 3, "ORL has 3 fresh wins regardless of stale cache"
    finally:
        session.close()


def test_series_endpoint_uses_fresh_count_not_stale_topwins():
    """Same fresh-count behavior on /series/{id} (the series detail page)."""
    session = _make_session()
    try:
        series_id, _, _ = _seed_det_orl_series_3_2(
            session, persisted_top_wins=4, persisted_bottom_wins=1
        )

        response = get_series(series_id=series_id, db=session)

        assert response.top_wins == 2, "fresh GameLog count, not stale 4"
        assert response.bottom_wins == 3


    finally:
        session.close()


def test_today_writes_scoreboard_final_through_to_gamelog():
    """When the live scoreboard reports a final for a GameLog row whose
    scores are still NULL, /today must persist the scores so that
    subsequent /bracket reads see the fresh winner_team_id.

    This is the write-through that closes the loop: LiveTicker polls
    /today every 60s → /today persists the final → bracket page (which
    /today doesn't share state with) picks up the fresh GameLog on its
    own next read.
    """
    session = _make_session()
    try:
        target = date(2026, 5, 13)
        series_id, det, orl = _seed_det_orl_series_3_2(session)

        # Add a 6th game today, NULL scores in DB. Scoreboard says it's
        # final, DET 116 - ORL 94.
        g6_id = "0042500106"
        session.add(
            GameLog(
                game_id=g6_id,
                season=SEASON,
                game_date=target,
                home_team_id=det.id,
                away_team_id=orl.id,
                home_score=None,
                away_score=None,
                season_type="Playoffs",
                series_id=series_id,
                series_game_num=6,
            )
        )
        session.commit()

        scoreboard = {
            g6_id: {
                "gameStatus": 3,
                "gameTimeUTC": "2026-05-14T01:00:00Z",
                "homeTeam": {"score": 116},
                "awayTeam": {"score": 94},
                "broadcasters": {"nationalTvBroadcasters": []},
            }
        }
        with patch("routers.playoffs._scoreboard_games_for_today", return_value=scoreboard), \
             patch("routers.playoffs._today_pacific", return_value=target):
            get_today(date_param=target.isoformat(), db=session)

        # Reload G6 from DB to confirm the write-through landed.
        session.expire_all()
        g6 = session.query(GameLog).filter_by(game_id=g6_id).first()
        assert g6.home_score == 116, "scoreboard final must be persisted"
        assert g6.away_score == 94, "scoreboard final must be persisted"

        # And /bracket now reflects the fresh count (DET 3 - ORL 3).
        bracket_response = get_bracket(season=SEASON, db=session)
        all_series = (
            bracket_response.east
            + bracket_response.west
            + ([bracket_response.finals] if bracket_response.finals else [])
        )
        match = next(s for s in all_series if s.series_id == series_id)
        assert match.top_wins == 3, "DET 2 + tonight's win = 3"
        assert match.bottom_wins == 3, "ORL still at 3"
    finally:
        session.close()


def test_today_does_not_overwrite_existing_gamelog_scores():
    """If GameLog already has scores (from the daily sync or an earlier
    /today write-through), /today must not overwrite them with the live
    scoreboard. Guards against the case where the scoreboard briefly
    serves a stale state during a delayed re-sync."""
    session = _make_session()
    try:
        target = date(2026, 5, 13)
        series_id, det, orl = _seed_det_orl_series_3_2(session)

        # Add a G6 today with scores already set (DET 105 - ORL 99).
        g6_id = "0042500106"
        session.add(
            GameLog(
                game_id=g6_id,
                season=SEASON,
                game_date=target,
                home_team_id=det.id,
                away_team_id=orl.id,
                home_score=105,
                away_score=99,
                season_type="Playoffs",
                series_id=series_id,
                series_game_num=6,
            )
        )
        session.commit()

        # Scoreboard claims totally different (and final) scores.
        scoreboard = {
            g6_id: {
                "gameStatus": 3,
                "gameTimeUTC": "2026-05-14T01:00:00Z",
                "homeTeam": {"score": 999},
                "awayTeam": {"score": 0},
                "broadcasters": {"nationalTvBroadcasters": []},
            }
        }
        with patch("routers.playoffs._scoreboard_games_for_today", return_value=scoreboard), \
             patch("routers.playoffs._today_pacific", return_value=target):
            get_today(date_param=target.isoformat(), db=session)

        session.expire_all()
        g6 = session.query(GameLog).filter_by(game_id=g6_id).first()
        # Original scores preserved — no overwrite.
        assert g6.home_score == 105
        assert g6.away_score == 99
    finally:
        session.close()
