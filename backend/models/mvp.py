from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Confidence = Literal["high", "medium", "low"]


class MvpScorePillar(BaseModel):
    label: str
    weight: float
    raw_score: float
    weighted_score: float
    display_score: float


class MvpTeamContext(BaseModel):
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    win_pct: Optional[float] = None
    net_rating: Optional[float] = None
    off_rating: Optional[float] = None
    def_rating: Optional[float] = None
    win_pct_rank: Optional[int] = None
    net_rating_rank: Optional[int] = None


class MvpOnOffProfile(BaseModel):
    on_minutes: Optional[float] = None
    off_minutes: Optional[float] = None
    on_net_rating: Optional[float] = None
    off_net_rating: Optional[float] = None
    on_off_net: Optional[float] = None
    on_ortg: Optional[float] = None
    on_drtg: Optional[float] = None
    off_ortg: Optional[float] = None
    off_drtg: Optional[float] = None
    confidence: Confidence = "low"


class MvpAdvancedProfile(BaseModel):
    usg_pct: Optional[float] = None
    ts_pct: Optional[float] = None
    efg_pct: Optional[float] = None
    bpm: Optional[float] = None
    obpm: Optional[float] = None
    dbpm: Optional[float] = None
    vorp: Optional[float] = None
    ws: Optional[float] = None
    win_shares_per_48: Optional[float] = None
    pie: Optional[float] = None
    net_rating: Optional[float] = None
    off_rating: Optional[float] = None
    def_rating: Optional[float] = None
    epm: Optional[float] = None
    raptor: Optional[float] = None
    lebron: Optional[float] = None


class MvpClutchAndPaceProfile(BaseModel):
    clutch_pts: Optional[float] = None
    clutch_fga: Optional[int] = None
    clutch_fg_pct: Optional[float] = None
    second_chance_pts: Optional[float] = None
    fast_break_pts: Optional[float] = None


class MvpPlayStyleRow(BaseModel):
    action_family: str
    label: str
    usage_share: Optional[float] = None
    points_per_possession: Optional[float] = None
    turnover_rate: Optional[float] = None
    ev_score: Optional[float] = None
    raw_volume: int = 0
    confidence: Confidence = "low"
    note: str


class MvpDataCoverage(BaseModel):
    has_season_stats: bool = False
    has_team_context: bool = False
    has_on_off: bool = False
    has_pbp_splits: bool = False
    has_play_style: bool = False
    warnings: List[str] = Field(default_factory=list)


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
    ts_delta: Optional[float] = None
    momentum: str = "steady"            # "hot" | "cold" | "steady"
    last_games: int = 0                 # count of recent game log rows used
    score_pillars: Dict[str, MvpScorePillar] = Field(default_factory=dict)
    case_summary: List[str] = Field(default_factory=list)
    team_context: Optional[MvpTeamContext] = None
    on_off: Optional[MvpOnOffProfile] = None
    advanced_profile: Optional[MvpAdvancedProfile] = None
    clutch_and_pace: Optional[MvpClutchAndPaceProfile] = None
    play_style: List[MvpPlayStyleRow] = Field(default_factory=list)
    data_coverage: Optional[MvpDataCoverage] = None


class MvpRaceResponse(BaseModel):
    season: str
    as_of_date: str                     # ISO date of most-recent game log row used
    candidates: List[MvpCandidate]
    weights: Dict[str, float]           # weights used for this response
    scoring_profile: str = "mvp_case_v1"


class MvpNearbyCandidate(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team_abbreviation: str
    composite_score: float


class MvpCandidateCaseResponse(BaseModel):
    season: str
    as_of_date: str
    candidate: MvpCandidate
    nearby: List[MvpNearbyCandidate] = Field(default_factory=list)
    weights: Dict[str, float]
    scoring_profile: str = "mvp_case_v1"
