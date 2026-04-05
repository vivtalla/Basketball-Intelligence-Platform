# Sprint 36 Closeout

**Sprint:** 36
**Date:** 2026-04-04
**Owner:** Codex
**Status:** Final

---

## Shipped

- Rebuilt the shot-lab presentation layer into a shared editorial-luxe system across player, compare, and evolution surfaces, including new shot-lab surface primitives, upgraded legends, stronger chrome, and harmonized spacing/motion treatment.
- Turned `ShotSprawlMap` into the hero surface with layered organic density fields, softened footprint treatment, richer story stats, and compare-friendly framing instead of the prior chunky grid/convex-hull look.
- Restyled `ShotValueMap`, `ShotDistanceProfile`, `CompareShotLab`, `ShotProfileDuel`, `ZoneProfilePanel`, and `ShotSeasonEvolution` so the shot lab reads as one premium visual suite while preserving Sprint 35 shared filters and data behavior.
- Reworked the player `Heat` view into a true shot-frequency heatmap with brighter hotspot cores, smoother density treatment, and a more neutral page-compatible atmosphere.
- Added a shared `ShotCourt` component so the main shot views and evolution mini-courts share one consistent court drawing foundation rather than drifting visual geometry.
- Verified the sprint with frontend `npm run lint` and `npm run build`, plus local route smoke checks on `/players/[playerId]` and `/compare`.

## Deferred / Not Finished

- The shared court silhouette is improved, but the exact half-court shape and three-point-line read still do not fully match the intended visual reference and should get a dedicated polish pass next sprint.
- The Sprint 36 closeout does not include a full interactive browser QA sweep with final designer approval across desktop and mobile breakpoints.
- No backend/API work was needed or shipped in this sprint.

## Coordination Lessons

- Single-stream ownership remained the right fit for this sprint because the changes were tightly coupled across multiple chart surfaces and benefited from one consistent visual hand.

## Workflow Lessons

- Building a shared presentation layer first made the follow-on chart restyles much cleaner than styling each visualization independently.
- Visual iteration moved faster once the local app stayed running and the user could review live surfaces instead of relying on static summaries.

## Technical Lessons

- Shared court geometry should live in one component; otherwise small per-chart SVG differences accumulate and make the shot suite feel inconsistent.
- Frequency heatmaps need separate hotspot-core treatment in addition to broader glow if the densest shooting pockets are supposed to read immediately on neutral page backgrounds.
- Premium compare visuals depend as much on framing and legend hierarchy as on the chart marks themselves.

## Next Sprint Seeds

- Finish the shared `ShotCourt` silhouette so the three-point shell, baseline, lane, and free-throw geometry read unmistakably as a real half-court.
- Continue tuning the shot-frequency heatmap for sharper hotspot contrast without making the full surface too dark for the homepage-adjacent design language.
- Explore lightweight legend and annotation overlays that explain what sprawl/value/distance views are saying without crowding the charts.
- Carry the shot-lab visual system into any remaining stats-first surfaces that still feel visually older than the new player/compare suite.

## Backlog Refresh

- Added a new shot-lab visual follow-on focused on final court geometry polish, heatmap calibration, and analytical annotations.
- Removed no backend/product-contract items because Sprint 36 was a pure frontend visual sprint.
