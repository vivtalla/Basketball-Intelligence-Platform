# Sprint 16 Data Gap Inventory

**Sprint:** 16  
**Date:** 2026-03-30  
**Status:** Active validation state

## Current Coverage Snapshot

| Season | `player_game_logs` | `player_on_off` | `lineup_stats` | `games` | `game_player_stats` | `game_team_stats` |
|--------|--------------------|-----------------|----------------|---------|---------------------|-------------------|
| `2022-23` | `40931` | `554` | `17094` | `0` | `0` | `0` |
| `2023-24` | `43394` | `595` | `16190` | `0` | `0` | `0` |
| `2024-25` | `43369` | `587` | `18395` | `1230` | `43369` | `2460` |
| `2025-26` | `39279` | `552` | `10378` | `1230` | `39279` | `2238` |

Warehouse-specific live state:

| Season | Scheduled games | Box complete | Parsed PBP | Materialized | Jobs |
|--------|------------------|--------------|------------|--------------|------|
| `2024-25` | `1230` | `1230` | `1230` | `1230` | `3692 complete` |
| `2025-26` | `1230` | `1119` | `579` | `1119` | `1617 complete`, `6 running`, `1736 queued` after clean worker restart |

## Sprint 16 Launch Assumptions

- Launch window remains `2022-23` through `2025-26`
- External metrics are fully out of scope for Sprint 16
- `2022-23` and `2023-24` are launch-complete on a legacy-plus-derived basis if the major pages are usable
- `2024-25` should remain warehouse-complete throughout the sprint
- `2025-26` is the only season that still needs major warehouse catch-up

## Page-To-Data Dependency Matrix

| Surface | Required data layers | Kickoff status | Gap class | Sprint 16 remediation |
|--------|-----------------------|----------------|-----------|-----------------------|
| Player page | `players`, `season_stats`, `player_game_logs`, `player_on_off`, PBP-derived splits | Validated on native data across all launch-window seasons | resolved | Fixed `gamelogs.py` Python 3.8 crash and confirmed representative player flows |
| Team page | `teams`, `player_game_logs`, `player_on_off`, `lineup_stats` | `2024-25` ready; `2025-26` still depends on warehouse/PBP finishing | in progress + accepted scope limit | Keep workers running for `2025-26`; treat `2022-23` / `2023-24` as legacy-plus-derived scope |
| Leaderboards | `season_stats`, `player_on_off`, `lineup_stats`, career rollups | Validated | resolved | Import-first messaging removed; native leaderboards return data |
| Compare | player profile + career rollups | Validated through the player/profile/career stack | resolved | No extra Sprint 16 data work required |
| Insights | multi-season `season_stats` | Validated after bug fix | resolved | Fixed prior-season calculation so breakouts populate again |
| Standings | `player_game_logs`-driven standings computation | Validated across all launch-window seasons | resolved | No extra Sprint 16 data work required |
| Coverage | warehouse/PBP coverage + job summary | `2024-25` ready; `2025-26` in progress; historical seasons intentionally not warehouse-backed | in progress + accepted scope limit | Finish `2025-26`; historical warehouse coverage remains out of scope |
| Game Explorer | warehouse `games`, `game_player_stats`, `game_team_stats`, PBP | `2024-25` ready; `2025-26` in progress; historical seasons use legacy PBP without warehouse summaries | in progress + accepted scope limit | Finish `2025-26`; no broad historical warehouse expansion planned |

## Explicit Sprint 16 Exit Criteria

- `2024-25` remains warehouse-complete and stable
- `2025-26` materially advances from the kickoff baseline, with warehouse-backed current-season pages continuing to improve from the clean attached-worker path
- the player-page and insights regressions found during Sprint 16 validation are fixed
- every launch-window page is either:
  - validated working, or
  - explicitly marked as an accepted non-blocking scope limit
- no remaining page should imply “data may be missing” when the real issue is a known, accepted scope boundary

## Explicitly Out Of Scope

- `EPM`, `LEBRON`, `PIPM`, `RAPTOR`, and `RAPM`
- full historical warehouse expansion for `2022-23` / `2023-24`
- new product features unrelated to data completeness
