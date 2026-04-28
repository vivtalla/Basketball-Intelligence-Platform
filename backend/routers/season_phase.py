"""Season-phase API surface (Sprint 73).

Single endpoint: `GET /api/season-phase` exposing the current league phase
inferred by `season_phase_service.get_current_phase`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from models.season_phase import SeasonPhaseResponse
from services.season_phase_service import get_current_phase

router = APIRouter()


@router.get("", response_model=SeasonPhaseResponse)
def get_season_phase(db: Session = Depends(get_db)) -> SeasonPhaseResponse:
    """Return the current league phase (regular season / playoffs / offseason)."""
    return get_current_phase(db)
