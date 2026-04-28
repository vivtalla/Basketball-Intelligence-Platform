# Sprint 75 Closeout — Playoff Command Center & Series Intelligence

**Date:** 2026-04-28  
**Branch:** `codex-sprint-75-playoff-command-center`  
**Status:** Implemented, verified, merged to `master`, and pushed to `origin/master`

---

## Shipped

### Playoff series intelligence API

- Added `playoff_series_intelligence_v1` with `GET /api/playoffs/series/{series_id}/intelligence`.
- Response includes series pulse, data coverage, Four Factors and regular-season deltas, star burden, shot-diet pressure, lineup chess, tactical edges, adjustment signals, warnings, and `analysis_metadata`.
- Added methodology registry support for the new `playoffs` domain and documented the methodology in `specs/platform-methodology.md`.
- Kept the model deterministic and roster/stat based only. No migration, no live ingest, no salary/trade/betting model.

### Real series simulator overrides

- Extended the existing simulator to accept non-mutating hypothetical state via `override_top_wins` and `override_bottom_wins`.
- Updated `<SeriesWPSimulator>` so "wins next" buttons now re-simulate from the hypothetical state and expose a reset action.

### `/bracket` Playoff Command Center

- Replaced the static bracket-only page with a coach/analyst command surface.
- Added selected-series navigation, today's playoff strip, Series Pulse, Four Factors Edge, Tactical Edges, Adjustment Signals, Star Burden, Shot Diet Pressure, Lineup Chess, simulator, and methodology reliability card.
- Added mobile-first vertical layout while keeping sparse-data states honest and non-blocking.

---

## Verification

- Backend targeted: `backend/venv/bin/python -m pytest backend/tests/test_playoff_routes.py -q` → **6 passed**
- Backend full: `backend/venv/bin/python -m pytest backend/tests -q` → **293 passed**, 2 pre-existing FastAPI deprecation warnings
- Frontend lint: `npm run lint` → 0 errors, 7 pre-existing `usePlayerStats.ts` warnings
- Frontend build: `npm run build` → clean, `/bracket` generated
- Whitespace: `git diff --check` → clean

---

## Deferred

- True shared-possession lineup matchup deltas remain a future endpoint.
- PostseasonHeatmap still needs leaderboard-level `position`/bucket fields for G/F/C dot coloring.
- Series snapshots and live in-game websocket/polling are still out of scope.
- Playoff PBP-derived cron unification remains in backlog; Sprint 75 consumes whatever playoff lineup/on-off rows exist.

---

## Workflow Lessons

- The fastest safe path for a one-hour sprint was one composed intelligence API plus one product surface, not broad page-by-page polish.
- Reusing Sprint 74 `analysis_metadata` kept the new playoff methodology auditable without inventing a separate trust UI.
- Direct route-function tests remain effective for this FastAPI codebase and avoid extra TestClient dependency churn.
