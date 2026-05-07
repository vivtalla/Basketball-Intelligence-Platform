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


# ---------------------------------------------------------------------------
# Sprint 91 Phase A — bracket auto-advancement + series-id team-pair attach
# ---------------------------------------------------------------------------


def test_today_advances_child_series_when_parent_clinches():
    """When a /today scoreboard final brings a parent series to 4 wins,
    the child series's empty seed slot must auto-populate with the winner
    so the next bracket read shows R2 wired up correctly. Reproduces the
    user-reported "#null v Detroit" scenario where R1-CLE-TOR closed but
    R2-BOT's top_seed_team_id never advanced.
    """
    session = _make_session()
    try:
        target = date(2026, 5, 13)
        # Seed CLE-TOR R1 with CLE up 3-0 going into G4 today.
        cle = Team(id=1610612739, abbreviation="CLE", name="Cleveland Cavaliers", city="Cleveland")
        tor = Team(id=1610612761, abbreviation="TOR", name="Toronto Raptors", city="Toronto")
        det = Team(id=1610612765, abbreviation="DET", name="Detroit Pistons", city="Detroit")
        session.add_all([cle, tor, det])
        session.commit()

        r1_id = "{0}-X-R1-CLE-TOR".format(SEASON)
        session.add(
            PlayoffSeries(
                season=SEASON, round=1, series_id=r1_id,
                top_seed_team_id=cle.id, bottom_seed_team_id=tor.id,
                top_seed=8, bottom_seed=13,
                top_wins=3, bottom_wins=0, status="active",
            )
        )
        # 3 prior CLE wins.
        for i in range(1, 4):
            session.add(
                GameLog(
                    game_id="00425001{0:02d}".format(i),
                    season=SEASON,
                    game_date=date(2026, 5, 1 + i),
                    home_team_id=cle.id, away_team_id=tor.id,
                    home_score=110, away_score=99,
                    season_type="Playoffs", series_id=r1_id, series_game_num=i,
                )
            )
        # G4 today, NULL scores in DB. Scoreboard says CLE 105 - TOR 92, final.
        g4_id = "0042500104"
        session.add(
            GameLog(
                game_id=g4_id, season=SEASON, game_date=target,
                home_team_id=tor.id, away_team_id=cle.id,
                home_score=None, away_score=None,
                season_type="Playoffs", series_id=r1_id, series_game_num=4,
            )
        )
        # Pre-existing R2-BOT row in the broken state (parent_top_series_id
        # populated but top seed slot still null).
        r2_id = "{0}-X-R2-BOT".format(SEASON)
        session.add(
            PlayoffSeries(
                season=SEASON, round=2, series_id=r2_id,
                top_seed_team_id=None, bottom_seed_team_id=det.id,
                top_seed=None, bottom_seed=3,
                top_wins=0, bottom_wins=0, status="scheduled",
                parent_top_series_id=r1_id, parent_bottom_series_id=None,
            )
        )
        session.commit()

        scoreboard = {
            g4_id: {
                "gameStatus": 3,
                "gameTimeUTC": "2026-05-14T01:00:00Z",
                "homeTeam": {"score": 92},
                "awayTeam": {"score": 105},
                "broadcasters": {"nationalTvBroadcasters": []},
            }
        }
        with patch("routers.playoffs._scoreboard_games_for_today", return_value=scoreboard), \
             patch("routers.playoffs._today_pacific", return_value=target):
            get_today(date_param=target.isoformat(), db=session)

        session.expire_all()
        # Parent series clinched and closed.
        r1 = session.query(PlayoffSeries).filter_by(series_id=r1_id).first()
        assert r1.status == "closed", "R1 should flip to closed on 4th win"
        assert r1.winner_team_id == cle.id, "CLE wins R1"

        # Child series's top seed advanced to CLE.
        r2 = session.query(PlayoffSeries).filter_by(series_id=r2_id).first()
        assert r2.top_seed_team_id == cle.id, "R2 top slot must auto-populate with CLE"
        assert r2.top_seed == 8, "winner's seed propagates to child"
        # Child becomes active now that both seeds are filled.
        assert r2.status == "active", "R2 flips active once both seeds are populated"
    finally:
        session.close()


