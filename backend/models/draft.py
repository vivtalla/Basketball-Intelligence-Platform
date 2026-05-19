"""Pydantic schemas for the FO3 Draft Prospect Workspace (Sprint 78).

The router returns `ProspectBoardResponse` for the board route and
`ProspectDetail` for the per-prospect deep dive.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CollegeStatLine(BaseModel):
    """Per-game pre-NBA line as it lives in `draft_prospect_stats`."""
    season: str
    league: str
    team_name: Optional[str] = None
    gp: Optional[int] = None
    min_pg: Optional[float] = None
    pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    stl_pg: Optional[float] = None
    blk_pg: Optional[float] = None
    tov_pg: Optional[float] = None
    fg_pct: Optional[float] = None
    fg3_pct: Optional[float] = None
    ft_pct: Optional[float] = None
    ts_pct: Optional[float] = None
    usg_pct: Optional[float] = None
    pace: Optional[float] = None


class NbaTranslation(BaseModel):
    """Pace-adjusted projection of pre-NBA per-game stats onto an NBA per-100 line.

    Pace adjustment: NBA ≈ 100 possessions/48; college ≈ 70 possessions/40.
    Multiplier = NBA_PACE / college_pace; per-game stats are scaled directly.
    `translation_confidence` is a 0..1 heuristic combining sample size,
    league strength, and the ratio between college and NBA pace.
    """
    source_season: str
    source_league: str
    college_pace: float
    nba_pace: float = 100.0
    pace_multiplier: float
    projected_pts_per100: Optional[float] = None
    projected_reb_per100: Optional[float] = None
    projected_ast_per100: Optional[float] = None
    projected_stl_per100: Optional[float] = None
    projected_blk_per100: Optional[float] = None
    projected_tov_per100: Optional[float] = None
    projected_ts_pct: Optional[float] = None
    projected_usg_pct: Optional[float] = None
    translation_confidence: float = Field(
        0.0, ge=0.0, le=1.0,
        description="0..1 confidence that this translation should be trusted.",
    )
    confidence_factors: List[str] = []


class NbaComp(BaseModel):
    """One NBA-comparable veteran for a draft prospect."""
    player_id: int
    player_name: str
    headshot_url: Optional[str] = None
    season: str
    team_abbreviation: Optional[str] = None
    similarity_score: float = Field(..., ge=0.0, le=100.0)
    archetype_label: Optional[str] = None
    rationale: str
    pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    ts_pct: Optional[float] = None
    usg_pct: Optional[float] = None


class MeasurementPanel(BaseModel):
    """Combine + workout measurements (lightweight fallback to listed h/w/wingspan)."""
    height_no_shoes: Optional[float] = None
    height_with_shoes: Optional[float] = None
    weight: Optional[float] = None
    wingspan: Optional[float] = None
    standing_reach: Optional[float] = None
    standing_vert: Optional[float] = None
    max_vert: Optional[float] = None
    lane_agility_seconds: Optional[float] = None
    three_quarter_sprint_seconds: Optional[float] = None
    source: Optional[str] = None


class DraftProspectSummary(BaseModel):
    """One row on the prospect board."""
    prospect_id: int
    external_id: str
    full_name: str
    draft_year: int
    age_on_draft_day: Optional[float] = None
    height_inches: Optional[float] = None
    weight_lbs: Optional[float] = None
    primary_position: Optional[str] = None
    school: Optional[str] = None
    school_type: Optional[str] = None
    consensus_rank: Optional[int] = None
    # Sprint 100 (Stream C) — additive board enrichment.
    consensus_rank_float: Optional[float] = None
    consensus_variance: Optional[float] = None
    projected_tier: Optional[str] = None
    mock_sources_count: Optional[int] = None
    headshot_url: Optional[str] = None
    archetype_label: Optional[str] = None
    pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    ts_pct: Optional[float] = None
    usg_pct: Optional[float] = None


class ProspectBoardResponse(BaseModel):
    draft_year: int
    count: int
    prospects: List[DraftProspectSummary] = []


# ── Sprint 100 (Stream C) — new response shapes for enriched detail ──


class MockRanking(BaseModel):
    """One mock-draft ranking entry on a prospect's detail."""
    source: str
    source_url: Optional[str] = None
    as_of: Optional[str] = None
    rank: int
    tier: Optional[str] = None
    position_projected: Optional[str] = None
    comp_player_name: Optional[str] = None


