from typing import List, Literal, Optional

from pydantic import BaseModel


class TeamComparisonSnapshot(BaseModel):
    abbreviation: str
    name: str
    season: str
    recent_record: Optional[str] = None
    net_rating: Optional[float] = None
    ts_pct: Optional[float] = None
    efg_pct: Optional[float] = None
    tov_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    pace: Optional[float] = None


class TeamComparisonRow(BaseModel):
    stat_id: str
    label: str
    team_a_value: Optional[float] = None
    team_b_value: Optional[float] = None
    higher_better: bool
    format: Literal["number", "percent", "signed"]
    edge: Literal["team_a", "team_b", "even"]


class TeamComparisonStory(BaseModel):
    label: str
    summary: str
    edge: Literal["team_a", "team_b", "even"]


class TeamComparisonResponse(BaseModel):
    season: str
    team_a: TeamComparisonSnapshot
    team_b: TeamComparisonSnapshot
    rows: List[TeamComparisonRow]
    stories: List[TeamComparisonStory]
