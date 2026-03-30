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


class GameTeamBoxScore(BaseModel):
    team_id: int
    team_abbreviation: Optional[str] = None
    is_home: bool
    won: Optional[bool] = None
    pts: int = 0
    reb: int = 0
    ast: int = 0
    stl: int = 0
    blk: int = 0
    tov: int = 0
    fgm: int = 0
    fga: int = 0
    fg_pct: Optional[float] = None
    fg3m: int = 0
    fg3a: int = 0
    fg3_pct: Optional[float] = None
    ftm: int = 0
    fta: int = 0
    ft_pct: Optional[float] = None
    oreb: int = 0
    dreb: int = 0
    pf: int = 0
    plus_minus: Optional[float] = None


class GamePlayerBoxScore(BaseModel):
    player_id: int
    player_name: str
    team_id: Optional[int] = None
    team_abbreviation: Optional[str] = None
    is_starter: bool
    wl: Optional[str] = None
    min: Optional[float] = None
    pts: int = 0
    reb: int = 0
    ast: int = 0
    stl: int = 0
    blk: int = 0
    tov: int = 0
    fgm: int = 0
    fga: int = 0
    fg_pct: Optional[float] = None
    fg3m: int = 0
    fg3a: int = 0
    fg3_pct: Optional[float] = None
    ftm: int = 0
    fta: int = 0
    ft_pct: Optional[float] = None
    oreb: int = 0
    dreb: int = 0
    pf: int = 0
    plus_minus: Optional[float] = None


class GameSummaryResponse(BaseModel):
    game_id: str
    season: str
    game_date: Optional[str] = None
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    home_team_abbreviation: Optional[str] = None
    away_team_abbreviation: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    materialized: bool
    home_team_stats: Optional[GameTeamBoxScore] = None
    away_team_stats: Optional[GameTeamBoxScore] = None
    players: List[GamePlayerBoxScore]
