"""Sprint 98 Stream A3 — Request-ID middleware.

Generates a UUID per incoming request (or honors a client-supplied
``X-Request-ID`` header), binds it to the structlog context so every
log line emitted during that request carries the same ``request_id``,
and echoes it back on the response so the client can correlate.

Usage in main.py:

    from utils.request_id_middleware import RequestIDMiddleware
    app.add_middleware(RequestIDMiddleware)
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from utils.logging_setup import bind_request_id

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Binds an ``X-Request-ID`` per request and propagates it via structlog.

    Honors a client-supplied ``X-Request-ID`` header (useful for distributed
    tracing) when present and well-formed; otherwise generates a fresh UUID.
    The bound id is scoped to the request's asyncio task via ``contextvars``,
    so logs emitted from downstream services and dependencies all carry it
    without explicit threading.
    """

    async def dispatch(self, request: Request, call_next):
        inbound = (request.headers.get(REQUEST_ID_HEADER) or "").strip()
        # Cap inbound IDs at 64 chars to avoid abuse, but otherwise trust them.
        candidate = inbound[:64] if inbound else None
        request_id = bind_request_id(candidate)

        response: Response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


__all__ = ["RequestIDMiddleware", "REQUEST_ID_HEADER"]
