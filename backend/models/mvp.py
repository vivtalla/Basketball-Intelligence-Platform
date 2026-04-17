from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class MvpCandidate(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team_abbreviation: str
    headshot_url: str
    gp: int
    composite_score: float          # normalized 0–100 relative to rank-1 player
    pts_pg: float
    reb_pg: float
    ast_pg: float
    ts_pct: Optional[float] = None
    bpm: Optional[float] = None
    pts_delta: Optional[float] = None   # last-10 avg PTS minus season avg PTS
    reb_delta: Optional[float] = None
    ast_delta: Optional[float] = None
    momentum: str = "steady"            # "hot" | "cold" | "steady"
    last_games: int = 0                 # count of recent game log rows used


class MvpRaceResponse(BaseModel):
    season: str
    as_of_date: str                     # ISO date of most-recent game log row used
    candidates: List[MvpCandidate]
    weights: Dict[str, float]           # weights used for this response
