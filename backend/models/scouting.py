from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ScoutingEvidence(BaseModel):
    label: str
    value: Optional[float] = None
    context: Optional[str] = None


class ClaimInferenceConfidence(BaseModel):
    """Sprint 65: calibrated confidence that a scouting claim is backed by real events.

    level ∈ {high, medium, low} based on three reasons:
      * anchored_event_count — PBP events that matched the claim above the score floor
      * opponent_specific_event_count — subset of anchored events from games vs this opponent
      * evidence_source_diversity — how many distinct evidence sources support the claim
        (PBP events + claim.evidence records + linkage_quality tiers present)
    """
    level: str                                 # "high" | "medium" | "low"
    reasons: List[str] = Field(default_factory=list)
    anchored_event_count: int = 0
    opponent_specific_event_count: int = 0
    evidence_source_diversity: int = 0


class ScoutingClaim(BaseModel):
    claim_id: str
    title: str
    summary: str
    evidence: List[ScoutingEvidence]
    clip_anchor_ids: List[str] = Field(default_factory=list)
    drilldowns: List[str] = Field(default_factory=list)
    inference_confidence: Optional[ClaimInferenceConfidence] = None  # Sprint 65


class ScoutingSection(BaseModel):
    eyebrow: str
    title: str
    claims: List[ScoutingClaim]


class ScoutingClipAnchor(BaseModel):
    clip_anchor_id: str
    claim_id: str
    game_id: str
    game_date: Optional[str] = None
    opponent_abbreviation: Optional[str] = None
    event_id: Optional[int] = None
    source_event_id: Optional[str] = None
    action_number: Optional[int] = None
    order_index: Optional[int] = None
    period: Optional[int] = None
    clock: Optional[str] = None
    event_type: Optional[str] = None
    action_family: Optional[str] = None
    title: str
    reason: str
    evidence_summary: str
    event_description: Optional[str] = None
    linkage_quality: str = "timeline"
    source_context: Optional[Dict[str, str]] = None
    deep_link_url: str
    opponent_specific: bool = False            # Sprint 65: true when the anchor's game is vs this opponent


class ScoutingLaunchContext(BaseModel):
    pre_read_url: str
    scouting_url: str
    compare_url: str
    export_url: str


class PlayTypeScoutingReportResponse(BaseModel):
    team_abbreviation: str
    opponent_abbreviation: str
    season: str
    data_status: str
    sections: List[ScoutingSection]
    clip_anchors: List[ScoutingClipAnchor]
    launch_context: ScoutingLaunchContext
    print_meta: Dict[str, str]
    warnings: List[str]


class ScoutingClipExportRequest(BaseModel):
    team: str
    opponent: str
    season: str
    claim_ids: List[str] = Field(default_factory=list)
    clip_anchor_ids: List[str] = Field(default_factory=list)
    return_to: Optional[str] = None


class ScoutingClipExportResponse(BaseModel):
    team_abbreviation: str
    opponent_abbreviation: str
    season: str
    data_status: str
    export_title: str
    clip_count: int
    clip_anchors: List[ScoutingClipAnchor]
    warnings: List[str]
