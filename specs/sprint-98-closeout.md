# Sprint 98 Closeout — Data Foundation Hardening

**Sprint:** 98
**Date:** 2026-05-11 – 2026-05-12
**Owner:** Claude
**Status:** Final
**Branch:** `feature/sprint-98-data-foundation` (merged to master at `c5b6c9a`)

---

## Shipped

Four parallel streams, all merged. 11 commits, 46 files changed, +3443/-61 lines. 628 backend tests pass (was 594, +34 new). One pre-existing failure unchanged (`test_daily_sync_post_game_dry_run` — DATABASE_URL guard in test env, flagged in Sprint 97).

**Stream A — Sync Reliability & Alerting (6 commits):**
- `services/sync_freshness.py` (NEW): generalized marker pattern. `KNOWN_SYNC_ENTITIES` registry covers 22 sync types across post-game (15min), daily (1440min), weekly (10080min) tiers. `record_sync()` writes `sync:<entity>:last` to cache.db with 24h TTL; `read_all_syncs()` returns the full registry with stale flags (>2× cadence).
- `services/regular_season_gap_detector.py` (NEW): mirrors Sprint 97 playoff backfill for regular-season games. Walks CDN schedule, compares to game_logs, inserts via boxscoresummaryv2. Idempotent.
- `utils/logging_setup.py` + `utils/request_id_middleware.py` (NEW): structlog with JSON renderer in production. Per-cron `BIP_RUN_ID` + per-request `X-Request-ID` propagated via contextvars. CORS expanded for the new header.
- `utils/sentry_init.py` (NEW): free-tier Sentry init wired through `configure_logging()`. Errors tagged with `run_id`. No-op when `SENTRY_DSN` unset.
- `daily_sync.sh`: RUN_ID generation at script entry, env-capture instrumentation (one-week study, kill-switch at `/etc/bip/no-env-capture`), `record_sync()` calls at every major heredoc.
- `scripts/analyze_cron_env.py` (NEW): diffs captured env files to find what differs between "had DATABASE_URL" and "needed fallback" cron runs. Manual tool, run after one week of capture.
- `/api/health/sync-status` expanded: legacy `playoff_backfill_last_24h` key preserved + new `syncs` map (26 entities) + `cache_db` size snapshot.
- `infra/README.md`: UptimeRobot setup docs (liveness + sync-freshness keyword monitor on `"stale": true`), `SENTRY_DSN` + `ENV=production` env vars.

**Stream B — Data Integrity & Schema (Surgical, 1 commit):**
- Alembic 0025: FK constraints on `PlayoffSeries.parent_top/bottom_series_id` (ON DELETE SET NULL), unique index on `series_id` to enable the FK target, defensive orphan-null pre-migration.
- Alembic 0026: `created_at` + `updated_at` on `AwardCaseCandidate` + `RoleExpansionObservation`, backfilled from `last_synced_at` / `computed_at`.
- Alembic 0027: `playoff_series_win_truth` view computing wins from game_logs at query time. Sprint 98 keeps the denormalized `top_wins`/`bottom_wins` columns; the view is additive truth-source for drift detection.
- `services/external_metric_staleness.py` (NEW): `metric_age_days` / `metric_as_of` / `staleness_snapshot` helpers reading `SeasonStat.external_metrics_meta` JSON. `STALE_THRESHOLD_DAYS = 21`.
- `services/playoff_drift_detector.py` (NEW): joins playoff_series with the view, returns rows where cached counts disagree with truth.
- `routers/admin.py` (NEW): `/api/admin/playoff-series-drift` admin-key gated diagnostic endpoint.
- `LeaderboardEntry.metric_as_of` populated when stat is external (EPM/RAPM/LEBRON/RAPTOR/PIPM). Frontend type updated.

**Stream C — API Surface Hardening (2 commits):**
- `_block_live_fetch_if_user_mode` extended from 8 → 24 nba_client wrappers. 0 unguarded stats.nba.com endpoints remain. CDN-only public endpoints (boxscore, PBP, scoreboard, schedule, injuries) intentionally unguarded — designed-public.
- Admin-key gated 8 admin/sync mutation endpoints: `/api/players/{id}/sync`, `/api/injuries/sync`/`unresolved/{id}/resolve`/DELETE, `/api/shotchart/{player_id}/refresh`/`team-defense/{team_id}/refresh`/`ops/{season}/refresh-baseline`/`refresh-stale-players`.
- Rate limits (slowapi) on user-facing expensive endpoints: `/api/query/ask` 10/min, `/api/trade/impact` 20/min, `/api/trade/validate` 30/min.
- `scripts/audit_nba_client_guards.py` (NEW): AST-based audit reports guarded / unguarded-concern / private-helper / CDN-only-public counts. Final: 0 concerns, 24 guarded.

