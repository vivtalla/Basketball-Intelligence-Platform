"""Sprint 97 — Tests for the playoff series gap-backfill service.

Six guarantees:
  1. _parse_series_slot correctly splits a playoff game_id.
  2. Backfill inserts a missing G1 between existing G2/G3, with correct
     metadata (series_id, season, season_type, scores).
  3. After a backfill, series_game_num is renumbered so date order
     matches position.
  4. Running the backfill twice doesn't double-insert (idempotency).
  5. When NBA returns None for a position, the loop stops probing higher
     positions in that series.
  6. Series with no existing games are skipped (nothing to backfill).
"""
from datetime import date
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GameLog, PlayoffSeries, Team  # noqa: E402
from services.playoff_series_backfill import (  # noqa: E402
    _parse_series_slot,
    backfill_playoff_series_gaps,
)


def _make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _seed_phi_nyk_series(session, *, with_g1=False):
    """Seed the PHI-NYK R2 series setup that bit us on 2026-05-10."""
    session.add(Team(id=1610612752, abbreviation="NYK", name="New York Knicks", city="New York"))
    session.add(Team(id=1610612755, abbreviation="PHI", name="Philadelphia 76ers", city="Philadelphia"))
    session.add(
        PlayoffSeries(
            season="2025-26",
            round=2,
            series_id="2025-26-E-R2-BOT",
            top_seed_team_id=1610612755,
            bottom_seed_team_id=1610612752,
            top_seed=2,
            bottom_seed=4,
            top_wins=0,
            bottom_wins=3,
            status="active",
        )
    )
    if with_g1:
        session.add(
            GameLog(
                game_id="0042500211",
                season="2025-26",
                game_date=date(2026, 5, 4),
                home_team_id=1610612752,
                away_team_id=1610612755,
                home_score=137,
                away_score=98,
                season_type="Playoffs",
                series_id="2025-26-E-R2-BOT",
                series_game_num=1,
            )
        )
    session.add(
        GameLog(
            game_id="0042500212",
            season="2025-26",
            game_date=date(2026, 5, 6),
            home_team_id=1610612752,
            away_team_id=1610612755,
            home_score=108,
            away_score=102,
            season_type="Playoffs",
            series_id="2025-26-E-R2-BOT",
            series_game_num=1 if not with_g1 else 2,  # the wrong vs right state
        )
    )
    session.add(
        GameLog(
            game_id="0042500213",
            season="2025-26",
            game_date=date(2026, 5, 8),
            home_team_id=1610612755,
            away_team_id=1610612752,
            home_score=94,
            away_score=108,
            season_type="Playoffs",
            series_id="2025-26-E-R2-BOT",
            series_game_num=2 if not with_g1 else 3,
        )
    )
    session.commit()


def test_parse_series_slot():
    assert _parse_series_slot("0042500211") == ("004250021", 1)
    assert _parse_series_slot("0042500117") == ("004250011", 7)
    assert _parse_series_slot("0042500102") == ("004250010", 2)
    # Non-playoff
    assert _parse_series_slot("0052500100") is None
    # Wrong length
    assert _parse_series_slot("004250021") is None
    # None / empty
    assert _parse_series_slot(None) is None
    assert _parse_series_slot("") is None


def test_backfill_inserts_missing_g1():
    session = _make_session()
    _seed_phi_nyk_series(session, with_g1=False)

    # Mock NBA fetch: position 1 exists; positions 4-7 return None (break).
    def fake_fetch(game_id):
        if game_id == "0042500211":
            return {
                "game_id": "0042500211",
                "game_date": "2026-05-04",
                "home_team_id": 1610612752,
                "away_team_id": 1610612755,
                "home_score": 137,
                "away_score": 98,
            }
        return None

    backfilled = backfill_playoff_series_gaps(
        session, "2025-26", fetch_fn=fake_fetch, sleep_fn=lambda _s: None
    )

    assert backfilled == ["0042500211"]
    # The new row exists with the right metadata
    new_row = session.query(GameLog).filter(GameLog.game_id == "0042500211").first()
    assert new_row is not None
    assert new_row.series_id == "2025-26-E-R2-BOT"
    assert new_row.home_score == 137
    assert new_row.away_score == 98
    assert new_row.season_type == "Playoffs"
    assert new_row.season == "2025-26"