def test_today_advancement_is_idempotent():
    """A second /today call after advancement must not re-flip status or
    overwrite already-populated child seeds. Locks down the case where
    LiveTicker polls /today every 60s — we'd otherwise repeatedly mutate
    the same rows without need."""
    session = _make_session()
    try:
        target = date(2026, 5, 13)
        # Seed an already-clinched R1 (CLE 4 wins, status already closed)
        # and an already-advanced R2 (CLE wired in as top seed).
        cle = Team(id=1610612739, abbreviation="CLE", name="Cleveland Cavaliers", city="Cleveland")
        tor = Team(id=1610612761, abbreviation="TOR", name="Toronto Raptors", city="Toronto")
        det = Team(id=1610612765, abbreviation="DET", name="Detroit Pistons", city="Detroit")
        session.add_all([cle, tor, det])
        session.commit()

        r1_id = "{0}-X-R1-CLE-TOR".format(SEASON)
        session.add(
            PlayoffSeries(
                season=SEASON, round=1, series_id=r1_id,
                top_seed_team_id=cle.id, bottom_seed_team_id=tor.id,
                top_seed=8, bottom_seed=13,
                top_wins=4, bottom_wins=0, status="closed",
                winner_team_id=cle.id,
            )
        )
        for i in range(1, 5):
            session.add(
                GameLog(
                    game_id="00425001{0:02d}".format(i),
                    season=SEASON,
                    game_date=date(2026, 5, 1 + i),
                    home_team_id=cle.id, away_team_id=tor.id,
                    home_score=110, away_score=99,
                    season_type="Playoffs", series_id=r1_id, series_game_num=i,
                )
            )
        r2_id = "{0}-X-R2-BOT".format(SEASON)
        session.add(
            PlayoffSeries(
                season=SEASON, round=2, series_id=r2_id,
                top_seed_team_id=cle.id, bottom_seed_team_id=det.id,
                top_seed=8, bottom_seed=3,
                top_wins=0, bottom_wins=0, status="active",
                parent_top_series_id=r1_id, parent_bottom_series_id=None,
            )
        )
        session.commit()

        # Today: a R2 game (DET-CLE), no scoreboard final (in progress).
        session.add(
            GameLog(
                game_id="0042500201", season=SEASON, game_date=target,
                home_team_id=det.id, away_team_id=cle.id,
                home_score=None, away_score=None,
                season_type="Playoffs", series_id=r2_id, series_game_num=1,
            )
        )
        session.commit()

        with patch("routers.playoffs._scoreboard_games_for_today", return_value={}), \
             patch("routers.playoffs._today_pacific", return_value=target):
            get_today(date_param=target.isoformat(), db=session)

        session.expire_all()
        r2 = session.query(PlayoffSeries).filter_by(series_id=r2_id).first()
        # Nothing should have changed — already-advanced state is preserved.
        assert r2.top_seed_team_id == cle.id
        assert r2.top_seed == 8
        assert r2.status == "active"
    finally:
        session.close()


def test_today_attaches_series_id_when_gamelog_missing_it():
    """If a today's GameLog row has no series_id but its team-pair matches
    an existing PlayoffSeries, /today must attach the series_id (and
    persist it to the row). Reproduces the production state where today's
    CLE-DET R2 game shipped with series_id=null because the bracket
    builder hadn't yet linked it."""
    session = _make_session()
    try:
        target = date(2026, 5, 13)
        cle = Team(id=1610612739, abbreviation="CLE", name="Cleveland Cavaliers", city="Cleveland")
        det = Team(id=1610612765, abbreviation="DET", name="Detroit Pistons", city="Detroit")
        session.add_all([cle, det])
        session.commit()

        r2_id = "{0}-X-R2-BOT".format(SEASON)
        session.add(
            PlayoffSeries(
                season=SEASON, round=2, series_id=r2_id,
                top_seed_team_id=cle.id, bottom_seed_team_id=det.id,
                top_seed=8, bottom_seed=3,
                top_wins=0, bottom_wins=0, status="active",
            )
        )
        # Today's R2 G1: scores final, but series_id=NULL on the row.
        g1_id = "0042500201"
        session.add(
            GameLog(
                game_id=g1_id, season=SEASON, game_date=target,
                home_team_id=det.id, away_team_id=cle.id,
                home_score=111, away_score=101,
                season_type="Playoffs", series_id=None, series_game_num=None,
            )
        )
        session.commit()

        with patch("routers.playoffs._scoreboard_games_for_today", return_value={}), \
             patch("routers.playoffs._today_pacific", return_value=target):
            response = get_today(date_param=target.isoformat(), db=session)

        # The response carries the matched series_id.
        assert len(response.games) == 1
        assert response.games[0].series_id == r2_id
        assert response.games[0].top_seed_team_abbr == "CLE"

        # And the row was persisted with the series_id attached.
        session.expire_all()
        g1 = session.query(GameLog).filter_by(game_id=g1_id).first()
        assert g1.series_id == r2_id, "series_id must be persisted to GameLog"
    finally:
        session.close()


