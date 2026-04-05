# Sprint 39 Closeout

**Sprint:** 39
**Date:** 2026-04-05
**Owner:** Codex
**Status:** Final

---

## Shipped

- Canonicalized the persisted shot payload around the fields current shot-lab, team-defense, Game Explorer, and 3D consumers actually need, then routed both queue-backed and legacy bulk shot writes through one shared enrichment and validation path.
- Tightened shot completeness semantics so `legacy` now means missing canonical context, `partial` means canonical context exists but linkage is incomplete or non-exact, `ready` means the payload and linkage contract are fully present, and `missing` still means no persisted row exists.
- Hardened shot-to-event follow-through by giving exact `shot_event_id` matches strict precedence, refusing to promote ambiguous fallback matches, and carrying exact/derived/timeline linkage quality through shot-lab and Game Explorer responses.
- Normalized What-If scenario identifiers across old and current names, improved confidence and bounded-language framing, and added stronger launch context between What-If, Style X-Ray, compare, and pre-read workflows.
- Improved Comparison Sandbox and scouting follow-through with source-aware compare URLs, browser-print-friendly compare entry points, stronger scouting clip-anchor matching, and more explicit handoff context in Game Explorer.
- Refreshed `specs/BACKLOG.md` to split `Now` into shot/data-platform versus product-intelligence tracks and added a standalone `MVP Tracking` section with a future MVP award-race tracker entry that remains out of Sprint 39 scope.

## Deferred / Not Finished

- Sprint 39 did not include the deeper 3D possession-choreography expansion; the sprint improved linkage truthfulness and handoff quality, not the full next layer of 3D playback.
- MVP tracking was added to the backlog only; no award-race implementation work shipped in this sprint.
- Full repo-wide backend verification and local route/API smoke checks were not rerun as part of this closeout pass; verification stayed targeted to the changed sprint surfaces.
- Existing Pydantic v2 deprecation warnings (`.dict()` / `.json()`) remain in the repo and are a cleanup follow-on rather than Sprint 39 blocking work.

## Coordination Lessons

- Treating shot enrichment as a shared contract first made the follow-on product work much easier to land; once the payload rules were explicit, What-If, compare, and scouting handoffs could stay additive.
- URL/state-first follow-through continues to be the safest way to deepen workflows in this codebase; preserving source context through compare and scouting was lower-risk than introducing a new persistence layer.

## Workflow Lessons

- A narrowly targeted verification pass was enough to safely land this sprint because the contract changes were concentrated in a few backend/frontend seams, but the sprint would still benefit from a broader post-closeout sweep.
- Tightening trust signals matters as much as adding capability: explicitly surfacing exact versus derived versus timeline context made the existing workflows feel more honest without adding major UI complexity.

## Technical Lessons

- Shot payload completeness should be defined by consumer needs, not by whatever upstream fields happen to be available today; shared validation is more durable than repeating ad hoc enrichment in multiple pipelines.
- Ambiguous timing-based shot linkage should stay unlinked rather than being promoted to “exact enough.” That preserves analytical trust better than squeezing out a few extra matched rows.
- Scenario-id drift between backend and frontend can accumulate quietly; a normalization layer with compatibility aliases is a cheap way to keep coaching workflows stable while the product language evolves.

## Next Sprint Seeds

- Extend the canonical shot/event contract into fuller replay and sequence-focused Game Explorer behavior now that exact versus derived linkage is explicit.
- Decide whether the stronger compare/scouting source-context workflow should remain URL-only or graduate into saved compare/snapshot artifacts.
- Pay down the lingering Pydantic v2 deprecation warnings so future closeout verification stays quieter and easier to read.
- Revisit the broader shot/backfill ops program now that canonical payload validation is stricter and more explicit.

## Verification

- `backend/venv/bin/pytest backend/tests/test_shotchart_db_first.py backend/tests/test_sprint33_coaching_system.py backend/tests/test_sprint25_decision_surfaces.py`
- `frontend: npm run build`

## Backlog Refresh

- Split the backlog’s current work into `Now — Shot/Data Platform` and `Now — Product Intelligence` so sprint selection reflects the repo’s real workstreams more clearly.
- Added a new standalone `MVP Tracking` section with an unscheduled future `MVP Award-Race Tracker` entry.
- Kept the shot-data completeness, shot-lab precision, compare, and scouting follow-ons visible because Sprint 39 strengthened their foundation rather than exhausting the full opportunity space.
