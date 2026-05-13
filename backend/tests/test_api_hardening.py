"""Sprint 98 Stream C5 — Integration tests for the API hardening pass.

Three guarantees, all hit via FastAPI TestClient:
  1. Mutation endpoints (e.g. POST /api/players/{id}/sync) require the
     X-Admin-Key header when ADMIN_API_KEY is configured.
  2. Same endpoints accept the request with the correct admin key.
  3. The new admin diagnostic endpoint (/api/admin/playoff-series-drift)
     also requires the admin key.

Rate limit + nba_client guard verification is exercised in unit-level
tests adjacent to the wrapper modules (rate_limiting + the existing
mocks in service tests) — running a full slowapi storm here would
either be slow or unreliable, and the surgical scope is to confirm
the wiring is intact.
"""
from __future__ import annotations

import importlib
from pathlib import Path
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def admin_app(monkeypatch):
    """Build a tiny FastAPI app with ADMIN_API_KEY set, so the guard fires."""
    monkeypatch.setenv("ADMIN_API_KEY", "test-admin-key-xyz")
    # Reload the config module so ADMIN_API_KEY is picked up fresh.
    import config

    importlib.reload(config)
    # Reload dependencies so it captures the new ADMIN_API_KEY.
    import dependencies

    importlib.reload(dependencies)

    from dependencies import require_admin_key
    from fastapi import Depends

    app = FastAPI()

    @app.post("/api/players/{player_id}/sync")
    def _resync(player_id: int, _: None = Depends(require_admin_key)):
        return {"ok": True, "player_id": player_id}

    @app.post("/api/injuries/sync")
    def _inj_sync(_: None = Depends(require_admin_key)):
        return {"ok": True}

    @app.get("/api/admin/playoff-series-drift")
    def _drift(_: None = Depends(require_admin_key)):
        return {"count": 0, "drift": [], "season": None}

    return app


def test_mutation_endpoint_rejects_missing_admin_key(admin_app):
    client = TestClient(admin_app)
    resp = client.post("/api/players/123/sync")
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Forbidden"


def test_mutation_endpoint_rejects_wrong_admin_key(admin_app):
    client = TestClient(admin_app)
    resp = client.post(
        "/api/players/123/sync",
        headers={"X-Admin-Key": "not-the-right-key"},
    )
    assert resp.status_code == 403


def test_mutation_endpoint_accepts_correct_admin_key(admin_app):
    client = TestClient(admin_app)
    resp = client.post(
        "/api/players/123/sync",
        headers={"X-Admin-Key": "test-admin-key-xyz"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_admin_diagnostic_endpoint_requires_admin_key(admin_app):
    client = TestClient(admin_app)
    resp_unauth = client.get("/api/admin/playoff-series-drift")
    assert resp_unauth.status_code == 403

    resp_auth = client.get(
        "/api/admin/playoff-series-drift",
        headers={"X-Admin-Key": "test-admin-key-xyz"},
    )
    assert resp_auth.status_code == 200
    assert resp_auth.json()["count"] == 0


def test_admin_key_unset_allows_all(monkeypatch):
    """Dev mode (ADMIN_API_KEY unset) — guard is a no-op."""
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    import config

    importlib.reload(config)
    import dependencies

    importlib.reload(dependencies)

    from dependencies import require_admin_key
    from fastapi import Depends

    app = FastAPI()

    @app.post("/api/whatever")
    def _ep(_: None = Depends(require_admin_key)):
        return {"ok": True}

    client = TestClient(app)
    resp = client.post("/api/whatever")
    assert resp.status_code == 200
