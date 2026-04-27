"""Team-Fit Intelligence endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from models.team_fit import TeamFitResponse
from services.team_fit_service import build_team_fit_report


router = APIRouter()


@router.get("/{player_id}", response_model=TeamFitResponse)
def team_fit_report(
    player_id: int,
    season: str = Query("2024-25"),
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """Explain a player's current roster fit and deterministic alternate fits."""
    return build_team_fit_report(db=db, player_id=player_id, season=season, limit=limit)
