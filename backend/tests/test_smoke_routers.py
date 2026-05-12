"""Sprint 98 Stream D2 — Cross-router smoke tests.

Each test hits one canonical endpoint per router and asserts a sane
status code. Goal: catch wire-up regressions (missing imports, route
prefix typos, broken dependency injection) BEFORE production deploy.

These tests don't verify response correctness — just that the route is
reachable, returns a documented status (200 for empty-DB-safe routes,
404 for routes that need data we haven't seeded, 422 for routes that
expect query params). The full backend suite covers correctness via
service-level tests.

The ``client`` fixture in conftest.py provides a TestClient against
the real FastAPI app with an in-memory DB and rate-limit / admin-key
disabled.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Endpoints that succeed against an empty DB (return empty lists / null).
# ---------------------------------------------------------------------------
SMOKE_GET_200 = [
    "/api/health",
    "/api/health/cache-stats",
    "/api/health/sync-status",
    "/api/season-phase",
    "/api/methodology",
    "/api/leaderboards/seasons",
    "/api/leaderboards/teams?season=2024-25",
    "/api/teams",
    "/api/standings?season=2024-25",
    "/api/playoffs/today?season=2024-25",
    "/api/playoffs/bracket?season=2024-25",
]


# ---------------------------------------------------------------------------
# Endpoints that legitimately 404 against an empty DB.
# These tests confirm the route is registered + the not-found path doesn't
# 500. Pass a known-bad id so the response is deterministic.
# ---------------------------------------------------------------------------
SMOKE_GET_404 = [
    "/api/teams/ZZZ",
    "/api/playoffs/series/nonexistent-series-id",
    "/api/games/00000000",
]


# ---------------------------------------------------------------------------
# Endpoints that require query params; missing-param 422 confirms the
# route is wired and FastAPI is enforcing validation.
# ---------------------------------------------------------------------------
SMOKE_GET_422 = [
    "/api/leaderboards",  # missing required `season`
    "/api/shotchart/1234",  # missing required `season`
]


def test_smoke_get_200_endpoints(client):
    """All these should return 200 even against an empty DB."""
    failures = []
    for path in SMOKE_GET_200:
        resp = client.get(path)
        if resp.status_code != 200:
            failures.append((path, resp.status_code, resp.text[:200]))
    assert not failures, f"non-200 responses: {failures}"


def test_smoke_get_404_endpoints(client):
    """All these should return 404 (not 500) when the requested entity doesn't exist."""
    failures = []
    for path in SMOKE_GET_404:
        resp = client.get(path)
        if resp.status_code != 404:
            failures.append((path, resp.status_code, resp.text[:200]))
    assert not failures, f"expected 404, got other: {failures}"


def test_smoke_get_422_endpoints(client):
    """Routes that require query params return 422 when missing them."""
    failures = []
    for path in SMOKE_GET_422:
        resp = client.get(path)
        if resp.status_code != 422:
            failures.append((path, resp.status_code, resp.text[:200]))
    assert not failures, f"expected 422, got other: {failures}"


def test_every_request_carries_request_id(client):
    """Sprint 98 A3 middleware applies to every route."""
    resp = client.get("/api/health")
    assert "X-Request-ID" in resp.headers
    resp2 = client.get("/api/health")
    # Each request gets a unique request-ID.
    assert resp.headers["X-Request-ID"] != resp2.headers["X-Request-ID"]


# Admin-key gating is covered by tests/test_api_hardening.py which builds
# its own minimal app, avoiding cross-test config/main module reload races
# that this smoke file's `client` fixture incurs.
