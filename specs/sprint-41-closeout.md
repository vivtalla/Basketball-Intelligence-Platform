# Sprint 41 Closeout

**Sprint:** 41
**Date:** 2026-04-05
**Owner:** Codex
**Status:** Final

---

## Shipped

- Extended the event-centered replay workflow into the main intelligence workspace by making `Trend Cards` and `What-If` emit additive replay targets with source-aware launch context, focused event metadata when available, and honest `derived` versus `timeline` labeling.
- Switched the insights `Trend Cards` surface onto the backend cards API so the product now uses one shared source of truth for card semantics, supporting stats, drilldowns, and replay follow-through.
- Added bounded replay evidence to `What-If` responses and carried that same decision thread into compare via additive replay query-state, so compare can preserve and reopen the attached Game Explorer evidence.
- Expanded Game Explorer source context with additive `source_surface` metadata so insight-launched sessions explain why the user landed on a sequence rather than only showing a generic deep-link banner.
- Kept the sprint additive and URL/state-first: no new persistence tables, no saved replay artifacts, and no route removals or renames.

## Deferred / Not Finished

- Sprint 41 did not extend replay adoption into prep queue, focus levers, or broader team decision surfaces; those remain logical next-wave candidates.
- The sprint kept compare continuity lightweight and did not attempt a broader compare storytelling or export overhaul.
- Trend cards still remain team-level evidence cards; lineup-level trend cards and richer export/print packaging remain future work.
- The sprint did not broaden into prep-snapshot archival or a new replay artifact model.

## Coordination Lessons

- Reusing the existing Game Explorer replay contract kept this sprint much smaller than introducing a new insight-specific deep-link format.
- Converting the trend cards UI to the backend cards API paid off immediately by centralizing evidence selection and replay metadata instead of duplicating trend logic in the frontend.

## Workflow Lessons

- Insights become materially more useful when every recommendation has a credible “show me the sequence” next step; replay follow-through matters as much as the summary card itself.
- Keeping weaker insight evidence explicitly labeled as timeline-only preserved trust better than stretching every card into a fake exact replay target.

## Technical Lessons

- A small additive `source_surface` field is enough to make shared replay banners feel intentional across multiple product surfaces.
- Replay-target helpers should only elevate to event-backed context when they have meaningful selectors; otherwise they should stay timeline-only instead of picking an arbitrary event.
- Backend tests on the new replay metadata were valuable because they also surfaced an older trend-card rotation-report keyword mismatch that had gone unnoticed.

## Next Sprint Seeds

- Extend replay adoption into prep queue, focus levers, and other decision-support surfaces now that insights use the shared replay contract successfully.
- Deepen What-If and trend-card calibration so the evidence links feel even more opponent-aware and analytically specific.
- Decide whether compare should grow beyond lightweight replay continuity into richer story-specific replay callouts or export behavior.

## Verification

- `backend/venv/bin/pytest backend/tests/test_sprint33_coaching_system.py backend/tests/test_shotchart_db_first.py`
- `backend/venv/bin/pytest`
- `frontend: npm run build`

## Backlog Refresh

- Removed `Replay Adoption Across Workflows` as a top `Next` item because the first insights-focused adoption pass is now shipped.
- Rewrote `Replay Workflow Expansion`, `Counterfactual What-If Suggestions`, and `Trend Cards Follow-Ons` as narrower follow-on opportunities instead of leaving Sprint 41’s shipped work described as future scope.
