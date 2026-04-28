from __future__ import annotations

from typing import Dict, List

from fastapi import HTTPException

from models.methodology import MethodologyDetailResponse, MethodologyDomain, MethodologyRegistryResponse


REGISTRY_VERSION = "methodology_registry_v1"


_DOMAINS: List[MethodologyDomain] = [
    MethodologyDomain(
        domain="shot_lab",
        label="Shot Lab and Shot Diagnosis",
        methodology_version="shot_quality_v1",
        status="active_with_rigor_followups",
        question_answered="How favorable are a player's shots, and is shot making beating expectation?",
        input_families=["player_shot_charts", "shot_quality_baselines", "play_by_play_events"],
        sample_gates=["Summary confidence high at 300+ attempts, medium at 100+, low below 100.", "Diagnosis requires 50 tracked shots and usable coverage."],
        confidence_rules=["Coverage state plus shot-attempt reliability drive interpretation."],
        reliability_policy="Use empirical Bayes shot-making stabilization and uncertainty bands as the next upgrade over hard bucket fallback.",
        explainability_policy="Expose expected-vs-actual deltas and additive drivers for location, shot value, clock, action family, and coverage.",
        known_limitations=["No defender-distance model unless tracking rows are available.", "Creation labels remain proxy-based."],
        validation_notes=["Validate expected shot model against a naive zone-only baseline on held-out error."],
        last_validation_date="2026-04-28",
        implementation_refs=["backend/services/shot_intelligence_service.py", "backend/services/shot_diagnosis_service.py"],
    ),
    MethodologyDomain(
        domain="team_fit",
        label="Team-Fit Intelligence",
        methodology_version="team_fit_v2",
        status="active_with_lineup_context_followup",
        question_answered="How well does a player supply value his roster needs, and where might fit improve?",
        input_families=["season_stats", "players", "teams", "lineup_stats", "player_analysis_contexts"],
        sample_gates=["Same 20-game role-vector gate as similarity.", "Alternative teams need at least 3 qualifying roster rows."],
        confidence_rules=["Roster sample, driver clarity, and warnings determine current confidence."],
        reliability_policy="Attach reliability to roster sample and driver clarity; future v3 should calibrate better-fit thresholds from historical examples.",
        explainability_policy="Show filled gaps, duplicated teammate strengths, role runway, and risk notes.",
        known_limitations=["No salary, contract, trade feasibility, or probability modeling.", "Same-season roster fit, not lineup simulation."],
        validation_notes=["Pressure-test Tatum/BOS overlap, traded TOT rows, thin rosters, specialists, and bad-fit cases."],
        last_validation_date="2026-04-28",
        implementation_refs=["backend/services/team_fit_service.py", "backend/services/similarity_service.py"],
    ),
    MethodologyDomain(
        domain="similarity",
        label="Player Similarity",
        methodology_version="similarity_v2",
        status="active_with_covariance_followup",
        question_answered="Which player-seasons are statistically closest by role and production?",
        input_families=["season_stats", "players", "player_archetype_service"],
        sample_gates=["20-game minimum and required feature completeness."],
        confidence_rules=["Feature completeness and pool size drive reliability."],
        reliability_policy="Current weighted Euclidean distance is transparent; future shrinkage Mahalanobis should address correlated features.",
        explainability_policy="Decompose distance by feature group so users understand why a comp appears.",
        known_limitations=["Similarity is resemblance, not quality, trajectory, or outcome prediction."],
        validation_notes=["Peer sets should be stable under small stat perturbations."],
        last_validation_date="2026-04-28",
        implementation_refs=["backend/services/similarity_service.py"],
    ),
    MethodologyDomain(
        domain="trend",
        label="Trend and Trajectory Intelligence",
        methodology_version="trend_intelligence_v1",
        status="active_with_bayesian_change_followup",
        question_answered="Is recent role or production change meaningful, noisy, matchup-driven, or injury-limited?",
        input_families=["player_game_logs", "game_player_stats", "player_analysis_contexts", "player_on_off"],
        sample_gates=["Player trend needs at least five regular-season game logs."],
        confidence_rules=["Recent-window size, availability context, and impact support drive interpretation."],
        reliability_policy="Future version should use Bayesian change detection and exponentially weighted recent form.",
        explainability_policy="Keep raw deltas visible while labeling injury-limited or noisy reads honestly.",
        known_limitations=["Current game-log role status is not a direct coach-intent model."],
        validation_notes=["Injury-limited minute drops must not become trust-loss labels."],
        last_validation_date="2026-04-28",
        implementation_refs=["backend/services/player_trend_service.py", "backend/services/trajectory_service.py"],
    ),
    MethodologyDomain(
        domain="opportunity",
        label="Opportunity Workspace",
        methodology_version="opportunity_v1",
        status="active_with_uplift_followup",
        question_answered="Which players show evidence of untapped role upside?",
        input_families=["season_stats", "player_on_off", "lineup_stats"],
        sample_gates=["Lineup rows need 100+ possessions.", "Confidence uses minutes per game and on-court minutes."],
        confidence_rules=["High at 28+ MPG and 500+ on minutes; medium at 18+ MPG and 200+ on minutes."],
        reliability_policy="Current capped z-score blend should evolve toward comparable role-expansion uplift estimates.",
        explainability_policy="Preserve current component drivers and add upside/downside/evidence strength.",
        known_limitations=["Directional, not a guarantee that efficiency survives a larger role."],
        validation_notes=["Role-player expansion fixtures should preserve efficiency only when comparable evidence supports it."],
        last_validation_date="2026-04-28",
        implementation_refs=["backend/services/opportunity_service.py"],
    ),
    MethodologyDomain(
        domain="style_xray",
        label="Style X-Ray and Team Identity",
        methodology_version="style_xray_v1",
        status="active_with_latent_space_followup",
        question_answered="What style identity best describes a team relative to the league?",
        input_families=["game_team_stats", "warehouse games", "play_type_proxy"],
        sample_gates=["Recent window warnings when fewer games than requested are available."],
        confidence_rules=["Label margin, recent drift, neighbor support, and play-type coverage should drive confidence."],
        reliability_policy="Future PCA/factor space should complement centroid distances while preserving readable labels.",
        explainability_policy="Map latent or centroid features back to pace, spacing, paint pressure, assist rate, and turnover profile.",
        known_limitations=["Paint pressure and transition remain proxies.", "Centroids simplify mixed identities."],
        validation_notes=["Track style identity drift teams and known matchup interaction cases."],
        last_validation_date="2026-04-28",
        implementation_refs=["backend/services/style_feature_service.py", "backend/services/style_xray_service.py"],
    ),
    MethodologyDomain(
        domain="mvp",
        label="MVP and Award Modeling",
        methodology_version="mvp_case_v3",
        status="active_with_uncertainty_followup",
        question_answered="Who has the best basketball value and strongest voter-facing award case?",
        input_families=["season_stats", "player_game_logs", "team_season_stats", "player_on_off", "gravity"],
        sample_gates=["Candidate pool and impact-metric coverage determine confidence."],
        confidence_rules=["Coverage, sample stability, and signal agreement produce candidate confidence."],
        reliability_policy="Add uncertainty bands and sensitivity reporting around pillar weights.",
        explainability_policy="Keep Basketball Value separate from Award Case, with capped modifiers clearly labeled.",
        known_limitations=["Imported impact metrics have external opaque methodologies.", "Clutch and signature samples are volatile."],
        validation_notes=["Calibrate Award Case against historical voting outcomes; keep Basketball Value basketball-first."],
        last_validation_date="2026-04-28",
        implementation_refs=["backend/services/mvp_service.py", "backend/services/gravity_service.py"],
    ),
    MethodologyDomain(
        domain="custom_metrics",
        label="Custom Metrics and Ask Registry",
        methodology_version="custom_metric_v1",
        status="active_with_reliability_warnings_followup",
        question_answered="How should user-defined weighted composites rank players?",
        input_families=["season_stats", "query_metric_registry"],
        sample_gates=["At least five eligible player rows are required."],
        confidence_rules=["Warnings surface weight concentration, mixed metric families, missing stats, and dominant components."],
        reliability_policy="Add low-sample and collinearity warnings for selected components.",
        explainability_policy="Show weighted z-score contributions and plain-language narratives.",
        known_limitations=["Composite quality depends on component choices and filter pool."],
        validation_notes=["Suggested default composites should come from validated methodology families."],
        last_validation_date="2026-04-28",
        implementation_refs=["backend/services/custom_metric_service.py", "backend/services/query_metric_registry.py"],
    ),
]

_DOMAIN_MAP: Dict[str, MethodologyDomain] = {domain.domain: domain for domain in _DOMAINS}


def list_methodologies() -> MethodologyRegistryResponse:
    return MethodologyRegistryResponse(version=REGISTRY_VERSION, domains=_DOMAINS)


def get_methodology_detail(domain: str) -> MethodologyDetailResponse:
    key = domain.strip().lower().replace("-", "_")
    item = _DOMAIN_MAP.get(key)
    if item is None:
        raise HTTPException(status_code=404, detail="Methodology domain '{0}' not found.".format(domain))
    related = [candidate.domain for candidate in _DOMAINS if candidate.domain != item.domain][:4]
    steps = [
        "Keep raw descriptive output visible alongside adjusted or reliability-weighted output.",
        "Add validation fixtures before changing score weights or label thresholds.",
        "Update specs/platform-methodology.md when this methodology materially changes.",
    ]
    return MethodologyDetailResponse(**item.model_dump(), related_domains=related, recommended_next_steps=steps)
