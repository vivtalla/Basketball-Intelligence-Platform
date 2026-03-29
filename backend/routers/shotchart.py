from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from data.nba_client import get_shot_chart_data
from models.shotchart import ShotChartResponse, ShotChartShot

router = APIRouter()


@router.get("/{player_id}", response_model=ShotChartResponse)
def player_shot_chart(
    player_id: int,
    season: str = Query(..., description='Season ID, e.g. "2023-24"'),
    season_type: str = Query("Regular Season", description='"Regular Season" or "Playoffs"'),
):
    if season_type not in ("Regular Season", "Playoffs"):
        raise HTTPException(status_code=422, detail='season_type must be "Regular Season" or "Playoffs"')

    try:
        raw_shots = get_shot_chart_data(player_id, season, season_type)
    except Exception:
        # stats.nba.com may be unreachable; return empty rather than 500
        raw_shots = []

    shots = [ShotChartShot(**s) for s in raw_shots]
    made = sum(1 for s in shots if s.shot_made)

    return ShotChartResponse(
        player_id=player_id,
        season=season,
        season_type=season_type,
        shots=shots,
        made=made,
        attempted=len(shots),
    )
