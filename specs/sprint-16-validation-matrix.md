# Sprint 16 Validation Matrix

**Sprint:** 16  
**Status:** Active checklist  
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
| Player page | `Needs Validation` | `Needs Validation` | `Needs Validation` | `Needs Validation` | External metrics are out of scope; validate native data only |
| Team page | `Needs Validation` | `Needs Validation` | `Ready` | `In Progress` | Historical warehouse guidance copy has been corrected; still needs page-level verification |
| Leaderboards | `Needs Validation` | `Needs Validation` | `Needs Validation` | `Needs Validation` | Old import-first empty-state copy has been removed; validate native stats / on-off / lineup views only |
| Compare | `Needs Validation` | `Needs Validation` | `Needs Validation` | `Needs Validation` | Native multi-season data should be sufficient |
| Insights | `Needs Validation` | `Needs Validation` | `Needs Validation` | `Needs Validation` | Should work from existing season stats |
| Standings | `Needs Validation` | `Needs Validation` | `Needs Validation` | `Needs Validation` | Driven by local `player_game_logs` |
| Coverage | `Accepted Scope Limit` | `Accepted Scope Limit` | `Ready` | `In Progress` | Historical warehouse coverage is intentionally out of scope |
| Game Explorer | `Accepted Scope Limit` | `Accepted Scope Limit` | `Ready` | `In Progress` | Historical seasons use legacy PBP; only `2024-25` / `2025-26` are warehouse-backed targets |

## Explicit Sprint Exit Checks

- `2024-25` warehouse remains stable with no failed or stalled jobs
- `2025-26` parsed PBP and derived tables keep advancing from the kickoff baseline
- `2023-24` historical PBP retry no longer presents lineup uniqueness/idempotency failures
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