class CombineMeasurement(BaseModel):
    """Sprint 100 combine measurement panel with explicit attribution."""
    combine_year: Optional[int] = None
    height_no_shoes: Optional[float] = None
    height_with_shoes: Optional[float] = None
    weight: Optional[float] = None
    wingspan: Optional[float] = None
    standing_reach: Optional[float] = None
    body_fat_pct: Optional[float] = None
    hand_length: Optional[float] = None
    hand_width: Optional[float] = None
    standing_vert: Optional[float] = None
    max_vert: Optional[float] = None
    lane_agility_seconds: Optional[float] = None
    three_quarter_sprint_seconds: Optional[float] = None
    bench_press_135: Optional[int] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    as_of: Optional[str] = None


class InternationalStatLine(BaseModel):
    season: str
    league: str
    team_name: Optional[str] = None
    games: Optional[int] = None
    minutes_per_game: Optional[float] = None
    ppg: Optional[float] = None
    rpg: Optional[float] = None
    apg: Optional[float] = None
    spg: Optional[float] = None
    bpg: Optional[float] = None
    fg_pct: Optional[float] = None
    three_pct: Optional[float] = None
    ft_pct: Optional[float] = None
    usage_rate: Optional[float] = None
    ts_pct: Optional[float] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    as_of: Optional[str] = None


class HistoricalComp(BaseModel):
    """Sprint 100 outcome-aware NBA comp."""
    player_id: int
    player_name: str
    season: Optional[str] = None
    similarity: float
    outcome_tier: Optional[str] = None
    career_summary: Optional[dict] = None
    neighbourhood_confidence: Optional[str] = None
    # Sprint 104 (Stream B) — position-aware comp metadata. Surfaced on
    # NbaComp cards so users see whether the match included a positional
    # boost ("matched on position + skill profile") vs raw distance only.
    position_bucket: Optional[str] = None
    position_match: Optional[bool] = None
    rationale: Optional[str] = None
    pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    ts_pct: Optional[float] = None
    usg_pct: Optional[float] = None


class RiskIndicators(BaseModel):
    age_risk: float = Field(..., ge=0.0, le=1.0)
    sample_risk: float = Field(..., ge=0.0, le=1.0)
    level_risk: float = Field(..., ge=0.0, le=1.0)
    athleticism_risk: float = Field(..., ge=0.0, le=1.0)
    shooting_risk: float = Field(..., ge=0.0, le=1.0)


class HistoricalBaseline(BaseModel):
    n_comps: int
    n_with_outcome: int
    insufficient: bool = False
    star_pct: float = 0.0
    starter_pct: float = 0.0
    role_player_pct: float = 0.0
    bust_pct: float = 0.0


class NbaTranslationV2(BaseModel):
    """Sprint 100 translation v2 — point + 95% CIs for the primary metrics."""
    source_season: Optional[str] = None
    source_league: Optional[str] = None
    league_strength_key: Optional[str] = None
    college_pace: Optional[float] = None
    nba_pace: Optional[float] = None
    pace_multiplier: Optional[float] = None
    league_strength_multiplier: Optional[float] = None
    age_multiplier: Optional[float] = None
    combined_volume_multiplier: Optional[float] = None
    pts_per100: Optional[dict] = None    # {point, lower, upper}
    reb_per100: Optional[dict] = None
    ast_per100: Optional[dict] = None
    stl_per100: Optional[float] = None
    blk_per100: Optional[float] = None
    tov_per100: Optional[float] = None
    ts_pct: Optional[dict] = None         # {point, lower, upper}
    three_pct: Optional[float] = None
    usg_pct: Optional[float] = None
    confidence_factors: List[str] = []
    # Sprint 104 (Stream B) — alternate-league projections. None when the
    # caller doesn't request them or pool data is missing.
    alternate_paths: Optional[List["CrossLeagueProjection"]] = None


# ── Sprint 102 (Stream B) — team-fit for draft prospects ─────────────


class FitDriverLite(BaseModel):
    """One feature contribution on a ProspectTeamFit.

    Lighter than the player-side FitDriver so the prospect-detail API
    stays compact when 5 teams × 3-4 drivers each are serialized.
    """
    feature_key: str
    label: str
    prospect_z: float
    team_need_z: float
    contribution: float


class OverlapFlagLite(BaseModel):
    """One teammate overlap flag on a ProspectTeamFit."""
    feature_key: str
    teammate_name: str
    teammate_id: Optional[int] = None
    gap: float


