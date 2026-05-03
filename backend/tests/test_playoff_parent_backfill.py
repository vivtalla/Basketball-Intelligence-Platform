"""Sprint 86 Stream A2 — backfill script for parent_*_series_id pointers.

Two scenarios:

1. A closed Round-1 parent without a downstream parent pointer gets the
   pointer set on the correct slot (TOP for 1v8 / 2v7, BOT for 4v5 / 3v6).
2. Re-running the backfill on the same DB is idempotent — pre-existing
   pointers are preserved, no duplicates are written.
"""
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import PlayoffSeries, Team  # noqa: E402
from data.backfill_playoff_parent_pointers import backfill_parent_pointers  # noqa: E402


def _make_session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Real West conference team_ids so the abbr-fallback conference resolver works.
OKC = (1610612760, "OKC", "Oklahoma City Thunder")
PHX = (1610612756, "PHX", "Phoenix Suns")  # bottom 8-seed for the test
LAC = (1610612746, "LAC", "LA Clippers")
GSW = (1610612744, "GSW", "Golden State Warriors")


def _seed_closed_round1_with_empty_round2(session, season="2025-26"):
    """Seed a closed Round-1 1v8 series (OKC sweeps PHX) AND its Round-2 child
    row with no parent pointers — mimics a series that closed pre-Sprint-85.
    The Round-2 row also has the OKC seat populated so the backfill can find
    it via the fallback search even without a stable slot_id."""
    session.add_all([Team(id=tid, abbreviation=abbr, name=name) for tid, abbr, name in (OKC, PHX, LAC, GSW)])
    session.commit()

    okc_phx_series_id = "{0}-W-R1-OKC-PHX".format(season)
    session.add(
        PlayoffSeries(
            season=season,
            round=1,
            series_id=okc_phx_series_id,
            top_seed_team_id=OKC[0],
            bottom_seed_team_id=PHX[0],
            top_seed=1,
            bottom_seed=8,
            top_wins=4,
            bottom_wins=0,
            status="closed",
            winner_team_id=OKC[0],
        )
    )

    # Round-2 child slot pre-populated with OKC in the TOP seat (as if it had
    # been minted by build_or_refresh_bracket from real games), but the
    # parent_top_series_id pointer is NULL — exactly the production state for
    # series that closed before Sprint 85.
    session.add(
        PlayoffSeries(
            season=season,
            round=2,
            series_id="{0}-W-R2-TOP".format(season),
            top_seed_team_id=OKC[0],
            bottom_seed_team_id=None,
            top_seed=1,
            bottom_seed=None,
            top_wins=0,
            bottom_wins=0,
            status="scheduled",
        )
    )
    session.commit()
    return okc_phx_series_id


def test_backfill_sets_parent_pointer_for_closed_round1_series():
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        season = "2025-26"
        parent_id = _seed_closed_round1_with_empty_round2(session, season=season)

        summary = backfill_parent_pointers(session, season=season)
        assert summary["closed_seen"] == 1
        # 1v8 is the TOP-arm "lower seed" row → child_slot == "TOP" → top pointer updated.
        assert summary["updated_top"] == 1
        assert summary["updated_bottom"] == 0
        assert summary["already_set"] == 0

        child = (
            session.query(PlayoffSeries)
            .filter(PlayoffSeries.series_id == "{0}-W-R2-TOP".format(season))
            .first()
        )
        assert child is not None
        assert child.parent_top_series_id == parent_id
        # Bottom seat parent stays NULL — its parent (4v5) hasn't closed yet.
        assert child.parent_bottom_series_id is None
    finally:
        session.close()


def test_backfill_is_idempotent_on_rerun():
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        season = "2025-26"
        _seed_closed_round1_with_empty_round2(session, season=season)

        first = backfill_parent_pointers(session, season=season)
        second = backfill_parent_pointers(session, season=season)

        # First run sets the pointer.
        assert first["updated_top"] == 1
        # Second run finds it already set — no further updates.
        assert second["updated_top"] == 0
        assert second["updated_bottom"] == 0
        assert second["already_set"] == 1
    finally:
        session.close()
