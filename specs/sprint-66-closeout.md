# Sprint 66 Closeout

**Sprint:** 66 — Staff Packet and Coaching Handoff
**Date:** 2026-04-23
**Owner:** Codex (single-stream sprint)
**Status:** Final

---

## Shipped

- Upgraded `pre_read_snapshots` from anonymous frozen decks into named staff packets with Alembic revision `0010_pre_read_packet_metadata`, adding persisted `title` and `note` fields while preserving frozen saved payloads.
- Extended Pre-Read snapshot contracts with packet metadata and packet-summary shape across backend Pydantic models and frontend TypeScript types, plus a new `PreReadPacketSelection` contract for pinned scouting claims and clip anchors.
- Rebuilt snapshot orchestration in `pre_read_snapshot_service.py`: packet-aware create/list/get/update flows, frozen scouting-claim capture from the scouting report, matchup/team-history summary filtering, and markdown export generated from the saved snapshot rather than live data.
- Added `PATCH /api/pre-read/snapshots/{snapshot_id}` for inline title/note edits and `GET /api/pre-read/snapshots/{snapshot_id}/markdown` for packet export.
- Reworked `/pre-read` into a staff-packet surface with packet library tabs (`This Matchup`, `Team History`), row-level `Open` / `Copy share link` / `Export markdown` actions, visible frozen-packet metadata, and packet-aware save flows.
- Added scouting-to-packet follow-through inside `ScoutingReportView`: analysts can pin up to 3 claims, each carrying the existing confidence pill plus up to 2 ranked clip anchors into the saved packet.
- Extended the Pre-Read deck contract and UI with a dedicated scouting-packet section so reopened packets keep selected claims, confidence reasons, and clip launch links alongside the prep story.
- Updated Prep Queue save behavior so packet saves return real snapshot objects with editable title/note metadata instead of anonymous recent-snapshot chips.
- Added Sprint 66 backend coverage for migration/schema expectations, packet create/list/get/update behavior, frozen scouting continuity, and markdown export ordering/content.

**Test deltas:** 3 new Sprint 66 backend tests in `test_sprint66_staff_packet.py`, plus a test-harness fix in `test_sprint33_coaching_system.py` so cache-backed coaching tests initialize correctly under the in-memory DB path. Full backend suite at 196 passing. Frontend `npm run build` passed. `npm run lint` passed with 7 pre-existing unused-type warnings in `frontend/src/hooks/usePlayerStats.ts`.

## Deferred / Not Finished

- Browser print remains the physical handout path; there is still no richer compare/trend/staff-bundle export beyond the packet markdown export added this sprint.
- Packet history is matchup/team oriented, but there is still no season-scale search/filter/sort management layer for heavy archive use.
- Prep Queue and Pre-Read save flows are packet-aware, but Compare/Game Explorer do not yet reopen directly into packet-specific frozen context beyond existing return links.

## Coordination Lessons

- The `AGENTS.md` kickoff rules were worth following literally here: branch/worktree setup and shared-file claims up front kept a schema-contract sprint from drifting into avoidable coordination risk.
- The manual smoke walkthrough mattered. Tests and builds passed before the walkthrough, but the live dev database had not been migrated, and only the browser/API smoke pass exposed that operational gap.

## Workflow Lessons

- For workflow-heavy sprints, snapshot-based exports are safer when generated from the frozen saved packet instead of rebuilt live views. That kept reopen/export behavior aligned even if underlying scouting or prep signals change later.
- When frontend and backend contracts both grow in one sprint, append-only discipline on shared TS files (`frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`) reduced merge risk without slowing the work down.

## Technical Lessons

- Pre-Read packet persistence needed two layers of data: editable metadata (`title`, `note`) and immutable frozen packet payload. Treating those separately kept reopening and export behavior stable while still allowing staff-facing cleanup edits after save.
- The live migration miss was a reminder that backend test coverage is not enough for packet flows that depend on local Postgres. Schema-changing sprints should include one post-migration API smoke before declaring the workflow done.
- Scouting continuity worked best when the snapshot stored the selected claim ids, clip-anchor ids, and the resolved frozen claim payload together. Recomputing selections from ids alone would have reintroduced drift and confidence-order mismatches later.

## Next Sprint Seeds

1. **Packet archive management** — add search/sort/filter affordances, richer team-history slicing, and possibly packet grouping by opponent or series.
2. **Packet-aware compare/trend exports** — let a saved packet pull in selected compare or trend artifacts without becoming a separate document-generator system.
3. **Broader trust calibration parity** — bring scouting-style confidence framing to Pre-Read focus levers, scenario cards, and decision-tool recommendations so coaching trust labels feel consistent across surfaces.
4. **Packet template presets** — explore reusable packet skeletons for recurring staff workflows once archive volume is high enough to justify it.

## Backlog Refresh

- Remove Prep/Pre-Read snapshot naming, library/history, and basic reopen/share flows from the backlog; Sprint 66 shipped the first full packet-management version.
- Rewrite the scouting follow-through backlog item away from "claim to Pre-Read jump" and toward broader packet curation/export follow-ons, since claim pinning into Pre-Read now exists.
- Rewrite the old Pre-Read deck follow-on away from basic snapshot library work and toward broader packet-aware follow-through and archive tooling.
