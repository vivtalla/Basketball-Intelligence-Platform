# Sprint 31 Closeout

**Sprint:** 31
**Date:** 2026-04-03
**Owner:** Claude
**Status:** Final

---

## Shipped

- Hexbin shot chart mode: flat-top hexagonal binning (no library), hex size ∝ shot frequency, color = efficiency delta vs league avg; added "Hex" toggle to existing scatter/heatmap toggle group
- `ZoneAnnotationCourt.tsx`: half-court SVG with FG%, efficiency delta, and volume printed directly on each zone; wired into both `ShotChart` (below court) and `ZoneProfilePanel` (replacing tile grid)
- `PerformanceCalendar.tsx`: GitHub-contribution-graph style game-by-game heatmap with 5-tier quantile color scale, metric toggle (PTS/REB/AST/FG%/+/-), native hover tooltips; wired into `PlayerDashboard` between CareerArcChart and GameLogTable
- Chart harmonization: `CareerArcChart` swapped to `AreaChart` with per-stat gradient fills and warm platform palette; `DualCareerArcChart` uses forest green / gold instead of blue / amber; `RadarChart` uses radial gradient fill; all Recharts grids/axes now use CSS variables
- Homepage hero: full-viewport height with CSS basketball court art (arcs, paint, 3pt line), staggered `fade-up` entrance animations (0–400ms delay), `StatCounter` animated count-up, platform card glow on hover
- `StandingsBumpChart.tsx`: conference rank-over-time Recharts `LineChart`, Y-axis inverted (rank 1 at top), hover-to-dim other teams, team color legend; expanded view added below both conference tables on standings page
- Extracted `heatColor()` and `ZONE_PATHS` to shared `shotchart-constants.ts` — no more duplication between `ShotChart` and new components
- `StatCounter.tsx` client component — `requestAnimationFrame` ease-out cubic count-up, no library dependency

## Deferred / Not Finished

- Codex had no Sprint 31 branch — single-stream sprint, all work owned by Claude
- `HomeLeagueLeaders` trend arrows were described in the plan but kept minimal (rank-position only) since delta data is not on `LeaderboardEntry`; richer trend arrows would require API change
- Radar pulse-ring animation (pulsing outer polygon) was scoped in plan but deferred — Recharts `PolarGrid` polygon is not addressable without DOM hacks; the radial gradient fill is the primary upgrade

## Coordination Lessons

- Single-stream sprint (frontend only, no Codex branch) was clean — no lock table friction, no merge-order concerns
- Plan-mode exploration with 2 parallel subagents gave a thorough codebase read before writing a line of code; the design agent's type-level audit (e.g., `ts_pct` not on `GameLogEntry`, `StandingsHistoryEntry` lacks rank field) saved rework

## Workflow Lessons

- For purely frontend sprints with no backend changes, single-stream with one Claude agent is faster and lower coordination overhead than a two-track split
- Extracting shared primitives (Step 0 as a blocker) before writing new components is the right sequencing pattern — prevented two components defining `heatColor` independently
- TypeScript build gate caught a Recharts `label` prop type mismatch on `StandingsBumpChart` that would have been a runtime error; run `npm run build` before marking any frontend sprint complete

## Technical Lessons

- Recharts `Line label` prop typing (`ImplicitLabelListType`) is very restrictive in v3; custom labels on last data point require a `<Customized>` component or a separate SVG overlay, not an inline render function — use the color legend pattern instead
- Recharts `AreaChart` + `Area` with gradient `fill` works cleanly in v3.8; just need to declare `<defs>` as a direct child before other chart children
- CSS `@keyframes` + `animation-delay` via inline `style` is enough for staggered entrance animations; no Framer Motion needed for this use case
- `backdropFilter` on SVG `<rect>` has inconsistent browser support; using high `fillOpacity` achieves the frosted-glass appearance without relying on it

## Next Sprint Seeds

- **Richer trend arrows on HomeLeagueLeaders**: add a `delta` or `rank_change` field to `LeaderboardEntry` backend response to enable meaningful directional arrows
- **Shot chart date-range filter**: add a date-range selector to `ShotChart` so analysts can isolate hot/cold streaks — the raw `game_date` field is available on `ShotChartShot` if enriched
- **PerformanceCalendar in CompareView**: wire `PerformanceCalendar` side-by-side for both players in `ComparisonView` so game-by-game rhythm can be compared directly
- **ZoneAnnotationCourt in compare**: `ShotProfileDuel` currently renders fingerprints only; replace or augment with `ZoneAnnotationCourt` side-by-side for richer visual compare
- **Animation polish pass**: fade-up on platform area cards (stagger each card), skeleton loaders that match final layout shape more precisely, `PerformanceCalendar` fade-in on data load
