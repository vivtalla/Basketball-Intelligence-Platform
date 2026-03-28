from typing import List, Optional

from pydantic import BaseModel


class GameEvent(BaseModel):
    action_number: int
    period: Optional[int] = None
    clock: Optional[str] = None
    team_id: Optional[int] = None
    team_abbreviation: Optional[str] = None
    player_id: Optional[int] = None
    player_name: Optional[str] = None
    event_type: Optional[str] = None
    description: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None


class GameTimelinePoint(BaseModel):
    action_number: int
    period: Optional[int] = None
    clock: Optional[str] = None
    home_score: int
    away_score: int
    scoring_team_id: Optional[int] = None
    scoring_team_abbreviation: Optional[str] = None
    description: Optional[str] = None


class GamePlayerSummary(BaseModel):
    player_id: int
    player_name: str
    team_id: Optional[int] = None
    team_abbreviation: Optional[str] = None
    pts: int = 0
    reb: int = 0
    ast: int = 0
    stl: int = 0
    blk: int = 0
    tov: int = 0
    min: Optional[float] = None
    plus_minus: Optional[int] = None


class GameDetailResponse(BaseModel):
    game_id: str
    season: str
    game_date: Optional[str] = None
    matchup: Optional[str] = None
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    home_team_name: Optional[str] = None
    home_team_abbreviation: Optional[str] = None
    away_team_name: Optional[str] = None
    away_team_abbreviation: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    timeline: List[GameTimelinePoint]
    top_players: List[GamePlayerSummary]
    events: List[GameEvent]
