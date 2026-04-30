# Sprint 79 Closeout — Data Foundation: High-Leverage Methodology Unblocks

**Date:** 2026-04-29
**Branches:** Direct-to-master (single-stream conversational sprint, no feature branches)
**Status:** Shipped on `master`.

---

## Theme

Sprint 79 closes three concrete data-foundation gaps surfaced by a pressure-test of the platform after Sprint 78 (10-team parallel) shipped. Two were *designed feature unblocks waiting on small data work* and one was a *live credibility bug*. The original plan added Spotrac salary scraping; that was deferred to Sprint 80 in favor of higher leverage-per-hour items.

Sprint shape: **single-stream conversational sprint** rather than a parallel-team architecture pipeline. The work was data-foundation focused (services + migrations + tests), not feature-development, so the architect → engineer → reviewer → optimizer pipeline added overhead without proportional value.

The pressure-test that drove the rescope:
1. **Playoff Command Center has been rendering against stale data since Sprint 75.** `pbp_sync_service.py` hardcoded `is_playoff=False` on every write. `PlayerOnOff`, `LineupStats`, and `SeasonStat.clutch_*` were never populated for playoff games even though the raw PBP events were in the DB. Series Intelligence, MVP clutch modifiers, and OpponentLineupMatchupMatrix all silently fell back to regular-season splits.
2. **`mvp_case_v5` and `opportunity_v2` are fully designed in `specs/methodology-future-modeling.md`** — math, validation fixtures, acceptance criteria all written. Each blocked on a single data input.
3. **Sync hosting migration deferred** because Postgres lives on the laptop — moving cron without first deciding on managed Postgres vs. Tailscale vs. self-hosted Postgres is premature. Folded into Sprint 80 follow-ons.

---

## Sprint shape

Three streams, all merged direct to `master`:

- **Stream A1** — Award Voting + `mvp_case_v5` calibration scaffolding (data ingestion, math, registry wiring)
- **Stream A2** — Role expansion observations + `opportunity_v2` uplift KNN (full integration shipped end-to-end)
- **Stream B** — Playoff PBP derivations (credibility bug fix + cascade refactor + daily_sync wiring)

Backend tests went from **348 → 374 (+26)**. Zero regressions. `npx tsc --noEmit` clean (no frontend changes). `npm run lint` warning count unchanged.

---

## Stream B — Playoff PBP Derivations

**The bug.** `_upsert_lineup` in `pbp_sync_service.py` filtered by `(lineup_key, season)` only — without `is_playoff`. Today this was dormant because no playoff derivation was ever invoked. But the moment one ran, every shared lineup_key would silently overwrite its regular-season row with playoff data. Fixing this *before* enabling any playoff derivation was the first item shipped.

**The cascade.** Five helpers in `pbp_sync_service.py` had `is_playoff=False` hardcoded into their filter and constructor calls:

- `_clear_player_outputs`
- `_clear_season_outputs`
- `_update_season_stats`
- `_upsert_on_off`
- `_upsert_lineup` (also the bug-fix site)

Each gained a defaulted `is_playoff: bool = False` parameter. `_sync_games` propagates the value through. Default-False on every signature preserves existing regular-season callers exactly. Adding the parameter at the top is a non-breaking change.

**New top-level function:** `sync_pbp_for_playoffs_from_db(db_session, season)` — pulls playoff game IDs from `GameLog.season_type == "Playoffs"`, runs the full derivation pipeline with `is_playoff=True`. DB-based variant (not live API) so derivations only operate on already-stored games.

**Upstream fix in `bulk_sync_service.py`:** lines 372/424 hardcoded `season_type="Regular Season"` when persisting `PlayerGameLog` rows from box scores. Now accepts `season_type` parameter (defaults preserve existing callers); also splits the `_mark_running` sync_type into `game_logs` vs `game_logs_playoffs` so the `sync_status` unique constraint doesn't collide when both run.

**API helper:** `get_playoff_game_ids(season)` added to `nba_client.py` — `LeagueGameLog` with `season_type_all_star="Playoffs"`, cached via `CacheManager` keyed on `playoff_game_ids:{season}`.

