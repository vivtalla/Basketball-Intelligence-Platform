"""Sprint 98 Stream B4 — Tests for the playoff series drift detector.

Two guarantees:
  1. When cached wins match the view, drift list is empty.
  2. When cached wins disagree with the view, the offending series is
     surfaced with both cached and true counts.

These tests run against an in-memory SQLite session that includes the
playoff_series_win_truth view created by migration 0027. We bootstrap
the view via the migration's CREATE VIEW SQL so the test doesn't depend
on running the full Alembic chain.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GameLog, PlayoffSeries, Team  # noqa: E402
from services.playoff_drift_detector import detect_drift  # noqa: E402


_VIEW_SQL = """
CREATE VIEW playoff_series_win_truth AS
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


def _make_session_with_view():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text(_VIEW_SQL))
        conn.commit()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _seed_phi_nyk(session, top_wins_cached: int, bottom_wins_cached: int, games: int):
    """Seed PHI-NYK R2 series with `games` games where NYK won every one,
    but PlayoffSeries.top_wins/bottom_wins are set to the cached values
    provided (which may disagree with reality).
    """
    session.add(Team(id=1610612752, abbreviation="NYK", name="Knicks", city="New York"))
    session.add(Team(id=1610612755, abbreviation="PHI", name="76ers", city="Philadelphia"))
    session.add(
        PlayoffSeries(
            season="2025-26",
            round=2,
            series_id="2025-26-E-R2-BOT",
            top_seed_team_id=1610612755,  # PHI top seed
            bottom_seed_team_id=1610612752,  # NYK bottom seed
            top_seed=2,
            bottom_seed=4,
            top_wins=top_wins_cached,
            bottom_wins=bottom_wins_cached,
            status="closed",
        )
    )
    # NYK (bottom seed) wins every game.
    for i in range(games):
        session.add(
            GameLog(
                game_id=f"00425002{10 + i}",  # 0042500210..0042500213
                season="2025-26",
                game_date=date(2026, 5, 4 + i),
                home_team_id=1610612752 if i % 2 == 0 else 1610612755,
                away_team_id=1610612755 if i % 2 == 0 else 1610612752,
                home_score=120 if i % 2 == 0 else 90,
                away_score=90 if i % 2 == 0 else 120,
                season_type="Playoffs",
                series_id="2025-26-E-R2-BOT",
                series_game_num=i + 1,
            )
        )
    session.commit()


def test_no_drift_when_cache_matches_view():
    db = _make_session_with_view()
    # PHI 0, NYK 4 cached AND NYK actually won all 4 games.
    _seed_phi_nyk(db, top_wins_cached=0, bottom_wins_cached=4, games=4)

    drift = detect_drift(db)
    assert drift == []


def test_drift_surfaces_when_cache_disagrees_with_view():
    db = _make_session_with_view()
    # NYK actually won 4-0; we incorrectly cache 0-3 (the Sprint 96
    # closeout-night situation).
    _seed_phi_nyk(db, top_wins_cached=0, bottom_wins_cached=3, games=4)

    drift = detect_drift(db)
    assert len(drift) == 1
    row = drift[0]
    assert row["series_id"] == "2025-26-E-R2-BOT"
    assert row["season"] == "2025-26"
    assert row["cached_top_wins"] == 0
    assert row["true_top_wins"] == 0
    assert row["cached_bottom_wins"] == 3
    assert row["true_bottom_wins"] == 4
    assert row["games_played"] == 4
