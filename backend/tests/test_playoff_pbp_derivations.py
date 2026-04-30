"""Sprint 79 Stream B — playoff PBP derivation isolation tests.

The critical bug being verified: prior to Sprint 79, _upsert_lineup() in
pbp_sync_service.py filtered by (lineup_key, season) only — without is_playoff —
meaning a playoff derivation would silently overwrite regular-season lineup rows
for any shared lineup. These tests assert the regular-season vs playoff isolation
holds end-to-end.
"""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.migrations import upgrade_database  # noqa: E402
from db.models import LineupStats, PlayerOnOff, SeasonStat  # noqa: E402
from services.pbp_sync_service import (  # noqa: E402
    _clear_player_outputs,
    _clear_season_outputs,
    _update_season_stats,
    _upsert_lineup,
    _upsert_on_off,
)


@pytest.fixture
def db_session():
    with TemporaryDirectory() as tmpdir:
        database_url = "sqlite:///{0}".format(Path(tmpdir) / "playoff_pbp.db")
        upgrade_database(database_url)
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            yield session
        finally:
            session.close()
            engine.dispose()


class _LineupAcc:
    """Minimal stand-in for the lineup accumulator object _upsert_lineup expects."""

    def __init__(self, possessions, team_pts, opp_pts, plus_minus, seconds):
        self.possessions = possessions
        self.team_pts = team_pts
        self.opp_pts = opp_pts
        self.plus_minus = plus_minus
        self.seconds = seconds


def test_upsert_lineup_isolates_regular_season_from_playoff(db_session):
    """The bug fix: shared lineup_key must not have regular-season row clobbered by playoff."""
    lineup_key = "100-200-300-400-500"
    season = "2024-25"
    team_id = 1610612760

    # Seed a regular-season lineup with a known signature value
    rs_acc = _LineupAcc(possessions=120, team_pts=140, opp_pts=110, plus_minus=30.0, seconds=600.0)
    _upsert_lineup(db_session, lineup_key, season, team_id, rs_acc, is_playoff=False)
    db_session.commit()

    rs_row = (
        db_session.query(LineupStats)
        .filter_by(lineup_key=lineup_key, season=season, is_playoff=False)
        .first()
    )
    assert rs_row is not None
    assert rs_row.plus_minus == 30.0
    assert rs_row.possessions == 120

    # Now run a playoff derivation that touches the same lineup_key
    po_acc = _LineupAcc(possessions=80, team_pts=90, opp_pts=95, plus_minus=-5.0, seconds=400.0)
    _upsert_lineup(db_session, lineup_key, season, team_id, po_acc, is_playoff=True)
    db_session.commit()

    # Regular-season row must be untouched
    rs_row_after = (
        db_session.query(LineupStats)
        .filter_by(lineup_key=lineup_key, season=season, is_playoff=False)
        .first()
    )
    assert rs_row_after.plus_minus == 30.0, "regular-season row was clobbered by playoff derivation"
    assert rs_row_after.possessions == 120

    # Playoff row exists separately
    po_row = (
        db_session.query(LineupStats)
        .filter_by(lineup_key=lineup_key, season=season, is_playoff=True)
        .first()
    )
    assert po_row is not None
    assert po_row.plus_minus == -5.0
    assert po_row.possessions == 80


def test_upsert_on_off_isolates_regular_season_from_playoff(db_session):
    """PlayerOnOff: same player_id + season can carry both regular-season and playoff rows."""
    player_id = 2544
    season = "2024-25"

    rs_data = {
        "on_minutes": 1800.0,
        "off_minutes": 200.0,
        "on_net_rating": 8.0,
        "off_net_rating": -3.0,
        "on_off_net": 11.0,
        "on_ortg": 118.0,
        "on_drtg": 110.0,
        "off_ortg": 108.0,
        "off_drtg": 111.0,
    }
    _upsert_on_off(db_session, player_id, season, rs_data, is_playoff=False)
    db_session.commit()

    po_data = {
        "on_minutes": 280.0,
        "off_minutes": 40.0,
        "on_net_rating": 4.0,
        "off_net_rating": -8.0,
        "on_off_net": 12.0,
        "on_ortg": 115.0,
        "on_drtg": 111.0,
        "off_ortg": 102.0,
        "off_drtg": 110.0,
    }
    _upsert_on_off(db_session, player_id, season, po_data, is_playoff=True)
    db_session.commit()

    rs_row = (
        db_session.query(PlayerOnOff)
        .filter_by(player_id=player_id, season=season, is_playoff=False)
        .first()
    )
    po_row = (
        db_session.query(PlayerOnOff)
        .filter_by(player_id=player_id, season=season, is_playoff=True)
        .first()
    )

    assert rs_row is not None and po_row is not None
    assert rs_row.on_minutes == 1800.0
    assert po_row.on_minutes == 280.0
    assert rs_row.on_off_net == 11.0
    assert po_row.on_off_net == 12.0


def test_clear_season_outputs_only_clears_matching_is_playoff(db_session):
    """_clear_season_outputs must scope its DELETE to the requested is_playoff."""
    season = "2024-25"

    # Seed both a regular-season and a playoff row for the same player + lineup
    _upsert_on_off(db_session, 2544, season, {"on_minutes": 1800.0, "off_minutes": 200.0,
                                              "on_net_rating": 8.0, "off_net_rating": -3.0,
                                              "on_off_net": 11.0, "on_ortg": 118.0,
                                              "on_drtg": 110.0, "off_ortg": 108.0,
                                              "off_drtg": 111.0}, is_playoff=False)
    _upsert_on_off(db_session, 2544, season, {"on_minutes": 280.0, "off_minutes": 40.0,
                                              "on_net_rating": 4.0, "off_net_rating": -8.0,
                                              "on_off_net": 12.0, "on_ortg": 115.0,
                                              "on_drtg": 111.0, "off_ortg": 102.0,
                                              "off_drtg": 110.0}, is_playoff=True)

    rs_acc = _LineupAcc(120, 140, 110, 30.0, 600.0)
    po_acc = _LineupAcc(80, 90, 95, -5.0, 400.0)
    _upsert_lineup(db_session, "1-2-3-4-5", season, 1610612760, rs_acc, is_playoff=False)
    _upsert_lineup(db_session, "1-2-3-4-5", season, 1610612760, po_acc, is_playoff=True)
    db_session.commit()

    # Clear only the playoff slice
    _clear_season_outputs(db_session, season, is_playoff=True)
    db_session.commit()

    # Regular-season rows survive
    assert db_session.query(PlayerOnOff).filter_by(season=season, is_playoff=False).count() == 1
    assert db_session.query(LineupStats).filter_by(season=season, is_playoff=False).count() == 1

    # Playoff rows are gone
    assert db_session.query(PlayerOnOff).filter_by(season=season, is_playoff=True).count() == 0
    assert db_session.query(LineupStats).filter_by(season=season, is_playoff=True).count() == 0
