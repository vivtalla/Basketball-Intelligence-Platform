from typing import Any, Dict, List, Optional

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
    clutch_fga: Optional[int] = None
    clutch_fg_pct: Optional[float] = None
    clutch_plus_minus: Optional[float] = None
    second_chance_pts: Optional[float] = None
    fast_break_pts: Optional[float] = None
    # Normalized rate stats (keyed by counting stat name)
    per36: Optional[Dict[str, float]] = None
    per100: Optional[Dict[str, float]] = None


class ClutchStats(BaseModel):
    player_id: int
    season: str
    clutch_pts: Optional[float] = None
    clutch_fga: Optional[int] = None
    clutch_fg_pct: Optional[float] = None
    clutch_plus_minus: Optional[float] = None
    second_chance_pts: Optional[float] = None
    fast_break_pts: Optional[float] = None


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


class PbpCoverage(BaseModel):
    player_id: int
    season: str
    eligible_games: int = 0
    synced_games: int = 0
    has_on_off: bool = False
    has_scoring_splits: bool = False
    status: str
    last_derived_at: Optional[str] = None


class PbpCoveragePlayerRow(BaseModel):
    player_id: int
    player_name: str
    team_abbreviation: Optional[str] = None
    season: str
    eligible_games: int = 0
    synced_games: int = 0
    has_on_off: bool = False
    has_scoring_splits: bool = False
    status: str
    last_derived_at: Optional[str] = None


class PbpCoverageTeamRow(BaseModel):
    team_id: int
    abbreviation: str
    name: str
    season: str
    player_count: int = 0
    players_ready: int = 0
    players_partial: int = 0
    players_none: int = 0
    eligible_games: int = 0
    synced_games: int = 0
    status: str


class PbpCoverageDashboard(BaseModel):
    season: str
    total_teams: int = 0
    total_players: int = 0
    teams_ready: int = 0
    teams_partial: int = 0
    teams_none: int = 0
    players_ready: int = 0
    players_partial: int = 0
    players_none: int = 0
    eligible_games: int = 0
    synced_games: int = 0
    teams: List[PbpCoverageTeamRow]
    players: List[PbpCoveragePlayerRow]


class PbpCoverageSeasonSummary(BaseModel):
    season: str
    total_teams: int = 0
    total_players: int = 0
    teams_ready: int = 0
    teams_partial: int = 0
    teams_none: int = 0
    players_ready: int = 0
    players_partial: int = 0
    players_none: int = 0
    eligible_games: int = 0
    synced_games: int = 0


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
    data_status: str = "missing"
    last_synced_at: Optional[str] = None


class GameLogEntry(BaseModel):
    game_id: str
    game_date: Optional[str] = None
    matchup: Optional[str] = None
    wl: Optional[str] = None
    min: Optional[float] = None
    pts: Optional[int] = None
    reb: Optional[int] = None
    ast: Optional[int] = None
    stl: Optional[int] = None
    blk: Optional[int] = None
    tov: Optional[int] = None
    fgm: Optional[int] = None
    fga: Optional[int] = None
    fg_pct: Optional[float] = None
    fg3m: Optional[int] = None
    fg3a: Optional[int] = None
    fg3_pct: Optional[float] = None
    ftm: Optional[int] = None
    fta: Optional[int] = None
    ft_pct: Optional[float] = None
    oreb: Optional[int] = None
    dreb: Optional[int] = None
    pf: Optional[int] = None
    plus_minus: Optional[int] = None
    pts_roll5: Optional[float] = None
    reb_roll5: Optional[float] = None
    ast_roll5: Optional[float] = None


class GameLogSeasonAverages(BaseModel):
    pts: Optional[float] = None
    reb: Optional[float] = None
    ast: Optional[float] = None
    stl: Optional[float] = None
    blk: Optional[float] = None
    tov: Optional[float] = None
    fg_pct: Optional[float] = None
    fg3_pct: Optional[float] = None
    ft_pct: Optional[float] = None
    min: Optional[float] = None
    plus_minus: Optional[float] = None


class GameLogResponse(BaseModel):
    player_id: int
    season: str
    season_type: str
    games: List[GameLogEntry]
    season_averages: GameLogSeasonAverages
    gp: int = 0
    data_status: str = "missing"
    last_synced_at: Optional[str] = None


class LeagueContext(BaseModel):
    season: str
    position_group: Optional[str]  # "G", "F", "C", or None (league-wide)
    league_medians: Dict[str, Optional[float]]
    position_medians: Dict[str, Optional[float]]
