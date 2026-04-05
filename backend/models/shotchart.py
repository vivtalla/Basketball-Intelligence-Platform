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
    game_id: Optional[str] = None
    game_date: Optional[str] = None
    period: Optional[int] = None
    clock: Optional[str] = None
    minutes_remaining: Optional[int] = None
    seconds_remaining: Optional[int] = None
    shot_value: Optional[int] = None
    shot_event_id: Optional[str] = None


class ShotChartResponse(BaseModel):
    player_id: int
    season: str
    season_type: str
    shots: List[ShotChartShot]
    made: int
    attempted: int
    data_status: str
    last_synced_at: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    available_start_date: Optional[str] = None
    available_end_date: Optional[str] = None
    available_game_dates: List[str] = []


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
    data_status: str
    last_synced_at: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    available_start_date: Optional[str] = None
    available_end_date: Optional[str] = None
