# Future Modeling Work — Award-Case Voter Calibration & Opportunity Uplift

Last updated: 2026-04-28

This memo scopes the two remaining open items from the Sprint 76 methodology rigor pass:

1. **MVP Award Case voter calibration** — turn the heuristic Award Case modifier weights into evidence-fit weights against historical voting outcomes.
2. **Opportunity uplift modeling** — turn the Opportunity composite into a quantified estimate of whether per-possession efficiency survives a larger usage role, grounded in historical role-expansion examples.

Both are **blocked on data ingestion**, not on math or service design. This memo locks down the design so the work can ship cleanly once the data lands.

---

## Shared context (already shipped this branch)

The Sprint 76 methodology rigor pass shipped seven primitives the modeling work below relies on:

- `weight_sensitivity_analysis` (custom_metric_v2, mvp_case_v4) for stability evidence on every composite
- `bayesian_change_score` (trend_intelligence_v2) for two-sample posterior change probability under Gaussian likelihoods
- `principal_components` / `project_to_components` (style_xray_v2) for low-rank latent reads on team and player matrices
- `mahalanobis_distance` + `shrunk_covariance` + `invert_matrix` (similarity_v3) for distance computation that whitens correlated features
- `softmax` (archetype_rules_v2) for membership distributions over discrete buckets
- `pearson_correlation` / `collinearity_warnings` (custom_metric_v2) for component-pair redundancy warnings
- `empirical_bayes_rate` / `empirical_bayes_delta` for shrinkage estimators (already wired into shot_quality_v2)

Both follow-on items will land as opt-in fields on existing response models — no new endpoints, no breaking schema changes — gated behind data-readiness flags so they degrade cleanly when the underlying historical data is incomplete.

---

## 1. MVP Award Case Voter Calibration (`mvp_case_v5`)

### Goal

Today the Award Case composite reuses the Basketball Value pillars and adds five capped narrative modifiers (`team_framing`, `eligibility_pressure`, `clutch`, `momentum`, `signature_games`) with hand-tuned weights `0.08 / 0.08 / 0.06 / 0.05 / 0.05`. The registry's `mvp_case_v4` policy explicitly notes "Calibrate Award Case against historical voting outcomes; keep Basketball Value basketball-first." Today those weights are defensible expert priors but not calibrated against any ground truth.

The goal of v5 is to fit those modifier weights against historical MVP voting outcomes so the Award Case ranking actually predicts ballot order rather than approximating it.

### Data prerequisites (the blocker)

We need a labeled dataset with one row per (player_id, season, ballot_position). Required fields:

- `player_id`, `season`, `ballot_position` (1 = 1st-place vote, 5 = 5th, NULL = not on ballot)
- `voter_count` (how many writers placed this player at this position) — the ballot is a weighted vote; we need point shares, not just counts
- `total_award_points` (computed from positions and voter_count, the published MVP point share)

NBA MVP voting data is published every season (1980-81 through current); the ingestion path is currently undefined. Likely sources:

- Basketball-Reference's `awards_share` table (best structured source; needs a scrape or CSV import)
- NBA.com's annual MVP press release (HTML, more brittle)

Storage: a new `award_voting` table with the above columns plus `award_type` ("MVP", "DPOY", "MIP" so the same loader serves future awards). Estimated 30 seasons × ~12 ranked candidates per season ≈ 360 rows for MVP alone — small enough to commit as a CSV and load via a script under `backend/data/`.

### Math

Once the data is loaded, the calibration is a straightforward weighted-regression problem:

```text
Let M_i ∈ ℝ^5 be candidate i's modifier vector (team_framing, eligibility_pressure,
clutch, momentum, signature_games), already z-scored across the season pool by the
existing pipeline.

Let B_i be the Basketball Value raw score (kept fixed; this is the basketball-first
ranking and is not part of the calibration target).

Let Y_i ∈ [0, 1] be the observed point share for candidate i in their season.

Fit:
   Award Case_i = B_i + W · M_i
   minimize Σ_i (rank_predicted(Award Case_i) - rank_observed(Y_i))^2

over weights W ∈ ℝ^5 with the constraint W >= 0 and Σ W_j ≤ 0.40
(keeping the modifier cap small so Basketball Value still dominates).
```

