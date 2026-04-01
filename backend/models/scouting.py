from typing import Dict, List, Optional

from pydantic import BaseModel


class ScoutingEvidence(BaseModel):
    label: str
    value: Optional[float] = None
    context: Optional[str] = None


class ScoutingClaim(BaseModel):
    title: str
    summary: str
    evidence: List[ScoutingEvidence]


class ScoutingSection(BaseModel):
    eyebrow: str
    title: str
    claims: List[ScoutingClaim]


class PlayTypeScoutingReportResponse(BaseModel):
    team_abbreviation: str
    opponent_abbreviation: str
    season: str
    sections: List[ScoutingSection]
    print_meta: Dict[str, str]
    warnings: List[str]
