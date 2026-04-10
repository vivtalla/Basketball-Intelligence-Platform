# Sprint 44 Closeout

## Summary

Sprint 44 established a cleaner canonical official-data foundation for current-season player and team dashboards, then turned that foundation into a meaningfully stronger `Player Stats` workspace instead of leaving the new data behind a basic table.

The sprint shipped in two phases:
- the April 6, 2026 official-data canonicalization and player-stats overhaul
- the April 9-10, 2026 follow-up polish and leaderboard correctness pass

## Shipped Work

### Official Data Canonicalization

- Added persisted `team_season_stats` plus Alembic migration `0003_team_season_stats.py` so team analytics can read canonical official team dashboard rows instead of rebuilding from player season aggregates
- Added `sync_official_season_stats()` and `sync_official_team_season_stats()` in `backend/services/sync_service.py`
- Updated `backend/data/daily_sync.sh` so current-season player and team official dashboards refresh as part of the standard daily sync path
- Added `specs/official-data-source-matrix.md` as the canonical registry for official NBA domains, ownership, persistence shape, and remaining gaps

### Team / Leaderboard Backend Follow-Through

- Expanded `LeaderboardEntry` to include `metric_values` covering the full sortable stat library so the frontend can render broader metric groups without extra round-trips
- Fixed leaderboard percentage behavior so `fg_pct`, `fg3_pct`, `ft_pct`, `efg_pct`, and `ts_pct` are derived from raw makes/attempts when stored percent columns are `NULL`
- Hardened warehouse season materialization to ignore future-dated game rows during aggregate rebuilds
- Switched team analytics reads onto the persisted official team-season table

### Player Stats Workspace Overhaul

- Reworked `frontend/src/app/player-stats/page.tsx` around metric groups, broader table coverage, and stronger workspace framing
- Added quick metric switching, mode-specific summary cards, and top-row spotlight cards so each board opens with immediate context
- Added user-facing table controls for compact density and pinned key columns
- Preserved workspace state in the URL for mode, stat, season context, filters, filter-panel state, density, pinned columns, and mode-specific thresholds
- Improved mobile scan-ability by surfacing team and games played inline on player rows
- Replaced flat empty states with board-specific guidance for players, career, on/off, and lineup modes

## Verification

- `backend/tests/test_leaderboards.py`
- `backend/tests/test_official_season_sync.py`
- `backend/tests/test_official_team_stats.py`
- `backend/tests/test_team_dashboard_parsing.py`
- `backend/tests/test_warehouse_materialization.py`
- `frontend`: `npm run lint`
- `frontend`: `npm run build`

## Deferred / Follow-Ons

- Persisted shareable presets or named saved views for the `Player Stats` workspace, beyond URL-only carryover
- Additional official-data domains called out in `specs/official-data-source-matrix.md`, especially player splits, team splits, and play-type dashboards
- Any deeper table virtualization or freeze-column refinement if the stats workspace grows beyond the current metric-group/table shape

## Workflow Notes

- The sprint’s implementation landed on `master` rather than a dedicated sprint branch, so Sprint 45 should return to the stated branch/worktree discipline in `AGENTS.md`
- The frontend build intermittently hit stale `.next` cleanup races during repeated local verification; wiping `.next` before rebuild remained a reliable local workaround

## Next Sprint Seeds

- Push the official-data foundation into the next missing high-value domain: player splits, team splits, or play type
- Consider adding saved `Player Stats` presets or staff-friendly share labels on top of the new URL-backed state model
- Continue polishing the workspace toward a true analyst cockpit rather than a leaderboard-first screen
