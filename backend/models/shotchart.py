from __future__ import annotations

from typing import List

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
