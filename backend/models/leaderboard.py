from __future__ import annotations

from typing import List

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team_abbreviation: str
    headshot_url: str
    gp: int
    stat_value: float


class LeaderboardResponse(BaseModel):
    stat: str
    season: str
    season_type: str
    entries: List[LeaderboardEntry]
