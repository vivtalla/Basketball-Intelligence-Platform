from typing import List

from pydantic import BaseModel

from models.team import TeamAvailabilityResponse, TeamFocusLever


class PreReadAdjustment(BaseModel):
    label: str
    recommendation: str


class PreReadSlide(BaseModel):
    title: str
    eyebrow: str
    bullets: List[str]


class PreReadDeckResponse(BaseModel):
    season: str
    team_abbreviation: str
    opponent_abbreviation: str
    focus_levers: List[TeamFocusLever]
    matchup_advantages: List[str]
    adjustments: List[PreReadAdjustment]
    team_availability: TeamAvailabilityResponse
    opponent_availability: TeamAvailabilityResponse
    slides: List[PreReadSlide]
