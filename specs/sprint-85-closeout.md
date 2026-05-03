# Sprint 85 Closeout — Bracket Auto-Advance + Per-Series Detail + Tracking/Hustle + Lint Cleanup

**Sprint:** 85
**Date:** 2026-05-02
**Owner:** Claude (4 parallel streams via subagents + main session integration)
**Status:** Final

---

## Shipped

First sprint executed end-to-end under the new 8-phase workflow from Sprint 84. 4 parallel streams; 480 → 490 backend tests (+10 net new); `npx tsc --noEmit` clean; `npm run build` succeeds; `npm run lint` 0 errors / 0 warnings (was 4 errors + 8 warnings).

### Stream D — Lint cleanup + Monte Carlo flake fix (`4ecb13c`, `bb66429`)
- 4 lint errors → 0:
  - `frontend/src/app/draft/[prospectId]/page.tsx:93` — `setError(null)` inside effect → consolidated state object pattern
  - `frontend/src/app/draft/page.tsx:65` — same pattern for `setIsLoading(true)` + `setError(null)`
  - `frontend/src/app/trade-machine/page.tsx:124` — 2 unescaped quotes → `&quot;`
- 8 warnings → 0:
  - `frontend/src/components/broadsheet/SeriesTrackerStrip.tsx:146` — removed dead `cellColor` function (returned empty string, never called)
  - `frontend/src/hooks/usePlayerStats.ts:85-91` — removed 7 unused type imports
- **Monte Carlo flake fix.** Sprint 83 closeout flagged `test_series_odds_monotonic_toward_winning_side` as flaky. Confirmed: 2/10 runs failed locally. Root cause: `playoff_simulator_service.py:436` did `rng.seed(hash(series_id))` — Python's `hash(str)` is randomized per-process when `PYTHONHASHSEED` isn't pinned. Fix: `rng.seed(series_id)` directly (str → deterministic hash). Verified 10/10 stable post-fix.

### Stream A — Bracket auto-advancement (`1dea7b7`)
- **Migration `0021_sprint85_bracket_advancement.py`**: adds `parent_top_series_id` + `parent_bottom_series_id` (nullable, indexed) to `playoff_series`; relaxes NOT NULL on `top_seed_team_id`/`bottom_seed_team_id`/`top_seed`/`bottom_seed` so half-populated TBD slots can persist. Reversible. Defensive `_has_table("teams")` guard in the SQLite batch_alter path so the legacy-baseline test that lacks `teams` doesn't blow up on FK reflection.
- **`playoff_bracket_service.py`**: new `_arm_for_top_seed`, `_compute_next_round_slot`, and `_auto_advance_closed_series`. Standard NBA bracket pairings encoded (1v8 → R2 vs 4v5 winner; 2v7 → R2 vs 3v6; etc., through CF and Finals). `build_or_refresh_bracket()` fires auto-advance only on close-transitions, with a self-heal fallback when a re-run would otherwise miss a missing child.
- **`PlayoffSeriesResponse`**: `top_seed`/`bottom_seed` now `Optional`; `top_wins`/`bottom_wins` default 0; new `parent_top_series_id`/`parent_bottom_series_id` fields.
- **`SeriesCard.tsx`**: TBD pill (dashed, muted, `bip-empty`) when either team is null; status label says "Awaiting winner of R{n}"; preserves all existing rendering when both teams populated.
- **+3 backend tests** in `test_playoff_routes.py`.

### Stream B — Per-series detail page (`d84b816`)
- **NEW backend service** `playoff_series_player_logs_service.py`: `build_series_player_logs(db, series_id)` joins series → games → `PlayerGameLog` rows, groups by team, sorts players by total minutes (desc), computes per-player series totals.
- **NEW endpoint** `GET /api/playoffs/series/{series_id}/player-logs` returning `PlayoffSeriesPlayerLogsResponse` (series_id + top_seed[] + bottom_seed[]).
- **NEW Pydantic models** appended to `models/playoffs.py`: `SeriesPlayerGameLine`, `SeriesPlayerLogs`, `PlayoffSeriesPlayerLogsResponse`.
- **NEW frontend route** `/playoff-series/[seriesId]` (client component using `useParams`; no Suspense gymnastics needed since path param, not query param).
- **NEW component** `SeriesPlayerLogTable` — grouped by player (header rows + per-game stat rows + totals), each game-row links to `/games/{game_id}`. +/- color coding. `bip-table` styling.
- **PlayoffCommandCenter**: added "View per-game player stats →" link in the SeriesRail header that deep-links to `/playoff-series/{selected_series_id}`.
- **+2 backend tests** in `test_playoff_routes.py` (sort order/grouping/totals + 404 path).

