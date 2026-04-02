from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from models.schedule import UpcomingScheduleGame
from services.schedule_service import list_upcoming_games

router = APIRouter()


@router.get("/upcoming", response_model=List[UpcomingScheduleGame])
def get_upcoming_schedule(
    season: str = Query("2024-25"),
    days: int = Query(7, ge=1, le=30),
    team: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return list_upcoming_games(
        db=db,
        season=season,
        days=days,
        team_abbreviation=team,
    )
