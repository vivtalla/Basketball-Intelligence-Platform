# CourtVue Labs Platform Methodology

Last updated: 2026-04-28

This document is the canonical methodology guide for CourtVue Labs. It explains what each major analytical surface is trying to answer, which data it trusts, how metrics and scores are derived, why the current method was chosen, and where the limitations are.

This is a human-readable audit document, not a generated field catalog. Implementation references point to the files that own the live behavior.

---

## 1. Data Foundation and Source Policy

CourtVue uses one persisted source of truth per product-relevant domain. User-facing reads should use local persisted data, not request-time NBA API repair.

Primary source families:

- Player profiles and season stats: `players`, `season_stats`
- Team season stats and splits: `team_season_stats`, `team_split_stats`, `team_shooting_split_stats`
- Game-level warehouse data: `games`, `game_team_stats`, `game_player_stats`, `raw_game_payloads`
- Play-by-play: `play_by_play_events`
- Shot charts: `player_shot_charts`, `shot_quality_baselines`
- Injuries and analysis context: `player_injuries`, `player_analysis_contexts`
- Derived lineup/on-off: `player_on_off`, `lineup_stats`

Why this design:

- It keeps pages fast and reproducible.
- It lets methodology describe data coverage honestly.
- It avoids mixed truth where one route silently fetches fresher external data than another.

Limitations:

- Current-season data depends on scheduled sync freshness.
- Some official domains are still incomplete or proxy-based.
- Derived surfaces are only as strong as the underlying warehouse coverage.

Implementation references:

- `specs/official-data-source-matrix.md`
- `backend/services/runtime_data_policy.py`
- `backend/services/warehouse_service.py`
- `backend/services/sync_service.py`

---

## 2. Common Math Primitives

Shared formulas live primarily in `backend/services/intel_math.py`.

Core rates:

```text
rate = numerator / denominator

TS% = PTS / (2 * (FGA + 0.44 * FTA))

eFG% = (FGM + 0.5 * 3PM) / FGA

estimated possessions = FGA - OREB + TOV + 0.44 * FTA

TOV% proxy = TOV / (FGA + 0.44 * FTA + extra_plays)

OREB% = OREB / (OREB + opponent DREB)

FTr = FTA / FGA

3PAr = 3PA / FGA
```

Normalization:

```text
z = (value - cohort_mean) / cohort_std

percentile_rank = (count_below + 0.5 * count_equal) / cohort_size * 100

weighted_score = sum(component_score_i * component_weight_i)
```

Conventions:

- If a denominator is missing or zero, the metric returns `None`.
- If a z-score pool has fewer than two values or zero standard deviation, the z-score defaults to `0.0`.
- `clamp(value, low, high)` is used when a model intentionally caps outliers.
- Confidence labels are usually `high`, `medium`, or `low`, but thresholds are model-specific.

Why this design:

- Ratios stay transparent and basketball-native.
- Z-scores make cross-player and cross-team comparisons cohort-relative.
- Percentiles make model outputs easier to read in product surfaces.

Limitations:

- Z-scores depend on pool construction; changing sample gates changes the interpretation.
- The 0.44 free-throw possession factor is an accepted estimate, not exact possession reconstruction.
- Per-game, rate, and impact metrics should not be blended without normalization.

Implementation references:

- `backend/services/intel_math.py`
- `backend/services/custom_metric_service.py`
- `backend/services/similarity_service.py`

---

## 2A. Methodology Registry, Reliability, and Validation

The rigor layer answers: which methodology is active, how stable is this read, and what validation evidence or limitations should travel with the score?

Public contract:

- `GET /api/methodology` lists registered domains, methodology versions, input families, sample gates, confidence rules, limitations, validation notes, docs path, and implementation references.
- `GET /api/methodology/{domain}` returns one domain with related domains and recommended next methodology steps.
- Registry entries also expose `last_validation_date` so stale methodology reviews are visible.
- Analytical responses may include optional `analysis_metadata` with:
  - `methodology_version`
  - `reliability_score`
  - `uncertainty_band`
  - `sample_context`
  - `driver_breakdown`
  - `limitations`
  - `validation_notes`

