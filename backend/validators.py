"""Reusable annotated query/path parameter types for input validation.

FastAPI resolves these via Pydantic v2 — invalid values receive a clean
422 Unprocessable Entity response before the handler runs.

Use FastAPI's Query/Path (not Pydantic's Field) so the pattern constraint
is recognised by FastAPI's parameter resolution, not just Pydantic's model
validation layer.

Note: ``Annotated`` requires Python 3.9+; we import from ``typing_extensions``
(a Pydantic v2 transitive dependency) to maintain Python 3.8 compatibility.
"""
from __future__ import annotations

from fastapi import Path, Query
from typing_extensions import Annotated

# "2025-26" format — rejects free-text, SQL meta-characters, arbitrary lengths.
# Usage in route: season: SeasonStr  (no additional = Query(...) needed)
SeasonStr = Annotated[str, Query(pattern=r"^\d{4}-\d{2}$", max_length=7)]

# Playoff series ID (path param) — alphanumeric + hyphens only, capped at 60 chars.
SeriesIdStr = Annotated[str, Path(pattern=r"^[\w-]{1,60}$", max_length=60)]
