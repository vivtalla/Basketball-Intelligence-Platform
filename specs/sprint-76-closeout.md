# Sprint 76 Closeout — Methodology Rigor Pass

**Date:** 2026-04-28
**Branch:** `claude/improve-evaluation-methods-ZAo94`
**Status:** Implemented, verified, ready for merge to `master`

---

## Theme

Pure backend methodology rigor pass. Every existing methodology version (v1) inherited from the registry's planned-upgrade list got either an end-to-end functional upgrade (math + service wiring + tests + registry bump) or, when blocked on data prerequisites, a focused design memo with explicit acceptance criteria. No frontend code changed; every backend response field added is `Optional` so existing consumers keep working unchanged.

---

## Shipped

### Reliability primitives (`backend/services/reliability_service.py`)

Eight new pure-Python primitives, all with input validation and tests:

- `_z_for_level` — z-table for 0.80 / 0.90 / 0.95 / 0.99 confidence levels; replaces the silent z=1.96 fallback in `wilson_interval` and `normal_uncertainty_band`.
- `pearson_correlation` and `collinearity_warnings` — for component-pair redundancy reporting.
- `covariance_matrix`, `shrunk_covariance`, `invert_matrix`, `mahalanobis_distance` — for distance computation that whitens correlated features.
- `weight_sensitivity_analysis` — measures rank stability under per-component weight perturbations.
- `principal_components` and `project_to_components` — power-iteration PCA with Gram-Schmidt re-orthogonalization and matrix deflation.
- `bayesian_change_score` — closed-form two-sample Gaussian Bayes factor → posterior change probability.
- `softmax` — numerically-stable softmax with per-call temperature.

`empirical_bayes_rate` was hardened to validate inputs and clamp the posterior into `[0, 1]`.

### Methodology version bumps (7 services)

Every promoted methodology surfaced a structured response field carrying the new evidence:

| Version | What it ships |
|---|---|
| `similarity_v3` | Shrunk-Mahalanobis distance method on `find_similar_players_with_archetype` with auto-fallback to weighted Euclidean. Resolved method exposed per-comp as `distance_method_used`. |
| `custom_metric_v2` | `pearson_correlation`-driven collinearity warnings + `weight_sensitivity` field with rank-stability evidence under ±10% weight perturbations. |
| `scouting_brief_v2` | `_detect_contradictions` covers role/trajectory, role/usage, and strengths/shot-profile rule families. New `contradictions: List[ScoutingBriefContradiction]` field. |
| `mvp_case_v4` | `weight_sensitivity` on the Basketball Value composite (`REFINED_VALUE_WEIGHTS`); kept separate from Award Case modifiers per registry policy. Adaptive `top_n`. |
| `style_xray_v2` | PCA latent space alongside the centroid archetype label. Top-2 axes with explained-variance ratios, subject coordinates, top positive/negative feature loadings. Pool gate `2 × n_features`. |
| `trend_intelligence_v2` | Bayesian two-sample change score per metric (minutes, points, plus_minus). Recent vs baseline window from `game_logs[:10]` vs `game_logs[10:]`. |
| `archetype_rules_v2` | Soft-membership distribution over the 13 archetype rules via per-condition sigmoid satisfactions and softmax. Hard label is anchored via a pre-softmax bonus so the soft distribution stays consistent with the hard classifier. |

### Validation harness expansion

`methodology_validation_v1 → v2`. Coverage went from 6 fixtures (team_fit + shot_lab only) to 17 fixtures spanning every registered methodology domain:

- New: `similarity_role_pool_stability`, `similarity_shrinkage_collinearity`, `trend_injured_star_window`, `trend_bayesian_change_evidence`, `opportunity_role_expansion_evidence`, `style_xray_drift_team`, `style_xray_latent_space`, `mvp_value_versus_award_split`, `mvp_basketball_value_weight_sensitivity`, `archetype_borderline_role_label`, `archetype_soft_memberships`, `custom_metrics_collinear_components`, `custom_metrics_weight_sensitivity`, `gravity_proxy_versus_official`, `scouting_brief_evidence_linkage`, `scouting_brief_contradictions`, `playoffs_thin_series_sample`.
- A test in `test_evaluation_methodology_improvements.py` asserts every registry domain has at least one fixture, so future registry additions can't ship without a fixture.

### Documentation

