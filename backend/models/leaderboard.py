from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team_abbreviation: str
    headshot_url: str
    gp: int
    stat_value: float
    # Always-included context columns
    pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    ts_pct: Optional[float] = None
    per: Optional[float] = None
    bpm: Optional[float] = None


class LeaderboardResponse(BaseModel):
    stat: str
    season: str
    season_type: str
    entries: List[LeaderboardEntry]


class CareerLeaderboardEntry(BaseModel):
    rank: int
    player_id: int
    player_name: str
    headshot_url: str
    seasons_played: int
    career_gp: int
    stat_value: float


class CareerLeaderboardResponse(BaseModel):
    stat: str
    entries: List[CareerLeaderboardEntry]


class CustomMetricComponent(BaseModel):
    stat_id: str
    label: str
    weight: float
    inverse: bool = False


class CustomMetricRequest(BaseModel):
    metric_name: Optional[str] = None
    player_pool: str = "all"
    season: str
    components: List[CustomMetricComponent]
    team_abbreviation: Optional[str] = None
    position: Optional[str] = None


class CustomMetricPlayerRanking(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team: str
    composite_score: float
    component_breakdown: Dict[str, float]


class CustomMetricNarrative(BaseModel):
    player_name: str
    narrative: str


class CustomMetricAnomaly(BaseModel):
    player_name: str
    dominant_stat: str
    contribution_pct: float


class CustomMetricResponse(BaseModel):
    metric_label: str
    metric_interpretation: str
    player_rankings: List[CustomMetricPlayerRanking]
    top_player_narratives: List[CustomMetricNarrative]
    anomalies: List[CustomMetricAnomaly]
    validation_warnings: List[str]
