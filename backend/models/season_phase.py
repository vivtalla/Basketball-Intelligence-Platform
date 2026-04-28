"""Pydantic schemas for the season-phase auto-detection service (Sprint 73)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


SeasonPhase = Literal[
    "regular_season",
    "playoff_play_in",
    "playoff_round_1",
    "playoff_round_2",
    "conference_finals",
    "finals",
    "offseason",
]


class SeasonPhaseResponse(BaseModel):
    phase: SeasonPhase
    season: str  # e.g. "2025-26"
    round_label: Optional[str] = None  # e.g. "First Round", "Conference Finals"
    last_updated_at: datetime
