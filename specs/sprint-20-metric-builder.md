# Sprint 20 — Team A: Custom Metric Builder

Status: Ready to Merge

## Goal

Extend `Leaderboards` with a user-defined composite metric workflow that validates a stat configuration, computes normalized weighted scores, ranks players, and explains what the metric rewards.

## Product shape

- Surface: existing `Leaderboards` page
- Primary workflow label: `Build Your Own Metric`
- Keep existing standard leaderboards visible nearby as context
- Hardwood Editorial styling remains active

## Backend contract

- Add `POST /api/leaderboards/custom-metric`
- Request shape:
  - `metric_name`
  - `player_pool`
  - `season`
  - `components[]` with `stat_id`, `label`, `weight`, `inverse`
- Response shape must match the sprint contract exactly:
  - `metric_label`
  - `metric_interpretation`
  - `player_rankings`
  - `top_player_narratives`
  - `anomalies`
  - `validation_warnings`

## Required rules

- Confirm all selected stats are available from real stored fields
- If weights do not sum to 1.0, normalize proportionally and warn
- Warn on degenerate weight concentration
- Warn when mixing raw volume stats with rate/per-possession stats
- Z-score normalize each component across the eligible player pool before weighting
- Apply inverse handling so lower-is-better stats contribute positively
- Exclude players missing any required stat and warn explicitly
- If fewer than 5 players qualify, return the specified insufficient-pool error
- Flag `weight-sensitive outliers` when one component drives more than 60% of total score contribution

## Frontend workflow

- Add a metric-builder panel inside `leaderboards`
- Include:
  - stat/component picker
  - weight editor
  - player-pool selector
  - season selector
  - validation/warning area
  - ranked results table
  - metric profile summary
  - anomaly callouts
- Use append-only additions in shared `types.ts` and `api.ts`
- If `3yr_avg` or `custom_range` are not cleanly backed by real data access, show them as deferred/unavailable rather than partially implementing them

## Test targets

- valid config returns rankings and metric profile
- non-1.0 weights normalize proportionally with warning
- incompatible stat family mix warns
- inverse handling is correct
- players missing component stats are excluded and warned
- <5 qualifying players returns insufficient-pool error
- anomaly detection flags >60% single-stat dominance
- leaderboards page still works for normal stat boards

## Implementation notes

- Implemented on Team A branch and merged into the Sprint 20 integration branch.
- Backend verification passed via compile check and `pytest backend/tests/test_custom_metric_service.py`.
- Frontend verification passed via `npm run lint` and integrated build validation on the kickoff branch.
