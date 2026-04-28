"""Pydantic schemas for the Sprint 67 Player Archetype engine.

Contracts consumed by:
- backend/routers/archetype.py (GET /api/archetype/{player_id})
- backend/services/similarity_service.py (archetype label attached to each comp)
- backend/services/scouting_brief_service.py (Role card source)

Schema discipline matches Sprint 60 team Style X-Ray response shapes so
frontend components can port cleanly from components/xray/*.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel


ArchetypeKey = Literal[
    "heliocentric_creator",
    "lead_ball_handler",
    "iso_scorer",
    "secondary_playmaker",
    "movement_shooter",
    "three_and_d_wing",
    "rim_pressure_guard",
    "connective_forward",
    "defensive_anchor",
    "interior_finisher",
    "stretch_big",
    "switchable_stopper",
    "rotational_energy",
    "balanced_role",
    "developmental",
]

ConfidenceBand = Literal["high", "medium", "low"]
ContributorDirection = Literal["above", "below"]


class ArchetypeContributor(BaseModel):
    feature_key: str
    label: str
    value: Optional[float] = None
    z: float
    direction: ContributorDirection


class ArchetypeSample(BaseModel):
    gp: int
    min_pg: float
    peer_pool_size: int


class PlayerArchetype(BaseModel):
    player_id: int
    season: str
    archetype_key: ArchetypeKey
    label: str
    confidence: ConfidenceBand
    reason: str
    contributors: List[ArchetypeContributor]
    sample: ArchetypeSample
    methodology_version: str
    confidence_note: Optional[str] = None


class ArchetypeHistoryEntry(BaseModel):
    """One row in a multi-season archetype timeline (Sprint 68)."""
    season: str
    archetype_key: ArchetypeKey
    label: str
    confidence: ConfidenceBand
    reason: str
    transitioned_from: Optional[ArchetypeKey] = None  # previous season's key, if different


class ArchetypeHistoryResponse(BaseModel):
    player_id: int
    player_name: Optional[str] = None
    entries: List[ArchetypeHistoryEntry]
    methodology_version: str