Use a coordinate-descent or small-grid search; the parameter space is 5-dimensional and well-bounded. No need for autograd or sklearn — pure Python over the historical pool.

A second pass should compute per-season cross-validation: hold out one season at a time, fit on the rest, and report rank-correlation (Spearman) on the held-out year. The reported calibration weights are the average across folds.

### Service wiring

- **No public schema change.** Replace the hand-tuned modifier weights at `mvp_service.py` line ~1920 with the calibrated weights at module import. The composition formula stays identical.
- **New methodology surface**: `MvpCalibration` model carrying `voter_calibration: { fold_count, mean_spearman_correlation, weight_vector, last_calibrated_season }`. Attach to `MvpRaceResponse.calibration: Optional[MvpCalibration]` so the registry can document the fit quality without breaking existing consumers.
- **Validation fixture** `mvp_award_case_voter_calibration` asserts the fitted weights on a held-out season produce Spearman ≥ 0.7 against the observed point share order.

### Acceptance criteria

1. `award_voting` table loaded with at least the last 15 seasons of MVP votes.
2. Fitted weights pass leave-one-season-out cross-validation with Spearman ≥ 0.7.
3. The five published modifier weights move by no more than 0.04 absolute on any pillar (i.e. calibration tunes, doesn't replace, the expert priors).
4. Registry bumps `mvp_case_v4 → v5` with `fold_count` and `last_calibrated_season` in `last_validation_date`.

### Out of scope

- DPOY / MIP / 6MOY calibration. The same harness can extend to these once the MVP loop is stable.
- Per-voter modeling (each writer's idiosyncratic weights). Aggregate point share is the calibration target.

---

## 2. Opportunity Uplift Modeling (`opportunity_v2`)

### Goal

Today the Opportunity composite blends five capped z-scores (efficiency-load, team-impact, role-fit, on-court availability, role headroom) into a single 0-100 score. The registry's `opportunity_v1` policy explicitly notes the planned upgrade: "interpretable uplift model estimating whether efficiency survives larger usage based on historical comparable role expansions."

The goal of v2 is to attach a quantified uplift estimate to every Opportunity row: **given a +5 percentage-point usage bump, how much does TS% historically change for comparable players?** The point of the model isn't to predict a single number with high confidence — it's to surface the historical evidence band so coaches can see whether the player's profile resembles role-expansion successes or failures.

### Data prerequisites (the blocker)

We need a "role expansion" dataset assembled from existing season stats:

For every (player_id, season) where the player has at least 40 games, find a same-player season `season - 1` (or `season - 2`) where the player had at least 40 games AND `usg_pct(season) - usg_pct(season-1) >= +0.03` (a meaningful role bump). Record:

- `player_id`, `from_season`, `to_season`
- `usg_delta` (target's usage shift)
- `pre_ts_pct`, `post_ts_pct`, `ts_delta` (the outcome to predict)
- `pre_ast_rate`, `pre_obpm`, `pre_age` (covariates the model conditions on)
- `pre_role_archetype` (already produced by `archetype_rules_v2` — reuse it)

This dataset already exists in latent form in the `season_stats` table — no new ingestion needed. We need a one-time materialization script that scans `season_stats`, finds qualifying season pairs, joins them, and writes to a new `role_expansion_observations` table. Estimated 10-12 seasons × ~30 qualifying players per season ≈ 350 observations. Small enough to recompute on every backfill.

The data **is** there. The blocker is engineering time to write the materialization script and keep it maintained.

### Math

Use a k-nearest-neighbors model in archetype-conditioned feature space — interpretable, no opaque ML, and small-data-friendly:

```text
For a target player T with current usg_pct(T), pre-bump archetype(T), and pre-bump
ts_pct(T):

1. Find the 20 nearest neighbors in the role-expansion observations whose
   pre-bump archetype matches T's archetype AND whose pre-bump ts_pct is within
   ±0.04 of T's, using shrunk Mahalanobis distance (similarity_v3 primitive)
   over (usg_delta, pre_ts_pct, pre_ast_rate, pre_obpm, pre_age).
2. Compute the empirical distribution of `ts_delta` across those neighbors.
3. Report:
     mean_uplift           = mean(ts_delta) over neighbors
     uplift_band_lower     = 25th percentile
     uplift_band_upper     = 75th percentile
     neighbor_count        = number of usable comparable cases
     evidence_confidence   = 'high' if neighbor_count >= 15, 'medium' if >= 8, 'low' otherwise
```

Falls back to None when fewer than 5 comparable neighbors exist (subject is too unique). The registry's `evidence_confidence` band lets the UI gate when to show the uplift number versus suppress it as too noisy.

### Service wiring

- **New `OpportunityUplift` response model** with `mean_uplift`, `uplift_band_lower`, `uplift_band_upper`, `neighbor_count`, `evidence_confidence`, `comparable_examples: List[str]` (top-3 neighbor names so analysts can audit the comp set).
- **`OpportunityRow.uplift: Optional[OpportunityUplift]`** attached when the role-expansion table is populated and the subject has enough comparables.
- **No registry version bump on the Opportunity composite itself**; the uplift travels as a sibling field. Still bump `opportunity_v1 → v2` in the registry to document the new payload contract.
- **Validation fixture** `opportunity_role_expansion_uplift` asserts that:
  - A clear-fit case (high TS, room to grow usage, archetype matches successful role-expansion comps) returns positive `mean_uplift` with `evidence_confidence >= medium`.
  - A thin-comp case returns `uplift = None` with no false confidence.

### Acceptance criteria

1. `role_expansion_observations` table materialized with at least 10 seasons of pairs.
2. Materialization script runs idempotently and produces the same rows on re-run.
3. The Opportunity response carries `uplift` for at least 60% of qualifying rows in the current season.
4. Held-out backtest: predict ts_delta for the 2024-25 expansion cases using only 2023-24 and earlier neighbors; mean absolute error ≤ 0.025 (i.e. 2.5 TS% points).
5. Registry bumps `opportunity_v1 → v2` with the materialization runbook referenced.

### Out of scope

- Multi-step uplift modeling (predicting season N+2 outcomes). v1 of v2 covers the immediate next-season projection only.
- Causal modeling. The KNN uplift is descriptive ("players similar to T who took on more usage tended to lose 1.5 TS%") not causal ("if T takes on more usage, his TS% will drop"). The UI copy must say "historically comparable cases" not "expected outcome".
- Modeling the team's outcome (W/L). This is a player-efficiency model only; team-impact modeling has its own backlog entry under "Team-Fit Calibration and Context Expansion".

---

## Sequencing and ownership

Either item can ship before the other. They share no engineering dependency.

If both are picked up in the same sprint:

- **Stream A (Award Case)**: data ingestion writes to `award_voting`, calibration runs offline, weights checked into the repo as a CSV, service reads them at import. Pure-Python modeling means no infra changes.
- **Stream B (Opportunity)**: materialization script runs as part of `daily_sync.sh`, KNN is computed at request time over the small (~350-row) historical pool. No model artifacts to ship, no registry-side surprises.

Both are bounded enough to fit in a single sprint each.

---

## References

- Sprint 76 closeout commits: `75087cb`, `b6f2f00`, `75c9a0a`, `f398c53`, `fc3e7b7`, `7fc6cc6`, `e0f4261`
- Methodology registry: `backend/services/methodology_registry_service.py`
- Validation harness: `backend/services/methodology_validation_service.py`, `specs/methodology-validation.md`
- Reliability primitives: `backend/services/reliability_service.py`
- Existing MVP composition: `backend/services/mvp_service.py` lines ~1908-1928
- Existing Opportunity composition: `backend/services/opportunity_service.py`
