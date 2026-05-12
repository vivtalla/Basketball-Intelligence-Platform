"""Global rate limiter shared across all routers.

Defined here (not in main.py) so routers can import without a circular
dependency. Gracefully falls back to a no-op when slowapi is not installed
(e.g., local development / CI environments that don't install all prod deps).
"""
from __future__ import annotations

from typing import Callable

from config import ENABLE_RATE_LIMIT

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    _slowapi_available = True
except ImportError:  # pragma: no cover — only absent in local dev without pip install
    class _NoOpLimiter:  # type: ignore[no-redef]
        """Stand-in used when slowapi is not installed."""

        def limit(self, limit_string: str) -> Callable:  # noqa: ARG002
            def decorator(f: Callable) -> Callable:
                return f
            return decorator

    limiter = _NoOpLimiter()  # type: ignore[assignment]
    _slowapi_available = False

# Effective rate limits — "10000/minute" is functionally unlimited and used
# when ENABLE_RATE_LIMIT=false so the feature flag works without a redeploy.
RATE_LIMIT_INTELLIGENCE = "30/minute" if ENABLE_RATE_LIMIT else "10000/minute"
RATE_LIMIT_ROSTER_FIT = "20/minute" if ENABLE_RATE_LIMIT else "10000/minute"
# Sprint 98 C3 — expensive user-facing endpoints. LLM query is the most
# costly (compute + paid API call); trade simulation is heavy SQL +
# scoring; both expand beyond Cloudflare's per-IP 100/10min WAF rule
# with finer-grained per-endpoint limits.
RATE_LIMIT_LLM_QUERY = "10/minute" if ENABLE_RATE_LIMIT else "10000/minute"
RATE_LIMIT_TRADE_IMPACT = "20/minute" if ENABLE_RATE_LIMIT else "10000/minute"
RATE_LIMIT_TRADE_VALIDATE = "30/minute" if ENABLE_RATE_LIMIT else "10000/minute"
