"""Sprint 98 Stream B3 — Tests for external-metric staleness helper.

Four guarantees:
  1. metric_age_days returns the integer day count for a well-formed meta.
  2. Malformed or missing meta returns None (not 0, not raises).
  3. metric_as_of returns the trimmed date string.
  4. staleness_snapshot flags ages above STALE_THRESHOLD_DAYS as stale.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.external_metric_staleness import (  # noqa: E402
    STALE_THRESHOLD_DAYS,
    metric_age_days,
    metric_as_of,
    staleness_snapshot,
)


def test_metric_age_days_basic():
    meta = {
        "epm": {"source": "DunksAndThrees", "as_of": "2026-04-15"},
        "lebron": {"source": "BBallIndex", "as_of": "2026-05-10"},
    }
    today = date(2026, 5, 11)
    assert metric_age_days(meta, "epm", now=today) == 26
    assert metric_age_days(meta, "lebron", now=today) == 1


def test_metric_age_days_handles_malformed_input():
    today = date(2026, 5, 11)
    assert metric_age_days(None, "epm", now=today) is None
    assert metric_age_days({}, "epm", now=today) is None
    assert metric_age_days({"epm": None}, "epm", now=today) is None
    assert metric_age_days({"epm": {"as_of": "not-a-date"}}, "epm", now=today) is None
    assert metric_age_days({"epm": {}}, "epm", now=today) is None
    # Missing metric returns None.
    assert metric_age_days({"lebron": {"as_of": "2026-05-10"}}, "epm", now=today) is None


def test_metric_as_of_returns_trimmed_date_string():
    meta = {"epm": {"as_of": "2026-04-15T00:00:00Z"}}
    assert metric_as_of(meta, "epm") == "2026-04-15"
    assert metric_as_of(meta, "rapm") is None
    assert metric_as_of(None, "epm") is None


def test_staleness_snapshot_flags_stale_threshold():
    today = date(2026, 5, 11)
    meta = {
        "fresh_metric": {"as_of": "2026-05-09"},  # 2 days old — not stale
        "borderline": {"as_of": (today - timedelta(days=STALE_THRESHOLD_DAYS)).isoformat()},  # exactly at threshold — not stale
        "stale_metric": {"as_of": "2026-04-01"},  # 40 days old — stale
        "missing_as_of": {"source": "x"},  # no as_of — dropped
    }
    snap = staleness_snapshot(meta, now=today)

    assert "fresh_metric" in snap
    assert snap["fresh_metric"]["stale"] is False
    assert snap["fresh_metric"]["age_days"] == 2

    assert "borderline" in snap
    assert snap["borderline"]["stale"] is False  # equal to threshold is not stale

    assert "stale_metric" in snap
    assert snap["stale_metric"]["stale"] is True
    assert snap["stale_metric"]["age_days"] == 40

    # Entries without as_of are dropped.
    assert "missing_as_of" not in snap