Reliability score:

```text
reliability_score = 100 * sample_size / (sample_size + target_sample)
```

Interpretation:

- The score is `50` when the sample reaches the domain target.
- It approaches `100` as the sample grows, but never means the model is perfect.
- Confidence labels map from reliability: high at `70+`, medium at `40+`, low below `40`.

Empirical Bayes shrinkage:

```text
posterior_rate = (successes + prior_rate * prior_weight) / (attempts + prior_weight)

posterior_mean =
  (observed_mean * sample_size + prior_mean * prior_weight)
  / (sample_size + prior_weight)
```

Uncertainty bands:

- Binary outcomes can use a Wilson score interval.
- Continuous means can use a normal approximation interval.
- The default documentation target is a 90% interval unless a surface says otherwise.

Robust normalization:

```text
robust_z = (value - median(values)) / (1.4826 * MAD(values))
```

When outliers dominate a feature, services should prefer robust or winsorized z-scores before percentile ranking. Percentiles and ranks should be interpreted after reliability adjustment, not as raw precision.

Why this design:

- It standardizes audit language without forcing every model into the same math.
- It separates score construction from score trustworthiness.
- It gives coaches readable caveats while preserving engineering traceability.

Limitations:

- First-pass reliability metadata is descriptive for many surfaces; not every model has completed historical calibration.
- Reliability is sample-aware but not automatically opponent-, schedule-, or role-adjusted.
- Confidence labels are still domain-specific summaries and should not replace the detailed sample context.

Implementation references:

- `backend/models/methodology.py`
- `backend/services/methodology_registry_service.py`
- `backend/services/reliability_service.py`
- `backend/routers/methodology.py`
- `specs/methodology-validation.md`

---

## 3. Player and Team Base Metrics

Base metrics answer: what happened in the season or game box score?

Definitions:

- Points, rebounds, assists, steals, blocks, turnovers: official box-score totals or per-game rates.
- FG%, 3P%, FT%: makes divided by attempts.
- TS%, eFG%, FTr, 3PAr: derived with the common formulas above.
- Offensive Rating: points scored per 100 possessions.
- Defensive Rating: points allowed per 100 possessions.
- Net Rating: Offensive Rating minus Defensive Rating.
- Usage Rate: estimated share of team possessions used by a player while on the floor, imported when available from official advanced rows.

Why this design:

- Official box-score values remain the stable base layer.
- Derived percentages are recomputed from raw makes/attempts when stored percentage fields are missing.
- Team and player pages can share language without each surface redefining core basketball stats.

Limitations:

- Imported advanced metrics such as PER, BPM, WS, VORP, EPM, RAPTOR, LEBRON, PIPM, RAPM, and DARKO are not CourtVue-original.
- Some advanced metrics are source-dependent and may be missing for historical or current seasons.
- Player names are not unique; player IDs are the canonical key.

Implementation references:

- `backend/services/stats_service.py`
- `backend/routers/leaderboards.py`
- `backend/services/query_metric_registry.py`
- `backend/db/models.py`

---

## 4. PBP-Derived Metrics, On/Off, and Lineups

PBP-derived surfaces answer: what happened while a player or lineup was actually on the floor?

Stint construction:

- Starting lineups come from box score starter flags.
- Substitution events update active five-man groups.
- Stint duration is measured from game clock timestamps.
- Team and opponent points are computed from score changes during the stint.

Core formulas:

```text
on_net_rating = points_scored_while_on - points_allowed_while_on per 100 possessions

off_net_rating = points_scored_while_off - points_allowed_while_off per 100 possessions

on_off_net = on_net_rating - off_net_rating

lineup_net_rating = lineup_points - opponent_points per 100 possessions
```

