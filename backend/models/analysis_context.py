from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


CONTEXT_TYPES = {"injury", "recovery", "availability_management", "manual_note"}
SOURCES = {"injury_report_auto", "manual"}
SEVERITIES = {"low", "medium", "high"}
FACETS = {"trend", "team_fit", "archetype", "similarity", "all"}


class AnalysisContextBase(BaseModel):
    season: str
    context_type: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    severity: Optional[str] = None
    note: Optional[str] = None
    applies_to: List[str] = ["all"]

    @field_validator("context_type")
    @classmethod
    def validate_context_type(cls, value: str) -> str:
        if value not in CONTEXT_TYPES:
            raise ValueError("unsupported context_type")
        return value

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in SEVERITIES:
            raise ValueError("unsupported severity")
        return value

    @field_validator("applies_to")
    @classmethod
    def validate_applies_to(cls, value: List[str]) -> List[str]:
        clean = value or ["all"]
        invalid = [item for item in clean if item not in FACETS]
        if invalid:
            raise ValueError("unsupported applies_to facet")
        return clean


class AnalysisContextCreate(AnalysisContextBase):
    pass


class AnalysisContextUpdate(BaseModel):
    context_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    severity: Optional[str] = None
    note: Optional[str] = None
    applies_to: Optional[List[str]] = None


class AnalysisContextResponse(AnalysisContextBase):
    id: Optional[int] = None
    player_id: int
    source: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisContextListResponse(BaseModel):
    player_id: int
    season: str
    contexts: List[AnalysisContextResponse]
