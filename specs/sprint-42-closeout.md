# Sprint 42 Closeout

**Sprint:** 42
**Date:** 2026-04-06
**Owner:** Codex
**Status:** Final

---

## Shipped

- Upgraded the team prep workflow so prep cards now carry opponent-aware `best edge`, `first adjustment`, and `urgency` rationale instead of only broad matchup summaries.
- Extended focus levers with richer coaching metadata, including projected impact framing, coaching prompts, and opponent-specific context, so prep, pre-read, and decision tools can tell the same story.
- Rebuilt the team `decision` tab into a backend-driven opponent-aware workspace by wiring it directly to lineup-impact, matchup-flags, play-type pressure, and follow-through reports.
- Preserved workflow continuity from prep queue into pre-read, compare, and Game Explorer through additive URL/state context instead of introducing a new persistence layer.
- Added lightweight pre-read integration so the deck now reflects the same first-adjustment and urgency logic shown on the team page.

## Deferred / Not Finished

- Sprint 42 did not broaden into saved prep artifacts or a snapshot/archival redesign; snapshots remain compatible, but archival is still not the hero workflow.
- The sprint kept replay continuity lightweight and URL/state-first rather than building a new artifact or film-session model.
- Lineup-impact reads can still be heavier than other local APIs on large datasets, so deeper performance tuning remains a future follow-on rather than part of this sprint.
- Compare was improved only insofar as it supports prep and decision continuity; broader compare storytelling and export work remains future scope.

## Coordination Lessons

- Reusing the existing decision and replay contracts kept this sprint much smaller than inventing a new prep-specific orchestration layer.
- Wiring the team page to existing backend reports unlocked more value than trying to grow a richer decision experience out of frontend-only heuristics.

## Workflow Lessons

- Prep cards become materially more useful once they answer both “why now?” and “what is the first action?” instead of only routing users into another page.
- Opponent selection needs to survive every handoff cleanly or the staff workflow immediately feels fragile; URL/state continuity was worth the extra contract work.

## Technical Lessons

- The frontend decision-report types had drifted from the backend models; realigning those contracts was necessary before the decision tab could become the primary workflow surface.
- Extending `TeamPrepQueueItem` and `TeamFocusLever` with additive rationale fields was enough to upgrade prep, pre-read, and decision surfaces together without route churn.
- Shared evidence and source-context types should stay explicit because scouting and decision surfaces reuse similar concepts with slightly different payload shapes.

## Next Sprint Seeds

- Deepen prep-to-replay continuity so the strongest prep levers can launch directly into more focused event-backed game review when evidence is strong enough.
- Continue calibrating lineup-impact wording, confidence framing, and local performance so the decision tab feels faster and more trustworthy on deeper datasets.
- Explore whether compare should surface the prep-selected lever more explicitly instead of only preserving it through URL/state continuity.

## Verification

- `backend/venv/bin/pytest backend/tests/test_sprint25_decision_surfaces.py backend/tests/test_sprint32_team_prep_core.py backend/tests/test_sprint33_coaching_system.py`
- `backend/venv/bin/pytest`
- `frontend: npm run build`
- Local smoke checks:
  - `GET /api/teams/ATL/prep-queue?season=2025-26&days=7`
  - `GET /teams/ATL?tab=decision&season=2025-26&opponent=BOS`

## Backlog Refresh

- Rewrote `Team Prep Queue Follow-Ons`, `Decision-Tool Calibration and Opponent Context`, and `Focus Levers Follow-Ons` so they describe narrower post-Sprint-42 follow-ons instead of the core workflow that is now shipped.
- Kept broader replay expansion, compare follow-through, and prep snapshot/archive work visible, but explicitly out of Sprint 42 scope.
