# Sprint 16 Validation Matrix

**Sprint:** 16  
**Status:** Active validation with remaining live `2025-26` warehouse catch-up  
**Goal:** Mark every launch-window page as validated, in progress, or accepted as a non-blocking scope limit before feature work resumes.

Legend:

- `Ready` — validated with current local data
- `In Progress` — expected to become ready from active warehouse work
- `Needs Validation` — data likely exists but the page has not been checked yet
- `Accepted Scope Limit` — intentionally not fully warehouse-backed, but not a launch blocker
- `Product Bug` — data exists, page behavior still needs a code fix

## Launch-Window Matrix

| Surface | `2022-23` | `2023-24` | `2024-25` | `2025-26` | Primary dependency / note |
|--------|-----------|-----------|-----------|-----------|---------------------------|
| Player page | `Ready` | `Ready` | `Ready` | `Ready` | Native player/profile/career/game-log/on-off stack validated after fixing the Python 3.8 `gamelogs.py` handler bug |
| Team page | `Accepted Scope Limit` | `Accepted Scope Limit` | `Ready` | `In Progress` | Historical seasons are legacy-plus-derived only; `2025-26` improves as warehouse PBP catches up |
| Leaderboards | `Ready` | `Ready` | `Ready` | `Ready` | Standard, on/off, and lineup leaderboard APIs all return data; old import-first copy removed |
| Compare | `Ready` | `Ready` | `Ready` | `Ready` | Compare uses the same player-profile and career stack validated on the player page |
| Insights | `Ready` | `Ready` | `Ready` | `Ready` | Fixed prior-season routing bug so breakouts now return improvers/decliners for all launch-window seasons |
| Standings | `Ready` | `Ready` | `Ready` | `Ready` | Driven by local `player_game_logs`; all four launch-window seasons return 30-team standings |
| Coverage | `Accepted Scope Limit` | `Accepted Scope Limit` | `Ready` | `In Progress` | Historical warehouse coverage is intentionally out of scope |
| Game Explorer | `Accepted Scope Limit` | `Accepted Scope Limit` | `Ready` | `In Progress` | Historical seasons use legacy PBP; only `2024-25` / `2025-26` are warehouse-backed targets |

## Explicit Sprint Exit Checks

- `2024-25` warehouse remains stable and complete (`1230/1230/1230`; all jobs complete)
- `2025-26` parsed PBP and derived tables keep advancing from the kickoff baseline (`1119` box, `579` parsed PBP, `1119` materialized at last check)
- no current recurrence of the old player-page Python 3.8 crash or the insights prior-season bug
- every `Needs Validation` or `In Progress` cell ends the sprint as one of:
  - `Ready`
  - `Accepted Scope Limit`
  - `Product Bug` with a documented follow-up

## Validation Procedure

For each `Needs Validation` or `In Progress` cell:

1. Open a representative entity or game for that season.
2. Record whether the page renders meaningful native data.
3. If it fails, classify the issue as one of:
   - `2025-26` warehouse incomplete
   - historical backfill incomplete
   - product code bug
   - accepted scope limit
4. Update this file before starting unrelated feature work.
