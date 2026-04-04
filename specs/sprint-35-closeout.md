# Sprint 35 Closeout

**Sprint:** 35
**Date:** 2026-04-03
**Owner:** Codex
**Status:** Final

---

## Shipped

- Enriched persisted shot-chart payloads with `game_id` and `game_date`, plus optional `start_date` / `end_date` filtering on `GET /api/shotchart/{player_id}` and `GET /api/shotchart/{player_id}/zones`.
- Upgraded `ShotChart` into a true shot lab with shared season, season-type, preset date window, and custom date-range controls that drive scatter, heat, hex, value, sprawl, zone breakdown, and distance profile together.
- Added `CompareShotLab` on `/compare` with shared season / season-type / date-window controls plus synchronized side-by-side `ShotValueMap`, `ShotSprawlMap`, `ShotDistanceProfile`, filtered `ShotProfileDuel`, and filtered `ZoneProfilePanel`s.
- Upgraded `ShotSeasonEvolution` with a Regular Season / Playoffs toggle while keeping empty playoff seasons visible as filmstrip cards instead of collapsing the layout.
- Added backend coverage for enriched shot serialization, date-window filtering, filtered zone aggregation, and overwrite-safe refresh behavior; verified with full backend `pytest` plus frontend `npm run lint` and `npm run build`.

## Deferred / Not Finished

- Team-level shot-defense / conceded-shot maps stayed out of core sprint scope and remain a follow-on.
- Full historical live backfill did not complete during closeout; the new `backend/data/backfill_shot_lab.sh` helper was added, but the live `stats.nba.com` run hit repeated timeouts and remains an ops follow-up.
- Live manual QA across local player and compare pages still depends on the local app processes and enriched backfill data being available.
- Use `specs/sprint-35-shot-lab-runbook.md` as the monitored backfill and merge checklist for PR #11.

## Coordination Lessons

- Single-stream ownership worked well again for a tightly coupled backend+frontend shot sprint, but `AGENTS.md` still needs to be reset immediately after closeout so future sessions do not inherit stale branch claims.

## Workflow Lessons

- Locking the backend filter contract first made the frontend shot-lab wiring much cleaner than trying to compute date windows independently in multiple components.
- React lint pushed back on effect-driven state resets; resetting shot-lab controls from user-action handlers and deriving clamped ranges in `useMemo` was the better pattern.

## Technical Lessons

- Extending the existing JSON shot payload was enough to unlock temporal shot workflows without adding a new relational shot-event table this sprint.
- Shared scaling hooks matter for compare visuals: value-map bubbles and distance ribbons needed synchronized maxima to make side-by-side reads trustworthy.
- Historical shot-chart backfills against `stats.nba.com` are still operationally fragile; the product path is ready, but bulk refreshes need timeout-aware reruns rather than assuming a single clean pass.

## Next Sprint Seeds

- Team-level shot-defense sprawl/value views using conceded opponent shots by team and season.
- Self-service shot-chart refresh action from missing/stale UI states instead of a passive synced-at badge only.
- Deeper shot context enrichment (`period`, `clock`, and stronger action-type overlays) for situational shot studies.
- Shareable / printable shot-lab snapshots so filtered compare and player views can be passed around intact.

## Backlog Refresh

- Removed the shipped Sprint 34 shot-chart follow-ons (date-range filter, compare shot lab, playoff evolution) from `specs/BACKLOG.md`.
- Added new follow-ons focused on team-defense shot maps, self-service refresh, richer shot context, and reusable shot-lab outputs.