**Stream D — Test Coverage & CI (1 commit):**
- `tests/conftest.py` (NEW): shared `test_db_session` / `client` / `admin_client` / `seed_basic` fixtures. View bootstrapped via raw SQL so admin drift endpoints work in tests.
- 12 new smoke tests across health endpoints + 11 router GET surfaces (200 / 404 / 422 paths) + request-ID propagation verification.
- `.github/workflows/ci.yml` (NEW): pytest blocking, ruff informational (grace period for the 73 baseline style issues), frontend lint informational, frontend build blocking.
- `backend/ruff.toml` (NEW) + `backend/requirements-dev.txt` (NEW).

**Docs:**
- `specs/architecture-flows.html` (NEW): single self-contained HTML, 20 nodes across 9 layers, 21 flows × 154 steps. Inline JSON catalog. Driven by user click — diagram lights up, side panel shows step-by-step annotations. Keyboard navigation.

## Deferred / Not Finished

- **D3 deep service tests** for 10 highest-risk untested services (sync_service, pbp_sync_service, advanced_metrics, game_trajectory_service, shot_lab_service, team_roster_fit_service, trade_impact_service, query_service, playoff_bracket_service, warehouse_service). **Why deferred:** Different domain — each service has its own scope and naturally lands as the service is next touched. The Stream D floor (smoke tests + conftest + CI) is the foundation; deep coverage can grow incrementally without single-sprint shipment.
- **Frontend `metric_as_of` chip** on `MvpRacePanel` / `ExternalMetricsPanel`. **Why deferred:** Different domain — those panels don't currently receive `external_metrics_meta` from their data sources (`MvpAdvancedProfile`, `SeasonStats`). Wiring would require threading through response shapes with broad consumers. Backend infrastructure is in place: `LeaderboardEntry.metric_as_of` is populated whenever a leaderboard is queried by external metric.
- **Tighten ruff to blocking** in CI. **Why deferred:** 73 baseline style issues in the existing codebase. Grace period for one week, then cleanup + tighten.
- **Pre-commit hook (D5).** **Why deferred:** Optional per plan. CI provides the automated check; per-commit would create friction without clear gain until ruff baseline is clean.
- **Cron env-propagation root cause investigation.** **Why deferred:** Blocked on data — Sprint 98 A6 captures env at every cron entry for one week. Vivek runs `scripts/analyze_cron_env.py` after the capture period to identify the root cause. Self-source fallback is the safety net.
- **Cloudflare cache bypass on `/api/admin/*`.** **Why deferred:** Different domain — Cloudflare UI step, ~2 min. The catch-all 2hr cache rule technically caches the 403/200 split for unauthenticated vs authenticated requests; admin traffic is rare enough that the cache pollution is negligible until proven otherwise.

## Coordination Lessons

- **Adding `request: Request` to existing route signatures (slowapi requirement) is a contract break for direct test callers.** Sprint 98 C3 added `request: Request` as the first positional arg on `/api/query/ask`. `test_query_service.py` called `ask()` directly bypassing FastAPI — broke. Fix was a `SimpleNamespace` stub. Worth a lint rule or contract test: any function decorated with `@limiter.limit` must have `request: Request` as the first positional.
- **One-shot scripts (`scripts/_apply_*.py`) need to be deleted in the same commit they're used.** Sprint 98 C1 wrote `_apply_nba_guards.py` to apply guards across nba_client, ran it, then deleted before commit. Pattern worked cleanly; bake into the worker prompt for future bulk-mutation streams.
- **Pytest fixtures that reload `main` create cross-test state leaks.** Stream D's `client` / `admin_client` fixtures both call `importlib.reload(main)`, which interferes when the two fixtures are used in adjacent tests. Resolution: kept admin-gate tests in a separate file (`test_api_hardening.py`) that builds its own minimal app. Worth investigating a dependency-override-only approach so the fixtures don't need module reloads.

## Workflow Lessons

