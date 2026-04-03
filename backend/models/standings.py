from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class StandingsSnapshot(BaseModel):
    date: str           # ISO "YYYY-MM-DD"
    wins: int
    losses: int
    win_pct: float


class StandingsHistoryResponse(BaseModel):
    team_id: int
    team_abbr: str
    conference: str
    snapshots: List[StandingsSnapshot]


class StandingsEntry(BaseModel):
    team_id: int
    abbreviation: str
    team_city: str
    team_name: str
    conference: str
    division: str
    playoff_rank: int
    wins: int
    losses: int
    win_pct: float
    games_back: Optional[float] = None
    l10: str
    home_record: str
    road_record: str
    pts_pg: Optional[float] = None
    opp_pts_pg: Optional[float] = None
    diff_pts_pg: Optional[float] = None
    current_streak: str
    clinch_indicator: Optional[str] = None
