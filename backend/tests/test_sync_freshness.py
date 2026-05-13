"""Sprint 98 — Tests for the generalized sync-freshness markers.

Four guarantees:
  1. record_sync writes a payload at the expected cache key, retrievable
     via CacheManager.peek.
  2. is_stale flips to True when the marker's age exceeds cadence * 2
     and False when within window. Missing markers (None) are always stale.
  3. read_all_syncs returns the full KNOWN_SYNC_ENTITIES map with each
     entity's marker state, including entities that have never run.
  4. Marker write failures are non-fatal — record_sync swallows
     CacheManager exceptions so a broken cache doesn't break syncs.
"""
from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _isolated_cache(monkeypatch):
    """Point CacheManager at a fresh sqlite file so tests don't share state."""
    from data import cache as cache_module

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setattr(cache_module.CacheManager, "_db_path", tmp.name)
    monkeypatch.setattr(cache_module.CacheManager, "_initialized", False)
    cache_module.CacheManager._stats = {"hit": 0, "miss": 0, "expired": 0}
    return tmp.name


def test_record_sync_writes_marker_readable_via_peek(monkeypatch):
    _isolated_cache(monkeypatch)
    from data.cache import CacheManager
    from services.sync_freshness import record_sync

    record_sync("playoff_backfill", count=3, source="post_game_cron")
    raw = CacheManager.peek("sync:playoff_backfill:last")
    assert raw is not None
    assert raw["count"] == 3
    assert raw["source"] == "post_game_cron"
    assert raw["error"] is None
    # ran_at must be an ISO8601 string ending in Z
    assert raw["ran_at"].endswith("Z")
    datetime.fromisoformat(raw["ran_at"].replace("Z", "+00:00"))


def test_is_stale_respects_cadence_window(monkeypatch):
    _isolated_cache(monkeypatch)
    from services.sync_freshness import is_stale

    now = datetime.now(timezone.utc)

    # playoff_backfill cadence is 15 min; stale boundary is 30 min.
    fresh = (now - timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    on_edge = (now - timedelta(minutes=25)).isoformat().replace("+00:00", "Z")
    expired = (now - timedelta(minutes=45)).isoformat().replace("+00:00", "Z")

    assert is_stale("playoff_backfill", fresh) is False
    assert is_stale("playoff_backfill", on_edge) is False
    assert is_stale("playoff_backfill", expired) is True

    # Missing marker is always stale.
    assert is_stale("playoff_backfill", None) is True

    # Unknown entities never flag stale.
    assert is_stale("totally_unknown_entity_xyz", None) is False


def test_read_all_syncs_returns_full_registry_including_uncovered(monkeypatch):
    _isolated_cache(monkeypatch)
    from services.sync_freshness import (
        KNOWN_SYNC_ENTITIES,
        read_all_syncs,
        record_sync,
    )

    record_sync("season_stats", count=595, source="daily_sync")

    snapshot = read_all_syncs()

    # Every known entity is in the map.
    assert set(snapshot.keys()) == set(KNOWN_SYNC_ENTITIES.keys())

    # The entity we recorded has a populated marker.
    ss = snapshot["season_stats"]
    assert ss["count"] == 595
    assert ss["source"] == "daily_sync"
    assert ss["stale"] is False
    assert ss["expected_cadence_min"] == 1440

    # An entity we never recorded shows as uncovered + stale.
    untouched = snapshot["salaries"]
    assert untouched["ran_at"] is None
    assert untouched["count"] == 0
    assert untouched["stale"] is True
    assert untouched["expected_cadence_min"] == 10080


def test_record_sync_swallows_cache_failures(monkeypatch):
    """If CacheManager.set raises, record_sync must NOT propagate the error."""
    from data import cache as cache_module
    from services.sync_freshness import record_sync

    def boom(*args, **kwargs):  # noqa: ANN001
        raise RuntimeError("simulated cache failure")

    monkeypatch.setattr(cache_module.CacheManager, "set", classmethod(lambda cls, *a, **kw: boom()))

    # Must not raise — the contract is "fail open" so sync jobs aren't blocked.
    record_sync("playoff_backfill", count=1, source="test")
