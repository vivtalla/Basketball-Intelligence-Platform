# Sprint 37 Closeout

**Sprint:** 37
**Date:** 2026-04-05
**Owner:** Codex
**Status:** Final

---

## Shipped

- Widened persisted shot-chart payloads with contextual fields for situational analysis and future 3D/play reconstruction: `period`, `clock`, `minutes_remaining`, `seconds_remaining`, `shot_value`, and `shot_event_id`.
- Extended `GET /api/shotchart/{player_id}` and `GET /api/shotchart/{player_id}/zones` with shared situational filters for `period_bucket`, `result`, and `shot_value`, on top of the existing date-window filtering.
- Added `POST /api/shotchart/{player_id}/refresh`, backed by the existing warehouse shot-chart queue path, so player and compare shot surfaces can self-queue refresh work instead of stopping at passive missing/stale states.
- Upgraded the player and compare shot labs so the new situational filters drive every existing shot surface together: scatter, heat, hex, value, sprawl, zone breakdown, distance profile, compare duel, and compare zone panels.
- Added a new player `ShotContextPanel` with top raw `action_type` summaries plus recent filtered shots that deep-link into Game Explorer.
- Updated Game Explorer so shot-lab deep links can prefill `period`, `event_type`, and `query` from URL state.

## Deferred / Not Finished

- The Game Explorer bridge is intentionally filter-based in v1; it does not yet promise exact shot-to-event replay matching.
- The 3D foundation shipped as data and UX groundwork only; no actual 3D rendering surface landed in this sprint.
- Live QA was completed through local route and API smoke checks, but not through a full interactive browser walkthrough with click-by-click confirmation of every filter combination.

## Coordination Lessons

- Single-stream ownership was still the right choice because the sprint cut across persisted backend contracts, shared SWR keys, and multiple shot-lab surfaces that all needed to move together.

## Workflow Lessons

- Locking the backend shot filter contract first again paid off; once the router and tests were correct, player and compare UI wiring stayed straightforward.
- Treating refresh as a queued product action, not a special-case frontend hack, kept the DB-first model intact while still improving usability.

## Technical Lessons

- Richer shot context can stay in the existing JSON payload for now; it unlocked meaningful situational analysis without forcing a new relational shot-event schema.
- Shared SWR key builders matter once refresh polling and multiple filter dimensions exist; centralizing those keys avoided drift between player and compare surfaces.
- The most useful 3D preparation work is not graphics first; it is reliable shot context plus a credible bridge into play-by-play exploration.

## Next Sprint Seeds

- Finish the 3D leap by introducing a real rendering stack and a narrow first 3D court/shot surface on top of Sprint 37’s richer payload.
- Improve the Game Explorer bridge from filter-based context to stronger shot-to-event matching where `shot_event_id`, `period`, `clock`, and descriptions are sufficient.
- Add shareable or printable shot-lab snapshots that preserve season, date window, and situational filters together.
- Extend the shot-lab model to team-defense / conceded-shot surfaces once the player and compare workflows have stabilized.

## Backlog Refresh

- Removed the shipped self-service shot refresh and richer situational shot-context items from the shot-lab backlog.
- Updated the 3D shot-chart backlog item so it now refers to building on the new Sprint 37 shot-context and Game Explorer foundation rather than starting from scratch.
