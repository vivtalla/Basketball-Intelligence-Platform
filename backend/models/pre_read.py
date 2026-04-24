from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from models.scouting import ClaimInferenceConfidence, ScoutingClipAnchor, ScoutingEvidence
from models.team import TeamAvailabilityResponse, TeamFocusLever, TeamPrepQueueItem
from models.styles import StyleShotProfileDriver
from models.trends import ReplayLaunchTarget


class WorkflowLaunchLinks(BaseModel):
    pre_read_url: str
    scouting_url: str
    compare_url: str
    prep_url: str
    follow_through_url: str
    game_review_url: str
    style_xray_url: Optional[str] = None
    replay_url: Optional[str] = None


class PreReadSnapshotRef(BaseModel):
    snapshot_id: str
    share_url: str
    created_at: str
    title: Optional[str] = None
    note: Optional[str] = None
    packet_summary: Optional["PreReadPacketSummary"] = None


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


class PreReadPacketSelection(BaseModel):
    claim_ids: List[str] = Field(default_factory=list)
    clip_anchor_ids: List[str] = Field(default_factory=list)


class PreReadScoutingPacketClaim(BaseModel):
    claim_id: str
    title: str
    summary: str
    evidence: List[ScoutingEvidence] = Field(default_factory=list)
    inference_confidence: Optional[ClaimInferenceConfidence] = None
    clip_anchors: List[ScoutingClipAnchor] = Field(default_factory=list)


class PreReadScoutingPacket(BaseModel):
    selection: PreReadPacketSelection = Field(default_factory=PreReadPacketSelection)
    claims: List[PreReadScoutingPacketClaim] = Field(default_factory=list)
    generated_at: Optional[str] = None
    source_url: Optional[str] = None


class PreReadPacketSummary(BaseModel):
    claim_count: int = 0
    clip_count: int = 0
    claim_titles: List[str] = Field(default_factory=list)


class PreReadSlide(BaseModel):
    title: str
    eyebrow: str
    bullets: List[str]


class PreReadPrepContext(BaseModel):
    prep_item: Optional[TeamPrepQueueItem] = None
    urgency: Optional[str] = None
    headline: Optional[str] = None
    urgency_rationale: Optional[str] = None
    best_edge_label: Optional[str] = None
    best_edge_rationale: Optional[str] = None
    first_adjustment_label: Optional[str] = None
    first_adjustment_rationale: Optional[str] = None
    shot_profile_driver: Optional[StyleShotProfileDriver] = None
    style_replay_target: Optional[ReplayLaunchTarget] = None
    xray_url: Optional[str] = None
    replay_url: Optional[str] = None


class PreReadDeckResponse(BaseModel):
    season: str
    team_abbreviation: str
    opponent_abbreviation: str
    data_status: str = "ready"
    canonical_source: str = "warehouse-plus-derived"
    runtime_policy: Optional[str] = None
    generated_at: Optional[str] = None
    focus_levers: List[TeamFocusLever]
    matchup_advantages: List[str]
    adjustments: List[PreReadAdjustment]
    team_availability: TeamAvailabilityResponse
    opponent_availability: TeamAvailabilityResponse
    slides: List[PreReadSlide]
    launch_links: WorkflowLaunchLinks
    prep_context: Optional[PreReadPrepContext] = None
    scouting_packet: Optional[PreReadScoutingPacket] = None
    snapshot: Optional[PreReadSnapshotRef] = None
    warnings: List[str] = Field(default_factory=list)


class PreReadSnapshotCreateRequest(BaseModel):
    team: str
    opponent: str
    season: str
    game_id: Optional[str] = None
    source_view: Optional[str] = None
    source_snapshot_id: Optional[str] = None
    title: Optional[str] = None
    note: Optional[str] = None
    packet_selection: Optional[PreReadPacketSelection] = None
    context: Dict[str, str] = Field(default_factory=dict)


class PreReadSnapshotUpdateRequest(BaseModel):
    title: Optional[str] = None
    note: Optional[str] = None


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
    title: Optional[str] = None
    note: Optional[str] = None
    packet_summary: Optional[PreReadPacketSummary] = None


class PreReadSnapshotResponse(BaseModel):
    snapshot_id: str
    share_url: str
    created_at: str
    title: Optional[str] = None
    note: Optional[str] = None
    packet_summary: Optional[PreReadPacketSummary] = None
    context: PreReadContext
    deck: PreReadDeckResponse


class PreReadSnapshotListResponse(BaseModel):
    items: List[PreReadSnapshotSummary]
