"""Pydantic schemas for the Sprint 67 Scouting Summary Brief.

Five-card brief strip rendered directly below PlayerHeader on `/players/[id]`.
Cards are composed server-side so confidence language stays consistent; any
missing source service causes the card to be skipped (never shown sparse).
"""
from typing import List, Literal, Optional

from pydantic import BaseModel


ScoutingCardType = Literal[
    "role",
    "strengths",
    "usage_efficiency",
    "shot_profile",
    "trajectory",
]

ScoutingCardConfidence = Literal["high", "medium", "low"]


class ScoutingBriefCard(BaseModel):
    card_type: ScoutingCardType
    title: str
    summary: str
    evidence: List[str] = []
    confidence: ScoutingCardConfidence
    deep_link: str


class ScoutingBriefResponse(BaseModel):
    player_id: int
    season: str
    methodology_version: str
    cards: List[ScoutingBriefCard]
    warnings: List[str] = []