Confidence:

- On/off and lineup reads are high variance.
- Many surfaces use possession or minute gates before treating a value as strong.
- Lineup opportunity work uses `MIN_LINEUP_POSSESSIONS = 100`.

Why this design:

- PBP stints are a better source for on/off and lineup context than season box scores.
- Clock-derived stint minutes avoid estimating time from possessions.

Limitations:

- PBP event quality and substitution completeness matter.
- Small lineups can swing wildly on schedule and teammate context.
- On/off is descriptive; it is not a pure player-impact estimate.

Implementation references:

- `backend/services/pbp_service.py`
- `backend/services/pbp_sync_service.py`
- `backend/services/lineup_context_service.py`
- `backend/services/lineup_impact_service.py`

---

## 5. Shot Lab and Shot Diagnosis

Shot Lab answers: where a player shoots, how favorable those shots are, and whether actual making beats expectation.

Shot quality v2:

- Methodology version: `shot_quality_v2`
- Baselines are materialized by season and season type in `shot_quality_baselines`.
- Each shot uses hierarchical baseline blending instead of hard fallback only.
- Exact context blends toward zone-distance-value, then zone-value, shot-value, and league priors as bucket samples thin.
- Raw actual and expected values remain visible; stabilized shot-making is additive.

Expected and actual formulas:

```text
actual_FG% = makes / attempts

actual_PPS = points / attempts

actual_eFG% = points / (2 * attempts)

expected_FG% = sum(baseline_FG% for shots) / attempts

expected_PPS = sum(baseline_PPS for shots) / attempts

expected_eFG% = expected_points / (2 * attempts)

delta = actual - expected

stabilized_delta =
  (actual_PPS - expected_PPS) * attempts / (attempts + prior_weight)

stabilized_PPS = expected_PPS + stabilized_delta
```

Confidence:

- Summary confidence: high at 300+ attempts, medium at 100+, low below 100.
- Zone/bin confidence: high at 75+ attempts, medium at 25+, low below 25.
- Coverage states distinguish ready, partial, legacy, missing, and stale data.
- `analysis_metadata.reliability_score` uses a 300-shot target for summary reads.
- Summary stabilized priors default to 150 attempts; zone priors default to 50 attempts; bin priors default to 35 attempts.
- Raw FG% uses a Wilson interval. PPS delta uses a normal uncertainty band when sample support is sufficient.
- Sustainability labels separate repeatable edge, likely hot streak, likely cold streak, and sample too thin.

Shot creation:

- Assisted/self-created and creation buckets are proxy labels from shot action language, shot type, clock, zone, and linked event context.
- Precision labels tell whether a split uses all shots, partial coverage, or inferred context.

Shot diagnosis v1:

- Minimum gate: 50 tracked shots and coverage not `legacy` or `missing`.
- Tags are deterministic rules over Shot Lab outputs.
- Tag ranking uses:

```text
tag_priority = abs(delta) * confidence_weight
confidence_weight = high: 1.0, medium: 0.7, low: 0.4
```

Examples:

- Elite corner gravity: corner zone PPS delta at least `+0.10` with at least 15 attempts.
- Rim pressure elite: restricted-area frequency at least `0.30` and FG% delta at least `+0.03`.
- Heat-check overperformance: summary PPS delta at least `+0.08` with medium/low confidence.
- Sustainability labels separate sustainable, hot streak, cold streak, and insufficient sample.

Why this design:

- It separates shot diet, shot quality, and shot making.
- It works from persisted location/context data without waiting for optical tracking.
- It keeps uncertainty visible through coverage and confidence labels.

Limitations:

- Shot quality is not defender-distance or contest based unless those feeds are later persisted.
- Creation labels are directional proxies, not official play-type or tracking truth.
- Expected value is only as good as the baseline pool and available context fields.
- V2 still does not use defender distance, contest quality, or optical tracking unless those feeds are later persisted.