### Stream C — Tracking + Hustle dashboards (`f6dfdf4`)
- **NEW services** `player_tracking_service.py` + `player_hustle_service.py`. Cache-first read from `PlayerTrackingStat` / `PlayerHustleStat`; sync-on-miss via existing `gravity_sync_service.sync_player_tracking_stats` / `sync_player_hustle_stats`.
- **NEW endpoints** `GET /api/players/{id}/tracking?season=...&is_playoff=...` and `GET /api/players/{id}/hustle?season=...&is_playoff=...`.
- **NEW components** `PlayerTrackingPanel.tsx` (3 family toggle: Shot Creation / Passing / Shot Defense) and `PlayerHustlePanel.tsx` (single 8-tile grid).
- **PlayerDashboard**: mounts both new panels after the existing splits/play-types panels. Both render in regular season AND playoffs (tracking + hustle data are valid for both — this is correct, unlike the splits gating).
- **`usePlayerTracking` / `usePlayerHustle`** SWR hooks added to `hooks/usePlayerStats.ts`.
- **+5 backend tests** in `test_player_splits_play_types.py`.

### Phase 6 deploy fixes (`a9490f5`, `358f588`)
- **`infra/deploy.sh:21` had a latent bug.** `source /etc/bip/env` doesn't auto-export variables when the file uses `KEY=value` (no `export`). The `--migrate` path's `alembic` subprocess didn't inherit `DATABASE_URL`, so it fell back to `alembic.ini`'s passwordless `postgresql://localhost/bip` and got `fe_sendauth: no password supplied`. Fix: `set -a; source /etc/bip/env; set +a`.
- **Even with env exported, `alembic.ini` hardcodes a password-less URL.** The `python -m alembic` invocation reads `sqlalchemy.url` from `alembic.ini`, ignoring `DATABASE_URL`. The `db.migrations.upgrade_database()` function correctly applies `set_main_option("sqlalchemy.url", DATABASE_URL)` before running alembic. Fix: deploy.sh now invokes `python -m db.migrations` (not raw alembic) so DATABASE_URL is honored. Tried wiring `DATABASE_URL` into `alembic/env.py` directly first — that broke the schema-test paths that pass per-test SQLite URLs, so reverted.

### Production smoke test (after deploy)
| Check | Result |
|-------|--------|
| `https://api.courtvue.app/api/health` | `{"status":"ok"}` |
| `/api/playoffs/bracket?season=2025-26` (Stream A) | Returns series with new `parent_top_series_id` + `parent_bottom_series_id` fields |
| `/api/playoffs/series/{id}/player-logs` (Stream B) | 15 top-seed + 15 bottom-seed players returned |
| `/api/players/1628983/tracking?season=2025-26` (Stream C) | 3 families: Shot Creation, Passing, Shot Defense |
| `/api/players/1628983/hustle?season=2025-26` (Stream C) | Real stats payload |

---

## Deferred / Not finished

- **OG image polish** — not in Sprint 85 scope per Vivek. Carried forward.
- **Frontend integration tests** — no Playwright E2E added; the workflow doc (Sprint 84) deferred this. Manual smoke remains the gate.
- **Bracket auto-advance frontend depth** — the parent-series label currently extracts only the round number ("winner of R1"). Richer "1v8 winner" labels would require either passing parent seeds in the response or a small lookup map. Acceptable for v1.

---

## Coordination Lessons

