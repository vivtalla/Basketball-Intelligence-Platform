# Sprint 12 Closeout

**Sprint:** 12
**Date:** 2026-03-30
**Owner:** Shared (Claude + Codex)
**Status:** Final

---

## Shipped

**Codex — Warehouse ops hardening (`codex-sprint-12-warehouse-ops` → merged to master):**
- Season-scoped `/run-next` endpoint: `season: Optional[str] = Query(None)` param passed to `run_next_job(db, season=season)`
- Retry/backoff in `run_next_job()`: re-queues with `run_after = now + timedelta(minutes=5 * attempt_count)` on failure; permanently marks FAILED at attempt_count ≥ 3
- `retry_failed_jobs(db, season)` service function: resets all permanently failed jobs for a season to queued (resets attempt_count)
- `POST /api/warehouse/retry-failed?season=` endpoint
- `backend/data/daily_sync.sh` cron wrapper; crontab entry documented in CLAUDE.md

**Codex — Game Explorer rebuild (`codex-sprint-12-game-explorer` → merged to master):**
- `frontend/src/app/games/[gameId]/page.tsx` rebuilt fresh from master (not from unsafe Sprint 10 branch)
- Dual-write to legacy `play_by_play` + idempotent `PlayerGameLog` upsert during warehouse migration window
- Idempotent warehouse sync fix (`a7d992d`)

**Claude — Frontend hardening (`feature/sprint-12-warehouse-frontend` → PR #9 → merged to master):**
- Season-scoped Run Next Job: `runNextWarehouseJob(season?)` passes `?season=` to backend; button label updated
- Retry Failed button: calls `retryFailedJobs(season)` → `POST /api/warehouse/retry-failed?season=`; shown only when `health.failed_jobs > 0`
- Failed Jobs collapsible panel: shows job_type, job_key, last_error, attempt_count for up to 10 jobs
- Sync Today hidden for historical seasons (derived from season end year vs calendar year)
- Code review fix: `getWarehouseJobs()` accepts `season` param — server-side filtering, not client-side slice of 50 global rows
- Code review fix: `handleAction` invalidates `pbp-dashboard-{season}` and `pbp-dashboard-seasons` keys so coverage cards refresh after warehouse actions

## Deferred / Not Finished

- Nothing critical deferred — all planned Sprint 12 scope shipped.
- Year-over-year trend indicators (Sprint 10 Claude branch) remains unmerged.

## Coordination Lessons

- Two-agent cross-review caught two medium issues in PR #9 before merge (season-scoped jobs fetch, stale SWR invalidation). Process continues to pay off.
- Codex completing extra scope (Game Explorer rebuild) while Claude was at session limit is a good pattern — unblocked work shouldn't wait. The rebuild-from-master approach for the unsafe Sprint 10 branch was the right call.
- Closing PR #8 (Sprint 11 frontend, superseded) cleanly before merging PR #9 keeps the PR history readable.

## Technical Lessons

- SWR invalidation must cover all keys that display data affected by an action, not just the keys directly mutated. The `pbp-dashboard-*` miss was a natural oversight — worth checking at review time.
- The `warehouse-jobs-failed` SWR key pattern needed the season included (`warehouse-jobs-failed-${season}`) once the API became season-scoped. Cache key and API param must stay in sync.

## Next Sprint Seeds

- Year-over-year trend indicators on player profiles (Sprint 10 Claude branch deferred; rebuild or rebase from master)
- Warehouse dashboard: auto-poll while `running_jobs > 0` (refresh every 10s without user action)
- Game Explorer: per-game PBP event viewer / play log drill-down
- Pipeline metrics: track and display avg job latency, throughput per day
- `daily_sync.sh` health check: alert (log or badge) if no jobs completed in last 24h
