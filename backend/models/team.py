from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from models.stats import LineupStatsResponse


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


class TeamAnalytics(BaseModel):
    team_id: int
    abbreviation: str
    name: str
    season: str
    gp: int
    w: int
    l: int
    w_pct: float
    pts_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    tov_pg: Optional[float] = None
    blk_pg: Optional[float] = None
    stl_pg: Optional[float] = None
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


class TeamRecentGame(BaseModel):
    game_id: str
    game_date: Optional[str] = None
    opponent_abbreviation: Optional[str] = None
    is_home: bool
    result: str
    team_score: Optional[int] = None
    opponent_score: Optional[int] = None
    margin: Optional[int] = None


class TeamPbpCoverage(BaseModel):
    season: str
    eligible_games: int = 0
    synced_games: int = 0
    players_with_on_off: int = 0
    players_with_scoring_splits: int = 0
    status: str


class TeamImpactLeader(BaseModel):
    player_id: int
    player_name: str
    team_abbreviation: Optional[str] = None
    on_off_net: Optional[float] = None
    on_minutes: Optional[float] = None
    bpm: Optional[float] = None
    pts_pg: Optional[float] = None
    clutch_pts: Optional[float] = None


class TeamIntelligenceResponse(BaseModel):
    team_id: int
    abbreviation: str
    name: str
    season: str
    conference: Optional[str] = None
    playoff_rank: Optional[int] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    win_pct: Optional[float] = None
    l10: Optional[str] = None
    current_streak: Optional[str] = None
    pts_pg: Optional[float] = None
    opp_pts_pg: Optional[float] = None
    diff_pts_pg: Optional[float] = None
    recent_record: Optional[str] = None
    recent_avg_margin: Optional[float] = None
    pbp_coverage: TeamPbpCoverage
    impact_leaders: List[TeamImpactLeader]
    best_lineups: List[LineupStatsResponse]
    worst_lineups: List[LineupStatsResponse]
    recent_games: List[TeamRecentGame]
