"""Sprint 98 Stream D1 — Shared pytest fixtures.

Adds three fixtures that any test file can opt into:
  - ``test_db_session``: in-memory SQLite session with the full schema
    created via SQLAlchemy ``Base.metadata.create_all``. No data.
  - ``client``: FastAPI ``TestClient`` bound to ``test_db_session`` via a
    ``get_db`` dependency override.
  - ``admin_client``: ``client`` with ``X-Admin-Key`` pre-attached, so
    admin-gated routes return 200 instead of 403.

Existing tests that build their own session don't need to migrate —
the fixtures here are additive. Sprint 98 D2 smoke tests + D3 deep
tests use these to avoid copy-pasting the session/TestClient setup.

Note on SQLite limitations vs. production Postgres: a few models use
JSON / Array column types that SQLite doesn't natively support; those
tests should override ``test_db_session`` to point at a real Postgres
via ``TEST_DATABASE_URL`` if needed. The fixtures here cover the
common case.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend/ is importable when running pytest from various cwds.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


_PLAYOFF_TRUTH_VIEW = """
CREATE VIEW IF NOT EXISTS playoff_series_win_truth AS
SELECT
    ps.series_id AS series_id,
    ps.season AS season,
    ps.top_seed_team_id AS top_seed_team_id,
    ps.bottom_seed_team_id AS bottom_seed_team_id,
    COALESCE(SUM(
        CASE
            WHEN ps.top_seed_team_id IS NOT NULL
                 AND gl.home_score IS NOT NULL
                 AND gl.away_score IS NOT NULL
                 AND (
                     (gl.home_team_id = ps.top_seed_team_id AND gl.home_score > gl.away_score)
                     OR (gl.away_team_id = ps.top_seed_team_id AND gl.away_score > gl.home_score)
                 )
            THEN 1 ELSE 0
        END
    ), 0) AS top_wins,
    COALESCE(SUM(
        CASE
            WHEN ps.bottom_seed_team_id IS NOT NULL
                 AND gl.home_score IS NOT NULL
                 AND gl.away_score IS NOT NULL
                 AND (
                     (gl.home_team_id = ps.bottom_seed_team_id AND gl.home_score > gl.away_score)
                     OR (gl.away_team_id = ps.bottom_seed_team_id AND gl.away_score > gl.home_score)
                 )
            THEN 1 ELSE 0
        END
    ), 0) AS bottom_wins,
    COUNT(gl.game_id) AS games_played
FROM playoff_series ps
LEFT JOIN game_logs gl
    ON gl.series_id = ps.series_id
    AND gl.season_type = 'Playoffs'
GROUP BY ps.series_id, ps.season, ps.top_seed_team_id, ps.bottom_seed_team_id
"""


@pytest.fixture
def test_db_session() -> Generator[Session, None, None]:
    """Fresh in-memory SQLite session with the full ORM schema + views.

    Includes the ``playoff_series_win_truth`` view (Sprint 98 migration
    0027) so endpoints that query the view work in tests without
    running the full Alembic chain.
    """
    from sqlalchemy import text

    from db.database import Base
    import db.models  # noqa: F401 — register every ORM model on Base.metadata

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text(_PLAYOFF_TRUTH_VIEW))
        conn.commit()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(test_db_session, monkeypatch):
    """FastAPI TestClient with the production app, but ``get_db`` overridden
    to yield the test session. Useful for smoke-testing every router.
    """
    # Disable rate limiting + admin gate for the smoke surface — we're
    # testing wiring, not security. Individual hardening tests should
    # build their own app with these enabled.
    monkeypatch.setenv("ENABLE_RATE_LIMIT", "false")
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)

    # Reload config so the flags take effect on app boot.
    import importlib

    import config

    importlib.reload(config)

    import main as main_module

    importlib.reload(main_module)
    from fastapi.testclient import TestClient
    from db.database import get_db

    def _override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    main_module.app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(main_module.app)
    finally:
        main_module.app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def admin_client(test_db_session, monkeypatch):
    """TestClient with a configured ADMIN_API_KEY + the header pre-attached.

    Use this when smoke-testing admin-gated endpoints to verify they
    accept the key (and, by extension, that the dependency wiring is
    intact).
    """
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key-xyz")
    monkeypatch.setenv("ENABLE_RATE_LIMIT", "false")

    import importlib

    import config

    importlib.reload(config)

    import main as main_module

    importlib.reload(main_module)
    from fastapi.testclient import TestClient
    from db.database import get_db

    def _override_get_db():
        try:
            yield test_db_session
        finally:
            pass

    main_module.app.dependency_overrides[get_db] = _override_get_db
    tc = TestClient(main_module.app, headers={"X-Admin-Key": "test-admin-key-xyz"})
    try:
        yield tc
    finally:
        main_module.app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def seed_basic(test_db_session):
    """Insert a minimal cohort: 2 teams + 5 players + 1 season of stats.

    Useful for smoke tests that need any rows in the DB. Returns a dict
    of the inserted records keyed by purpose.
    """
    from db.models import Player, SeasonStat, Team

    teams = [
        Team(id=1610612747, abbreviation="LAL", name="Lakers", city="Los Angeles"),
        Team(id=1610612744, abbreviation="GSW", name="Warriors", city="San Francisco"),
    ]
    for t in teams:
        test_db_session.add(t)

    players = [
        Player(
            id=2544,
            full_name="LeBron James",
            first_name="LeBron",
            last_name="James",
            team_id=1610612747,
        ),
        Player(
            id=201939,
            full_name="Stephen Curry",
            first_name="Stephen",
            last_name="Curry",
            team_id=1610612744,
        ),
    ]
    for p in players:
        test_db_session.add(p)
    test_db_session.flush()

    season_stats = [
        SeasonStat(
            player_id=2544,
            season="2024-25",
            team_abbreviation="LAL",
            is_playoff=False,
            gp=70,
            pts_pg=25.4,
            reb_pg=7.8,
            ast_pg=8.1,
        ),
        SeasonStat(
            player_id=201939,
            season="2024-25",
            team_abbreviation="GSW",
            is_playoff=False,
            gp=72,
            pts_pg=27.1,
            reb_pg=4.4,
            ast_pg=6.0,
        ),
    ]
    for ss in season_stats:
        test_db_session.add(ss)
    test_db_session.commit()

    return {"teams": teams, "players": players, "season_stats": season_stats}