def test_backfill_renumbers_series_game_num():
    session = _make_session()
    _seed_phi_nyk_series(session, with_g1=False)
    # Pre-backfill: G2 has series_game_num=1, G3 has 2 (the wrong state)
    pre_212 = session.query(GameLog).filter(GameLog.game_id == "0042500212").first()
    pre_213 = session.query(GameLog).filter(GameLog.game_id == "0042500213").first()
    assert pre_212.series_game_num == 1
    assert pre_213.series_game_num == 2

    def fake_fetch(game_id):
        if game_id == "0042500211":
            return {
                "game_id": "0042500211",
                "game_date": "2026-05-04",
                "home_team_id": 1610612752,
                "away_team_id": 1610612755,
                "home_score": 137,
                "away_score": 98,
            }
        return None

    backfill_playoff_series_gaps(
        session, "2025-26", fetch_fn=fake_fetch, sleep_fn=lambda _s: None
    )

    # Post-backfill: G1=211, G2=212, G3=213 (renumbered)
    g1 = session.query(GameLog).filter(GameLog.game_id == "0042500211").first()
    g2 = session.query(GameLog).filter(GameLog.game_id == "0042500212").first()
    g3 = session.query(GameLog).filter(GameLog.game_id == "0042500213").first()
    assert g1.series_game_num == 1
    assert g2.series_game_num == 2
    assert g3.series_game_num == 3


def test_backfill_is_idempotent():
    session = _make_session()
    _seed_phi_nyk_series(session, with_g1=True)  # already correct

    fetch_calls = []

    def fake_fetch(game_id):
        fetch_calls.append(game_id)
        return None  # NBA returns nothing → stop probing

    backfilled = backfill_playoff_series_gaps(
        session, "2025-26", fetch_fn=fake_fetch, sleep_fn=lambda _s: None
    )

    # No gaps → no inserts. May probe G4 (one past max) to check for a
    # newly-finished game; that's allowed and expected.
    assert backfilled == []
    # Total games in DB unchanged
    assert (
        session.query(GameLog)
        .filter(GameLog.series_id == "2025-26-E-R2-BOT")
        .count()
        == 3
    )


def test_backfill_breaks_when_nba_returns_none():
    session = _make_session()
    # Seed a series with only G3 — backfill should attempt G1, get None, stop.
    session.add(Team(id=1610612752, abbreviation="NYK", name="New York Knicks", city="New York"))
    session.add(Team(id=1610612755, abbreviation="PHI", name="Philadelphia 76ers", city="Philadelphia"))
    session.add(
        PlayoffSeries(
            season="2025-26",
            round=2,
            series_id="2025-26-E-R2-BOT",
            top_seed_team_id=1610612755,
            bottom_seed_team_id=1610612752,
            top_seed=2,
            bottom_seed=4,
            status="active",
        )
    )
    session.add(
        GameLog(
            game_id="0042500213",
            season="2025-26",
            game_date=date(2026, 5, 8),
            home_team_id=1610612755,
            away_team_id=1610612752,
            home_score=94,
            away_score=108,
            season_type="Playoffs",
            series_id="2025-26-E-R2-BOT",
            series_game_num=1,
        )
    )
    session.commit()

    calls = []

    def fake_fetch(game_id):
        calls.append(game_id)
        return None  # NBA has nothing for any position

    backfilled = backfill_playoff_series_gaps(
        session, "2025-26", fetch_fn=fake_fetch, sleep_fn=lambda _s: None
    )
    assert backfilled == []
    # Should have probed position 1 (first missing) then broken — not also 2,4.
    assert calls == ["0042500211"]


def test_backfill_skips_series_with_no_games():
    session = _make_session()
    session.add(Team(id=1610612752, abbreviation="NYK", name="New York Knicks", city="New York"))
    session.add(Team(id=1610612755, abbreviation="PHI", name="Philadelphia 76ers", city="Philadelphia"))
    # PlayoffSeries with no GameLog rows yet (scheduled or just-created)
    session.add(
        PlayoffSeries(
            season="2025-26",
            round=2,
            series_id="2025-26-E-R2-BOT",
            top_seed_team_id=1610612755,
            bottom_seed_team_id=1610612752,
            top_seed=2,
            bottom_seed=4,
            status="scheduled",
        )
    )
    session.commit()

    calls = []

    def fake_fetch(game_id):
        calls.append(game_id)
        return None

    backfilled = backfill_playoff_series_gaps(
        session, "2025-26", fetch_fn=fake_fetch, sleep_fn=lambda _s: None
    )
    # Scheduled series not in (active, closed) → never queried
    # Even if it were active, no existing rows = no slot to derive from
    assert backfilled == []
    assert calls == []