def test_today_does_not_attach_series_id_across_seasons():
    """A team pair could match a series in a different season's bracket.
    The match must require season equality to avoid wiring this season's
    games to a historical series."""
    session = _make_session()
    try:
        target = date(2026, 5, 13)
        cle = Team(id=1610612739, abbreviation="CLE", name="Cleveland Cavaliers", city="Cleveland")
        det = Team(id=1610612765, abbreviation="DET", name="Detroit Pistons", city="Detroit")
        session.add_all([cle, det])
        session.commit()

        # Historical CLE-DET series from a prior season.
        old_id = "2023-24-X-R2-BOT"
        session.add(
            PlayoffSeries(
                season="2023-24", round=2, series_id=old_id,
                top_seed_team_id=cle.id, bottom_seed_team_id=det.id,
                top_seed=8, bottom_seed=3,
                top_wins=4, bottom_wins=2, status="closed",
            )
        )
        # Today's game — current season, no series_id on row.
        session.add(
            GameLog(
                game_id="0042500201", season=SEASON, game_date=target,
                home_team_id=det.id, away_team_id=cle.id,
                home_score=111, away_score=101,
                season_type="Playoffs", series_id=None,
            )
        )
        session.commit()

        with patch("routers.playoffs._scoreboard_games_for_today", return_value={}), \
             patch("routers.playoffs._today_pacific", return_value=target):
            response = get_today(date_param=target.isoformat(), db=session)

        # No match found (current season has no CLE-DET series). series_id
        # remains None — we must not wire it to the historical series.
        assert response.games[0].series_id is None
    finally:
        session.close()


def test_today_attach_derives_series_game_num_from_prior_completed_games():
    """Sprint 92 — when /today attaches a series_id to an unmatched row,
    it must also derive series_game_num so the UI can render "G2" / "G3"
    labels. The number = count of prior series games + 1, ordered by
    (game_date, game_id)."""
    session = _make_session()
    try:
        target = date(2026, 5, 13)
        cle = Team(id=1610612739, abbreviation="CLE", name="Cleveland Cavaliers", city="Cleveland")
        det = Team(id=1610612765, abbreviation="DET", name="Detroit Pistons", city="Detroit")
        session.add_all([cle, det])
        session.commit()

        r2_id = "{0}-E-R2-BOT".format(SEASON)
        session.add(
            PlayoffSeries(
                season=SEASON, round=2, series_id=r2_id,
                top_seed_team_id=cle.id, bottom_seed_team_id=det.id,
                top_seed=8, bottom_seed=3,
                top_wins=0, bottom_wins=0, status="active",
            )
        )
        # Two prior R2 games, both with series_id stamped (G1 + G2).
        for i, gdate in enumerate([date(2026, 5, 10), date(2026, 5, 11)], start=1):
            session.add(
                GameLog(
                    game_id="00425001{0:02d}".format(i),
                    season=SEASON, game_date=gdate,
                    home_team_id=det.id, away_team_id=cle.id,
                    home_score=111, away_score=101,
                    season_type="Playoffs", series_id=r2_id, series_game_num=i,
                )
            )
        # Today's G3, no series_id stamped (the bug we're closing).
        g3_id = "0042500103"
        session.add(
            GameLog(
                game_id=g3_id, season=SEASON, game_date=target,
                home_team_id=cle.id, away_team_id=det.id,
                home_score=110, away_score=99,
                season_type="Playoffs", series_id=None, series_game_num=None,
            )
        )
        session.commit()

        with patch("routers.playoffs._scoreboard_games_for_today", return_value={}), \
             patch("routers.playoffs._today_pacific", return_value=target):
            response = get_today(date_param=target.isoformat(), db=session)

        # Response carries the derived game number.
        today_game = next(g for g in response.games if g.game_id == g3_id)
        assert today_game.series_id == r2_id
        assert today_game.series_game_num == 3, (
            "third game in the series should be labeled G3"
        )

        # And the row was persisted so subsequent reads see it.
        session.expire_all()
        g3 = session.query(GameLog).filter_by(game_id=g3_id).first()
        assert g3.series_id == r2_id
        assert g3.series_game_num == 3
    finally:
        session.close()


