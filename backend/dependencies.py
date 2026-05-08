"""Shared FastAPI dependencies for Sprint 93 hardening."""
from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException

from config import ADMIN_API_KEY


async def require_admin_key(x_admin_key: Optional[str] = Header(None)) -> None:
    """Guard for admin/mutation endpoints.

    When ADMIN_API_KEY is not configured (dev mode), all requests pass.
    In production set ADMIN_API_KEY in /etc/bip/env — requests without
    the matching X-Admin-Key header receive a 403.
    """
    if not ADMIN_API_KEY:
        return
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")
