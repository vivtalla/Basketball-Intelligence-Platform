# Sprint 28 Closeout

**Sprint:** 28
**Date:** 2026-04-01
**Owner:** Claude
**Status:** Final

---

## Shipped

- `GET /api/compare/player-availability?player_a={id}&player_b={id}` — returns current injury status for both compare players in one call; null slot = healthy/no data
- `InjuryStatusBadge` component — compact pill (Out/Questionable/Probable) with colour-coded status variants
- `useCompareAvailability` SWR hook — fires only when both player slots are filled, players mode only
- `ComparisonView` now shows injury badge under each player name and a yellow warning banner when either player is injured
- `POST /api/injuries/unresolved/{id}/resolve` — matches an unresolved row to a player, upserts `PlayerInjury`, deletes the unresolved row
- `DELETE /api/injuries/unresolved/{id}` — dismisses stale unresolved rows
- `/admin/injuries/unresolved` page — table with Resolve (player-search modal + confirm) and Dismiss actions; SWR revalidates on each action
- Fixed pre-existing lint error in `pre-read/page.tsx`: replaced `setState`-in-`useEffect` with `useSearchParams`-initialized state + `Suspense` wrapper

## Deferred / Not Finished

- Standings history / trend line — requires `snapshot_date` column + unique constraint change + materialization rewrite; deferred to Sprint 29
- Shot zone analytics — data shape is ready but opens a new product lane; deferred to Sprint 29
- Pre-read deck PDF/share export — backlog item, no Sprint 27 or 28 grounding

## Coordination Lessons

- Single-stream shape worked cleanly; no file lock contention, no merge-order issues
- Pre-existing lint error was caught during verification — confirms that running lint before committing is load-bearing

## Workflow Lessons

- Stashing to confirm pre-existing vs. introduced lint errors is worth the extra step
- `fetchApi` already accepted `RequestInit` — checking existing API primitives before adding new ones saved a refactor

## Technical Lessons

- `useSearchParams` initialization pattern (instead of `setState`-in-`useEffect`) is the correct Next.js approach for URL-param-initialized state; should be the default going forward
- The injury availability query uses two DB hits per player (latest `report_date` + player row); acceptable at compare page load but would need a single-query rewrite if used on a high-traffic list surface

## Next Sprint Seeds

- Standings trend line: add `snapshot_date` column + change unique constraint on `team_standings`, update `materialize_standings()` to append daily rows, render last-30-days win-pct curve on standings page
- Shot zone analytics: aggregate `zone_basic` / `zone_area` from `PlayerShotChart.shots` JSON, add player zone summary panel and side-by-side compare view
- Alias backfill for two-way and recently traded players to reduce future unresolved injury rows
- Pre-read deck export: PDF-friendly print layout or share link for the briefing deck
