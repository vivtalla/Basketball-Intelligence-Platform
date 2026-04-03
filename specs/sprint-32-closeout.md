# Sprint 32 Closeout

**Sprint:** 32
**Date:** 2026-04-03
**Owner:** Codex
**Status:** Final

---

## Shipped

- Canonicalized `GET /api/teams/{abbr}/intelligence` for modern seasons onto warehouse-backed `games`, `play_by_play_events`, and latest `team_standings`
- Added stable team-intelligence readiness metadata: `data_status`, `canonical_source`, and `last_synced_at`
- Added `GET /api/teams/{abbr}/prep-queue?season=...&days=...` as a DB-first team-prep workflow built from schedule, standings, injuries, compare, and focus-lever context
- Added the team-page `prep` tab plus `TeamPrepQueuePanel` with urgency framing, edge/adjustment summaries, scouting-mode launch, and copyable pre-read share links
- Added Sprint 32 backend coverage for warehouse team intelligence + prep queue, then ran full backend `pytest`, frontend `npm run lint`, and frontend `npm run build`

## Deferred / Not Finished

- No saved prep snapshots or archival layer yet; share links still point to live query-state URLs
- Team prep urgency is heuristic and directional, not yet opponent-model-calibrated

## Coordination Lessons

- Single-stream backend + frontend delivery was clean for this sprint because the new feature sat mostly in one route family and one team page
- Closing the sprint with full-repo verification before docs/push made the closeout much safer than relying on targeted tests alone

## Workflow Lessons

- For data-foundation sprints, pairing one canonical backend migration with one visible workflow is the right balance; the sprint feels product-meaningful instead of purely infrastructural
- Additive response metadata (`data_status`, `canonical_source`, timestamps) continues to be the safest way to evolve DB-first surfaces without misleading the UI

## Technical Lessons

- `team_standings` is good enough to drive team-page rank/context today, but playoff rank still has to be recomputed from the latest conference snapshot because it is not materialized directly
- Prep urgency and first-action summaries are best treated as bounded heuristics until the opponent-aware decision layer gets a more explicit calibration pass

## Next Sprint Seeds

- Saved prep snapshots by matchup/date so staff can archive and share a frozen pre-read state
- Opponent-aware focus levers and prep urgency calibration tied more directly to matchup profile and rest disadvantage
- Remaining DB-first cleanup in secondary advanced/trend routes that still lean on request-time sync helpers
- Compare-side visual follow-ons from Sprint 31: `PerformanceCalendar` and `ZoneAnnotationCourt`

## Backlog Refresh

- Added prep-queue follow-ons around saved snapshots and stronger calibration
- Kept the remaining DB-first cleanup item because Sprint 32 focused on team-prep-adjacent canonicalization, not every remaining secondary route
