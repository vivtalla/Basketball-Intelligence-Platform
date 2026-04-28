# Methodology Validation Harness

Last updated: 2026-04-28

This document defines the validation layer for CourtVue methodology work. It is the companion to `specs/platform-methodology.md`: the methodology doc explains how each model works, while this document explains how we pressure-test whether the model is behaving responsibly.

> Validation report is `methodology_validation_v2`. Every registered methodology domain now has at least one named regression fixture; reliability primitives accept the documented set of confidence levels (`0.80`, `0.90`, `0.95`, `0.99`) without silent z-value fallbacks.

## Validation Principles

- Every methodology-bearing service should expose a version, input families, sample gates, confidence or reliability rules, known limitations, and validation notes.
- Validation should include golden qualitative fixtures, statistical calibration where historical labels exist, and drift checks when upstream data or code changes.
- Raw descriptive metrics stay visible even when adjusted or shrinkage-based estimates are added.
- Explainability is part of validation: if a score moves, the driver breakdown should explain why.

## Shared Golden Fixtures

Use these as recurring smoke cases when methodology changes:

- Tatum/BOS Team-Fit: should surface teammate overlap with high-skill wings and avoid treating overlap as a pure negative.
- Traded player with `TOT`: should resolve or warn clearly rather than inventing a current team.
- Injured-star trend window: raw production drop should not become a blunt `losing_trust` label when injury context overlaps the window.
- Role-player opportunity expansion: should highlight efficient, low-usage players only when team impact and role-fit evidence also support it.
- Specialist shooter Shot Lab profile: should separate shot diet, shot quality, and shot-making overperformance.
- High-variance small lineup: raw on/off can be shown, but adjusted-impact or confidence language must flag sample risk.
- Style identity drift team: recent movement should be visible without overwriting season identity too aggressively.
- MVP candidate with strong Basketball Value but weak Award Case: basketball value and voter-facing award case should remain separate.

## Calibration Targets by Domain

### Shot Lab

Primary target:

- Expected-shot models should beat a naive zone-only baseline on held-out Brier-style error or log loss.

Current v2 validation:

- Verify hierarchical baseline blending is stable: exact context, zone-distance-value, zone-value, shot-value, league.
- Verify low-attempt bins show low confidence and uncertainty instead of strong sustainability claims.
- Verify `analysis_metadata.reliability_score` rises with attempts, a Wilson interval is present for actual FG%, and stabilized PPS delta shrinks thin samples toward expected value.

Current rigor upgrade:

- `shot_quality_v2` uses hierarchical baseline blending and empirical Bayes stabilization for shot-making deltas to distinguish repeatable finishing from hot streaks.

### Team-Fit

Primary target:

- Better-fit labels should clear calibrated delta and reliability gates, not just a raw score edge.

Current v3 validation:

- Current team is excluded from alternates.
- `TOT` rows produce clear warnings or latest-qualified-season fallback when appropriate.
- Duplicate features include covering teammate, player z, teammate z, feature label, and `0.4x` multiplier.
- Thin rosters reduce confidence and produce sample notes.
- `analysis_metadata.driver_breakdown` exposes skill supply, roster need, role competition, and alternate delta.
- Current fit is separated from theoretical best usage so stars are not punished solely for teammate overlap.
- Better-fit labels are reliability-gated: +5 at high reliability, +7 at medium, never better-fit at low reliability.
- Injury/recovery/availability contexts change confidence language, not raw component math.

Planned calibration upgrade:

- Calibrate better-fit thresholds from historical roster examples.
- Add lineup role compatibility and injury/context flags without introducing salary or trade-feasibility logic.

## Validation Endpoint

`GET /api/methodology/validation` returns the structured fixture set. The current list (`methodology_validation_v2`) covers every registered methodology domain:

- Team-Fit: `team_fit_tatum_bos_overlap`, `team_fit_traded_tot`, `team_fit_thin_playoff_sample`, `team_fit_role_player_clear_fit`
- Shot Lab: `shot_lab_specialist_shooter`, `shot_lab_low_attempt_hot_streak`
- Similarity: `similarity_role_pool_stability`, `similarity_shrinkage_collinearity`
- Trend: `trend_injured_star_window`, `trend_bayesian_change_evidence`
- Opportunity: `opportunity_role_expansion_evidence`
- Style X-Ray: `style_xray_drift_team`, `style_xray_latent_space`
- MVP: `mvp_value_versus_award_split`, `mvp_basketball_value_weight_sensitivity`
- Archetype: `archetype_borderline_role_label`, `archetype_soft_memberships`
- Custom Metrics: `custom_metrics_collinear_components`, `custom_metrics_weight_sensitivity`
- Gravity: `gravity_proxy_versus_official`
- Scouting: `scouting_brief_evidence_linkage`, `scouting_brief_contradictions`
- Playoffs: `playoffs_thin_series_sample`

### Similarity

Primary target:

- Peer sets should be stable under small stat perturbations and explain which feature groups drive distance.

Current v3 validation:

- Same-season z-score pool uses qualified rows only.
- Team-Fit mode applies duplicate penalties without changing default similarity responses.
- `distance_method` selects between `weighted_euclidean` (default) and `shrunk_mahalanobis` (similarity_v3). Mahalanobis distance is built on the candidate pool's shrunk inverse covariance (`λ = 0.2` by default) so correlated features no longer double-count against each other.
- The service falls back to weighted Euclidean automatically below `3 × n_features` candidate rows or whenever the inverse cannot be computed; the resolved method is exposed as `distance_method_used` on every comp.

Planned rigor upgrade:

- Explicit role-only, production-quality, and age-development modes.
- Calibrate the shrinkage parameter against held-out historical neighbor stability.

