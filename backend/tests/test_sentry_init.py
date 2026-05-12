"""Sprint 98 Stream A4 — Tests for Sentry init.

Three guarantees:
  1. Without SENTRY_DSN, init_sentry returns False (no-op behavior).
  2. With SENTRY_DSN, init_sentry returns True and calls sentry_sdk.init.
  3. Init is idempotent — second call returns True without re-initializing.
"""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils import sentry_init as sentry_init_module  # noqa: E402


def test_no_dsn_returns_false(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    sentry_init_module.reset_for_tests()
    assert sentry_init_module.init_sentry() is False


def test_empty_dsn_string_returns_false(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "   ")
    sentry_init_module.reset_for_tests()
    assert sentry_init_module.init_sentry() is False


def test_dsn_present_invokes_sentry_init(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://fakekey@sentry.example.com/1")
    monkeypatch.setenv("ENV", "test")
    sentry_init_module.reset_for_tests()

    init_calls = []

    def fake_init(**kwargs):
        init_calls.append(kwargs)

    monkeypatch.setattr("sentry_sdk.init", fake_init)

    result = sentry_init_module.init_sentry()
    assert result is True
    assert len(init_calls) == 1
    assert init_calls[0]["dsn"] == "https://fakekey@sentry.example.com/1"
    assert init_calls[0]["environment"] == "test"
    assert init_calls[0]["traces_sample_rate"] == 0.0


def test_init_is_idempotent(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://fakekey@sentry.example.com/1")
    sentry_init_module.reset_for_tests()

    init_calls = []
    monkeypatch.setattr("sentry_sdk.init", lambda **kwargs: init_calls.append(kwargs))

    first = sentry_init_module.init_sentry()
    second = sentry_init_module.init_sentry()
    assert first is True
    assert second is True
    # Second call must NOT re-invoke sentry_sdk.init.
    assert len(init_calls) == 1