def test_today_inserts_gamelog_row_for_scoreboard_only_finals():
    """Sprint 92 — when /today encounters a scoreboard-only final (no
    GameLog row exists), it must INSERT a row so that /bracket and
    /series/{id} reflect the win on their next read instead of lagging
    by one daily-sync cycle. Reproduces the production state where R2
    games existed only on the live scoreboard for ~12 hours after a
    game ended until the 6am sync caught up."""
    session = _make_session()
    try:
        target = date(2026, 5, 13)
        cle = Team(id=1610612739, abbreviation="CLE", name="Cleveland Cavaliers", city="Cleveland")
        det = Team(id=1610612765, abbreviation="DET", name="Detroit Pistons", city="Detroit")
        session.add_all([cle, det])
        session.commit()

        r2_id = "{0}-E-R2-BOT".format(SEASON)
        session.add(
            PlayoffSeries(
                season=SEASON, round=2, series_id=r2_id,
                top_seed_team_id=cle.id, bottom_seed_team_id=det.id,
                top_seed=8, bottom_seed=3,
                top_wins=0, bottom_wins=0, status="active",
            )
        )
        session.commit()

        # Today's G1 — DET wins 111-101 — exists only in the scoreboard
        # payload, NOT in GameLog yet.
        g1_id = "0042500201"
        scoreboard = {
            g1_id: {
                "gameId": g1_id,
                "gameStatus": 3,
                "gameTimeUTC": "2026-05-14T01:00:00Z",
                "homeTeam": {"teamId": det.id, "teamTricode": "DET", "score": 111},
                "awayTeam": {"teamId": cle.id, "teamTricode": "CLE", "score": 101},
                "broadcasters": {"nationalTvBroadcasters": []},
            }
        }
        with patch("routers.playoffs._scoreboard_games_for_today", return_value=scoreboard), \
             patch("routers.playoffs._today_pacific", return_value=target):
            response = get_today(date_param=target.isoformat(), db=session)

        # Response shows the live final.
        assert len(response.games) == 1
        assert response.games[0].series_id == r2_id
        assert response.games[0].home_pts == 111
        assert response.games[0].away_pts == 101

        # And — the new behavior — a GameLog row was inserted.
        session.expire_all()
        log = session.query(GameLog).filter_by(game_id=g1_id).first()
        assert log is not None, (
            "scoreboard-only final must INSERT a GameLog row so /bracket "
            "doesn't lag by a daily-sync cycle"
        )
        assert log.season == SEASON
        assert log.season_type == "Playoffs"
        assert log.home_team_id == det.id
        assert log.away_team_id == cle.id
        assert log.home_score == 111
        assert log.away_score == 101
        assert log.series_id == r2_id
        assert log.series_game_num == 1, "first game in the series should be G1"

        # /bracket counts wins fresh from GameLog (Sprint 91), so this win
        # should now be visible to bracket reads.
        bracket_resp = get_bracket(season=SEASON, db=session)
        all_series = (
            bracket_resp.east + bracket_resp.west
            + ([bracket_resp.finals] if bracket_resp.finals else [])
        )
        match = next(s for s in all_series if s.series_id == r2_id)
        assert match.bottom_wins == 1, (
            "DET (bottom seed) win should be reflected in /bracket immediately"
        )
        assert match.top_wins == 0
    finally:
        session.close()


def test_today_does_not_insert_gamelog_for_in_progress_scoreboard_games():
    """Only finals (gameStatus=3) trigger the GameLog insert. Live games
    (status=2) and scheduled tipoffs (status=1) are still ephemeral —
    inserting incomplete rows would race the daily sync and pollute
    GameLog with mid-game scores that aren't authoritative."""
    session = _make_session()
    try:
        target = date(2026, 5, 13)
        cle = Team(id=1610612739, abbreviation="CLE", name="Cleveland Cavaliers", city="Cleveland")
        det = Team(id=1610612765, abbreviation="DET", name="Detroit Pistons", city="Detroit")
        session.add_all([cle, det])
        session.commit()

        r2_id = "{0}-E-R2-BOT".format(SEASON)
        session.add(
            PlayoffSeries(
                season=SEASON, round=2, series_id=r2_id,
                top_seed_team_id=cle.id, bottom_seed_team_id=det.id,
                top_seed=8, bottom_seed=3,
                top_wins=0, bottom_wins=0, status="active",
            )
        )
        session.commit()

        g1_id = "0042500201"
        # gameStatus=2 (in progress)
        scoreboard = {
            g1_id: {
                "gameId": g1_id,
                "gameStatus": 2,
                "gameTimeUTC": "2026-05-14T01:00:00Z",
                "homeTeam": {"teamId": det.id, "teamTricode": "DET", "score": 78},
                "awayTeam": {"teamId": cle.id, "teamTricode": "CLE", "score": 72},
                "broadcasters": {"nationalTvBroadcasters": []},
            }
        }
        with patch("routers.playoffs._scoreboard_games_for_today", return_value=scoreboard), \
             patch("routers.playoffs._today_pacific", return_value=target):
            get_today(date_param=target.isoformat(), db=session)

        session.expire_all()
        log = session.query(GameLog).filter_by(game_id=g1_id).first()
        assert log is None, (
            "in-progress games must not trigger a GameLog insert — "
            "let the daily sync write the authoritative final later"
        )
    finally:
        session.close()
