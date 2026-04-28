"""Season-phase auto-detection (Sprint 73).

Looks at the wall-clock month and any recent playoff `GameLog` rows to decide
which phase the league is in (offseason / regular season / play-in / each
playoff round / finals) and tags the highest active `PlayoffSeries` round so
that callers can pull the right context.

A 5-minute wall-clock cache keyed by `(season, today's date)` prevents the
hot path (e.g. nba_client cache TTL lookups) from hammering the DB.

Usage::

    phase_response = get_current_phase()              # opens its own session
    phase_response = get_current_phase(db)            # explicit session

    if _active_phase_is_playoffs():
        ...
"""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta
from typing import Dict, Optional, Tuple

from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import GameLog
from models.season_phase import SeasonPhase, SeasonPhaseResponse


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_CACHE_TTL_SECONDS = 300  # 5 minutes
_cache: Dict[Tuple[str, str], Tuple[float, SeasonPhaseResponse]] = {}


def _cache_get(key: Tuple[str, str]) -> Optional[SeasonPhaseResponse]:
    entry = _cache.get(key)
    if entry is None:
        return None
    cached_at, value = entry
    if time.time() - cached_at > _CACHE_TTL_SECONDS:
        _cache.pop(key, None)
        return None
    return value


def _cache_set(key: Tuple[str, str], value: SeasonPhaseResponse) -> None:
    _cache[key] = (time.time(), value)


def _clear_cache() -> None:
    """Test-friendly hook to flush the in-memory cache."""
    _cache.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Months (1-indexed) that map to each fixed phase when no DB signal is present.
_OFFSEASON_MONTHS = {7, 8, 9}
_PLAYOFF_WINDOW_MONTHS = {4, 5, 6}


def _active_season_for_today(today: date) -> str:
    """Compute the canonical "YYYY-YY" season string for a given date.

    The NBA season "2025-26" runs from October 2025 through June 2026, with the
    rollover to the next season happening in August (preseason / new league
    year). Months Aug-Dec belong to the season that *starts* in that calendar
    year; Jan-Jul belong to the season that *ended* in that calendar year.
    """
    if today.month >= 8:
        start_year = today.year
    else:
        start_year = today.year - 1
    return f"{start_year}-{str((start_year + 1) % 100).zfill(2)}"


def _round_label(phase: SeasonPhase) -> Optional[str]:
    return {
        "regular_season": "Regular Season",
        "playoff_play_in": "Play-In",
        "playoff_round_1": "First Round",
        "playoff_round_2": "Conference Semifinals",
        "conference_finals": "Conference Finals",
        "finals": "Finals",
        "offseason": "Offseason",
    }.get(phase)


def _phase_for_round(round_value: int) -> Optional[SeasonPhase]:
    return {
        1: "playoff_round_1",
        2: "playoff_round_2",
        3: "conference_finals",
        4: "finals",
    }.get(round_value)


def _has_recent_playoff_games(db: Session, today: date) -> bool:
    """Return True if at least one playoff GameLog row exists in the last 7 days."""
    cutoff = today - timedelta(days=7)
    try:
        row = (
            db.query(GameLog.game_id)
            .filter(GameLog.season_type == "Playoffs")
            .filter(GameLog.game_date >= cutoff)
            .filter(GameLog.game_date <= today)
            .first()
        )
    except Exception:
        return False
    return row is not None


def _max_active_playoff_round(db: Session, season: str) -> Optional[int]:
    """Highest `round` for the season with status in (scheduled, active).

    Falls back to the highest round of any series for the season when nothing
    is scheduled/active (e.g. all rounds are closed already).
    """
    try:
        # Local import — `PlayoffSeries` is part of EA1's parallel work and
        # may not be present on every checkout's models module.
        from db.models import PlayoffSeries  # type: ignore
    except Exception:
        return None

    try:
        active_round = (
            db.query(PlayoffSeries.round)
            .filter(PlayoffSeries.season == season)
            .filter(PlayoffSeries.status.in_(("scheduled", "active")))
            .order_by(PlayoffSeries.round.desc())
            .first()
        )
        if active_round is not None and active_round[0] is not None:
            return int(active_round[0])

        any_round = (
            db.query(PlayoffSeries.round)
            .filter(PlayoffSeries.season == season)
            .order_by(PlayoffSeries.round.desc())
            .first()
        )
        if any_round is not None and any_round[0] is not None:
            return int(any_round[0])
    except Exception:
        return None
    return None


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def _detect_phase(db: Session, today: date) -> SeasonPhase:
    """Pure detection logic with no caching, called by both public entry points."""
    month = today.month

    # Offseason (July–September)
    if month in _OFFSEASON_MONTHS:
        return "offseason"

    season = _active_season_for_today(today)
    in_playoff_window = month in _PLAYOFF_WINDOW_MONTHS
    has_playoff_games = _has_recent_playoff_games(db, today) if in_playoff_window else False

    if in_playoff_window and has_playoff_games:
        active_round = _max_active_playoff_round(db, season)
        phase = _phase_for_round(active_round) if active_round else None
        if phase is not None:
            return phase
        # Recent playoff games but no series rows yet — must still be playoffs.
        return "playoff_round_1"

    # Early April with no games yet often corresponds to the play-in tournament.
    if month == 4 and not has_playoff_games:
        if today.day <= 20:
            return "playoff_play_in"
        # Late April with no playoff games is an unusual signal — fall back to
        # checking for an active series anyway, then default to round 1.
        active_round = _max_active_playoff_round(db, season)
        phase = _phase_for_round(active_round) if active_round else None
        if phase is not None:
            return phase
        return "playoff_round_1"

    # May–June with no recent playoff games: still postseason; pull whatever
    # round the bracket table reports.
    if in_playoff_window:
        active_round = _max_active_playoff_round(db, season)
        phase = _phase_for_round(active_round) if active_round else None
        if phase is not None:
            return phase
        return "playoff_round_1"

    return "regular_season"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_current_phase(db: Optional[Session] = None) -> SeasonPhaseResponse:
    """Return the current league phase, cached for 5 minutes per (season, day)."""
    today = date.today()
    season = _active_season_for_today(today)
    cache_key = (season, today.isoformat())

    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    owns_session = False
    if db is None:
        db = SessionLocal()
        owns_session = True

    try:
        phase = _detect_phase(db, today)
    finally:
        if owns_session:
            db.close()

    response = SeasonPhaseResponse(
        phase=phase,
        season=season,
        round_label=_round_label(phase),
        last_updated_at=datetime.utcnow(),
    )
    _cache_set(cache_key, response)
    return response


def _active_phase_is_playoffs() -> bool:
    """Sync helper used by `nba_client._cache_ttl_for_season` to short-circuit
    the regular-season cache TTL during the postseason window.
    """
    try:
        response = get_current_phase()
    except Exception:
        # If we cannot read the DB, fall back to the wall-clock window so the
        # caller still gets a sensible default.
        month = date.today().month
        return month in _PLAYOFF_WINDOW_MONTHS
    return response.phase.startswith("playoff") or response.phase == "finals" or response.phase == "conference_finals"
