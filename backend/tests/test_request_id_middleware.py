"""Sprint 98 Stream A3 — Tests for request-ID middleware + structlog binding.

Three guarantees:
  1. Every response gets an X-Request-ID header.
  2. A client-supplied X-Request-ID is honored (round-trips on the response).
  3. Inbound IDs longer than 64 chars are truncated to prevent abuse.
"""
from __future__ import annotations

from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _make_app():
    from utils.logging_setup import reset_for_tests
    from utils.request_id_middleware import RequestIDMiddleware

    reset_for_tests()
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/echo")
    def echo():
        return {"ok": True}

    return app


def test_response_always_carries_request_id_header():
    client = TestClient(_make_app())
    resp = client.get("/echo")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    rid = resp.headers["X-Request-ID"]
    # UUID4 form: 36 chars with 4 dashes.
    assert len(rid) == 36
    assert rid.count("-") == 4


def test_inbound_request_id_is_echoed():
    client = TestClient(_make_app())
    inbound = "client-supplied-trace-abc123"
    resp = client.get("/echo", headers={"X-Request-ID": inbound})
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"] == inbound


def test_inbound_request_id_is_truncated_at_64_chars():
    client = TestClient(_make_app())
    long_inbound = "x" * 200
    resp = client.get("/echo", headers={"X-Request-ID": long_inbound})
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"] == "x" * 64
