from typing import Literal, Optional

from fastapi import Depends, Query
from fastapi.routing import APIRouter

from db.database import get_db
from models.lineups import LineupBuilderRequest, LineupBuilderResult, LineupLeaderboardResult, SublineupsResult
from services.lineup_builder_service import build_lineup_builder_result
from services.lineup_leaderboard_service import build_lineup_leaderboard
from services.lineup_sublineup_service import build_sublineups
from sqlalchemy.orm import Session

router = APIRouter()

SeasonType = Literal["Regular Season", "Playoffs"]
SortBy = Literal["net_rating", "ortg", "drtg", "plus_minus", "possessions", "minutes"]
SortDir = Literal["asc", "desc"]
SubSize = Literal[2, 3, 5]


@router.get("/leaderboard", response_model=LineupLeaderboardResult)
def get_lineup_leaderboard(
    season: str = Query("2024-25"),
    season_type: SeasonType = Query("Regular Season"),
    team_id: Optional[int] = Query(None),
    min_possessions: int = Query(100, ge=1),
    sort_by: SortBy = Query("net_rating"),
    sort_dir: SortDir = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> LineupLeaderboardResult:
    return build_lineup_leaderboard(
        db=db,
        season=season,
        season_type=season_type,
        team_id=team_id,
        min_possessions=min_possessions,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
    )


@router.post("/builder", response_model=LineupBuilderResult)
def post_lineup_builder(
    request: LineupBuilderRequest,
    db: Session = Depends(get_db),
) -> LineupBuilderResult:
    return build_lineup_builder_result(
        db=db,
        player_ids=request.player_ids,
        season=request.season,
        season_type=request.season_type,
    )


@router.get("/sublineups", response_model=SublineupsResult)
def get_sublineups(
    season: str = Query("2024-25"),
    team_id: int = Query(...),
    season_type: SeasonType = Query("Regular Season"),
    size: SubSize = Query(5),
    min_possessions: int = Query(50, ge=1),
    db: Session = Depends(get_db),
) -> SublineupsResult:
    is_playoff = season_type == "Playoffs"
    return build_sublineups(
        db=db,
        team_id=team_id,
        season=season,
        is_playoff=is_playoff,
        size=size,
        min_possessions=min_possessions,
    )