Implementation references:

- `backend/services/shot_intelligence_service.py`
- `backend/services/shot_diagnosis_service.py`
- `backend/services/shot_intelligence_ops_service.py`
- `backend/models/shotchart.py`

---

## 6. Player Archetypes, Similarity, and Team-Fit

### Player Archetype

Player archetypes answer: what role identity does this player most resemble in this season?

Method:

- Uses regular-season `season_stats` plus parsed player height.
- Uses a same-season peer pool with `gp >= 20`, `min_pg >= 15`, and required features present.
- Traded players prefer the `TOT` row when available.
- Features are normalized to same-season z-scores.
- First matching rule wins.

Core feature examples:

- `usg_z`: usage burden.
- `ast_rate_z`: `(AST per game * 36) / minutes per game`.
- `par3_z`: `3PA / FGA`.
- `ftr_z`: `FTA / FGA`.
- `stl_rate_z`: `(STL per game * 36) / minutes per game`.
- `blk_rate_z`: `(BLK per game * 36) / minutes per game`.

Confidence:

```text
high = mean(abs(trigger_z)) >= 1.0
medium = mean(abs(trigger_z)) >= 0.6
low = otherwise
```

Why this design:

- Rule ordering is readable and coach-auditable.
- Same-season z-scores reduce era and league-context bias.
- Deterministic labels are easier to debug than opaque clustering.

Limitations:

- Borderline players can feel surprising when several rules are close.
- Missing features or sample gates can push players to developmental/balanced states.
- Archetypes are regular-season identity labels, not playoff matchup predictions.

Implementation references:

- `backend/services/player_archetype_service.py`
- `backend/models/archetype.py`
- `specs/sprint-67-archetype-rules.md`

### Similarity

Similarity answers: which player-seasons look statistically closest?

Legacy distance:

- Uses 9 weighted features: points, rebounds, assists, steals, blocks, turnovers, TS%, usage, PER.
- Requires `gp >= 20` and all feature values present.
- Computes same-season z-scores and weighted Euclidean distance.

Role-aware v2:

- Adds `3PAr`, `FTr`, steals, and blocks as role-shaping features.
- Modes:
  - `season`: same-season role-aware comps.
  - `age`: comps within plus/minus one year of subject age.
  - `team_fit`: same-season comps with teammate-duplicate penalties.

Formula:

```text
weighted_z_i = z_i * feature_weight_i

distance = sqrt(sum((subject_weighted_z_i - candidate_weighted_z_i)^2))

similarity_score = 100 / (1 + distance)
```

Why this design:

- Euclidean distance is transparent and easy to audit.
- Z-scores make cross-era comparison more reasonable than raw stat comparison.
- Role-aware features keep low-box-score style differences visible.

Limitations:

- Similarity is statistical resemblance, not career trajectory or quality equivalence.
- Missing feature values exclude rows.
- Team-fit mode changes ranking logic but remains roster-stat based only.

Implementation references:

- `backend/services/similarity_service.py`
- `backend/routers/similarity.py`

### Team-Fit

Team-Fit answers: how clearly does this player supply value his current roster needs, and where else might he fit better?

Methodology version: `team_fit_v3`

Inputs:

- Same 13 z-scored features as role-aware similarity.
- Current team resolved from the selected season row.
- If a player only has `TOT`, current-team fit returns a warning; if a previous qualified season exists, the service may fall back for display.

Scoring dimensions:

```text
fit_score =
  0.45 * value_supplied_score
  + 0.30 * teammate_overlap_score
  + 0.25 * role_runway_score
```

Current implementation details:

- `value_supplied` rewards features where the player is above cohort average and the roster is thin.
- `teammate_overlap` penalizes features already covered by same-team teammates.
- `role_runway` focuses on usage, scoring, playmaking, spacing, rim pressure, defensive activity, rim protection, and rebounding.
- A covered feature is one where `abs(player_z - teammate_z) < 0.5`.
- Covered features receive the Sprint 68 duplicate multiplier: `0.4x`.
- Alternate teams are labeled a better fit only when `score_delta_vs_current >= +5.0`.
- V3 adds reliability-gated better-fit labels:

```text
high reliability: better fit requires +5
medium reliability: better fit requires +7
low reliability: never label as better fit
```

- V3 separates current roster fit from theoretical best usage:

```text
theoretical_usage_score =
  0.55 * skill_supply_score
  + 0.45 * roster_need_score
  + usage_bonus

fit_gap_vs_theoretical = theoretical_usage_score - current_fit_score
```

- Injury, recovery, and availability contexts soften confidence notes without changing raw component math.
- Playoff Team-Fit can run, but low game samples must visibly reduce confidence.
- Teams need at least 3 qualifying player rows.
- `analysis_metadata.reliability_score` uses qualified current-roster rows against an 8-player target.
- `driver_breakdown` exposes skill supply, roster need, role competition, and best alternate delta when available.

Why this design:

- It makes roster fit visible instead of hiding it inside similarity ranking.
- It is deterministic and coach-readable.
- It intentionally excludes trade mechanics to keep the question basketball-specific.

Limitations:

- No salary, contracts, trade assets, injuries, probability, or future projection.
- Position buckets are coarse: guard, forward, center, other.
- Fit is same-season roster fit, not lineup simulation.
- The current `+5.0` better-fit threshold is deterministic; future versions should calibrate it against historical fit examples.

Implementation references:

- `backend/services/team_fit_service.py`
- `backend/services/similarity_service.py`
- `backend/models/team_fit.py`

---

## 7. Trend, Trajectory, Opportunity, and Decision Intelligence

### Player Trend Intelligence

Player Trend answers: is a player's recent role and production changing relative to his season baseline?

Method:

- Uses recent regular-season game logs against season-long averages.
- Computes recent form, trust signals, impact context, and role status.
- Role status rules include:
  - Entrenched starter: at least 8 starts in last 10 and minutes holding near baseline.
  - Rising rotation: recent minutes up at least 4 or at least five 30-plus-minute recent games.
  - Losing trust: recent minutes down at least 4 or at least five recent games under 20 minutes.
  - Volatile role: high recent minute volatility.

Injury-aware adjustment:

- Analysis contexts overlapping the recent window are loaded for the `trend` facet.
- If raw role status is `losing_trust` and the recent window overlaps injury/recovery/availability context, display status becomes `injury_context`.
- Raw minutes and production deltas remain visible.

Why this design:

- It preserves the statistical signal while preventing misleading interpretation.
- It makes injury context explanatory metadata, not a rewrite of the data.

Limitations:

- Game-log role status is not a coaching intent model.
- Injury reports can be incomplete or vague.
- Manual contexts supplement but do not delete official injury source rows.

Implementation references:

- `backend/services/player_trend_service.py`
- `backend/services/analysis_context_service.py`
- `backend/models/player.py`

### Trajectory

Trajectory answers: which players are rising, slumping, or stable over a recent game window?

Formula:

- Recent split minus baseline split is computed for TS%, points, usage, assists, turnovers, and rebounds.
- Deltas are z-scored across the selected player pool.
- Weighted trajectory score uses:
  - TS%: `0.25`
  - Points: `0.20`
  - Usage: `0.20`
  - Assists: `0.15`
  - Turnover percentage: `-0.10`
  - Rebounds: `0.10`

Labels:

- `Breaking Out`: z-score at least `1.5`
- `Quietly Rising`: z-score at least `0.5`
- `Stable`: between `-0.5` and `0.5`
- `Slumping`: z-score at most `-0.5`
- `Collapsing`: z-score at most `-1.5`

Why this design:

- It rewards multi-signal movement rather than one big scoring night.
- Z-scoring makes movement relative to the active comparison pool.

