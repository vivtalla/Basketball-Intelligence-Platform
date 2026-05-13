"""Sprint 99 — In-process TTL cache for build_mvp_race results.

The MVP race composite costs ~12s on cold cache because it touches PBP
events, game logs, calibration, and per-candidate deep profiles. Cloudflare
edge-caches the response for 4h, which protects the warm steady state — but
the user who arrives right after a deploy or right after TTL expiry pays
the full origin cost.

This cache adds a second layer inside each gunicorn worker: a TTL'd dict
keyed on the request shape. Once a worker has computed a race for a given
(season, top, min_gp, position, profile, season_type) tuple, every
subsequent caller within that worker gets the cached MvpRaceResponse for
4h — even when Cloudflare misses.

Notes:
- Per-process. Two gunicorn workers each maintain their own cache; the
  first request to each worker still pays cold. The cron warmer
  (`scripts/warm_mvp_cache.py`) handles the cross-worker miss by hitting
  the endpoint via the public DNS multiple times.
- Threadsafe via a single lock. The compute is held inside the lock so
  concurrent requests for the same key deduplicate.
- TTL=14400s matches the Cloudflare ``max-age=14400`` on the response.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 14400  # 4 hours; matches Cloudflare cache-control header


class TTLCache:
    """Tiny TTL cache. Single-process, threadsafe, compute-under-lock."""

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._store: Dict[Tuple, Tuple[float, object]] = {}
        self._lock = threading.Lock()
        self.stats = {"hits": 0, "misses": 0, "computes": 0}

    def get_or_compute(self, key: Tuple, compute_fn: Callable[[], object]) -> object:
        now = time.time()
        # Fast path — try the cache without holding the lock during fetch.
        cached = self._store.get(key)
        if cached is not None:
            stored_at, value = cached
            if now - stored_at < self._ttl:
                self.stats["hits"] += 1
                return value

        # Slow path — hold the lock so concurrent requests for the same key
        # don't both compute. Re-check under the lock to handle the race.
        with self._lock:
            cached = self._store.get(key)
            if cached is not None:
                stored_at, value = cached
                if now - stored_at < self._ttl:
                    self.stats["hits"] += 1
                    return value
            self.stats["misses"] += 1
            self.stats["computes"] += 1
            value = compute_fn()
            self._store[key] = (time.time(), value)
            return value

    def invalidate(self) -> int:
        """Drop everything. Returns the prior entry count."""
        with self._lock:
            n = len(self._store)
            self._store.clear()
            return n

    def snapshot(self) -> Dict:
        with self._lock:
            return {
                "ttl_seconds": self._ttl,
                "entries": len(self._store),
                "keys": list(self._store.keys()),
                **self.stats,
            }


# Singleton for the MVP race result. Other endpoints can mint their own
# TTLCache instances if they want the same pattern.
mvp_race_cache = TTLCache(ttl_seconds=DEFAULT_TTL_SECONDS)


def cache_key(
    season: str,
    top: int,
    min_gp: int,
    position: Optional[str],
    profile: Optional[str],
    season_type: str = "Regular Season",
) -> Tuple:
    """Stable key for the (season, top, min_gp, position, profile, season_type) shape."""
    return ("mvp_race", season, top, min_gp, position or "", profile or "", season_type)


__all__ = ["TTLCache", "mvp_race_cache", "cache_key", "DEFAULT_TTL_SECONDS"]
