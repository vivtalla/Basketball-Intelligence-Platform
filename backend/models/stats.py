from typing import Dict, List, Optional

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
    darko: Optional[float] = None
    epm: Optional[float] = None
    rapm: Optional[float] = None
    # External public metrics (imported via CSV)
    lebron: Optional[float] = None
    raptor: Optional[float] = None
    pipm: Optional[float] = None
    # Split BPM components
    obpm: Optional[float] = None
    dbpm: Optional[float] = None
    # Secondary box-score metrics
    ftr: Optional[float] = None      # Free Throw Rate
    par3: Optional[float] = None     # 3-Point Attempt Rate
    ast_tov: Optional[float] = None  # Assist-to-Turnover Ratio
    oreb_pct: Optional[float] = None # Offensive Rebound %
    # Play-by-play derived stats
    clutch_pts: Optional[float] = None
    clutch_fg_pct: Optional[float] = None
    clutch_plus_minus: Optional[float] = None
    second_chance_pts: Optional[float] = None
    fast_break_pts: Optional[float] = None
    # Normalized rate stats (keyed by counting stat name)
    per36: Optional[Dict[str, float]] = None
    per100: Optional[Dict[str, float]] = None


class OnOffStats(BaseModel):
    player_id: int
    season: str
    on_minutes: Optional[float] = None
    off_minutes: Optional[float] = None
    on_net_rating: Optional[float] = None
    off_net_rating: Optional[float] = None
    on_off_net: Optional[float] = None
    on_ortg: Optional[float] = None
    on_drtg: Optional[float] = None
    off_ortg: Optional[float] = None
    off_drtg: Optional[float] = None


class LineupStatsResponse(BaseModel):
    lineup_key: str
    player_ids: List[int]
    player_names: List[str]
    season: str
    team_id: Optional[int] = None
    minutes: Optional[float] = None
    net_rating: Optional[float] = None
    ortg: Optional[float] = None
    drtg: Optional[float] = None
    plus_minus: Optional[float] = None
    possessions: Optional[int] = None


class CareerStatsResponse(BaseModel):
    player_id: int
    player_name: str
    seasons: List[SeasonStats]
    career_totals: Optional[SeasonStats] = None
    playoff_seasons: List[SeasonStats] = []