Limitations:

- Current trajectory implementation is scoped to the supported current-season workflow.
- Recent windows can still be schedule- and role-sensitive.

Implementation references:

- `backend/services/trajectory_service.py`
- `frontend/src/components/trajectory/TrajectoryMethodologyDrawer.tsx`

### Opportunity

Opportunity answers: where might a player have untapped role upside?

Methodology version: `opportunity_v1`

Signals, each capped at plus/minus `2.0` z-score:

- `efficiency_load_gap`: efficiency z minus usage z.
- `team_impact_swing`: z-scored player on/off net.
- `lineup_synergy_lift`: top teammate lineup net rating minus baseline lineup net rating.
- `role_fit_gap`: cohort-relative role needs such as spacing, efficiency, and foul pressure.
- `cohort_percentile`: cohort-relative net-rating and scoring composite.

Weights:

```text
opportunity_score =
  0.30 * efficiency_load_gap
  + 0.25 * team_impact_swing
  + 0.20 * lineup_synergy_lift
  + 0.15 * role_fit_gap
  + 0.10 * cohort_percentile
```

Confidence:

- High if minutes per game at least 28 and on minutes at least 500.
- Medium if minutes per game at least 18 and on minutes at least 200.
- Low otherwise.
- `analysis_metadata.reliability_score` uses the full filtered candidate pool against a 25-player target.
- Driver metadata records the composite weights so users can audit why a board ranked as it did.

Why this design:

- It looks for players whose efficiency, impact, and lineup context suggest more room.
- Capping z-scores prevents one outlier from dominating the board.

Limitations:

- It is directional, not a coaching guarantee.
- Same-team lineup context can miss league-wide role fit.
- On/off and lineup inputs are sample-sensitive.
- The current model is not yet a true role-expansion uplift model; efficiency-survival risk is a planned rigor upgrade.

Implementation references:

- `backend/services/opportunity_service.py`
- `frontend/src/components/opportunity/MethodologyDrawer.tsx`

### Decision and Focus Tools

Decision tools answer: what staff-facing levers, matchup flags, or rotation questions deserve attention?

Method:

- Uses persisted team stats, opponent context, matchup flags, lineup/on-off data, scouting claims, and replay anchors.
- Severity and confidence are rule-based.
- Follow-through links carry users into compare, prep, replay, or scouting workflows.

Why this design:

- Staff tools should explain what changed and what action it suggests.
- Confidence framing matters more than a single opaque score.

Limitations:

- These tools are decision support, not lineup optimization solvers.
- Some recommendations depend on partial play-type or PBP coverage.

Implementation references:

- `backend/services/decision_support_service.py`
- `backend/services/team_focus_service.py`
- `backend/services/matchup_flag_service.py`
- `backend/services/follow_through_service.py`

---

## 8. Style X-Ray and Team Identity

Team style answers: how does a team play relative to the league?

Style features:

- Pace: estimated possessions.
- TS% and eFG%.
- Assist rate: assists divided by made field goals.
- Three-point rate: `3PA / FGA`.
- Paint pressure proxy: `clamp(1 - 3PAr + 0.2 * FTr, 0, 2)`.
- Transition proxy: `clamp(possessions / 100 + 0.15 * 3PAr, 0, 2.5)`.
- Turnover rate: common turnover proxy.
- Offensive rebound rate: `OREB / (OREB + opponent DREB)`.
- Free-throw rate: `FTA / FGA`.

Style labels:

- Percentile thresholds label teams as transition-leaning, three-point pressure, paint-driven, pick-and-roll/movement, chaos-prone, halfcourt/pressure, or balanced.

Style X-Ray:

- Converts style features into percentile vectors.
- Compares vectors to archetype centroids with mean absolute distance.
- Nearest neighbors are teams with the lowest vector distance.
- Stability is `stable` when the top-two archetype distance gap is at least `4.0`; otherwise `mixed`.
- Play-type proxy can refine the primary label when available.

