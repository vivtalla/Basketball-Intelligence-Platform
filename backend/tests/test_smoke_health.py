"""Sprint 98 Stream D2 — Smoke tests for the health endpoints.

Confirms wiring is intact end-to-end. Each test hits the endpoint and
asserts 200 + the documented response shape. These are the highest-
priority smoke tests since UptimeRobot polls them in production.
"""
from __future__ import annotations


def test_health_returns_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_cache_stats_returns_counters(client):
    resp = client.get("/api/health/cache-stats")
    assert resp.status_code == 200
    body = resp.json()
    # Required keys per Sprint 88.
    for key in ("hit", "miss", "expired", "total", "row_count", "size_bytes"):
        assert key in body, f"missing key {key} in response"


def test_health_sync_status_returns_three_sections(client):
    """Sprint 98 expansion — must include legacy + new sections."""
    resp = client.get("/api/health/sync-status")
    assert resp.status_code == 200
    body = resp.json()

    assert "playoff_backfill_last_24h" in body  # legacy Sprint 97 key
    assert "syncs" in body  # new Sprint 98 map
    assert "cache_db" in body  # new Sprint 98 cache-size snapshot

    # `syncs` is a dict of entity → state.
    assert isinstance(body["syncs"], dict)
    # Every entity's record has the expected shape.
    for entity, state in body["syncs"].items():
        for key in ("ran_at", "count", "stale", "expected_cadence_min"):
            assert key in state, f"sync entity {entity} missing key {key}"

    # cache_db snapshot.
    for key in ("size_bytes", "size_kb", "row_count"):
        assert key in body["cache_db"]


def test_health_sync_status_carries_request_id(client):
    """The Sprint 98 A3 request-ID middleware must echo a header on every
    response from the production app, including the health endpoints.
    """
    resp = client.get("/api/health/sync-status")
    assert "X-Request-ID" in resp.headers
    rid = resp.headers["X-Request-ID"]
    assert len(rid) >= 1
