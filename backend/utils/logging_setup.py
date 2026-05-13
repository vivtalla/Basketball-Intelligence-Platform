"""Sprint 98 Stream A3 — Structured logging with cron RUN_ID propagation.

Why this exists: the Sprint 96 closeout-night incident hid a 5-day silent
cron failure partly because logs were unstructured stdout text — no way
to correlate the steps of a single cron run against each other or to
search for a specific failed entity quickly. This module configures
``structlog`` with a JSON renderer in production and a console renderer
in dev, and binds ``BIP_RUN_ID`` (set by ``daily_sync.sh`` per cron
invocation) to the logger context so every line emitted during one
cron tick shares a ``run_id``.

Usage:

    # FastAPI app — configure once at startup. Adds the request-ID
    # middleware so every HTTP request gets a fresh request_id binding.
    from utils.logging_setup import configure_logging
    configure_logging()

    # Sync scripts — same one-liner at entry.
    from utils.logging_setup import configure_logging, get_logger
    configure_logging()
    log = get_logger(__name__)
    log.info("starting", season=season)

The stdlib ``logging.getLogger(__name__).info(...)`` form keeps working —
structlog's ``LoggerFactory`` bridges the two so existing callers don't
need to migrate to access structured output. New code should prefer
``structlog.get_logger()`` so it gets kwargs-style structured fields.
"""
from __future__ import annotations

import logging
import os
import sys
import uuid
from typing import Any, Optional

import structlog


_CONFIGURED = False


def configure_logging(
    *,
    level: int = logging.INFO,
    force_json: Optional[bool] = None,
) -> None:
    """Configure structlog + stdlib logging.

    Args:
        level: log level (default INFO).
        force_json: override JSON-vs-console renderer choice. If None,
            uses ``ENV=production`` to decide. Tests can force a renderer
            without setting env vars.

    Idempotent — calling twice is a no-op on the second call.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    if force_json is None:
        use_json = os.getenv("ENV", "dev").lower() == "production"
    else:
        use_json = force_json

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if use_json:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    # Keep stdlib logging functional so existing `logging.getLogger(__name__)`
    # callers still emit (they'll just emit the raw message, not structured
    # kwargs — that's fine until they migrate).
    logging.basicConfig(level=level, format="%(message)s", stream=sys.stderr, force=True)

    # If the caller is a cron tick, BIP_RUN_ID is exported by daily_sync.sh
    # at the top of the script — bind it to the global context so every log
    # line from this process is correlatable.
    run_id = os.getenv("BIP_RUN_ID")
    if run_id:
        structlog.contextvars.bind_contextvars(run_id=run_id)

    # Sprint 98 Stream A4 — initialize Sentry as part of the same boot path.
    # No-op when SENTRY_DSN is unset (dev / tests). Coupling sentry init to
    # configure_logging means every script that wants structured logs also
    # gets free error capture, with no extra wiring.
    try:
        from utils.sentry_init import init_sentry

        init_sentry()
    except Exception:  # noqa: BLE001 — Sentry init must never block boot
        pass

    _CONFIGURED = True


def get_logger(name: str = "") -> Any:
    """Return a structlog logger, calling configure_logging() on demand."""
    if not _CONFIGURED:
        configure_logging()
    return structlog.get_logger(name)


def bind_request_id(request_id: Optional[str] = None) -> str:
    """Bind a request_id to the current task's contextvars and return it.

    If ``request_id`` is None, generates a fresh UUID. Returns the bound
    id so the caller can echo it back on the response (e.g. as an
    ``X-Request-ID`` header).
    """
    rid = request_id or str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(request_id=rid)
    return rid


def reset_for_tests() -> None:
    """Reset the module-level CONFIGURED flag so tests can re-init."""
    global _CONFIGURED
    _CONFIGURED = False
    structlog.contextvars.clear_contextvars()


__all__ = [
    "bind_request_id",
    "configure_logging",
    "get_logger",
    "reset_for_tests",
]
