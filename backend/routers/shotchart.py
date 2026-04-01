from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from data.nba_client import _cache_ttl_for_season, get_shot_chart_data
from db.database import get_db
from db.models import PlayerShotChart
from models.shotchart import ShotChartResponse, ShotChartShot

router = APIRouter()


def _build_response(player_id: int, season: str, season_type: str, raw_shots: list) -> ShotChartResponse:
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


@router.get("/{player_id}", response_model=ShotChartResponse)
def player_shot_chart(
    player_id: int,
    season: str = Query(..., description='Season ID, e.g. "2023-24"'),
    season_type: str = Query("Regular Season", description='"Regular Season" or "Playoffs"'),
    db: Session = Depends(get_db),
):
    if season_type not in ("Regular Season", "Playoffs"):
        raise HTTPException(status_code=422, detail='season_type must be "Regular Season" or "Playoffs"')

    now = datetime.utcnow()

    # --- DB cache check ---
    cached = (
        db.query(PlayerShotChart)
        .filter(
            PlayerShotChart.player_id == player_id,
            PlayerShotChart.season == season,
            PlayerShotChart.season_type == season_type,
        )
        .first()
    )
    if cached and cached.expires_at and cached.expires_at > now:
        return _build_response(player_id, season, season_type, cached.shots or [])

    # --- Fetch from nba_api ---
    try:
        raw_shots = get_shot_chart_data(player_id, season, season_type)
    except Exception:
        # stats.nba.com may be unreachable; return empty rather than 500.
        # If we have a stale cache entry, return it rather than nothing.
        if cached:
            return _build_response(player_id, season, season_type, cached.shots or [])
        raw_shots = []

    # --- Persist to DB ---
    try:
        ttl_seconds = _cache_ttl_for_season(season)
        expires_at = now + timedelta(seconds=ttl_seconds)
        if cached:
            cached.shots = raw_shots
            cached.shot_count = len(raw_shots)
            cached.fetched_at = now
            cached.expires_at = expires_at
        else:
            db.add(PlayerShotChart(
                player_id=player_id,
                season=season,
                season_type=season_type,
                shots=raw_shots,
                shot_count=len(raw_shots),
                fetched_at=now,
                expires_at=expires_at,
            ))
        db.commit()
    except Exception:
        db.rollback()
        # Persistence failure is non-fatal — still return the data.

    return _build_response(player_id, season, season_type, raw_shots)
