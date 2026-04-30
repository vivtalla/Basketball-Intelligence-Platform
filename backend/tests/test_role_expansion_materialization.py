"""Sprint 79 Stream A2 — role_expansion materialization tests.

Methodology: specs/methodology-future-modeling.md#2.
"""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.migrations import upgrade_database  # noqa: E402
from db.models import Player, RoleExpansionObservation, SeasonStat, Team  # noqa: E402
from services.role_expansion_materialization_service import (  # noqa: E402
    MIN_USG_DELTA,
    materialize_role_expansion,
)


@pytest.fixture
def db_session():
    with TemporaryDirectory() as tmpdir:
        database_url = "sqlite:///{0}".format(Path(tmpdir) / "role_expansion.db")
        upgrade_database(database_url)
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            yield session
        finally:
            session.close()
            engine.dispose()


def _make_team(session, team_id, abbr):
    team = Team(id=team_id, abbreviation=abbr, name=abbr, city=abbr)
    session.add(team)
    session.flush()
    return team


def _make_player(session, player_id, name, birth_date="1995-01-01"):
    player = Player(
        id=player_id,
        full_name=name,
        first_name=name.split()[0],
        last_name=name.split()[-1],
        is_active=True,
        birth_date=birth_date,
    )
    session.add(player)
    session.flush()
    return player


def _make_season_stat(session, player_id, season, *, ts_pct, usg_pct, gp=70,
                     team_abbr="OKC", ast_pg=4.0, min_pg=32.0, obpm=2.0):
    row = SeasonStat(
        player_id=player_id,
        season=season,
        team_abbreviation=team_abbr,
        is_playoff=False,
        gp=gp,
        ts_pct=ts_pct,
        usg_pct=usg_pct,
        ast_pg=ast_pg,
        min_pg=min_pg,
        obpm=obpm,
    )
    session.add(row)
    session.flush()
    return row


def test_finds_qualifying_pair_with_usg_bump(db_session):
    """Year-over-year +5pp usage with sufficient GP -> 1 row written."""
    _make_team(db_session, 1610612760, "OKC")
    _make_player(db_session, 100, "Test Player")
    _make_season_stat(db_session, 100, "2022-23", ts_pct=0.58, usg_pct=0.20, gp=70)
    _make_season_stat(db_session, 100, "2023-24", ts_pct=0.56, usg_pct=0.25, gp=72)
    db_session.commit()

    result = materialize_role_expansion(db=db_session)

    assert result["rows_inserted"] == 1
    assert result["rows_updated"] == 0
    obs = db_session.query(RoleExpansionObservation).first()
    assert obs is not None
    assert obs.from_season == "2022-23"
    assert obs.to_season == "2023-24"
    assert abs(obs.usg_delta - 0.05) < 1e-6
    assert abs(obs.ts_delta - (-0.02)) < 1e-6
    assert obs.pre_ts_pct == 0.58


def test_skips_below_threshold_usg_delta(db_session):
    """Usage growth below +0.03 doesn't qualify as role expansion."""
    _make_team(db_session, 1610612760, "OKC")
    _make_player(db_session, 200, "Stable Usage")
    _make_season_stat(db_session, 200, "2022-23", ts_pct=0.55, usg_pct=0.20, gp=70)
    _make_season_stat(db_session, 200, "2023-24", ts_pct=0.55, usg_pct=0.21, gp=72)  # +0.01 only
    db_session.commit()

    result = materialize_role_expansion(db=db_session)
    assert result["rows_inserted"] == 0
    assert db_session.query(RoleExpansionObservation).count() == 0


def test_skips_low_gp_seasons(db_session):
    """Seasons with GP < 40 don't count even if usg delta is large."""
    _make_team(db_session, 1610612760, "OKC")
    _make_player(db_session, 300, "Injured Player")
    _make_season_stat(db_session, 300, "2022-23", ts_pct=0.55, usg_pct=0.18, gp=30)  # too few
    _make_season_stat(db_session, 300, "2023-24", ts_pct=0.55, usg_pct=0.28, gp=70)
    db_session.commit()

    result = materialize_role_expansion(db=db_session)
    assert result["rows_inserted"] == 0
    assert result["rows_skipped"] >= 1


def test_skips_non_consecutive_seasons(db_session):
    """A player with a gap year (e.g. injury, overseas) shouldn't pair across the gap."""
    _make_team(db_session, 1610612760, "OKC")
    _make_player(db_session, 400, "Gap Year Player")
    _make_season_stat(db_session, 400, "2021-22", ts_pct=0.55, usg_pct=0.20, gp=70)
    # 2022-23 missing
    _make_season_stat(db_session, 400, "2023-24", ts_pct=0.55, usg_pct=0.30, gp=70)
    db_session.commit()

    result = materialize_role_expansion(db=db_session)
    assert result["rows_inserted"] == 0


def test_idempotent_rerun_produces_zero_new_rows(db_session):
    """Running the materializer twice should produce the same row, updated not duplicated."""
    _make_team(db_session, 1610612760, "OKC")
    _make_player(db_session, 500, "Repeat Player")
    _make_season_stat(db_session, 500, "2022-23", ts_pct=0.58, usg_pct=0.20, gp=70)
    _make_season_stat(db_session, 500, "2023-24", ts_pct=0.60, usg_pct=0.26, gp=72)
    db_session.commit()

    first = materialize_role_expansion(db=db_session)
    assert first["rows_inserted"] == 1
    assert first["rows_updated"] == 0

    second = materialize_role_expansion(db=db_session)
    assert second["rows_inserted"] == 0
    assert second["rows_updated"] == 1

    # Still exactly one row in the DB
    assert db_session.query(RoleExpansionObservation).count() == 1


def test_aggregates_traded_player_seasons(db_session):
    """A player traded mid-season has multiple SeasonStat rows. Aggregate by GP-weighted avg."""
    _make_team(db_session, 1610612760, "OKC")
    _make_team(db_session, 1610612747, "LAL")
    _make_player(db_session, 600, "Traded Player")
    # Pre season: split between two teams
    _make_season_stat(db_session, 600, "2022-23", ts_pct=0.55, usg_pct=0.18, gp=40, team_abbr="OKC")
    _make_season_stat(db_session, 600, "2022-23", ts_pct=0.60, usg_pct=0.22, gp=30, team_abbr="LAL")
    # Post season: single team, big role
    _make_season_stat(db_session, 600, "2023-24", ts_pct=0.58, usg_pct=0.27, gp=72, team_abbr="LAL")
    db_session.commit()

    result = materialize_role_expansion(db=db_session)
    assert result["rows_inserted"] == 1

    obs = db_session.query(RoleExpansionObservation).first()
    # Pre-season weighted avg: (0.55*40 + 0.60*30) / 70 = 0.5714, (0.18*40 + 0.22*30) / 70 = 0.1971
    assert abs(obs.pre_ts_pct - 0.5714285714) < 1e-4
    assert abs(obs.pre_ts_pct * 70 - (0.55 * 40 + 0.60 * 30)) < 1e-4
