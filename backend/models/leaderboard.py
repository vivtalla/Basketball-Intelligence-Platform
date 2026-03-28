from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team_abbreviation: str
    headshot_url: str
    gp: int
    stat_value: float
    # Always-included context columns
    pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    ts_pct: Optional[float] = None
    per: Optional[float] = None
    bpm: Optional[float] = None


class LeaderboardResponse(BaseModel):
    stat: str
    season: str
    season_type: str
    entries: List[LeaderboardEntry]


class CareerLeaderboardEntry(BaseModel):
    rank: int
    player_id: int
    player_name: str
    headshot_url: str
    seasons_played: int
    career_gp: int
    stat_value: float


class CareerLeaderboardResponse(BaseModel):
    stat: str
    entries: List[CareerLeaderboardEntry]
