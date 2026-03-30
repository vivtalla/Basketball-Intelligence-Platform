# Sprint 13 Closeout

**Sprint:** 13
**Date:** 2026-03-30
**Owner:** Codex (Claude token-limited this sprint)
**Status:** Final

---

## Shipped

**Codex — Warehouse reliability + ops visibility (`codex-sprint-13-warehouse-reliability` → PR #10):**

- **Shared request throttle** (`ApiRequestState` ORM model + `api_request_state` table): DB-backed distributed rate limiter using `SELECT FOR UPDATE` row-level lock, serializes NBA API calls across all worker processes — no more rate-limit collisions under parallel workers
- **Worker loop mode** (`warehouse_jobs.py --loop`): workers poll for work indefinitely with configurable `--idle-sleep` and `--summary-every` flags instead of exiting when queue empties
- **`warehouse_worker_pool.sh`**: start/stop/restart/status commands, PID file management, per-worker log files in `logs/warehouse/`, environment-variable configuration for worker count, season, log dirs
- **`POST /api/warehouse/reset-stale`**: re-queues all jobs with expired leases (stalled running jobs), with optional `?season=` scope
- **`GET /api/warehouse/jobs/summary`**: full queue snapshot — status counts, per-type breakdown, stalled jobs, recent failures, global throttle state
- **Frontend auto-poll** in `WarehousePipelinePanel`: polls every 15s while any jobs are active; new ops snapshot section on coverage page showing queue/stalled/failed counts and throttle status
- **YoY trend callouts**: `PlayerHeader` shows season-over-season stat deltas (PPG, TS%, AST, REB); `TeamIntelligencePanel` shows net rating, scoring, and assist-rate trends
- **Game Explorer event drill-down**: click any PBP event row for score context at that moment, formatted clock, player profile link
- **Coverage page memo stabilization**: prevented render loop from unstable `useMemo` inputs

## Deferred / Not Finished

**Claude Sprint 13 plan (not started — session token limit):**
- Auto-poll via SWR `refreshInterval` function on `useWarehouseSeasonHealth` (Codex shipped a more complete version via `useEffect` + `setInterval` with toggle)
- Expandable event rows in Game Explorer (Codex shipped this)
- Both Claude tasks were superseded by Codex's broader implementation

**Still open:**
- `feature/sprint-10-yoy-trends` Claude branch — YoY player stat trends in StatTable are already on master (shipped earlier); branch can be closed
- SIGTERM handler in `warehouse_jobs.py` — `finally: db.close()` doesn't run on SIGTERM; low practical risk but clean fix is to add `signal.signal(SIGTERM, lambda *_: sys.exit(0))`
- `reset_stale_jobs()` has no grace-period buffer — jobs with tight leases could be reclaimed mid-execution
- Coverage page memo deps (`[data?.teams]`) still unstable across SWR refetches (performance only, not correctness)
- Pipeline metrics endpoint (job latency/throughput) — deferred from Sprint 12, still not built

## Coordination Lessons

- When Claude hits a session token limit mid-sprint, Codex can pick up the full scope — the sprint plan in `specs/sprint-13-plan.md` (or the plan file) gives enough context. Happened smoothly this sprint.
- Cross-agent review caught three mediums before merge. All were already survivable since workers were running on the updated code path. Review remains valuable even when risk is low.
- Codex shipped broader scope than planned (full ops visibility, YoY callouts across player + team) — good use of extra capacity.

## Technical Lessons

- DB-backed distributed throttle (`SELECT FOR UPDATE`) is the right pattern for coordinating multiple Python worker processes — avoids per-process rate-limit collisions without a Redis/queue dependency.
- Worker loop + PID files + shell pool script is the simplest operational model that works — no daemon framework, no distributed queue, easy to debug with `kill` and log tailing.
- SWR `refreshInterval` as a function (receives latest data, returns ms) eliminates chicken-and-egg polling problems. Codex used `useEffect` + `setInterval` instead — both work; SWR function form is cleaner for next time.

## Next Sprint Seeds

- Fix SIGTERM handler in `warehouse_jobs.py` (one line: `signal.signal(SIGTERM, lambda *_: sys.exit(0))`)
- Fix coverage memo deps: `[data?.teams]` → `[data]`
- Pipeline metrics: `started_at`/`completed_at` on `IngestionJob` → avg latency + daily throughput in `/jobs/summary`
- Game summary API: `GET /api/games/{game_id}/summary` querying `GameTeamStat` + `GamePlayerStat` for team box scores + per-team leaders (Claude's Sprint 13 plan, still relevant)
- Close `feature/sprint-10-yoy-trends` branch (work already on master)
