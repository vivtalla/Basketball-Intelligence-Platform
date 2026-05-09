from typing import List, Literal, Optional

from pydantic import BaseModel

LineupArchetype = Literal[
    "Elite", "Offensive Wall", "Defensive Wall", "Balanced", "Negative", "Unclassified"
]

LineupConfidence = Literal["high", "medium", "low"]


class LineupLeaderboardEntry(BaseModel):
    lineup_key: str
    player_ids: List[int]
    player_names: List[str]
    team_id: Optional[int] = None
    team_abbreviation: Optional[str] = None
    season: str
    minutes: Optional[float] = None
    possessions: Optional[int] = None
    net_rating: Optional[float] = None
    ortg: Optional[float] = None
    drtg: Optional[float] = None
    plus_minus: Optional[float] = None
    shrunk_net_rating: Optional[float] = None
    team_net_baseline: Optional[float] = None
    net_vs_baseline: Optional[float] = None
    confidence: LineupConfidence
    archetype: LineupArchetype


class LineupLeaderboardResult(BaseModel):
    season: str
    total: int
    lineups: List[LineupLeaderboardEntry]


class LineupBuilderRequest(BaseModel):
    player_ids: List[int]
    season: str
    season_type: Literal["Regular Season", "Playoffs"] = "Regular Season"


class PlayerRemovalImpact(BaseModel):
    player_id: int
    player_name: str
    lineups_without_count: int
    avg_net_rating_without: Optional[float] = None
    delta_vs_full: Optional[float] = None
    note: str


class LineupBuilderResult(BaseModel):
    submitted_player_ids: List[int]
    submitted_player_names: List[str]
    exact_match: Optional[LineupLeaderboardEntry] = None
    closest_matches: List[LineupLeaderboardEntry]
    player_removal_impacts: List[PlayerRemovalImpact]
    match_quality: Literal["exact", "partial", "none"]
    warnings: List[str]


class SublineupsResult(BaseModel):
    team_id: int
    team_abbreviation: str
    season: str
    size: int
    lineups: List[LineupLeaderboardEntry]
