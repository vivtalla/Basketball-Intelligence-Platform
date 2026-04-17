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


class StandingsRecentTrendGame(BaseModel):
    date: str
    won: bool
    margin: int
    is_home: bool
    opponent_abbreviation: Optional[str] = None


class StandingsRecentTrend(BaseModel):
    games: List[StandingsRecentTrendGame]
    last_10_record: str
    avg_margin: float
    direction: str


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
    gp: Optional[int] = None
    pts_pg: Optional[float] = None
    opp_pts_pg: Optional[float] = None
    diff_pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    tov_pg: Optional[float] = None
    stl_pg: Optional[float] = None
    blk_pg: Optional[float] = None
    fg_pct: Optional[float] = None
    fg3_pct: Optional[float] = None
    ft_pct: Optional[float] = None
    plus_minus_pg: Optional[float] = None
    off_rating: Optional[float] = None
    def_rating: Optional[float] = None
    net_rating: Optional[float] = None
    pace: Optional[float] = None
    efg_pct: Optional[float] = None
    ts_pct: Optional[float] = None
    pie: Optional[float] = None
    oreb_pct: Optional[float] = None
    dreb_pct: Optional[float] = None
    tov_pct: Optional[float] = None
    ast_pct: Optional[float] = None
    off_rating_rank: Optional[int] = None
    def_rating_rank: Optional[int] = None
    net_rating_rank: Optional[int] = None
    pace_rank: Optional[int] = None
    efg_pct_rank: Optional[int] = None
    ts_pct_rank: Optional[int] = None
    oreb_pct_rank: Optional[int] = None
    tov_pct_rank: Optional[int] = None
    current_streak: str
    recent_trend: Optional[StandingsRecentTrend] = None
    clinch_indicator: Optional[str] = None
