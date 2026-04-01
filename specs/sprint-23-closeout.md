# Sprint 23 Closeout

**Sprint:** 23  
**Date:** 2026-03-31  
**Owner:** Codex  
**Status:** Final

---

## Shipped

- Added team-vs-team `Comparison Sandbox` mode on `/compare`
- Added `Focus Levers` backend + team-page panel driven by four-factor heuristics
- Added `Usage vs Efficiency` coach workflow on `/insights`
- Added printable `/pre-read` game-day briefing deck
- Post-closeout hotfix bundle:
  - fixed local dev CORS defaults for `localhost` and `127.0.0.1` on ports `3000` and `3001`
  - improved player compare so profile reads do not redundantly trigger heavy sync-on-read work
  - repaired incomplete player full names in the local database and normalized future syncs
  - fixed duplicate traded-player rows in Usage vs Efficiency
  - standardized selected tab/pill styles for better contrast and readability

## Deferred / Not Finished

- No play-type EV or matchup-exploit taxonomy work shipped this sprint
- Pre-read is printable HTML only; no PDF/export pipeline yet

## Coordination Lessons

- Four parallel feature tracks worked best when shared files stayed integration-owned and append-only
- Starting from a clean Sprint 23 worktree avoided the stale Sprint 12 branch contamination risk

## Workflow Lessons

- Selective bounded workers were useful, but the main rollout still needed to own final integration and validation
- DB-backed smoke checks were essential for tuning coach-facing heuristics, especially usage/efficiency thresholds

## Technical Lessons

- Turbopack production builds still need out-of-sandbox execution in this environment
- Team decision-support features can ship quickly when they reuse `GameTeamStat` instead of waiting for a richer play-type taxonomy

## Next Sprint Seeds

- Add lineup-to-lineup mode and printable export to the Comparison Sandbox
- Evolve Focus Levers into opponent-aware matchup emphasis instead of team-only heuristics
- Add richer redistribution logic and confidence framing to Usage vs Efficiency
- Extend Pre-Read into share/export workflows and optional PDF generation

## Backlog Refresh

- Removed shipped backlog items for Comparison Sandbox, Four-Factor Decision Engine, Usage vs Efficiency Dashboard, and Game-Day Pre-Read Deck
- Rewrote them as follow-on opportunities around matchup intelligence, export workflows, and deeper coaching recommendations
