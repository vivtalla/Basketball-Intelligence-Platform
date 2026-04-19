# Sprint 57 Closeout

**Sprint:** 57
**Date:** 2026-04-19
**Owner:** Claude (single-stream)
**Status:** Final

---

## Shipped

- Extended `TrajectoryPlayerRow` with `player_id`, `position`, `position_percentile` (0–100 via normal CDF), `driver_contributions` (all signals sorted by abs weighted contribution), `evidence_games` (top 3 recent-window games), `clutch_context`, `on_off_context`, `recent_averages`, `baseline_averages`
- New `build_trajectory_series()` endpoint (`GET /api/insights/trajectory/{player_id}/series`) returning per-game time-series for rolling sparklines
- New `lineup_context_service.py` + `GET /api/insights/lineup-context/{player_id}` — top 5 teammates by shared possessions (≥100 poss gate), possession-weighted net rating, on/off from `PlayerOnOff`, LIKE false-positive guard
- Redesigned `TrajectoryTracker` into a two-column workspace: ranked list with inline `DriverBar` left, detail panel right with `RollingSparklines`, `DriverBar` full decomp, `ClutchSplitCard`, `OnOffSwingCard`, `ShotQualityDeltaCard`, and `EvidenceGames` chips linking to Game Explorer
- New `InsightsHeader` component shared by all four insights tabs; cross-tab handoff chips on all tabs
- Factored `insights/page.tsx` to use `InsightsHeader` with URL-backed team/season/opponent state
- Added collapsible lineup context block to `PlayerPbpInsights` (Team Impact & Clutch panel)
- Added lineup context collapsible to `MvpRacePanel` Team Impact section
- 8 new lineup-context tests + 7 new trajectory-service tests; all 17 pass

## Deferred / Not Finished

- Trajectory compare toggle (pin up to 3 players side-by-side, URL-shareable) — deprioritized to keep scope tight
- Shot-quality delta uses TS% proxy (recent vs baseline) — full `shot_quality_v1` per-window compute deferred; low-sample card already shows "insufficient coverage" hint
- UsageEfficiencyDashboard, TrendCardsPanel, WhatIfPanel polish (empty-state copy, skeleton shapes) — header sharing shipped, panel interior polish remains

## Coordination Lessons

- Single-stream sprint avoided all lock-table friction. For tightly coupled full-stack sprints, single-stream is faster than two parallel agents.

## Technical Lessons

- LIKE queries on `lineup_key` (e.g., `"%{player_id}%"`) generate false positives when a player ID is a substring of another (e.g., "12" matches "123"). Always parse IDs from the key and verify membership before accumulating stats.
- Normal CDF via `math.erf` gives accurate 0–100 percentiles without scipy; keep this pattern for future bucket-level ranking.
- SWR hook pre-allocation is required at component top level regardless of whether the player is selected — pass `null` as the key to suppress the fetch when not needed.

## Next Sprint Seeds

- **Usage vs Efficiency revamp** — richer role/shot-profile redistribution suggestions, team-specific calibration, clearer formula communication, connect usage flags into player trend and compare workflows (Vivek explicitly called this out)
- **Trajectory compare toggle** — pin up to 3 players side-by-side in the Trajectory detail panel, URL-shareable via `compare=ids`
- **Shot-quality delta (full)** — integrate `shot_quality_v1` per-window compute into trajectory evidence when coverage is above trust threshold
- **Trend Cards lineup-level cards** — add lineup-level weekly cards where sample support is strong
- **Usage/Efficiency → Trend Cards handoff** — connect usage flags into player trend and compare workflows directly from the Usage panel

## Backlog Refresh

- "Usage vs Efficiency Follow-Ons" in BACKLOG.md — still open; revamp is the top seed for Sprint 58
- "MVP Award-Race Follow-Ons" lineup-with/without item — partially shipped (lineup context now renders in Team Impact); dated on/off history and ballot simulation remain deferred
- Trajectory compare toggle added as a next-sprint seed above; not yet in BACKLOG.md