- `specs/methodology-future-modeling.md` (new, ~200 lines) — design memo for the two remaining open items (Award Case voter calibration, Opportunity uplift modeling). Each entry: data prerequisites, math sketch, service wiring, acceptance criteria, out-of-scope list. Both are blocked on data ingestion, not engineering.
- `specs/platform-methodology.md` published the new formulas: z-level table, collinearity primitive, shrunk Mahalanobis, weight-perturbation sensitivity, PCA, Bayesian change score, soft-membership softmax.
- `specs/methodology-validation.md` published the v2 fixture list and per-domain v2 policy notes.
- `specs/BACKLOG.md` got two new explicit blocked-on-data entries (`mvp_case_v5` voter calibration, `opportunity_v2` uplift modeling), each linking back to the design memo.

---

## Verification

- Backend full: `python -m pytest -q` → **346 passed**, 2 pre-existing FastAPI deprecation warnings (was 293 at Sprint 75 close; +53 net new tests)
- Frontend lint: `npm run lint` → 0 errors, 7 pre-existing `usePlayerStats.ts` warnings (unchanged)
- Frontend build: `npm run build` → clean; all 19 routes generated
- Backend response models: every new field is `Optional`; frontend `methodology_version` strings are rendered as free-form, not pinned via equality, so version bumps don't break the existing UI

---

## Deferred (with explicit unblockers)

The two items in the design memo:

- **`mvp_case_v5` Award Case voter calibration** — needs `award_voting` table loaded with at least 15 seasons of MVP point shares (Basketball-Reference's `awards_share`). Math is constrained coordinate descent; acceptance criterion is leave-one-season-out Spearman ≥ 0.7.
- **`opportunity_v2` uplift modeling** — needs `role_expansion_observations` table materialized from existing `season_stats` (one-time script, no new ingestion). KNN over archetype-bucketed covariates; acceptance criterion is held-out MAE ≤ 0.025 TS%.

Each is single-sprint-sized once the data prerequisite is met. The Sprint 76 reliability primitives (`mahalanobis_distance`, `softmax`, `weight_sensitivity_analysis`) cover the math infra both items would otherwise need.

---

## Frontend follow-ons

The new optional response fields don't have UI yet. None block the merge — the methodology evidence is auditable via the API today — but each is a natural next-sprint item:

- `MvpRaceResponse.weight_sensitivity` → `MvpMethodologyDrawer` could render the Basketball Value rank-stability statement.
- `StyleXRayResponse.latent_space` → `XRayMethodologyDrawer` could render the top-2 PCA axes with feature loadings.
- `PlayerTrendReport.change_evidence` → `TrajectoryMethodologyDrawer` could render the per-metric posterior change probabilities.
- `PlayerArchetype.memberships` → `PlayerArchetypeProfile` could surface adjacent archetypes with their membership share.
- `ScoutingBriefResponse.contradictions` → `ScoutingBrief` could render a small contradictions footer when present.
- `CustomMetricResponse.weight_sensitivity` → metrics workspace could surface the rank-stability interpretation alongside existing validation warnings.

---

## Workflow lessons

- Shipping a primitive without service wiring is scaffolding. Every primitive in this branch has a paired service-level upgrade and tests against real data flow, not just primitive math tests.
- The validation harness's coverage check (every registry domain must have a fixture) caught two domains that would otherwise have shipped without a regression test.
- Optional response fields are the right back-compat shape for methodology evidence; the frontend only consumes what its types declare, so the API can ship rigor evidence ahead of UI without breakage.
- For nested rules (e.g. `heliocentric_creator` is a stricter `lead_ball_handler`) the soft-membership math needs anchoring to the hard classifier, not just sigmoid-product softmax — discovered during test failure on a clear-fit fixture and resolved with a pre-softmax score bonus.

---

## Commits on the sprint branch

`75087cb` Reliability primitive bug fixes + collinearity warnings + validation fixture coverage
`b6f2f00` similarity_v3 — shrunk Mahalanobis distance with auto-fallback
`75c9a0a` custom_metric_v2 + scouting_brief_v2 — weight sensitivity & contradiction detection
`f398c53` mvp_case_v4 — Basketball Value weight-perturbation sensitivity
`fc3e7b7` style_xray_v2 — PCA latent space alongside centroid archetype
`7fc6cc6` trend_intelligence_v2 — Bayesian change-score evidence
`e0f4261` archetype_rules_v2 — soft memberships alongside hard label
`4592e87` Design memo + backlog: Award Case voter calibration & Opportunity uplift