Why this design:

- Percentile vectors are readable and stable across seasons.
- Archetype centroids make team identity explainable without ML clustering.
- Recent drift separates season identity from current movement.

Limitations:

- Paint pressure and transition are proxies.
- Play-type inference is not official tracking.
- Centroid labels simplify teams with mixed identities.

Implementation references:

- `backend/services/style_feature_service.py`
- `backend/services/style_xray_service.py`
- `backend/routers/styles.py`
- `frontend/src/components/xray/XRayMethodologyDrawer.tsx`

---

## 9. Scouting, Prep, and Follow-Through Confidence

Scouting and prep answer: what should an analyst watch or carry into a staff workflow?

Scouting claim confidence:

- Claims are ranked by confidence level, opponent-specific evidence count, and anchored event count.
- Clip anchors are scored by matching claim tokens, event action type/family, and evidence text to PBP events.
- Linkage quality distinguishes exact/derived event links from timeline-only evidence.

Prep and Pre-Read:

- Prep queues preserve selected context into packet snapshots.
- Pre-Read packets freeze selected claims and notes so reopened packets do not drift when live data changes.

Why this design:

- Staff workflows need stable handoffs, not recomputed claims that shift later.
- Confidence should tell whether evidence is direct, inferred, or timeline-adjacent.

Limitations:

- PBP text matching is heuristic.
- Clip anchors are not full video labels.
- Packet snapshots intentionally trade freshness for reproducibility.

Implementation references:

- `backend/routers/scouting.py`
- `backend/services/scouting_brief_service.py`
- `backend/services/pre_read_service.py`
- `backend/services/pre_read_snapshot_service.py`

---

## 10. MVP, Gravity, and Award Case Modeling

MVP answers two related but separate questions:

- Basketball Value: how strong has the player been on court?
- Award Case: how strong is the voter-facing MVP candidacy?

Basketball Value pillars:

- Impact: `0.30`
- Efficiency: `0.20`
- Scoring load: `0.15`
- Playmaking load: `0.10`
- Team value: `0.15`
- Availability: `0.10`

Award Case:

```text
award_case_raw =
  basketball_value_raw
  + 0.08 * team_framing
  + 0.08 * eligibility_pressure
  + 0.06 * clutch
  + 0.05 * momentum
  + 0.05 * signature_games
```

Display scores:

- Basketball Value and Award Case are converted to percentile ranks inside the candidate pool.
- Main rank uses Award Case.
- Basketball Value rank remains visible.

Modifier examples:

- Eligibility pressure: eligible `+0.25`, at risk `-0.45`, ineligible `-1.25`.
- Clutch component blends clutch points, attempts, FG%, and result context with confidence scaling.
- Signature game leverage blends points, rebounds, assists, opponent strength, TS bonus, win bonus, and plus-minus.

Gravity:

- Official NBA Gravity rows are preferred when present.
- CourtVue proxy Gravity uses shot profile, play type, tracking, hustle, and on/off data.
- Proxy formulas are capped to `0-100`.

Proxy examples:

```text
shooting_gravity =
  clamp(38 + 3PA_per_game * 5
          + three_rate * 28
          + deep_three_rate * 25
          + spot_up_PPP * 6)

rim_gravity =
  clamp(35 + FTA_per_game * 5
          + rim_rate * 30
          + usage * 0.35)

spacing_lift =
  clamp(50 + on_off_net * 1.4
          + (TS - 57) * 1.1)

overall_gravity = average(component_gravities)
```

Gravity context adjustment:

```text
gravity_modifier = (overall_gravity - 50) * 0.12 * confidence_scale
context_adjusted_score = award_case_score + gravity_modifier
```

Why this design:

- It separates basketball value from award politics.
- It keeps external impact metrics useful without letting any single imported source dominate.
- Gravity stays context-first until source coverage is stronger.

