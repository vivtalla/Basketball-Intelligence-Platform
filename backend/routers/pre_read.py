from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from models.pre_read import PreReadDeckResponse
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