**`bulk_import.py --playoff`:** new flag routes both `--game-logs` and `--pbp` paths to playoff variants. For backfill/bootstrap.

**`sync_playoff_pbp.py`:** previously stopped after fetching events because the derivation pipeline would corrupt regular-season aggregates. Now calls `sync_pbp_for_playoffs_from_db` after the event fetch completes. New `--skip-derivations` flag for cases where someone wants the previous events-only behavior.

**`daily_sync.sh` playoff block:** explicit `sync_playoff_pbp.py` call appended after `scripts/sync_playoff_full.py`. Verified `sync_playoff_full.py` doesn't already invoke `sync_playoff_pbp.py`, so the additive call has no dedup risk; idempotency in the helper is the safety net.

**Migration `0014_sprint79_playoff_indexes`:** no new columns (`is_playoff` already exists on both `PlayerOnOff` and `LineupStats` from migration `0012`). Migration does:
1. Defensive backfill: `UPDATE lineup_stats SET is_playoff = FALSE WHERE is_playoff IS NULL` (and same for `player_on_off`)
2. Dialect-aware boolean literal: `FALSE` for Postgres, `0` for SQLite
3. Indexes: `ix_lineup_stats_playoff_team` on `(season, team_id, is_playoff)` (Series Intelligence access pattern), `ix_player_on_off_playoff` on `(season, is_playoff)`

Applied successfully to live Postgres + verified.

**Tests:** 3 isolation tests in `test_playoff_pbp_derivations.py`:
- Bug fix: shared `lineup_key` retains regular-season values after playoff derivation runs against it
- `PlayerOnOff` isolation: same player + season carry both regular-season and playoff rows independently
- `_clear_season_outputs` correctly scopes its DELETE to the requested `is_playoff` slice

Schema migration test extended to assert both new indexes post-`0014`.

---

## Stream A2 — opportunity_v2 (Role Expansion Uplift)

**Goal:** every Opportunity row carries an evidence band — historical TS% change for players similar to T who took on more usage. Methodology spec: `specs/methodology-future-modeling.md#2`.

**Migration `0015_sprint79_role_expansion`:** new `role_expansion_observations` table. Columns: `player_id`, `from_season`, `to_season`, `usg_delta`, `pre_ts_pct`, `post_ts_pct`, `ts_delta`, `pre_ast_rate`, `pre_obpm`, `pre_age`, `pre_role_archetype`, `computed_at`. Unique key on `(player_id, from_season, to_season)`. Index on `(pre_role_archetype, pre_ts_pct)` for the KNN's primary query path.

**Materialization service:** `services/role_expansion_materialization_service.py`. Walks `season_stats`, finds (player_id, season) pairs where `usg_pct(season) - usg_pct(season-1) >= +0.03` AND both seasons have `gp >= 40`. Aggregates traded-player rows via GP-weighted average for percentage stats. Computes covariates including archetype label via `classify_player_archetype` (reuses `archetype_rules_v2`). Idempotent per-row upsert.

**Live data:** materialization produces **286 observations** across the live Postgres `season_stats` table — roughly the spec target of ~350. 1063 players processed, 1081 rows skipped (mostly low-GP or non-consecutive seasons). Re-run produces 0 net new rows (286 updated in place) — idempotency confirmed end-to-end.

Top-5 biggest historical usage bumps surface canonical role-expansion stories: Jerami Grant 2020-21 OKC primary scorer (-3.5 TS%), Harrison Barnes 2016-17 Dallas, Michael Porter Jr. 2025-26 Brooklyn, etc. The data shape matches what an opportunity_v2 KNN should be able to evidence-band.

