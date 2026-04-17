# Sprint 47 Closeout

**Sprint:** 47
**Date:** 2026-04-17
**Owner:** Claude
**Status:** Final

---

## Shipped

- Added `TeamSplitRow` and `TeamSplitsResponse` TypeScript interfaces to `frontend/src/lib/types.ts`
- Added `getTeamSplits()` API client to `frontend/src/lib/api.ts`
- Added `useTeamSplits()` SWR hook to `frontend/src/hooks/usePlayerStats.ts`
- Added `TeamSplitsPanel` component: family toggle (Location, Win/Loss, Days Rest, Month, Pre/Post All-Star), stat table with W%, PTS, AST, REB, FG%, +/-, loading skeleton, and honest empty state for unsynced teams
- Added "Splits" tab to `/teams/[abbr]` page between Analytics and Lineups; hook pre-allocated and gated when tab is inactive
- Added situational split signals to `TeamPrepQueuePanel`: per-card Home/Away W%, W-L record, and +/- using splits data already fetched at page level — no additional API calls
- Verified: `npm run lint` clean, `npm run build` clean (TypeScript + all 16 routes)

## Deferred / Not Finished

- Team splits not yet surfaced in `ComparisonView` or team compare — planned as additive follow-on
- Team shooting split dashboards remain a high-value follow-on (persisting `TeamDashboardByShootingDashboard` shot-area/type/distance families)

## Coordination Lessons

- Single-stream, Claude-only sprint ran smoothly with no file lock contention
- No Codex branch for Sprint 47; parallel team model not needed for a frontend-only pass

## Workflow Lessons

- Frontend-only sprints against already-persisted backend data are fast and low-risk — good template for future polish/wiring sprints
- Pre-allocating SWR hooks at page top level (gated by tab) continues to be the right pattern; the team page is now at 12 pre-allocated hooks and remains readable

## Technical Lessons

- The `split_family` values from the backend are human-readable strings ("Location", "Win/Loss", etc.) — `FAMILY_LABELS` map in `TeamSplitsPanel` should stay in sync with any new families added to the sync pipeline
- `w_pct` comes from the DB as a decimal (0.0–1.0), not a percentage — always multiply by 100 at display time
- The `is_home` flag on prep queue items is the right signal for selecting which location split to surface per card

## Next Sprint Seeds

- Wire team general splits into `ComparisonView`: side-by-side Home/Away + W/L breakdown for two teams
- Persist `TeamDashboardByShootingDashboard` families (shot area, type, distance) following the Sprint 45 pattern — this is the top "Now" backlog item
- Add a "Splits" entry to the team compare sidebar or opponent-context panel once the compare surface is ready for it
- Expand `TeamSplitsPanel` with days-rest and month trend context (e.g., best rest advantage, current month performance)

## Backlog Refresh

- Remove "Team General Splits UI" from the deferred list — it shipped
- Keep "Team Shooting Split Dashboards" as the top "Now" data-platform item
- Add "Team splits in ComparisonView" as a follow-on seed under the Comparison Sandbox section
