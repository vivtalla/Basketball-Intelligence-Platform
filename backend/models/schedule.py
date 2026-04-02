from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel


class UpcomingScheduleGame(BaseModel):
    game_id: str
    season: str
    game_date: Optional[date] = None
    status: str
    home_team_abbreviation: Optional[str] = None
    home_team_name: Optional[str] = None
    away_team_abbreviation: Optional[str] = None
    away_team_name: Optional[str] = None
