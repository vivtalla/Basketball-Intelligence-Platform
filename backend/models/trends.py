from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class TrendSeriesPoint(BaseModel):
    label: str
    value: Optional[float] = None


class TrendCard(BaseModel):
    card_id: str
    title: str
    direction: Literal["up", "down", "flat"]
    magnitude: Optional[float] = None
    significance: Literal["high", "medium", "low"]
    summary: str
    series: List[TrendSeriesPoint]
    supporting_stats: Dict[str, Optional[float]]
    drilldowns: List[str]


class TrendCardsResponse(BaseModel):
    team_abbreviation: str
    team_name: str
    season: str
    window_games: int
    cards: List[TrendCard]
    warnings: List[str]


class WhatIfRequest(BaseModel):
    team: str
    season: str
    scenario_type: str
    delta: float
    window: int = 10
    opponent: Optional[str] = None
    context: Dict[str, str] = Field(default_factory=dict)


class WhatIfComparablePattern(BaseModel):
    team_abbreviation: str
    season: str
    summary: str
    distance: Optional[float] = None


class WhatIfResponse(BaseModel):
    team_abbreviation: str
    season: str
    scenario_type: str
    delta: float
    expected_direction: str
    confidence: Literal["high", "medium", "low"]
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    driver_features: List[str]
    comparable_patterns: List[WhatIfComparablePattern]
    warnings: List[str]