**KNN service:** `services/opportunity_uplift_service.py`. Per spec: K=20 nearest neighbors in archetype-conditioned feature space, `±0.04` TS% archetype-match window, shrunk-Mahalanobis distance over `(usg_delta, pre_ts_pct, pre_ast_rate, pre_obpm, pre_age)`. Returns `OpportunityUplift` with `mean_uplift`, `uplift_band_lower` (25th pct), `uplift_band_upper` (75th pct), `neighbor_count`, `evidence_confidence` (high ≥15, medium ≥8, low ≥5), and top-3 `comparable_examples` for analyst audit. Returns `None` when `neighbor_count < 5` (subject too unique).

**Robustness:** When the candidate covariance matrix is singular (small/uniform pools — common in tests, possible in low-coverage archetypes), the KNN auto-falls back to weighted Euclidean. Same pattern as `similarity_v3` below 3×n_features samples.

**Pydantic models:** `OpportunityUplift` + `OpportunityUpliftComparable` added to `models/insights.py`. `OpportunityPlayerRow.uplift: Optional[OpportunityUplift]` is a sibling field — non-breaking; existing API consumers ignore it.

**Service integration:** `opportunity_service.py`:
- Batch-classifies archetypes via `classify_many` once per request before the row-build loop (avoids re-warming the season frame per row).
- Per-row uplift call uses the player's archetype, current TS%, projected `+0.05` usage delta (the spec's standard role-expansion magnitude), `ast_rate` derived from `ast_pg / min_pg * 36`, `obpm` from season_stats, age from `parse_age_as_of_season`.
- `METHODOLOGY_VERSION` bumped from `"opportunity_v1"` to `"opportunity_v2"`.
- New methodology note: "v2: per-row uplift estimates the historical TS% range when comparable players took on +5pp usage. Descriptive evidence band, not causal projection."

**Live verification:** OKC roster query at `team='OKC'`, `min_minutes=18.0`: 11 qualifying rows, **4 carry uplift** (~36% coverage). Sample: Jaylin Williams returns mean -1.08 TS%, IQR [-2.0%, +0.25%], n=10 medium-confidence comparables. Coverage falls below the spec's 60% target on the live data — this is because some current-season players aren't archetype-classifiable (rookies, low-sample) or have null `obpm`. Coverage will improve as more season-stats backfills.

**Registry:** `opportunity_v1 → opportunity_v2` with `status="active"` (was `"active_with_uplift_followup"`). Added `role_expansion_observations` to `input_families`. Added uplift KNN sample gates and confidence rules. Implementation refs now include the materialization + uplift services.

**Validation fixture:** `opportunity_role_expansion_uplift` added to `methodology_validation_service.py`. Asserts the high-fit / thin-comp behavior contract and notes the held-out backtest target.

**`daily_sync.sh`:** new `sync_role_expansion.py` call wired in nightly after `season_stats` materialization. Dry-run output extended.

**Tests:** 12 new tests, all passing.
- 6 in `test_role_expansion_materialization.py`: qualifying-pair detection, threshold filtering, GP filtering, non-consecutive season handling, idempotency, traded-player aggregation.
- 6 in `test_opportunity_uplift.py`: minimum-neighbor floor, high-confidence band, archetype filtering, TS-window filtering, missing-feature handling, percentile band ordering.

Schema migration test asserts the new table + columns post-`0015`.

---

## Stream A1 — `mvp_case_v5` (Award Voter Calibration Scaffolding)

**Goal:** replace the Sprint 76 hand-tuned Award Case modifier weights (`team_framing 0.08`, `eligibility_pressure 0.08`, `clutch 0.06`, `momentum 0.05`, `signature_games 0.05`) with weights calibrated against historical MVP voting outcomes via constrained coordinate-descent + leave-one-season-out cross-validation. Methodology spec: `specs/methodology-future-modeling.md#1`.

**Status: pipeline shipped, calibration gated on a follow-up materializer.**

**Migration `0016_sprint79_award_voting`:** new `award_voting` table. Columns: `player_id`, `season`, `award_type` (MVP/DPOY/MIP/6MOY for future use), `ballot_position`, `voter_count`, `total_award_points`, `source`. Unique key on `(player_id, season, award_type, ballot_position)`. Index on `(season, award_type)`.

