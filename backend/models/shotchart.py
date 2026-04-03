from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class ShotChartShot(BaseModel):
    loc_x: int
    loc_y: int
    shot_made: bool
    shot_type: str
    action_type: str
    zone_basic: str
    zone_area: str
    distance: int


class ShotChartResponse(BaseModel):
    player_id: int
    season: str
    season_type: str
    shots: List[ShotChartShot]
    made: int
    attempted: int


class ZoneStat(BaseModel):
    zone_basic: str
    zone_area: str
    attempts: int
    made: int
    fg_pct: Optional[float] = None    # None when attempts < 5
    pps: Optional[float] = None
    freq: float


class ZoneProfileResponse(BaseModel):
    player_id: int
    season: str
    season_type: str
    total_attempts: int
    zones: List[ZoneStat]