class ProspectTeamFit(BaseModel):
    """One team's fit profile for a draft prospect.

    Surfaced as ``team_fit_top: List[ProspectTeamFit]`` on ProspectDetail
    (top-N teams ranked by fit_score desc). Also drives the
    ``best_team_fit_*`` denormalized fields on HistoricalProspectEntry.
    """
    team_abbreviation: str
    team_id: Optional[int] = None
    fit_score: float = Field(..., ge=0.0, le=100.0)
    fit_label: str  # "better_fit" | "similar_fit" | "different_fit"
    summary: str
    value_drivers: List[FitDriverLite] = []
    overlap_flags: List[OverlapFlagLite] = []
    role_runway_note: Optional[str] = None
    methodology_version: str = "team_fit_v3_draft_adapter"


# ── Sprint 104 (Stream B) — strengths/weaknesses synthesis + cross-league ──


class ProspectFeatureNote(BaseModel):
    """One strength or weakness highlight derived from feature z-score."""
    feature_key: str
    label: str
    z_score: float


class ProspectProfile(BaseModel):
    """Algorithmic synthesis of a prospect's profile vs same-year same-bucket pool.

    Sprint 104 (Stream B). Derived on demand from existing
    DraftProspectStat rows — no new data source required. Drives the
    StrengthsWeaknessesPanel on the prospect-detail page.
    """
    archetype_label: str
    archetype_distance: float
    strengths: List[ProspectFeatureNote] = []
    weaknesses: List[ProspectFeatureNote] = []
    pool_size: int
    pool_bucket: Optional[str] = None
    insufficient_pool: bool = False
    methodology_version: str = "synthesis_v1"


class CrossLeagueProjection(BaseModel):
    """Alternate-path per-100 projection (if-G-League, if-Euroleague).

    Compact; just the primary per-100 metrics so response size stays
    manageable. Surfaced as ``alternate_paths`` on NbaTranslationV2.
    """
    league: str
    league_strength_key: str
    league_strength_multiplier: float
    projected_pts_per100: Optional[float] = None
    projected_reb_per100: Optional[float] = None
    projected_ast_per100: Optional[float] = None
    projected_ts_pct: Optional[float] = None
    projected_usg_pct: Optional[float] = None


class HistoricalProspectEntry(BaseModel):
    """One row in the historical-class endpoint (Sprint 100 new endpoint)."""
    prospect_id: int
    name: str
    draft_pick: Optional[int] = None
    draft_team: Optional[str] = None
    predicted_tier_at_time: Optional[str] = None
    outcome_tier: Optional[str] = None
    career_summary: Optional[dict] = None
    # Sprint 102 (Stream B) — denormalized top-1 team-fit pin for sortable
    # table column. Computed on demand from the prospect's translated NBA
    # profile vs the rosters of the prospect's draft season.
    best_team_fit_abbr: Optional[str] = None
    best_team_fit_score: Optional[float] = None


class HistoricalClassResponse(BaseModel):
    draft_year: int
    prospects: List[HistoricalProspectEntry] = []
    as_of: str


class ProspectDetail(BaseModel):
    summary: DraftProspectSummary
    bio: Optional[str] = None
    college_stats: List[CollegeStatLine] = []
    translation: Optional[NbaTranslation] = None
    measurement: Optional[MeasurementPanel] = None
    nba_comps: List[NbaComp] = []
    # Sprint 100 (Stream C) — additive enriched fields. v1 callers see no
    # breaking change; v2-aware callers consume these new top-level keys.
    mock_rankings: List[MockRanking] = []
    combine_measurements: Optional[CombineMeasurement] = None
    international_stats: List[InternationalStatLine] = []
    historical_comps: List[HistoricalComp] = []
    risk_indicators: Optional[RiskIndicators] = None
    historical_baseline: Optional[HistoricalBaseline] = None
    translation_v2: Optional[NbaTranslationV2] = None
    # Sprint 102 (Stream B) — top-N teams ranked by fit_score desc. Computed
    # from the prospect's translated NBA stat profile against current
    # NBA team rosters via the team_fit_v3 algorithm (adapted).
    team_fit_top: Optional[List[ProspectTeamFit]] = None
    # Sprint 104 (Stream B) — algorithmic strengths/weaknesses + archetype.
    profile: Optional[ProspectProfile] = None
