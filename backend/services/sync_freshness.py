"""Sprint 98 — Generalized sync-freshness markers.

Every periodic sync step writes a marker via :func:`record_sync`. The marker
goes to ``cache.db`` at key ``sync:<entity>:last`` with a 24h TTL.
``/api/health/sync-status`` reads the registry of known entities and reports
whether each run is fresh relative to its expected cadence.

The Sprint 97 ``sync_gaps:playoff_backfill:last`` marker is preserved for
back-compat — the endpoint still returns it under ``playoff_backfill_last_24h``
in addition to the new ``syncs`` map.

Failures inside :func:`record_sync` are non-fatal: the caller logs and
continues, matching the Sprint 97 backfill pattern. A failed marker write
must never break a working sync job.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from data.cache import CacheManager

logger = logging.getLogger(__name__)


# Entity name → expected cadence between successful runs, in minutes.
# ``stale`` flips to True when ``now - ran_at > cadence * 2`` — a generous
# buffer so a single missed tick doesn't trip the alert.
KNOWN_SYNC_ENTITIES: Dict[str, int] = {
    # Post-game tier (every 15 min during active game windows).
    "playoff_backfill": 15,
    "regular_season_gap": 15,
    "bracket_refresh": 15,
    "injuries": 15,
    "playoff_finals_today": 15,
    "team_splits_playoff": 15,
    # Daily tier (6am UTC full run).
    "warehouse_jobs": 1440,
    "season_stats": 1440,
    "team_season_stats": 1440,
    "team_general_splits": 1440,
    "team_shooting_splits": 1440,
    "player_general_splits": 1440,
    "play_type_stats": 1440,
    "standings": 1440,
    "hustle_player": 1440,
    "hustle_team": 1440,
    "team_tracking": 1440,
    "role_expansion": 1440,
    "streaks_milestones": 1440,
    "injury_history": 1440,
    "award_modifiers": 1440,
    "cache_db_cleanup": 1440,
    "shot_charts_queue": 1440,
    # Weekly tier (Sunday).
    "salaries": 10080,
    "draft_prospects": 10080,
    "player_tracking": 10080,
    # 3-hour tier (Sprint 99 — Cloudflare cache warmer for /api/mvp/race).
    # Cadence is 180 min; stale boundary at 2x (6h) so a single missed
    # tick doesn't trip the alert.
    "mvp_race_warm": 180,
}

MARKER_TTL_SECONDS = 86400  # 24h — matches Sprint 97 convention
STALE_CADENCE_MULTIPLIER = 2  # stale = age > expected_cadence * 2


def _marker_key(entity: str) -> str:
    return f"sync:{entity}:last"


def record_sync(
    entity: str,
    count: int = 0,
    source: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    """Write a freshness marker for a sync entity.

    Called by every sync step on both success and failure. ``count`` is the
    number of rows / records the step touched; ``error`` is the truncated
    exception string when the step failed (``None`` on success). ``source``
    is a free-form tag identifying the caller (e.g. ``"daily_sync.sh"``).

    Idempotent — overwrites any prior marker. Failures here are non-fatal:
    the caller logs and continues. Unknown entities are still recorded so
    new sync types surface in the response without a code change.
    """
    try:
        payload = {
            "ran_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "count": count,
            "source": source,
            "error": error,
        }
        CacheManager.set(_marker_key(entity), payload, ttl_seconds=MARKER_TTL_SECONDS)
    except Exception as exc:  # noqa: BLE001 — observability writes never propagate
        logger.warning("failed to record sync marker for %s: %s", entity, exc)


def read_sync(entity: str) -> Optional[Dict]:
    """Read the most recent marker for an entity, or ``None`` if missing/expired."""
    try:
        return CacheManager.peek(_marker_key(entity))
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to read sync marker for %s: %s", entity, exc)
        return None


def is_stale(entity: str, ran_at_iso: Optional[str]) -> bool:
    """Decide whether the last run is stale relative to the entity's cadence.

    Returns True when:
        - No marker exists (``ran_at_iso`` is ``None``), OR
        - The marker's timestamp is older than ``cadence * STALE_CADENCE_MULTIPLIER``.

    Unknown entities (not in ``KNOWN_SYNC_ENTITIES``) are never flagged stale
    so ad-hoc sync types don't show as alerting-state by default.
    """
    cadence = KNOWN_SYNC_ENTITIES.get(entity)
    if cadence is None:
        # Unknown entity — we have no expectation, never flag stale.
        return False
    if ran_at_iso is None:
        return True
    try:
        ran_at = datetime.fromisoformat(ran_at_iso.replace("Z", "+00:00"))
    except ValueError:
        return True
    if ran_at.tzinfo is None:
        ran_at = ran_at.replace(tzinfo=timezone.utc)
    age_min = (datetime.now(timezone.utc) - ran_at).total_seconds() / 60.0
    return age_min > cadence * STALE_CADENCE_MULTIPLIER


def read_all_syncs() -> Dict[str, Dict]:
    """Return a map of every known entity to its marker state.

    Entities with no marker still appear with ``ran_at=None`` and
    ``stale=True`` so consumers can see uncovered jobs without
    inspecting the cache directly.
    """
    out: Dict[str, Dict] = {}
    for entity, cadence_min in KNOWN_SYNC_ENTITIES.items():
        marker = read_sync(entity) or {}
        ran_at = marker.get("ran_at")
        out[entity] = {
            "ran_at": ran_at,
            "count": marker.get("count", 0),
            "source": marker.get("source"),
            "error": marker.get("error"),
            "expected_cadence_min": cadence_min,
            "stale": is_stale(entity, ran_at),
        }
    return out


__all__ = [
    "KNOWN_SYNC_ENTITIES",
    "MARKER_TTL_SECONDS",
    "is_stale",
    "read_all_syncs",
    "read_sync",
    "record_sync",
]
