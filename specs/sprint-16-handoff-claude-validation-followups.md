# Sprint 16 Handoff: Claude Validation Follow-ups

**From:** Codex  
**To:** Claude  
**Status:** Ready  
**Date:** 2026-03-30

## Summary

Sprint 16 validation has started. The current backend/data baseline is strong enough to begin the frontend validation and empty-state cleanup lane immediately.

This handoff captures the first concrete UI issues found during the kickoff sweep so the validation branch can start with decision-complete fixes instead of rediscovery.

## Current data baseline

- `2024-25` is warehouse-complete:
  - `1230` box complete
  - `1230` parsed PBP
  - `1230` materialized
- `2025-26` is still the active warehouse catch-up season:
  - `1119` box complete
  - `501` parsed PBP
  - `1119` materialized
  - `1563 complete`, `4 running`, `1792 queued` jobs
- Historical launch-window seasons are legacy-plus-derived, not historical warehouse targets:
  - `2022-23`: `40931` game logs / `554` on-off / `17094` lineups
  - `2023-24`: `43394` game logs / `595` on-off / `16190` lineups

## Required validation stance

- External metrics are fully out of scope for Sprint 16.
- `2022-23` and `2023-24` should be treated as launch-usable on native + derived data.
- `2024-25` and `2025-26` are the only warehouse-backed target seasons for coverage/Game Explorer completeness.
- Empty states should no longer imply “run import first” when the real issue is either:
  - active `2025-26` warehouse catch-up, or
  - accepted historical warehouse scope limits

## Concrete UI issues to fix first

### 1. Leaderboards still use old import-first messaging

File:
- `frontend/src/app/leaderboards/page.tsx`

Current issues:
- Career mode empty state says: `Run bulk import for multiple seasons first.`
- On/off empty state says: `Run play-by-play import for this season.`
- Lineups empty state says: `Run play-by-play import for this season.`
- Footer note still says: `On/Off requires play-by-play import ...`

Required change:
- Replace those with Sprint 16-accurate wording:
  - no direct import instructions
  - generic “no data available for this selection yet” where appropriate
  - on/off and lineup copy should refer to local play-by-play-derived coverage, not imports
- Treat launch-window seasons as expected-to-work paths, not user-operated import workflows

### 2. Historical team intelligence guidance is too warehouse-centric

Files:
- `frontend/src/components/TeamIntelligencePanel.tsx`
- `frontend/src/app/teams/[abbr]/page.tsx`

Current issue:
- partial/none coverage guidance still tells users to finish season sync from the coverage board
- that is appropriate for `2024-25` / `2025-26`, but misleading for `2022-23` / `2023-24`

Required change:
- make the guidance season-aware
- for `2024-25` / `2025-26`:
  - keep the warehouse-sync guidance
- for `2022-23` / `2023-24`:
  - explain that historical seasons rely on legacy-plus-derived support
  - avoid implying the coverage board is the required next step unless validation proves a real blocker

### 3. Validation matrix ownership

File:
- `specs/sprint-16-validation-matrix.md`

Required use:
- update this file as you validate the launch-window surfaces
- convert `Needs Validation` / `In Progress` cells into:
  - `Ready`
  - `Accepted Scope Limit`
  - `Product Bug`

## Recommended validation order

1. Leaderboards
2. Team page / team intelligence
3. Player page / PBP insights
4. Compare
5. Insights
6. Standings
7. Coverage
8. Game Explorer

## Acceptance bar for your branch

- no misleading import-first instructions remain on launch-window pages
- historical seasons no longer get pushed toward warehouse completion as if they were required warehouse targets
- any remaining non-ready page state is explicitly classified in `specs/sprint-16-validation-matrix.md`