### Trend and Trajectory

Primary target:

- Injury-limited role drops should not be classified as coach-trust loss.

Current v2 validation:

- Same minutes/production drop is `losing_trust` without injury context and injury-contextual with overlapping injury/recovery context.
- Recent-window deltas remain visible after interpretation changes.
- Bayesian change scores attach a `(z_score, posterior_change_probability)` per metric (minutes, points, plus_minus). Probabilities ≥ 0.7 indicate a meaningful shift; ≤ 0.3 indicate within-noise drift. Baselines below four games short-circuit so thin samples don't produce false confidence.

Planned rigor upgrade:

- Exponentially-weighted recent form so the most recent games dominate the change score.
- Schedule strength and role/minute context conditioning before computing the change.
- Coach-trust trend should use starts, closing-lineup appearances, minutes, and availability-adjusted expectations.

### Opportunity

Primary target:

- Opportunity calls should identify role upside without mistaking one noisy on/off spike for a scalable role.

Current validation:

- Composite weights remain exposed.
- Z-score caps prevent single-axis domination.
- Directional hints require concurrent efficiency-load and team-impact evidence.
- `analysis_metadata.reliability_score` reflects the full filtered pool, not only visible leaderboard rows.

Planned rigor upgrade:

- Interpretable uplift model estimating whether efficiency survives larger usage based on historical comparable role expansions.
- League-wide peer opportunity board and downside-risk bands.

### Style X-Ray

Primary target:

- Style labels should be season-relative, stable enough for staff communication, and sensitive enough to meaningful recent drift.

Current v2 validation:

- Percentile vectors and nearest-centroid distances are reproducible.
- Label stability uses the margin between top style matches.
- Latent space via PCA: the response attaches a top-2 axis decomposition with subject coordinates, explained-variance ratios, and the strongest positive/negative feature loadings on each axis. League pools below `2 × n_features` complete rows fall back to None so coaches stay on the centroid view.

Planned rigor upgrade:

- Opponent-specific style interaction showing which identities stress or neutralize each other.
- Calibrated PCA shrinkage that adapts to league pool size.

### MVP, Gravity, and Awards

Primary target:

- Basketball Value and Award Case should remain separable, and proxy Gravity should not overclaim tracking-grade certainty.

Current v4 validation:

- Basketball Value and Award Case ranks can diverge.
- Gravity context adjustment is capped and confidence-scaled.
- Profile-comparison sensitivity reports rank movement across the box-first / balanced / impact-consensus profiles.
- Weight-perturbation sensitivity attaches a `MvpWeightSensitivity` object to every race response with `max_rank_change` and `top_set_jaccard` over ±10% perturbations of `REFINED_VALUE_WEIGHTS`; the `interpretation` copy escalates to a coach-readable warning when the top-5 ordering flips by more than one rank.

Planned rigor upgrade:

- Historical voter calibration for Award Case.
- Dated historical snapshots before using impact, clutch, Gravity, or opponent context in timeline reconstruction.

### Scouting, Prep, and Follow-Through

Primary target:

- Evidence confidence should reflect directness, opponent specificity, recency, and claim-driver strength.

Current v2 validation:

- Packet snapshots stay frozen after save.
- Claim links distinguish exact/derived event links from timeline-only evidence.
- Cross-card contradiction detection covers three rule families (role/trajectory, role/usage, strengths/shot-profile) and skips low-confidence archetypes plus insufficient-sample diagnoses to avoid noise. Tensions surface as a structured `contradictions` list rather than blending into card copy.

Planned rigor upgrade:

- Calibrated evidence confidence model.
- Expanded contradiction rule set covering opportunity-vs-trajectory and shot-profile-vs-archetype tensions.

### Custom Metrics and Ask

Primary target:

- User-built composites should warn when they mix metric families, low-sample components, highly collinear inputs, or fragile rankings under small weight perturbations.

Current v2 validation:

- Weights are normalized.
- Dominant single-component influence creates a warning.
- Lower-is-better stats invert correctly.
- Pearson correlation ≥ 0.85 between component pairs surfaces a collinearity warning.
- Top-5 ranking sensitivity under ±10% weight perturbations is published as a structured `weight_sensitivity` field; ranking flips of more than one rank emit a plain-language warning.

Planned rigor upgrade:

- Suggested default composites generated from validated methodology families.
- Larger-perturbation sensitivity (±25%, ±50%) for power users who want to stress-test composites further.

## Drift and Documentation Checks

Before merging methodology changes:

- `specs/platform-methodology.md` must mention any new methodology version.
- New proxy metrics must include limitation language.
- Golden fixtures should be rerun manually or through service tests when the affected domain changes.
- Registry metadata should include `last validation` notes once historical calibration jobs exist.

Current automated checks:

- Reliability math unit tests cover empirical Bayes shrinkage, robust z-scores, Wilson intervals, confidence mapping, and the `_z_for_level` table for `0.80`, `0.90`, `0.95`, and `0.99` confidence intervals.
- Methodology registry tests cover core domains and domain lookup.
- Custom-metric service tests cover collinearity warnings (`pearson_correlation` ≥ 0.85) so composites that double-count the same signal warn the caller.
- Custom-metric service tests cover weight-sensitivity reporting: stable composites surface zero rank changes and Jaccard 1.0; concentrated composites surface non-zero changes and trigger the plain-language warning.
- Scouting-brief contradiction-detector tests cover the three v1 rule families (role/trajectory, role/usage, strengths/shot-profile) and confirm that low-confidence archetypes and developmental fallbacks short-circuit the detector.
- Validation fixture coverage is asserted at the test level: every registered domain in `list_methodologies()` must have at least one fixture in `methodology_validation_report()`.
