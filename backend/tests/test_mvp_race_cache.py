"""Sprint 99 — Tests for the MVP race in-process TTL cache."""
from __future__ import annotations

import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.mvp_race_cache import TTLCache, cache_key  # noqa: E402


def test_get_or_compute_caches_under_ttl():
    cache = TTLCache(ttl_seconds=60)
    call_count = {"n": 0}

    def compute():
        call_count["n"] += 1
        return f"result-{call_count['n']}"

    key = ("test", "key")
    assert cache.get_or_compute(key, compute) == "result-1"
    assert cache.get_or_compute(key, compute) == "result-1"
    assert cache.get_or_compute(key, compute) == "result-1"
    assert call_count["n"] == 1
    snap = cache.snapshot()
    assert snap["hits"] == 2
    assert snap["computes"] == 1
    assert snap["entries"] == 1


def test_get_or_compute_recomputes_after_ttl():
    cache = TTLCache(ttl_seconds=0)  # immediate expiry
    call_count = {"n": 0}

    def compute():
        call_count["n"] += 1
        return f"v{call_count['n']}"

    key = ("k",)
    v1 = cache.get_or_compute(key, compute)
    # Force a clock tick.
    time.sleep(0.01)
    v2 = cache.get_or_compute(key, compute)
    assert v1 == "v1"
    assert v2 == "v2"
    assert cache.snapshot()["computes"] == 2


def test_invalidate_drops_entries():
    cache = TTLCache(ttl_seconds=60)
    cache.get_or_compute(("a",), lambda: 1)
    cache.get_or_compute(("b",), lambda: 2)
    cache.get_or_compute(("c",), lambda: 3)
    assert cache.snapshot()["entries"] == 3
    n = cache.invalidate()
    assert n == 3
    assert cache.snapshot()["entries"] == 0


def test_cache_key_includes_all_dimensions():
    a = cache_key("2025-26", 10, 20, None, None)
    b = cache_key("2025-26", 10, 20, None, None)
    c = cache_key("2025-26", 10, 20, "G", None)
    d = cache_key("2024-25", 10, 20, None, None)
    e = cache_key("2025-26", 25, 20, None, None)
    f = cache_key("2025-26", 10, 20, None, None, "Playoffs")
    assert a == b
    assert a != c
    assert a != d
    assert a != e
    assert a != f
