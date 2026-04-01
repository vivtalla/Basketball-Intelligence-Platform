# Sprint 25 Closeout

**Sprint:** 25  
**Date:** 2026-04-01  
**Owner:** Codex  
**Status:** Final

---

## Shipped

- Added the first platform-intelligence layer: team-page decision tools, guided game follow-through, pace/style profiles, and in-season trend cards
- Added beta/foundation workflows for what-if scenarios, play-style x-ray, play-type scouting, and lineup/style compare follow-ons
- Extended `/pre-read`, `/compare`, `/insights`, and Game Explorer with preserved context and coaching-oriented drill-down paths
- Added new backend analytics/report services, routers, response models, and Sprint 25 QA coverage

## Deferred / Not Finished

- Play-type work remains heuristic and inferred, not a full native action taxonomy
- Scouting remains browser-print-first; no dedicated PDF pipeline shipped this sprint

## Coordination Lessons

- Contract-first kickoff kept shared-file conflicts low even with multiple specialist streams
- Additive service/model/router splits worked better than trying to widen existing feature files too early

## Workflow Lessons

- Selective bounded workers were useful for analytics, API, frontend, and QA slices, but final integration still needed to stay centralized
- DB-backed smokes were worth doing after compile/test/build because they caught real runtime readiness without needing a full manual QA pass

## Technical Lessons

- Turbopack production builds still require out-of-sandbox execution in this environment
- The current warehouse can support meaningful coach-facing intelligence now, but inferred play-type features must stay explicitly confidence-labeled

## Next Sprint Seeds

- Upgrade inferred action families into stronger opponent-aware scouting and clip-anchor workflows
- Improve what-if calibration, confidence framing, and comparable-pattern storytelling
- Add printable/shareable compare outputs and richer lineup-to-game follow-through
- Extend trend cards into lineup-level weekly cards where sample support is strong

## Backlog Refresh

- Removed shipped backlog items for Decision-Driven Coaching Tools, Guided Game Follow-Through, Pace and Style Profiles, and In-Season Trend Cards
- Rewrote What-If, Play-Style X-Ray, Play-Type Scouting, and Comparison follow-ons as deeper next-step opportunities
