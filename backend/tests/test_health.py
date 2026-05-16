"""Sprint 100 (Stream D) — tests for memory observability on /api/health.

These exist alongside the Sprint 98 smoke tests; they only cover the new
Stream D surface area (memory snapshot + /api/health/memory threshold).
"""

from __future__ import annotations

from unittest import mock


def test_health_includes_memory(client):
    """/api/health should always expose a memory snapshot."""
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "memory" in body
    assert body["workers"] == 1


def test_health_memory_ok_under_low_usage(client):
    """/api/health/memory returns ok when system + swap are well under limits."""
    snapshot = {
        "process_rss_mb": 320.0,
        "system_total_mb": 1989.0,
        "system_available_mb": 900.0,
        "system_used_pct": 50.0,
        "swap_total_mb": 2048.0,
        "swap_used_mb": 100.0,
        "swap_used_pct": 5.0,
    }
    with mock.patch("utils.memory_stats.get_memory_snapshot", return_value=snapshot):
        res = client.get("/api/health/memory")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["swap_used_pct"] == 5.0
    assert body["system_used_pct"] == 50.0


def test_health_memory_warning_at_60_pct_swap(client):
    snapshot = {
        "system_used_pct": 70.0,
        "swap_used_pct": 70.0,
    }
    with mock.patch("utils.memory_stats.get_memory_snapshot", return_value=snapshot):
        res = client.get("/api/health/memory")
    assert res.json()["status"] == "warning"


def test_health_memory_critical_at_high_swap(client):
    """Swap > 85% should escalate to critical so UptimeRobot pages."""
    snapshot = {
        "system_used_pct": 80.0,
        "swap_used_pct": 90.0,
    }
    with mock.patch("utils.memory_stats.get_memory_snapshot", return_value=snapshot):
        res = client.get("/api/health/memory")
    assert res.status_code == 200
    assert res.json()["status"] == "critical"


def test_health_memory_critical_at_high_system_pct(client):
    """system_used_pct > 95 is also critical even if swap looks fine."""
    snapshot = {
        "system_used_pct": 96.0,
        "swap_used_pct": 30.0,
    }
    with mock.patch("utils.memory_stats.get_memory_snapshot", return_value=snapshot):
        res = client.get("/api/health/memory")
    assert res.json()["status"] == "critical"


def test_health_memory_graceful_when_psutil_unavailable(client):
    """Endpoint must stay 200 with status=unknown when psutil import fails."""
    with mock.patch(
        "utils.memory_stats.get_memory_snapshot",
        return_value={"error": "unavailable"},
    ):
        res = client.get("/api/health/memory")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "unknown"
    assert body["error"] == "unavailable"


def test_memory_snapshot_returns_dict():
    """Direct unit test — exercises the real psutil path when available."""
    from utils.memory_stats import get_memory_snapshot

    snap = get_memory_snapshot()
    assert isinstance(snap, dict)
    # When psutil IS available we expect at least one of the standard keys.
    # When it's not, we expect the explicit error sentinel.
    if "error" not in snap:
        assert "system_total_mb" in snap or "process_rss_mb" in snap


def test_classify_thresholds_edge_cases():
    """classify_memory_status — boundary conditions."""
    from utils.memory_stats import classify_memory_status

    assert classify_memory_status({"swap_used_pct": 0, "system_used_pct": 50}) == "ok"
    assert classify_memory_status({"swap_used_pct": 60.1, "system_used_pct": 50}) == "warning"
    assert classify_memory_status({"swap_used_pct": 85.1, "system_used_pct": 50}) == "critical"
    assert classify_memory_status({"swap_used_pct": 10, "system_used_pct": 95.1}) == "critical"
    assert classify_memory_status({"error": "unavailable"}) == "unknown"
