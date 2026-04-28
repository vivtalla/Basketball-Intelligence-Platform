"""Pydantic schemas for the playoff API surface (Sprint 73).

Covers the bracket overview, per-series detail, today's slate, and the
series simulator response.
"""
from __future__ import annotations

from datetime import date as _date
from typing import List, Literal, Optional

from pydantic import BaseModel


PlayoffSeriesStatus = Literal["scheduled", "active", "closed"]


class PlayoffSeriesGame(BaseModel):
    game_id: str
    game_date: Optional[_date] = None
    home_team_id: Optional[int] = None
    home_team_abbr: Optional[str] = None
    away_team_id: Optional[int] = None
    away_team_abbr: Optional[str] = None
    home_pts: Optional[int] = None
    away_pts: Optional[int] = None
    winner_team_id: Optional[int] = None
    series_game_num: Optional[int] = None


class PlayoffSeriesResponse(BaseModel):
    season: str
    round: int
    series_id: str
    top_seed_team_id: Optional[int] = None
    bottom_seed_team_id: Optional[int] = None
    top_seed_team_abbr: Optional[str] = None
    bottom_seed_team_abbr: Optional[str] = None
    top_seed: int
    bottom_seed: int
    top_wins: int
    bottom_wins: int
    status: PlayoffSeriesStatus
    winner_team_id: Optional[int] = None
    games: List[PlayoffSeriesGame] = []


class PlayoffBracketResponse(BaseModel):
    season: str
    east: List[PlayoffSeriesResponse] = []
    west: List[PlayoffSeriesResponse] = []
    finals: Optional[PlayoffSeriesResponse] = None


class PlayoffSeriesGameWithMatchup(PlayoffSeriesGame):
    """A playoff game annotated with the series context it belongs to."""
    series_id: Optional[str] = None
    season: Optional[str] = None
    round: Optional[int] = None
    top_seed_team_abbr: Optional[str] = None
    bottom_seed_team_abbr: Optional[str] = None
    top_wins: Optional[int] = None
    bottom_wins: Optional[int] = None
    status: Optional[PlayoffSeriesStatus] = None


class PlayoffTodayResponse(BaseModel):
    date: _date
    games: List[PlayoffSeriesGameWithMatchup] = []


class SeriesSimulationCurrentState(BaseModel):
    top_seed_team_abbr: Optional[str] = None
    bottom_seed_team_abbr: Optional[str] = None
    top_wins: int
    bottom_wins: int
    games_played: int
    status: PlayoffSeriesStatus


class SeriesProjectionEntry(BaseModel):
    game_num: int
    home_team_abbr: Optional[str] = None
    away_team_abbr: Optional[str] = None
    home_win_prob: float


class SeriesSimulationResponse(BaseModel):
    series_id: str
    current_state: SeriesSimulationCurrentState
    projection: List[SeriesProjectionEntry] = []
    top_seed_series_win_prob: float = 0.0
    bottom_seed_series_win_prob: float = 0.0
    trials: int = 0
