# Sprint 40 Closeout

**Sprint:** 40
**Date:** 2026-04-05
**Owner:** Codex
**Status:** Final

---

## Shipped

- Turned Game Explorer into an event-centered replay workflow by adding focused event targets, highlighted action numbers, short surrounding sequences, and source-aware replay context on top of the existing game-visualization contract.
- Expanded the 3D visualizer from a single-step scaffold into a sequence-aware analytical replay surface with lead-in, focus, and follow-through navigation while keeping exact, derived, and timeline linkage explicitly labeled.
- Preserved replay context across shot-lab and scouting handoffs with additive URL/state parameters such as source label, claim id, clip anchor id, linkage quality, focus event id, and focused action number.
- Upgraded scouting clip anchors from narrative-only deep links into event-backed replay candidates with richer event metadata, anchor-quality labeling, and export-ready claim context.
- Kept the sprint additive and backward compatible: no route removals, no new persistence layer, and no new shot-event table.

## Deferred / Not Finished

- Sprint 40 did not attempt native video playback or any external film integration; the workflow remains video-adjacent and browser-first.
- Prep snapshots, What-If / Style X-Ray follow-ons, broader compare expansion, and larger backfill / DB-first cleanup work all remain out of scope for this sprint.
- Some scouting anchors still degrade to honest timeline context when event evidence is thin; the sprint improved trust and follow-through rather than forcing full event resolution for every claim.
- Existing Pydantic v2 deprecation warnings remain in the repo and were not addressed as part of this workflow sprint.

## Coordination Lessons

- Treating replay focus as a shared contract across shot lab, scouting, and Game Explorer avoided one-off deep-link behavior and made the frontend flow easier to reason about.
- The URL/state-first approach continues to be the right fit for CourtVue Labs when expanding workflows across surfaces without introducing a persistence migration.

## Workflow Lessons

- A visible workflow sprint lands best when the same trust model appears in every handoff; exact, derived, and timeline labeling mattered as much as the new replay controls themselves.
- Event-centered replay and clip export fit naturally together because they share the same question: “what exact possession or surrounding sequence should a coach inspect next?”

## Technical Lessons

- Focused replay is safer when it resolves through stable event identifiers first, then falls back to action-number and filtered context only when necessary.
- Sequence-aware 3D playback does not need a radically different rendering system; it can grow from the existing procedural court and step metadata if the event-focus contract is explicit.
- Scouting-anchor quality improves materially when claim scoring considers evidence labels and action-family hints instead of only free-text matching.

## Next Sprint Seeds

- Decide whether the new event-centered replay workflow should extend into trend cards, What-If drilldowns, and prep queue follow-through links.
- Deepen the 3D scene choreography beyond the current focused sequence now that Game Explorer can reliably center on a target event.
- Consider whether scouting clip exports should stay URL-first or evolve into saved analyst artifacts once staff workflows demand archival sharing.
- Continue the remaining completeness/backfill program so event-centered replay can assume broader historical coverage with less manual refresh work.

## Verification

- `backend/venv/bin/pytest`
- `backend/venv/bin/pytest backend/tests/test_shotchart_db_first.py backend/tests/test_sprint33_coaching_system.py`
- `frontend: npm run build`

## Backlog Refresh

- Removed the core Sprint 40 hero work from the backlog as a primary “Now” item: event-centered Game Explorer replay, sequence-focused 3D follow-through, and the first event-backed scouting clip workflow are now shipped.
- Kept follow-on opportunities visible where Sprint 40 clearly opened a next layer rather than exhausting the space, especially around broader workflow adoption, deeper 3D choreography, and saved artifacts versus URL-only state.