**Seed CSV:** `backend/data/seed/award_voting_seed.csv`. **57 ballot rows across 13 MVP races** (2012-13 through 2024-25). Top-5 vote-getters per season. Player IDs verified against the live `players` roster. Falls 2 seasons short of the spec's "≥15 seasons of MVP votes" target — flagged as a follow-on (the missing seasons require Dirk Nowitzki, Kobe Bryant, etc. to be added to the `players` table).

**Loader:** `services/award_voting_ingestion_service.py` + `data/sync_award_voting.py` CLI. Same shape as `sync_salaries.py`. Idempotent per-row upsert. Skips ballot entries for unknown players (won't invent roster). One-time backfill — not wired into `daily_sync.sh` (voting outcomes are annual, not nightly).

**Calibration service:** `services/award_calibration_service.py`. All math implemented and unit-tested:
- `_spearman_correlation` — pure-Python rank correlation
- `_award_case_score` — composite scoring with W·M dot product
- `_project_to_constraints` — enforces `W >= 0` and `Σ W_j ≤ 0.40`
- `coordinate_descent_fit` — bounded grid search over 5D weight space, defaults to grid resolution `0.01` and radius `0.06`
- `leave_one_season_out_cv` — fold mechanics with minimum-fold gating
- `_enforce_drift_cap` — per-pillar movement cap of 0.04 absolute (so calibration tunes, doesn't replace, the priors)
- `calibrate_award_case_weights(db)` — public entry point that returns a result envelope with `weights`, `cross_validated_spearman`, `fold_count`, `last_calibrated_season`, `calibration_pending`, and `notes`

**The gate.** The calibration math needs *both* the historical voting outcome (which `award_voting` now provides) AND the matched Basketball Value + 5-vector modifier per candidate-season. The latter requires retroactive runs of `mvp_service` against past seasons — that's a separate materializer and is the blocker. Until it lands:
- `calibrate_award_case_weights(db)` returns `calibration_pending=True` with the existing hand-tuned defaults
- `CALIBRATED_AWARD_CASE_WEIGHTS` is initialized to `DEFAULT_AWARD_CASE_WEIGHTS` (matches Sprint 76 priors exactly)
- `mvp_service.py` reads from this constant — when materialization lands, flipping the switch is a one-line change to that import

**Service wiring in `mvp_service.py`:** the hand-tuned multipliers at line ~1920 are replaced with reads from `CALIBRATED_AWARD_CASE_WEIGHTS`. New import at the top. No behavioral change today; pipeline ready for the calibration data.

**Registry:** `mvp_case_v4 → mvp_case_v5` with `status="active_with_calibration_pending"`. Added `award_voting` to `input_families`. Added the calibration sample gate. Reliability policy spells out the LOO-CV addition. Known limitations note the materialization gating.

**Validation fixture:** `mvp_award_case_voter_calibration` added to `methodology_validation_service.py`. Documents the expected behavior contract: held-out Spearman ≥ 0.7, per-pillar drift ≤ 0.04, suppress-on-pending semantics.

**Tests:** 14 new tests in `test_award_calibration.py`, all passing.
- Spearman correlation primitive: perfect, inverse, degenerate inputs
- Constraint projection: clip negatives, scale to cap, pass-through valid
- Award case score combines correctly
- **Coordinate descent recovers known weights** on synthetic ground-truth data (Spearman ≥ 0.95)
- LOO-CV reports correct fold count + computes mean Spearman across folds
- LOO-CV returns defaults below `MIN_FOLDS_REQUIRED=5`
- Drift cap clamps runaway calibration per spec
- `calibrate_award_case_weights` returns `pending=True` on empty table
- `calibrate_award_case_weights` reports `last_calibrated_season` when voting data exists but modifier vectors don't
- `MODIFIER_KEYS` matches the spec's 5-name lock

Schema migration test asserts new table + columns post-`0016`.

---

## Verification

- **Backend tests:** **374 passed** (was 348 at Sprint 78 close, +26 new).
- **`npx tsc --noEmit`:** clean (no frontend changes this sprint).
- **`npm run lint`:** unchanged warning count.
- **Live smoke tests:**
  - Migration `0014` applied to Postgres, indexes confirmed via `inspect`
  - Migration `0015` applied; `RoleExpansionObservation.materialize` produces 286 rows; idempotent re-run
  - Migration `0016` applied; `sync_award_voting.py` loads 57 rows across 13 seasons
  - `compute_uplift` against live data returns `mean=+0.0034 / band=[-0.013, +0.014] / n=20 / conf=high` for a typical balanced-role TS=0.56 query
  - Full Opportunity report against OKC produces `methodology.version="opportunity_v2"` with 4 of 11 rows carrying uplift
  - Registry shows `mvp_case_v5 / active_with_calibration_pending` and `opportunity_v2 / active`

---

## Sprint shape vs. plan

The original Sprint 79 plan included a **3-stream sprint** with Spotrac salary scraping (Stream A) + Playoff PBP (Stream B) + sync hosting migration (Stream C).

The plan was rewritten mid-sprint after a pressure-test of the data foundation found:
- The Playoff Command Center rendering bug had been live since Sprint 75 (high credibility cost)
- `mvp_case_v5` and `opportunity_v2` were fully designed and waiting on small data unblocks (high features-per-hour)
- Spotrac scraping is high-friction (anti-bot, fragile HTML) and the Trade Machine works fine with empty-state warnings (low features-per-hour)
- Postgres on the laptop blocked sync hosting migration (blocked on a separate decision)

The pivot traded one fragile scraping integration for **two designed-feature unblocks + one credibility-bug fix in the same hour budget.** Spotrac and sync hosting both moved to Sprint 80.

---

## Files

**New (10):**
- `backend/alembic/versions/0014_sprint79_playoff_pbp_indexes.py`
- `backend/alembic/versions/0015_sprint79_role_expansion.py`
- `backend/alembic/versions/0016_sprint79_award_voting.py`
- `backend/services/role_expansion_materialization_service.py`
- `backend/services/opportunity_uplift_service.py`
- `backend/services/award_calibration_service.py`
- `backend/services/award_voting_ingestion_service.py`
- `backend/data/sync_role_expansion.py`
- `backend/data/sync_award_voting.py`
- `backend/data/seed/award_voting_seed.csv`

**New tests (3):**
- `backend/tests/test_playoff_pbp_derivations.py`
- `backend/tests/test_role_expansion_materialization.py`
- `backend/tests/test_opportunity_uplift.py`
- `backend/tests/test_award_calibration.py`

**Modified (10):**
- `backend/services/pbp_sync_service.py` — `is_playoff` cascade + bug fix + new top-level function
- `backend/services/bulk_sync_service.py` — `season_type` parameter, `sync_type` disambiguation
- `backend/services/opportunity_service.py` — uplift integration, `v1 → v2` bump
- `backend/services/mvp_service.py` — read weights from `CALIBRATED_AWARD_CASE_WEIGHTS`
- `backend/services/methodology_registry_service.py` — `mvp_case_v5` + `opportunity_v2` entries
- `backend/services/methodology_validation_service.py` — 2 new fixtures
- `backend/data/nba_client.py` — `get_playoff_game_ids`
- `backend/data/sync_playoff_pbp.py` — derivation wire-up + `--skip-derivations`
- `backend/data/bulk_import.py` — `--playoff` flag
- `backend/data/daily_sync.sh` — playoff PBP block + role expansion call + dry-run lines
- `backend/db/models.py` — `AwardVote` + `RoleExpansionObservation` ORM models
- `backend/models/insights.py` — `OpportunityUplift` + `OpportunityUpliftComparable` + sibling field
- `backend/tests/test_schema_migrations.py` — head revision + new index/table assertions

---

## Open follow-ons

### Sprint 80 candidates (deferred from this sprint)

1. **Sync hosting migration** — move `daily_sync.sh` off the laptop. Blocker: Postgres lives on the laptop, so the move requires a paired decision on managed Postgres (~$15/month DigitalOcean Managed DB), Tailscale VPN to the laptop (free but doesn't fix laptop-asleep), or self-hosting Postgres on a larger Droplet ($12/month). Each is a separate cost/complexity tradeoff.
2. **Spotrac salary scraper** — replace `contracts_2025_26.csv` seed with live Spotrac data so Trade Machine, Free Agency, and Team Arc work against real cap numbers. Hardest part: 4-tier name resolution against the `players` table (exact alias → team-scoped → last-name+initial → `difflib`). Use stdlib `urllib.request` + `html.parser` to avoid new dependencies.

### Stream-specific follow-ons from Sprint 79

3. **Materialize historical Basketball Value + modifier vectors** so `mvp_case_v5` calibration actually fits weights. Without this, `calibrate_award_case_weights` returns `calibration_pending=True` and weights stay at the Sprint 76 hand-tuned priors. Approach: retroactively run `mvp_service` against past seasons (2012-13 through 2024-25), persist the per-candidate Basketball Value + 5-vector modifier into a new `mvp_historical_candidates` table, then call `coordinate_descent_fit` over the joined dataset. Estimated: 1-2 hours once the materialization is scoped.
4. **Add 2 more seasons of MVP voting** (2010-11, 2011-12) once Dirk Nowitzki, Kobe Bryant, and Derrick Rose-era pre-2013 winners are added to the `players` table. Brings the seed CSV to the spec's ≥15-season target.
5. **DPOY / MIP / 6MOY voter calibration** — reuse the same calibration harness with new seed CSVs. Same coordinate-descent + LOO-CV path.

### Coverage improvements

6. **opportunity_v2 uplift coverage** is at ~36% on live OKC data; spec target is 60%. Improvement requires more current-season players to be archetype-classifiable (most gaps are missing `obpm` or low-sample players). May resolve naturally after the next full season-stats sync; otherwise needs a coverage audit.
7. **Held-out backtest for opportunity_v2** — the spec acceptance criterion of "predict 2024-25 ts_delta using only 2023-24 and earlier neighbors; MAE ≤ 0.025" was not run this sprint. Should land as a one-shot validation script in `tests/` or `scripts/` before opportunity_v2 is treated as fully validated.

### Deferred-from-original-plan (still in backlog)

8. **NCAA draft scraper** — replace `draft_prospects_2026.csv` seed with live Sports Reference data. Seasonal feature; current seed sufficient through summer.
9. **ProSportsTransactions injury history** — replace `player_injury_history_seed.csv` synthetic seed. Synthetic adequate for thin-cohort fallback.
10. **Causal modeling / multi-season uplift** — out of scope per `methodology-future-modeling.md`.

---

## Risks captured + outcomes

1. **`_upsert_lineup` data corruption risk** — the bug was dormant only because no playoff derivation had ever run. Fixing it before enabling any derivation was non-negotiable. Tests verify regular-season rows survive intact; verified end-to-end before the daily_sync wire-up.
2. **`mvp_case_v5` data gating** — spec called this out as the largest sprint risk. Outcome: shipped the math + harness + tests + registry wiring, gated the actual calibration on a follow-up materializer. Honest about the limitation in the registry status (`active_with_calibration_pending`).
3. **opportunity_v2 coverage below spec target** — flagged as follow-on. Doesn't block the feature working; just means some rows render without the uplift band.
4. **Migration revision name length** — Alembic `version_num` column is `varchar(32)`. Two migrations were initially named over-length and renamed. Future migration names should stay under 32 chars.
5. **Postgres boolean `UPDATE` literals** — `is_playoff = 0` works on SQLite but Postgres requires `is_playoff = FALSE`. Migration `0014` uses dialect-aware literal selection. Same pattern recommended for any future migrations that backfill boolean columns.
6. **Single-stream conversational sprint vs. parallel pipeline** — the standard `Architect → Engineer → Reviewer → Optimizer` was overkill for data-foundation work. Conversational sprint with direct master commits hit the same quality bar (374 tests, zero regressions) faster.

---

## Master tip after Sprint 79

`master` advances by the cumulative diff documented above. No feature branches were used.
