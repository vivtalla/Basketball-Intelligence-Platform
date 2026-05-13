"""Sprint 98 Stream A4 — Sentry error tracking.

Free-tier (5K events/mo) error capture for FastAPI + cron scripts.
Gated on the ``SENTRY_DSN`` environment variable: unset means no-op,
so dev environments and tests are unaffected.

Tags every event with the ``BIP_RUN_ID`` env var when present so cron-tick
errors can be filtered alongside the structlog ``run_id`` context.

Usage — automatic when configure_logging() is called (logging_setup.py
invokes init_sentry()). If you need to init Sentry without the full
logging setup, call init_sentry() directly:

    from utils.sentry_init import init_sentry
    init_sentry()
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_INITIALIZED = False


def init_sentry(dsn: Optional[str] = None) -> bool:
    """Initialize Sentry if SENTRY_DSN is set.

    Args:
        dsn: optional override; otherwise reads ``SENTRY_DSN`` from env.

    Returns:
        True if Sentry is now active, False if no DSN was provided.

    Idempotent — calling twice is a no-op. Tags the active scope with the
    ``BIP_RUN_ID`` env var when present.
    """
    global _INITIALIZED
    if _INITIALIZED:
        return True

    effective_dsn = (dsn or os.getenv("SENTRY_DSN", "")).strip()
    if not effective_dsn:
        return False

    try:
        import sentry_sdk
    except ImportError:
        logger.warning("SENTRY_DSN set but sentry-sdk not installed; skipping init")
        return False

    environment = os.getenv("ENV", "dev")
    sentry_sdk.init(
        dsn=effective_dsn,
        environment=environment,
        # No performance / trace sampling — Sprint 98 only wants error capture.
        # Bumping this from 0.0 means paying for transactions, which the free
        # tier (5K events/mo total) doesn't have headroom for.
        traces_sample_rate=0.0,
        # Drop noisy default integrations that capture log records — we
        # already have structlog for that and don't want duplicate signals.
        send_default_pii=False,
        attach_stacktrace=True,
    )

    run_id = os.getenv("BIP_RUN_ID")
    if run_id:
        sentry_sdk.set_tag("run_id", run_id)

    _INITIALIZED = True
    return True


def reset_for_tests() -> None:
    """Reset the module-level flag so tests can re-init."""
    global _INITIALIZED
    _INITIALIZED = False


__all__ = ["init_sentry", "reset_for_tests"]
