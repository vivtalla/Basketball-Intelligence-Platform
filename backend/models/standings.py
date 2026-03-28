from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


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
