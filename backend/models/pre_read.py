from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from models.team import TeamAvailabilityResponse, TeamFocusLever, TeamPrepQueueItem


class WorkflowLaunchLinks(BaseModel):
    pre_read_url: str
    scouting_url: str
    compare_url: str
    prep_url: str
    follow_through_url: str
    game_review_url: str


class PreReadSnapshotRef(BaseModel):
    snapshot_id: str
    share_url: str
    created_at: str


class PreReadContext(BaseModel):
    team_abbreviation: str
    opponent_abbreviation: str
    season: str
    game_id: Optional[str] = None
    source_view: Optional[str] = None
    source_snapshot_id: Optional[str] = None
    extras: Dict[str, str] = Field(default_factory=dict)


class PreReadAdjustment(BaseModel):
    label: str
    recommendation: str


class PreReadSlide(BaseModel):
    title: str
    eyebrow: str
    bullets: List[str]


class PreReadPrepContext(BaseModel):
    prep_item: Optional[TeamPrepQueueItem] = None
    urgency: Optional[str] = None
    headline: Optional[str] = None


class PreReadDeckResponse(BaseModel):
    season: str
    team_abbreviation: str
    opponent_abbreviation: str
    data_status: str = "ready"
    canonical_source: str = "warehouse-plus-derived"
    generated_at: Optional[str] = None
    focus_levers: List[TeamFocusLever]
    matchup_advantages: List[str]
    adjustments: List[PreReadAdjustment]
    team_availability: TeamAvailabilityResponse
    opponent_availability: TeamAvailabilityResponse
    slides: List[PreReadSlide]
    launch_links: WorkflowLaunchLinks
    prep_context: Optional[PreReadPrepContext] = None
    snapshot: Optional[PreReadSnapshotRef] = None
    warnings: List[str] = Field(default_factory=list)


class PreReadSnapshotCreateRequest(BaseModel):
    team: str
    opponent: str
    season: str
    game_id: Optional[str] = None
    source_view: Optional[str] = None
    source_snapshot_id: Optional[str] = None
    context: Dict[str, str] = Field(default_factory=dict)


class PreReadSnapshotSummary(BaseModel):
    snapshot_id: str
    share_url: str
    created_at: str
    team_abbreviation: str
    opponent_abbreviation: str
    season: str
    game_id: Optional[str] = None
    prep_headline: Optional[str] = None
    saved_from: Optional[str] = None


class PreReadSnapshotResponse(BaseModel):
    snapshot_id: str
    share_url: str
    created_at: str
    context: PreReadContext
    deck: PreReadDeckResponse


class PreReadSnapshotListResponse(BaseModel):
    items: List[PreReadSnapshotSummary]