Limitations:

- MVP scoring is candidate-pool relative.
- Imported impact metrics carry their own opaque methodologies.
- Proxy Gravity is not official tracking-based Gravity.
- Clutch and signature-game samples are volatile.

Implementation references:

- `backend/services/mvp_service.py`
- `backend/services/gravity_service.py`
- `specs/mvp-tracker-methodology-brief.md`

---

## 11. Availability, Injuries, and Analysis Context

Analysis Context answers: what real-world context should change interpretation without changing raw stats?

Context types:

- `injury`
- `recovery`
- `availability_management`
- `manual_note`

Automatic injury windows:

- Built from `player_injuries`.
- Any non-available injury status opens or continues an unavailable window.
- Severity:
  - `high`: out or doubtful.
  - `medium`: questionable or game-time decision.
  - `low`: other unavailable statuses.
- When an available report closes an injury window, a 7-day recovery buffer is added.

Manual contexts:

- Persisted in `player_analysis_contexts`.
- Source is `manual`.
- Can apply to `all` facets or targeted facets such as `trend` and `team_fit`.

Why this design:

- Analysts need to override or supplement automatic injury context.
- Context changes the conclusion, not the source stat history.

Limitations:

- Injury reports can miss private team context.
- Recovery buffers are heuristic.
- Current v1 context is applied most directly to Trend Intelligence, with broader rollout planned.

Implementation references:

- `backend/services/analysis_context_service.py`
- `backend/models/analysis_context.py`
- `backend/routers/players.py`

---

## 12. Custom Metrics and Ask Registry

Custom Metrics answer: how should a user-defined composite rank players?

Method:

- Validate all component stats against supported `SeasonStat` fields.
- Normalize weights to sum to `1.0`.
- Invert lower-is-better stats such as turnovers and defensive rating.
- Z-score each component across the selected eligible pool.
- Composite score is the weighted sum of component z-scores.

Formula:

```text
component_z_i = zscore(component_value_i)

if inverse:
  component_z_i = zscore(-component_value_i)

custom_metric_score = sum(component_z_i * normalized_weight_i)
```

Warnings:

- If weights do not sum to `1.0`, they are normalized.
- If one component is at least `85%` of the weight, the metric is marked weight-sensitive.
- If per-game volume stats are mixed with rate or impact stats, interpretation warnings are shown.
- If one component contributes more than `60%` of a player's absolute contribution, an anomaly is surfaced.

Ask/query metric registry:

- Maps user-facing terms and aliases to supported metric keys.
- Defines labels, descriptions, formats, entity types, source tables, and whether higher is better.

Why this design:

- Z-score blending lets users combine unlike units.
- Warnings make custom rankings auditable rather than pretending every composite is stable.

Limitations:

- Custom metrics are only as meaningful as the user's component choices.
- Z-score pools change when filters change.
- Imported impact stats remain external methodologies.

Implementation references:

- `backend/services/custom_metric_service.py`
- `backend/services/query_metric_registry.py`
- `backend/services/query_service.py`

---

## 13. Global Interpretation Rules

Use these defaults when reading CourtVue methodology:

- Treat `None` as unavailable, not zero.
- Check sample size before trusting a rate.
- Prefer same-season z-scores for role and style comparison.
- Treat proxy metrics as directional unless the UI labels them as official.
- Read confidence notes and warnings as part of the result, not decoration.
- Do not infer trade feasibility from Team-Fit.
- Do not infer health or coach trust from raw production drops without availability context.

Known platform-wide limitations:

- No optical tracking model is assumed unless a surface explicitly says it uses tracking rows.
- Shot quality is location/context based today, not defender-distance based.
- On/off, clutch, lineup, and signature-game metrics are high variance.
- Current-season outputs can lag source updates until sync jobs run.
- Some methodology is deterministic by design, which improves auditability but can miss nuance a trained analyst would add.
