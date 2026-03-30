# Sprint 16 Data Gap Inventory

**Sprint:** 16  
**Date:** 2026-03-30  
**Status:** Kickoff baseline

## Current Coverage Snapshot

| Season | `player_game_logs` | `player_on_off` | `lineup_stats` | `games` | `game_player_stats` | `game_team_stats` |
|--------|--------------------|-----------------|----------------|---------|---------------------|-------------------|
| `2022-23` | `40931` | `554` | `17094` | `0` | `0` | `0` |
| `2023-24` | `43394` | `595` | `16190` | `0` | `0` | `0` |
| `2024-25` | `43369` | `587` | `18395` | `1230` | `43369` | `2460` |
| `2025-26` | `39293` | `551` | `9392` | `1230` | `39293` | `2238` |

Warehouse-specific kickoff state:

| Season | Scheduled games | Box complete | Parsed PBP | Materialized | Jobs |
|--------|------------------|--------------|------------|--------------|------|
| `2024-25` | `1230` | `1230` | `1230` | `1230` | `2441 complete`, `1 running`, `1250 queued` |
| `2025-26` | `1230` | `1119` | `501` | `1119` | `1563 complete`, `4 running`, `1792 queued` |

## Sprint 16 Launch Assumptions

- Launch window remains `2022-23` through `2025-26`
- External metrics are fully out of scope for Sprint 16
- `2022-23` and `2023-24` are launch-complete on a legacy-plus-derived basis if the major pages are usable
- `2024-25` should remain warehouse-complete throughout the sprint
- `2025-26` is the only season that still needs major warehouse catch-up

## Page-To-Data Dependency Matrix

| Surface | Required data layers | Kickoff status | Gap class | Sprint 16 remediation |
|--------|-----------------------|----------------|-----------|-----------------------|
| Player page | `players`, `season_stats`, `player_game_logs`, `player_on_off`, PBP-derived splits | Should be usable across all launch-window seasons | needs validation | Validate representative players and fix any null/partial-data bugs |
| Team page | `teams`, `player_game_logs`, `player_on_off`, `lineup_stats` | `2024-25` should be ready; `2025-26` still depends on warehouse/PBP finishing | in progress | Keep workers running and validate team intelligence/lineup sections |
| Leaderboards | `season_stats`, `player_on_off`, `lineup_stats`, career rollups | Should be broadly usable without external metrics | needs validation | Remove misleading empty-state behavior if data already exists |
| Compare | player profile + career rollups | Should be usable on native data alone | needs validation | Validate multi-season compare flows and fix any partial-data rendering bugs |
| Insights | multi-season `season_stats` | Expected to be usable now | needs validation | Validate representative player/team outputs |
| Standings | `player_game_logs`-driven standings computation | Expected to be usable across launch-window seasons | needs validation | Confirm representative seasons and note any accepted limits |
| Coverage | warehouse/PBP coverage + job summary | `2024-25` ready; `2025-26` in progress; historical seasons intentionally not warehouse-backed | in progress + accepted scope limit | Finish `2025-26`; treat historical warehouse coverage as out of scope unless product validation proves a blocker |
| Game Explorer | warehouse `games`, `game_player_stats`, `game_team_stats`, PBP | `2024-25` ready; `2025-26` in progress; historical seasons use legacy PBP without warehouse summaries | in progress + accepted scope limit | Finish `2025-26`; only add selective historical warehouse support if validation proves necessary |

## Explicit Sprint 16 Exit Criteria

- `2024-25` remains at zero failed and zero stalled warehouse jobs
- `2025-26` materially advances from the kickoff baseline, with warehouse-backed current-season pages working reliably
- `2023-24` historical PBP retry path is confirmed healthy on the idempotent write path
- every launch-window page is either:
  - validated working, or
  - explicitly marked as an accepted non-blocking scope limit
- no remaining page should imply “data may be missing” when the real issue is a known, accepted scope boundary

## Explicitly Out Of Scope

- `EPM`, `LEBRON`, `PIPM`, `RAPTOR`, and `RAPM`
- full historical warehouse expansion for `2022-23` / `2023-24`
- new product features unrelated to data completeness
