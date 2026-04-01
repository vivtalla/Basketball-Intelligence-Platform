from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from models.compare import TeamComparisonResponse
from services.compare_service import build_team_comparison_report

router = APIRouter()


@router.get("/teams", response_model=TeamComparisonResponse)
def compare_teams(
    team_a: str = Query(...),
    team_b: str = Query(...),
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    return build_team_comparison_report(
        db=db,
        team_a=team_a,
        team_b=team_b,
        season=season,
    )
