"""Pydantic schemas for the Sprint 67 Shot Profile Diagnosis module.

Contracts consumed by:
- backend/routers/shotchart.py (GET /api/shotchart/{player_id}/diagnosis)
- backend/services/scouting_brief_service.py (Shot Profile card source)

Pure layer over shot_intelligence_service outputs. No new DB tables; no
changes to shot_quality_baselines or Alembic 0008.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel


ShotDiagnosisSentiment = Literal["strength", "risk", "neutral"]
ShotDiagnosisGrade = Literal["green", "yellow", "red"]
ShotSampleConfidence = Literal["high", "medium", "low"]
Sustainability = Literal["Sustainable", "Hot Streak", "Cold Streak", "Insufficient Sample"]
CreationBurden = Literal["Self-Created Heavy", "Balanced", "Assisted Heavy"]


class ShotDiagnosisEvidence(BaseModel):
    metric: str
    value: Optional[float] = None
    delta: Optional[float] = None
    zone: Optional[str] = None
    note: Optional[str] = None


class ShotDiagnosisTag(BaseModel):
    key: str
    label: str
    sentiment: ShotDiagnosisSentiment
    grade: ShotDiagnosisGrade
    sample_confidence: ShotSampleConfidence
    evidence: List[ShotDiagnosisEvidence] = []


class ShotDiagnosisResponse(BaseModel):
    player_id: int
    season: str
    season_type: str
    methodology_version: str
    headline: str
    sustainability: Sustainability
    creation_burden: CreationBurden
    tags: List[ShotDiagnosisTag] = []
    sample_confidence: ShotSampleConfidence
    coverage_state: str
    total_shots: int
