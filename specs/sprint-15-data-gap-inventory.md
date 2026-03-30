# Sprint 15 Data Gap Inventory

**Sprint:** 15  
**Date:** 2026-03-30  
**Status:** Active working document

## Current Coverage Snapshot

| Season | `season_stats` | `player_game_logs` | `player_on_off` | `lineup_stats` | `games` | `game_player_stats` | `game_team_stats` |
|--------|----------------|--------------------|-----------------|----------------|---------|---------------------|-------------------|
| `2022-23` | `824` | `40931` | `554` | `17094` | `0` | `0` | `0` |
| `2023-24` | `895` | `43394` | `595` | `16193` | `0` | `0` | `0` |
| `2024-25` | `953` | `43369` | `587` | `18395` | `1230` | `43369` | `2460` |
| `2025-26` | `746` | `39293` | `545` | `8296` | `1230` | `39293` | `2238` |

Warehouse-specific state:

| Season | Scheduled games | Box complete | Parsed PBP | Materialized |
|--------|------------------|--------------|------------|--------------|
| `2024-25` | `1230` | `1230` | `1230` | `1230` |
| `2025-26` | `1230` | `1119` | `423` | `1119` |

## Page-To-Data Dependency Matrix

| Surface | Required data layers | Current launch-window status | Gap class | Remediation path |
|--------|-----------------------|------------------------------|-----------|------------------|
| Player page | `players`, `season_stats`, `player_game_logs`, `player_on_off`, clutch/scoring splits, external metric columns | Core stats/logs available for `2022-23` to `2025-26`; external metrics still blank; PBP-derived coverage now present for all four seasons | external CSV/manual source | Import `EPM`, `RAPM`, `LEBRON`, `RAPTOR`, `PIPM`; then revalidate representative stars/rotation/bench players |
| Team page | `teams`, `season_stats`, `player_game_logs`, `player_on_off`, `lineup_stats` | `2022-23` to `2024-25` should be broadly usable; `2025-26` still depends on warehouse/PBP continuing to fill | in progress | Keep `2025-26` workers running; validate lineup/intelligence sections after each queue checkpoint |
| Leaderboards | `season_stats`, multi-season career rows, `player_on_off`, `lineup_stats` | Standard/career/on-off/lineup data now exists for four launch seasons, but external metrics remain blank and UI still contains old import guidance | in progress + external CSV/manual source | Finish external-metric import; then remove/accept remaining empty states after validation |
| Compare | `player_profile`, `career_stats`, advanced metric history | Box-score and career data present; external metric rows depend on CSV imports | external CSV/manual source | Import metrics and validate multi-year comparisons for representative players |
| Insights / Breakout Tracker | multi-season `season_stats` | Launch-window seasons already have enough season stats to function | ready | Validate output quality and confirm no missing-player edge cases |
| Standings | `player_game_logs`-derived standings computation | Should work for seasons with populated `player_game_logs` (`2022-23` to `2025-26`) | ready | Validate supported seasons and note that older seasons remain out of scope this sprint |
| Coverage | PBP coverage dashboard, warehouse job summary | `2024-25` ready; `2025-26` partially ready while queue continues | in progress | Continue warehouse work and confirm dashboard rows populate for `2025-26` as PBP advances |
| Game Explorer | `games`, `game_player_stats`, `game_team_stats`, `play_by_play` / warehouse-derived PBP | `2024-25` ready; `2025-26` partially ready; `2022-23` / `2023-24` supported through legacy PBP but not warehouse game summaries | in progress + future product decision | Finish `2025-26` warehouse; only backfill historical warehouse game summaries if product validation proves legacy support is insufficient |

## Missing Data Sources

### External metrics required for launch completeness

| Metric | Source | Import path | Known gap status |
|--------|--------|-------------|------------------|
| `EPM` | Dunks & Threes | `backend/data/epm_rapm_import.py --metrics epm` | CSV not yet acquired locally |
| `RAPM` | Public RAPM / nbarapm | `backend/data/epm_rapm_import.py --metrics rapm` | CSV not yet acquired locally |
| `LEBRON` | BBall Index | `backend/data/epm_rapm_import.py --metrics lebron` | CSV not yet acquired locally |
| `RAPTOR` | FiveThirtyEight historical data | `backend/data/epm_rapm_import.py --metrics raptor` | CSV not yet acquired locally |
| `PIPM` | Basketball Index historical files | `backend/data/epm_rapm_import.py --metrics pipm` | CSV not yet acquired locally |

### Explicit source-gap policy

If a metric cannot be sourced freely for a launch-window season:

1. mark the metric/season pair as a source gap in this document,
2. keep the UI behavior explicit about missing imported data,
3. do not misclassify the issue as a warehouse or NBA-feed bug.

## Sprint 15 Acceptance Targets

### Data completion

- `2024-25`: no failed jobs, no stalled jobs, full warehouse completeness maintained
- `2025-26`: box sync complete, PBP materially advanced toward full completed-game coverage, materialization and derived tables continue climbing
- `2022-23` and `2023-24`: `player_game_logs`, `player_on_off`, and `lineup_stats` remain populated and stable
- `2023-24` historical PBP retry completes cleanly on the idempotent write path

### Product validation

- No launch-window page should rely on “run import first” guidance when the underlying data already exists
- Remaining empty states must be attributable to one of:
  - unfinished `2025-26` warehouse/PBP work
  - missing external metric CSVs
  - explicit out-of-scope historical warehouse backfill

## Open Questions To Resolve During The Sprint

- Whether `2022-23` / `2023-24` need full warehouse game-summary support, or whether legacy-plus-derived support is sufficient for launch
- Whether the managed `warehouse_worker_pool.sh` launcher can be made reliable enough to replace attached local workers in this environment
- Whether `raw_game_payloads` needs an additional idempotency fix for repeated `cdn_pbp` payload inserts during retries
