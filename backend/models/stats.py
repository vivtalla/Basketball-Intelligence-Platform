from typing import List, Optional

from pydantic import BaseModel


class SeasonStats(BaseModel):
    season: str
    team_abbreviation: str
    gp: int = 0
    gs: int = 0
    min_pg: float = 0.0
    pts_pg: float = 0.0
    reb_pg: float = 0.0
    ast_pg: float = 0.0
    stl_pg: float = 0.0
    blk_pg: float = 0.0
    tov_pg: float = 0.0
    fg_pct: float = 0.0
    fg3_pct: float = 0.0
    ft_pct: float = 0.0
    # Raw totals (useful for calculations)
    pts: int = 0
    reb: int = 0
    ast: int = 0
    fgm: int = 0
    fga: int = 0
    fg3m: int = 0
    fg3a: int = 0
    ftm: int = 0
    fta: int = 0
    oreb: int = 0
    dreb: int = 0
    stl: int = 0
    blk: int = 0
    tov: int = 0
    pf: int = 0
    min_total: float = 0.0
    # Advanced metrics
    ts_pct: Optional[float] = None
    efg_pct: Optional[float] = None
    usg_pct: Optional[float] = None
    per: Optional[float] = None
    bpm: Optional[float] = None
    off_rating: Optional[float] = None
    def_rating: Optional[float] = None
    net_rating: Optional[float] = None
    ws: Optional[float] = None
    vorp: Optional[float] = None
    pie: Optional[float] = None
    pace: Optional[float] = None


class CareerStatsResponse(BaseModel):
    player_id: int
    player_name: str
    seasons: List[SeasonStats]
    career_totals: Optional[SeasonStats] = None
    playoff_seasons: List[SeasonStats] = []