- **Subagent sandbox issue (3rd sprint in a row).** All 3 implementation agents (A/B/C) hit the same Sprint 83/82-era denial: cannot run `pytest`/`npm`/`python` against worktree paths from inside a subagent. They all completed the file work correctly but parent session had to run all verification + commit + merge. **Operating model is now formalized:** subagents stage; parent verifies + commits + merges. Wrote this into the Stream prompts up-front for Sprint 85 — prevented re-discovery friction.
- **Lock table claims worked.** `backend/models/playoffs.py`, `backend/routers/playoffs.py`, `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts` were all jointly claimed. Streams A and B both edited the playoff files; merge produced exactly 1 conflict marker (test file's section divider, both wanted the same anchor) — easy resolve. Streams B and C's append-only edits to `api.ts` and `types.ts` produced 2 more conflicts on the file's tail — also easy because both were pure appends. **Lesson stands: lock the shared file, but the actual append-only pattern matters more than the lock.**
- **Merge order discipline (D → A → B → C) prevented compound chaos.** D landing first cleared the lint baseline so subsequent merges' `npm run lint` were trivially green. A landing second meant B's appended models slotted next to A's modified `PlayoffSeriesResponse` cleanly.

## Workflow Lessons

- **Phase 3 QA caught a real production blocker.** The schema-migration test failure was an actual bug: Stream A's batch_alter_table on SQLite blew up on the legacy-baseline test path. If we'd merged without running `pytest -q`, the next agent that ran the schema-test would have hit the same failure mid-sprint. **Phase 3 earned its keep on the very first sprint that exercised it.**
- **Phase 6 surfaced a latent infra bug from Sprint 84.** The `--migrate` flag had never been exercised in production before. Two issues compounded: env not auto-exported during source, AND alembic.ini not using DATABASE_URL. Both fixed; the deploy.sh `--migrate` path is now actually production-ready instead of nominally-supported. **The new workflow phases force-test the infra paths that quietly didn't work before.**
- **Phase 7 production smoke is required.** All 4 stream surfaces passed smoke test on production; this is the first time we've systematically verified each new endpoint in production immediately after deploy. Catches any prod-vs-local divergence (e.g. caching, cors, dependency versions) before users do.
- **Per-stream worktrees + parallel agents work for ~6-hr sized streams.** Total wall-clock for Streams A+B+C was ~12 minutes of agent execution (running concurrently) vs ~18-24 hours of serial implementation. Parent session integration + QA + deploy added another ~30 minutes.

## Technical Lessons

- **`source /etc/bip/env` does NOT export variables to subprocesses by default** in bash. The file uses `KEY=value` (no `export`), so the variables are shell-local. Wrap with `set -a` / `set +a` to auto-export, OR add `export` keywords to every line of `/etc/bip/env`. We chose `set -a` so the env file stays portable.
- **`alembic.ini`'s hardcoded `sqlalchemy.url` overrides everything** unless overridden by `set_main_option`. Raw `python -m alembic upgrade head` ignores `DATABASE_URL`. Always invoke via `python -m db.migrations` in any deploy script — that path correctly forwards the env-derived URL.
- **`hash(str)` is non-deterministic across Python processes** unless `PYTHONHASHSEED` is pinned. Never use it for seeding deterministic simulations. Use the string directly (`rng.seed(s)`) or `hashlib.sha256(s.encode()).digest()` for cryptographic determinism.
- **SQLite `batch_alter_table` reflects existing FKs** to recreate them. If the FK target table is absent, reflection fails with `NoSuchTableError`. Guard batch_alter operations with `_has_table(target)` checks for tests that exercise partial-baseline schemas.
- **Next.js path params (`/[id]`) don't need Suspense wrapping** — only query-string params via `useSearchParams` do. Stream B's per-series detail page used `useParams<{seriesId}>()` and skipped the Sprint 84 Suspense gymnastics entirely.

## Next Sprint Seeds (Sprint 86)

1. **OG image polish** (Sprint 84-deferred) — load real fonts into Satori, stat callouts, parameterize for per-page share cards.
2. **Bracket auto-advance frontend label richness** — pass parent seeds into the response so the TBD pill can show "winner of 1v8" instead of just "winner of R1".
3. **Per-series detail page sortable columns** — current grouped-by-player layout is rigid; add ascending/descending sort on PTS, MIN, +/-, etc.
4. **Team-level tracking dashboards** — Stream C did player tracking only; team-level (`LeagueDashTeamPtStats`) is the parallel for the Insights / Team-Defense surfaces.
5. **CDN cache headers on the new endpoints** — currently inheriting the 2hr default catch-all. Player tracking + hustle could go higher (12hr, matches splits cadence). Per-series player logs could go to 30min during active series.
6. **Backfill `parent_*_series_id` on existing closed series** — the auto-advance only fires on close-transitions. Existing closed series in production have null parent pointers. One-shot backfill script + idempotent re-run.

## Backlog Refresh

Removed (shipped):
- "Bracket auto-advancement"
- "Per-series detail page"
- "Lint cleanup pass" (errors + warnings + flaky test all resolved)
- "Tracking / Hustle / Passing dashboards" (player-level shipped; team-level remains)

New entries:
- "Bracket auto-advance frontend label richness" (Sprint 85 polish carry)
- "Backfill parent_*_series_id on existing closed series" (Sprint 85 polish carry)
- "Team-level tracking dashboards" (Sprint 85 follow-on)
- "Per-series detail page sortable columns" (Sprint 85 polish)

Carried:
- OG image polish, Spotrac retry, award cohort expansion.
