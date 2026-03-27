from fastapi import APIRouter, HTTPException

from models.stats import CareerStatsResponse
from services.stats_service import get_player_career_stats

router = APIRouter()


@router.get("/{player_id}/career", response_model=CareerStatsResponse)
def career_stats(player_id: int):
    try:
        data = get_player_career_stats(player_id)
        return CareerStatsResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {e}")
