# Sprint 15 Validation Matrix

**Sprint:** 15  
**Status:** Active checklist  
**Goal:** Mark every launch-window page as validated, blocked, or accepted-with-gap before feature work resumes.

Legend:

- `Ready` — validated with current local data
- `In Progress` — expected to become ready from active warehouse/backfill work
- `Accepted Gap: Licensed Metrics` — page is launch-usable, but some premium external metrics are intentionally absent
- `Blocked: Historical Warehouse` — would require explicit historical warehouse backfill
- `Needs Validation` — data likely present but page has not been checked yet

## Launch-Window Matrix

| Surface | `2022-23` | `2023-24` | `2024-25` | `2025-26` | Primary dependency / note |
|--------|-----------|-----------|-----------|-----------|---------------------------|
| Player page | `Accepted Gap: Licensed Metrics` | `Accepted Gap: Licensed Metrics` | `Accepted Gap: Licensed Metrics` | `Accepted Gap: Licensed Metrics` | Core stats + PBP are present; premium metrics should not block launch usability |
| Team page | `Needs Validation` | `Needs Validation` | `Ready` | `In Progress` | `2025-26` still depends on warehouse/PBP continuing to fill |
| Leaderboards | `Accepted Gap: Licensed Metrics` | `Accepted Gap: Licensed Metrics` | `Accepted Gap: Licensed Metrics` | `Accepted Gap: Licensed Metrics` | Standard/on-off/lineup data exists; free launch path should not depend on premium metrics |
| Compare | `Accepted Gap: Licensed Metrics` | `Accepted Gap: Licensed Metrics` | `Accepted Gap: Licensed Metrics` | `Accepted Gap: Licensed Metrics` | Career and profile data exist; imported premium metrics are additive rather than required |
| Insights | `Needs Validation` | `Needs Validation` | `Needs Validation` | `Needs Validation` | Depends mainly on `season_stats`; should be viable already |
| Standings | `Needs Validation` | `Needs Validation` | `Needs Validation` | `Needs Validation` | Computed from `player_game_logs`, not external APIs |
| Coverage | `Blocked: Historical Warehouse` | `Blocked: Historical Warehouse` | `Ready` | `In Progress` | Coverage page is warehouse/PBP-first; only `2024-25` / `2025-26` are sprint targets |
| Game Explorer | `Blocked: Historical Warehouse` | `Blocked: Historical Warehouse` | `Ready` | `In Progress` | Historical seasons have legacy PBP but not warehouse-backed game summaries |

## Explicit Sprint Exit Checks

- `2023-24` historical PBP retry completes without `uq_lineup_season` failure
- `2024-25` warehouse stays at zero failed / zero stalled jobs
- `2025-26` keeps advancing on:
  - parsed PBP
  - materialized game stats
  - `player_on_off`
  - `lineup_stats`
- `RAPTOR` is imported or clearly queued as the primary free external metric
- each missing licensed/source-gated metric-season pair is explicitly marked in `specs/sprint-15-data-gap-inventory.md`

## Validation Procedure

For each `Needs Validation` or `In Progress` cell:

1. Open the page for a representative entity in that season.
2. Record whether the data rendered meaningfully.
3. If it failed, classify the gap as one of:
   - warehouse incomplete
   - historical backfill incomplete
   - accepted licensed metric gap
   - product code bug
4. Update this file or the sprint notes before opening unrelated feature work.
