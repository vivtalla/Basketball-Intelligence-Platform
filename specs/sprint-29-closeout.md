# Sprint 29 Closeout

**Sprint:** 29
**Date:** 2026-04-02
**Owner:** Claude + Codex
**Status:** Final

---

## Shipped

- Standings history foundation in `team_standings`: added `snapshot_date`, updated uniqueness to `(team_id, season, snapshot_date)`, and preserved daily snapshots instead of one mutable row per team-season
- `GET /api/standings/history?season=...&days=...` plus `StandingsHistoryResponse` model for last-N-days team win-percentage series
- Standings page trend-line UX: `WinPctSparkline` plus standings-table integration on `/standings`
- Player zone analytics from persisted shot charts: `GET /api/shotchart/{player_id}/zones`, zone-profile panel on player pages, and compare-page zone profile support
- Zone panel aggregation fix: combined all `zone_area` slices into full `zone_basic` summaries so paint, mid-range, corner 3, and above-the-break 3 cards reflect true totals
- Shot-chart reads are now DB-first: `GET /api/shotchart/{player_id}` no longer fetches `stats.nba.com` during user requests
- Shot-chart responses now expose `data_status` (`ready`, `stale`, `missing`) and `last_synced_at` so the UI can distinguish synced, stale, and unsynced states
- Queue-first shot-chart ingestion in the warehouse job system: `sync_season_shot_charts` fan-out jobs and `sync_player_shot_chart` worker jobs, with `source_runs` logging on player fetches
- Current-season ops automation now enqueues shot-chart refresh work from `backend/data/daily_sync.sh`

## Deferred / Not Finished

- Broader DB-first product reads are still incomplete: player profile bootstrap, career stats, and some game-log flows still retain request-time `nba_api` fallbacks outside the shot-chart path
- Shot-chart baseline coverage is in progress rather than complete; the queue and worker path are in place, but full current/historical season coverage still depends on backfill throughput and upstream reliability
- The compare page remains client-driven, so a curl-only smoke check confirms route load but not fully hydrated browser behavior without an interactive session

## Verification

- `python -m compileall backend`
- `npm run lint -- src/components/ShotChart.tsx src/components/ZoneProfilePanel.tsx src/hooks/usePlayerStats.ts src/lib/api.ts src/lib/types.ts`
- `npm run build`
- `bash -n backend/data/daily_sync.sh`
- Backend import smoke check for edited warehouse + shot-chart modules
- Local backend API smoke checks:
  - `GET /api/standings?season=2024-25`
  - `GET /api/standings/history?season=2024-25&days=30`
  - `GET /api/shotchart/1627759?season=2024-25&season_type=Regular%20Season`
  - `GET /api/shotchart/1627759/zones?season=2024-25&season_type=Regular%20Season`
- Local frontend route smoke checks:
  - `/standings`
  - `/players/1627759`
  - `/compare?playerA=1627759&playerB=1631096`

## Known Gaps / Risks

- `backend/venv` does not currently have `pytest` installed, so the new backend test file was added but not executed in this workspace
- Shot-chart backfill can still hit `stats.nba.com` timeouts; queue retry behavior handles this, but full coverage depends on workers continuing to drain successfully
- The standings history endpoint is working against locally materialized snapshots, but current dev data only shows a shallow two-day series until more daily snapshots accumulate

## Coordination Lessons

- The Sprint 29 feature branch was already in good shape; the main follow-up work was operational hardening and closeout, not a second round of product exploration
- Queue-backed ingestion made it much easier to recover from partial state than route-time fallback logic would have

## Workflow Lessons

- Local smoke checks in this workspace may need elevated access even for `localhost` and Postgres; when a command that should work locally fails with permissions, re-run it with explicit escalation instead of assuming the app is down
- Long-running loop workers can outlive the session and interfere with a newer code path. Process inventory before diagnosing queue behavior is worth doing early

## Technical Lessons

- Persisted shot charts in Postgres are already sufficient for the current scatter, heatmap, and zone-profile surfaces; the immediate platform win was changing read semantics and ingestion scheduling, not adding a new storage system
- Queue fan-out plus per-player jobs is the right shape for shot charts, but stale retry timestamps and orphaned workers can create misleading "unknown job type" failures after code changes if old processes are still alive

## Next Sprint Seeds

- Remove remaining request-time `nba_api` fallbacks from player profile, career, and game-log reads so the site is consistently DB-first
- Add warehouse/readiness visibility for shot-chart coverage so analysts can tell whether a player is truly missing data or just waiting on ingestion
- Decide whether shot-chart storage should expand to richer shot context (`game_id`, game date, period/clock, assisted flags, defender context) before new shot-quality products depend on it