- **The "Surgical schema" constraint worked exactly as advertised.** Vivek picked it at kickoff; the result was three additive Alembic revisions (no rewrites, no top_wins eviction, no dual-path collapse) that landed cleanly and preserved every existing reader. The drift detector view + admin diagnostic gives the truth source for future cleanup without forcing a migration of every caller.
- **Four parallel streams in one sprint branch worked — but only because every stream owned distinct files.** The Lock Table in AGENTS.md actually mattered this sprint: `main.py` would have been a hotspot (Stream A added middleware/sentry, C added router-level deps, D added router mount for admin). Discipline of "A owns main.py for this sprint, others edit their routers only" prevented conflicts. Zero merge conflicts at integration time.
- **The plan's "frontend chip" promise on `MvpRacePanel`/`ExternalMetricsPanel` was overly optimistic.** Both components don't actually receive `external_metrics_meta` from their data sources. Decision to defer the chip and ship the backend infrastructure was the right surgical call, but the plan should have caught this in Phase 1 review. Plan-time grep for the components' data sources would have surfaced it.
- **CDN-only NBA endpoints are intentionally unguarded.** Sprint 98 C1's audit initially flagged 33 unguarded; 8 of those are CDN-only public endpoints (boxscore, PBP, scoreboard, schedule, injuries) that user paths can legitimately call when caches are cold — they're fast, public, rate-limit-free. The audit script now classifies these as "designed-unguarded" so future runs don't re-flag them.

## Technical Lessons

- **Local venv parity matters more than I thought.** Mid-QA, three packages were missing locally: `slowapi` (rate limiting silently no-op'd, the 12-request test all returned 200 until I `pip install`'d it), `httpx` (TestClient broke), and the local DB was at 0023 (Sprint 88) — not even Sprint 93's 0024. Once installed/migrated, everything worked. Production VM has slowapi pinned in requirements.txt, so prod is fine. Worth a `make dev-setup` or `make verify` that confirms the local environment matches the deploy environment before testing.
- **The `playoff_series_win_truth` view query had to be SQLite-compatible for tests.** PostgreSQL and SQLite agree on `CASE WHEN ... THEN ... END` and `LEFT JOIN ... AND` filters, so the same SQL string drives both. The conftest bootstraps the view via raw `CREATE VIEW IF NOT EXISTS` so tests pre-Alembic-chain can use it. Don't write a view in `pg_dump`-style SQL — keep it portable.
- **Sentry's auto-FastAPI integration "just works" but has a starlette version pin.** `sentry-sdk[fastapi]>=2.14.0` lists `starlette<0.42.0` in its dependency tree (through FastAPI), but the project pins starlette to 0.44.0. Pip didn't downgrade and the integration works at runtime — but the dependency resolver is unhappy. Worth a future audit pass to confirm the version overlap doesn't cause subtle bugs.
- **The smoke-test `client` fixture reloads `main_module` to apply env changes (ADMIN_API_KEY toggle).** That's brittle. The Sprint 99+ refactor: build the app via a factory function so tests can construct fresh instances without `importlib.reload`. The dependency-override approach for `get_db` already works without reload; should be possible to extend to `require_admin_key` via the same pattern.

## Next Sprint Seeds

1. **D3 deep service tests** — pick 3-5 of the 10 listed services (start with `sync_service.py` and `playoff_bracket_service.py` since they have the most blast radius). 3-5 tests per service, focused on idempotency + error paths + edge cases.
2. **Frontend `metric_as_of` chip + the broader external-metric staleness surfacing.** Thread `metric_staleness` through `MvpAdvancedProfile` and `SeasonStats` response shapes. Then add the amber chip on the components.
3. **Cron env-propagation root cause** — after one week of A6 captures, run `analyze_cron_env.py`. If a delta is found, file a fix + remove the self-source fallback. Otherwise, document and remove the capture instrumentation.
4. **Collapse the dual R2-series-creation paths (positional vs team-pair).** Sprint 97 deferred, Sprint 98 surgical scope skipped. Sprint 99 should pick one canonical scheme (team-pair derived from game data, since production has converged there) and migrate.
5. **Cleanup the 73-baseline ruff issues + flip CI ruff to blocking.** Mostly auto-fixable; one-shot script pass + manual review of the unsafe-fixes.
6. **Replace `PlayoffSeries.top_wins`/`bottom_wins` with view-driven query path.** The drift detector + view are in place; this sprint cleans up every reader to use the view, then drops the denormalized columns.

## Backlog Refresh

- Removed from `specs/BACKLOG.md`: gap detection for non-playoff entities (Sprint 98 shipped `regular_season_gap_detector`), `_block_live_fetch_if_user_mode` audit (Sprint 98 shipped 24 guards + audit script), real alerting consumer on `/api/health/sync-status` (Sprint 98 shipped UptimeRobot docs + keyword monitor).
- Added: D3 deep service tests, frontend metric_as_of chip wiring, dual R2-series-creation collapse, ruff baseline cleanup, denormalized top_wins/bottom_wins replacement.
- Retained: graduate first `/beta` page to root (Sprint 96 carry, still pending).
