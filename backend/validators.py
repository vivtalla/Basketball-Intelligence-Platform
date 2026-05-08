"""Reusable annotated query-parameter types for input validation.

FastAPI resolves these via Pydantic v2 — invalid values receive a clean
422 Unprocessable Entity response before the handler runs.

Note: ``Annotated`` requires Python 3.9+; we import from ``typing_extensions``
(a Pydantic v2 transitive dependency) to maintain Python 3.8 compatibility.
"""
from __future__ import annotations

from typing_extensions import Annotated
from pydantic import Field

# "2025-26" format — rejects free-text, SQL meta-characters, arbitrary lengths.
SeasonStr = Annotated[str, Field(pattern=r"^\d{4}-\d{2}$", max_length=7)]

# NBA team abbreviation — 2 or 3 uppercase letters only.
TeamAbbr = Annotated[str, Field(pattern=r"^[A-Za-z]{2,3}$", max_length=3)]

# Playoff series ID — alphanumeric + hyphens, capped at 60 chars.
SeriesIdStr = Annotated[str, Field(pattern=r"^[\w-]{1,60}$", max_length=60)]
