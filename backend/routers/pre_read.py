from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from models.pre_read import PreReadDeckResponse
from models.scouting import PlayTypeScoutingReportResponse
from routers.scouting import build_play_type_scouting_report
from services.pre_read_service import build_pre_read_deck

router = APIRouter()


@router.get("", response_model=PreReadDeckResponse)
def get_pre_read(
    team: str = Query(...),
    opponent: str = Query(...),
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    return build_pre_read_deck(db=db, team=team, opponent=opponent, season=season)


@router.get("/scouting", response_model=PlayTypeScoutingReportResponse)
def get_pre_read_scouting_report(
    team: str = Query(...),
    opponent: str = Query(...),
    season: str = Query("2025-26"),
    window: int = Query(10, ge=3, le=20),
    db: Session = Depends(get_db),
):
    return build_play_type_scouting_report(
        db=db,
        team=team,
        opponent=opponent,
        season=season,
        window=window,
    )
