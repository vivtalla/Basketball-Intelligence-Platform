from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import PlayerShotChart
from models.shotchart import ShotChartResponse, ShotChartShot, ZoneProfileResponse, ZoneStat

router = APIRouter()

# Zone point values for PPS calculation
_ZONE_POINTS = {
    "Restricted Area": 2,
    "In The Paint (Non-RA)": 2,
    "Mid-Range": 2,
    "Left Corner 3": 3,
    "Right Corner 3": 3,
    "Above the Break 3": 3,
    "Backcourt": 3,
}


def _data_status(cached: Optional[PlayerShotChart], now: datetime) -> str:
    if not cached:
        return "missing"
    if not cached.shot_count:
        return "missing"
    if cached.expires_at and cached.expires_at > now:
        return "ready"
    return "stale"


def _last_synced_at(cached: Optional[PlayerShotChart]) -> Optional[str]:
    return cached.fetched_at.isoformat() if cached and cached.fetched_at else None


def _build_response(
    player_id: int,
    season: str,
    season_type: str,
    raw_shots: list,
    data_status: str,
    last_synced_at: Optional[str],
) -> ShotChartResponse:
    shots = [ShotChartShot(**s) for s in raw_shots]
    made = sum(1 for s in shots if s.shot_made)
    return ShotChartResponse(
        player_id=player_id,
        season=season,
        season_type=season_type,
        shots=shots,
        made=made,
        attempted=len(shots),
        data_status=data_status,
        last_synced_at=last_synced_at,
    )


@router.get("/{player_id}/zones", response_model=ZoneProfileResponse)
def player_shot_zones(
    player_id: int,
    season: str = Query(..., description='Season ID, e.g. "2023-24"'),
    season_type: str = Query("Regular Season", description='"Regular Season" or "Playoffs"'),
    db: Session = Depends(get_db),
):
    """Return zone-aggregated shot efficiency for a player from cached shot data.

    Reads only from the player_shot_charts DB cache — no nba_api call.
    Returns total_attempts=0 and zones=[] if no cached data exists.
    """
    if season_type not in ("Regular Season", "Playoffs"):
        raise HTTPException(status_code=422, detail='season_type must be "Regular Season" or "Playoffs"')

    now = datetime.utcnow()
    cached = (
        db.query(PlayerShotChart)
        .filter(
            PlayerShotChart.player_id == player_id,
            PlayerShotChart.season == season,
            PlayerShotChart.season_type == season_type,
        )
        .first()
    )

    shots = (cached.shots or []) if cached else []
    total = len(shots)

    # Aggregate by (zone_basic, zone_area)
    zone_map: dict = {}
    for s in shots:
        key = (s.get("zone_basic", "Unknown"), s.get("zone_area", ""))
        if key not in zone_map:
            zone_map[key] = {"made": 0, "attempted": 0}
        zone_map[key]["attempted"] += 1
        if s.get("shot_made"):
            zone_map[key]["made"] += 1

    zones = []
    for (zone_basic, zone_area), counts in zone_map.items():
        att = counts["attempted"]
        made = counts["made"]
        pts = _ZONE_POINTS.get(zone_basic, 2)
        fg_pct = (made / att) if att >= 5 else None
        pps = round(fg_pct * pts, 4) if fg_pct is not None else None
        zones.append(ZoneStat(
            zone_basic=zone_basic,
            zone_area=zone_area,
            attempts=att,
            made=made,
            fg_pct=round(fg_pct, 4) if fg_pct is not None else None,
            pps=pps,
            freq=round(att / total, 4) if total > 0 else 0.0,
        ))

    zones.sort(key=lambda z: z.freq, reverse=True)

    return ZoneProfileResponse(
        player_id=player_id,
        season=season,
        season_type=season_type,
        total_attempts=total,
        zones=zones,
        data_status=_data_status(cached, now),
        last_synced_at=_last_synced_at(cached),
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
    if cached:
        return _build_response(
            player_id,
            season,
            season_type,
            cached.shots or [],
            data_status=_data_status(cached, now),
            last_synced_at=_last_synced_at(cached),
        )

    return _build_response(
        player_id,
        season,
        season_type,
        [],
        data_status="missing",
        last_synced_at=None,
    )
