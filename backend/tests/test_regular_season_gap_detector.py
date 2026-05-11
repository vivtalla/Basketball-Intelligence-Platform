"""Sprint 98 — Tests for the regular-season gap detector.

Four guarantees mirror the playoff backfill suite:
  1. Schedule walker correctly parses the CDN payload and filters to
     window-bound regular-season Finals.
  2. Detector inserts a missing game with correct metadata when NBA's
     boxscoresummary returns Final.
  3. Detector is idempotent — running twice doesn't double-insert.
  4. When NBA's per-game summary returns None for a missing game, the
     detector skips it (no insert) but continues probing the rest.
"""
from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GameLog, Team  # noqa: E402
from services.regular_season_gap_detector import (  # noqa: E402
    _enumerate_schedule_finals,
    detect_and_backfill_regular_season_gaps,
)


def _make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _isolated_cache(monkeypatch):
    """Point CacheManager at a fresh sqlite file so freshness writes don't share state."""
    from data import cache as cache_module

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setattr(cache_module.CacheManager, "_db_path", tmp.name)
    monkeypatch.setattr(cache_module.CacheManager, "_initialized", False)
    cache_module.CacheManager._stats = {"hit": 0, "miss": 0, "expired": 0}


def _seed_teams(session):
    session.add(Team(id=1610612747, abbreviation="LAL", name="Lakers", city="Los Angeles"))
    session.add(Team(id=1610612744, abbreviation="GSW", name="Warriors", city="San Francisco"))
    session.commit()


def _cdn_schedule_envelope(games_with_status):
    """Build a CDN-shape schedule envelope from ``[(game_id, gameCode, status), ...]``."""
    return {
        "source": "cdn_schedule",
        "payload": {
            "leagueSchedule": {
                "gameDates": [
                    {
                        "games": [
                            {
                                "gameId": gid,
                                "gameCode": gcode,
                                "gameStatus": status,
                            }
                            for gid, gcode, status in games_with_status
                        ]
                    }
                ]
            }
        },
    }


def test_enumerate_schedule_finals_filters_to_regular_season_finals_in_window():
    today = date(2026, 1, 20)
    # Mix: in-window final regular-season game, in-window upcoming, out-of-window,
    # playoff game (wrong prefix), final outside window.
    envelope = _cdn_schedule_envelope(
        [
            ("0022500001", "20260115/LALGSW", 3),  # in window, final, RS — keep
            ("0022500002", "20260119/LALGSW", 1),  # in window, upcoming — skip
            ("0022500003", "20251220/LALGSW", 3),  # before window — skip
            ("0042500001", "20260115/LALGSW", 3),  # playoff prefix — skip
            ("0022500004", "20260120/LALGSW", 3),  # today (excluded by window) — skip
        ]
    )

    finals = _enumerate_schedule_finals(
        season="2025-26",
        days_back=14,
        today=today,
        fetch_schedule_fn=lambda season: envelope,
    )

    assert finals == [("0022500001", date(2026, 1, 15))]


def test_detector_inserts_missing_final_game(monkeypatch):
    _isolated_cache(monkeypatch)
    db = _make_session()
    _seed_teams(db)

    today = date(2026, 1, 20)
    envelope = _cdn_schedule_envelope(
        [("0022500077", "20260118/LALGSW", 3)],
    )

    def fake_summary(game_id: str):
        assert game_id == "0022500077"
        return {
            "game_id": game_id,
            "game_date": "2026-01-18",
            "home_team_id": 1610612744,
            "away_team_id": 1610612747,
            "home_score": 120,
            "away_score": 115,
        }

    backfilled = detect_and_backfill_regular_season_gaps(
        db,
        season="2025-26",
        today=today,
        fetch_schedule_fn=lambda season: envelope,
        fetch_summary_fn=fake_summary,
        sleep_fn=None,
    )

    assert backfilled == ["0022500077"]
    row = db.query(GameLog).filter_by(game_id="0022500077").one()
    assert row.season == "2025-26"
    assert row.season_type == "Regular Season"
    assert row.game_date == date(2026, 1, 18)
    assert row.home_score == 120
    assert row.away_score == 115


def test_detector_is_idempotent(monkeypatch):
    _isolated_cache(monkeypatch)
    db = _make_session()
    _seed_teams(db)

    today = date(2026, 1, 20)
    envelope = _cdn_schedule_envelope(
        [("0022500077", "20260118/LALGSW", 3)],
    )
    summary = {
        "game_id": "0022500077",
        "game_date": "2026-01-18",
        "home_team_id": 1610612744,
        "away_team_id": 1610612747,
        "home_score": 120,
        "away_score": 115,
    }

    # First call inserts.
    first = detect_and_backfill_regular_season_gaps(
        db,
        season="2025-26",
        today=today,
        fetch_schedule_fn=lambda season: envelope,
        fetch_summary_fn=lambda gid: summary,
        sleep_fn=None,
    )
    assert first == ["0022500077"]

    # Second call finds it already present and inserts nothing.
    second = detect_and_backfill_regular_season_gaps(
        db,
        season="2025-26",
        today=today,
        fetch_schedule_fn=lambda season: envelope,
        fetch_summary_fn=lambda gid: summary,
        sleep_fn=None,
    )
    assert second == []
    assert db.query(GameLog).filter_by(game_id="0022500077").count() == 1


def test_detector_skips_when_per_game_summary_returns_none(monkeypatch):
    """If NBA's per-game summary contradicts the schedule (says not-Final
    or fails to fetch), the detector skips that game but continues probing
    the rest of the window.
    """
    _isolated_cache(monkeypatch)
    db = _make_session()
    _seed_teams(db)

    today = date(2026, 1, 20)
    envelope = _cdn_schedule_envelope(
        [
            ("0022500077", "20260118/LALGSW", 3),  # NBA says not-Final
            ("0022500078", "20260119/LALGSW", 3),  # NBA confirms Final
        ],
    )

    def fake_summary(game_id: str):
        if game_id == "0022500077":
            return None
        return {
            "game_id": game_id,
            "game_date": "2026-01-19",
            "home_team_id": 1610612744,
            "away_team_id": 1610612747,
            "home_score": 105,
            "away_score": 99,
        }

    backfilled = detect_and_backfill_regular_season_gaps(
        db,
        season="2025-26",
        today=today,
        fetch_schedule_fn=lambda season: envelope,
        fetch_summary_fn=fake_summary,
        sleep_fn=None,
    )

    assert backfilled == ["0022500078"]
    # Confirm the skipped one was not inserted.
    assert db.query(GameLog).filter_by(game_id="0022500077").count() == 0
