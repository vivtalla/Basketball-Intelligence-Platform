# Sprint 34 Closeout

**Sprint:** 34
**Date:** 2026-04-03
**Owner:** Claude
**Status:** Final

---

## Shipped

- `ShotValueMap`: zone bubbles where area ∝ shot frequency and fill color ∝ value added (FG% delta × zone points). First Goldsberry-style view that combines volume and efficiency into a single "value" signal. New "Value" mode in the ShotChart toggle.
- `ShotSprawlMap`: topographic shot density map using a 25×24 grid with 5×5 Gaussian kernel smoothing, rendered as 4-tier density contours. Convex hull traces the player's court footprint with a sq-ft coverage stat. New "Sprawl" mode in the ShotChart toggle.
- `ShotDistanceProfile`: continuous 0–30 ft distance-frequency ribbon. SVG area curve height = shot frequency; per-2ft segment fill colored by efficiency delta vs expected. Recharts sparkline overlaid for precise FG% on hover with landmark lines at 4, 14, 22, 23.75 ft. Lives below the zone breakdown table in ShotChart.
- `ShotSeasonEvolution`: career filmstrip of mini zone-heatmap courts, one per season. 10 pre-allocated SWR hook slots (no conditional hooks). Recharts AreaChart timeline of FG% and 3P% below. Wired into PlayerDashboard between ShotChart and ZoneProfilePanel.
- `ZONE_CENTROIDS` exported from `shotchart-constants.ts` (was previously private in ZoneAnnotationCourt); ZoneAnnotationCourt updated to import from shared constant.
- ShotChart toggle extended from 3 modes (scatter/heat/hex) to 5 (scatter/heat/hex/value/sprawl).
- lint: ✓ clean · TypeScript: ✓ clean · build: ✓ clean

## Deferred / Not Finished

- Nothing deferred. All four planned features shipped to master.

## Coordination Lessons

- Single-stream sprint (Claude only) with no Codex involvement kept coordination overhead near zero. This is the right shape for pure frontend visualization work where all components live in the same few files.

## Workflow Lessons

- Writing all four new components before touching the wiring files (ShotChart.tsx, PlayerDashboard.tsx) worked cleanly — each component is self-contained and the wiring was one focused pass at the end.
- The `hidden` CSS wrapper approach for the value/sprawl modes (hiding the existing scatter/heat/hex court SVG rather than conditionally mounting it) avoids React unmount/remount on toggle which would reset scroll position.

## Technical Lessons

- SVG `clipPath` + rectangle fills is a clean way to achieve per-segment color variation on an area curve without D3 — apply geometry-colored rects, then clip to the area path shape.
- The 5×5 Gaussian convolution for the sprawl map is fast enough synchronously in `useMemo` for ≤1000 shots; beyond that the subsample path in convexHull keeps it bounded.
- Pre-allocated SWR hook slots for `ShotSeasonEvolution` (10 slots, unconditional) are the correct pattern per CLAUDE.md. ESLint does not flag these as rules-of-hooks violations when inside a named custom hook function.
- `ZONE_CENTROIDS` was duplicated between `ZoneAnnotationCourt.tsx` and the new components; extracting it to `shotchart-constants.ts` was the right call and required minimal changes.

## Next Sprint Seeds

- **Shot chart date-range filter**: per-shot `game_date` field exists in the data; a date slider on ShotChart would let users isolate hot/cold streaks or pre/post-trade splits.
- **ShotValueMap in ComparisonView**: put two players' value maps side by side on the compare page — direct visual contrast of where each player creates or destroys value.
- **ShotSeasonEvolution for Playoffs**: the filmstrip currently shows Regular Season only; a toggle to switch to Playoff data would be a natural follow-on.
- **Sprawl map for team-level shot defense**: aggregate opponent shot locations against a team to show which court areas a defense concedes — same components, different data query.
- **Shot chart synced-at refresh button**: the "data not synced" state currently shows a banner; a one-click sync trigger would complete the self-service workflow.

## Backlog Refresh

- Removed "Visualization Follow-Ons (Sprint 31 seeds)" shot chart items (value map, zone profile improvements) from BACKLOG.md — these shipped this sprint.
- Added shot chart follow-on seeds (date-range filter, compare integration, playoff toggle) to BACKLOG.md under Now.
