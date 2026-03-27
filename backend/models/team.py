from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class TeamRosterPlayer(BaseModel):
    player_id: int
    full_name: str
    position: str
    jersey: str
    headshot_url: str
    season: Optional[str] = None
    pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    per: Optional[float] = None
    bpm: Optional[float] = None


class TeamRosterResponse(BaseModel):
    team_id: int
    abbreviation: str
    name: str
    players: List[TeamRosterPlayer]
    synced_count: int


class TeamSummary(BaseModel):
    team_id: int
    abbreviation: str
    name: str
    player_count: int
