# Sprint 58 Closeout

**Sprint:** 58
**Date:** 2026-04-19
**Owner:** Claude
**Status:** Final

---

## Shipped

- New `opportunity_service.py`: multi-axis Opportunity Score via 5 capped z-scores (±2.0) per position bucket (G/F/C) — `efficiency_load_gap` (0.30), `team_impact_swing` (0.25), `lineup_synergy_lift` (0.20), `role_fit_gap` (0.15), `cohort_percentile` (0.10)
- Bulk lineup synergy: single `LineupStats` query for the full season, partitioned in Python — no per-player DB roundtrips
- High/medium/low confidence bands derived from minutes, PBP on/off sample size, and lineup possessions
- Directional hints (team impact + efficiency gate, ≥ medium confidence) with structured `hint_basis` signal list
- `GET /api/insights/opportunity` — season, team, min_minutes, position params; methodology block in response
- Old `/api/insights/usage-efficiency` deprecated (`deprecated=True`) but kept live
- 13 new backend tests covering bucketing, z-score capping, confidence bands, hint triggers, possession gate, and team rollup
- Full `UsageEfficiencyDashboard.tsx` rewrite: two-column Opportunity Workspace with team/position/signal filters
- 8 new `opportunity/` components: `OpportunityDriverBar`, `OpportunityRow`, `EfficiencyLoadCard`, `TeamImpactCard`, `RoleFitCard`, `CohortPositionCard`, `DirectionalHintBanner`, `MethodologyDrawer`, `TeamRollup`
- `SIGNAL_DESCRIPTIONS` dict with hover tooltips (`title` attribute + `cursor-help` + dotted underline) across all driver labels, filter chips, and methodology rows
- `UsageLoadBoard.tsx` deleted (retired)
- Append-only additions to `types.ts`, `api.ts`, `usePlayerStats.ts`

## Deferred / Not Finished

- `/api/insights/usage-efficiency` hard deletion (scheduled Sprint 59+)
- "Compare" chip handing off to `/compare` with top-3 positional peers (from plan; deprioritized as out of scope)
- Cross-tab handoff chip in `InsightsHeader` for the Opportunity ↔ Trajectory link (partially done via inline links in detail panel; full `InsightsHeader` integration deferred)

## Coordination Lessons

- Solo sprint (no Codex branch) — no merge-order friction this sprint.
- Plan was unusually tight with Sprint 57 reuse (DriverBar, `useLineupContext`, position buckets) — having prior sprint primitives listed explicitly in the plan saved significant design time.

## Workflow Lessons

- React Compiler auto-memoization: removing `useMemo` entirely and using plain computed variables resolved the lint error cleanly. Rule to carry forward: **never wrap React Compiler-managed dependencies in `useMemo`**.
- Hoisting synergy cohort stats outside the per-player loop was a non-obvious O(n²) fix — worth a dedicated verification pass on any service with nested signal computations.

## Technical Lessons

- React Compiler (`eslint-plugin-react-compiler`) rejects `useMemo` when its inferred deps diverge from source deps. Symptom: "Compilation Skipped: Existing memoization could not be preserved." Fix: delete `useMemo`, let the compiler handle it.
- `_bulk_lineup_synergy()` pattern (fetch all rows once, partition in Python) is the right template for any signal that would otherwise fire N queries per player list.
- `cohort_percentile` z-score via `math.erf` produces valid 0–100 percentile bounds; confirmed by test suite.

## Next Sprint Seeds

1. **Hard-delete `/api/insights/usage-efficiency`** and its service after confirming no callers remain — run `grep -r usage-efficiency` across frontend and any external clients.
2. **Opportunity ↔ Trajectory cross-tab chip** in `InsightsHeader`: when a player is pinned in Opportunity, show "See Trajectory →" in the shared header (not just inside the detail panel).
3. **Compare chip**: from the Opportunity detail panel, hand off to `/compare` with the pinned player + top-2 positional peers pre-loaded.
4. **Opportunity score persistence / caching**: the service recomputes on every request. Consider a short-lived in-memory or Redis cache keyed by `(season, team, min_minutes, position)` — especially for the all-teams, all-positions query.
5. **Team roll-up tile click → pin**: clicking a roll-up driver tile should pin the first qualifying player into the detail panel (currently tiles are informational only).

## Backlog Refresh

- Remove "Opportunity Workspace" from backlog — shipped.
- Add: "Hard-delete deprecated usage-efficiency endpoint (Sprint 59)" as high priority.
- Add: "Opportunity ↔ Trajectory cross-tab chip via InsightsHeader" as medium priority.
- Add: "Opportunity score caching layer" as low priority.
