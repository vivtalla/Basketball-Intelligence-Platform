# Sprint 88 Closeout — Data Foundation Audit + Full Implementation

**Sprint:** 88
**Date:** 2026-05-03
**Owner:** Claude (single sequential stream, main session)
**Status:** Final

---

## Shipped

3 parallel Explore agents (DB structure, caching, sync pipeline) audited the full backend + data foundation end-to-end. Sprint 88 implemented every meaningful finding within the existing stack (no new services, no cost change). 500 backend tests still pass post-implementation. `npm run build` clean. `npm run lint` 0 errors.

The single biggest user-facing win: **player + team hustle and tracking tables are now synced in regular season**, not just playoffs. Previously, those 4 endpoints (`/api/players/{id}/{tracking,hustle}`, `/api/teams/{abbr}/{tracking,hustle}`) returned empty for 6 months/year — Sprint 86 hotfix made the empty response fast, but Sprint 88 closes the upstream sync gap.

### Stream A — Completeness syncs (`feature/sprint-88-data-foundation`)

- `daily_sync.sh` now runs `sync_player_hustle_stats` + `sync_team_hustle_stats` + `sync_team_tracking_stats` every nightly run for `(current_season, season_type)`. Cost: 2 cheap NBA API calls (single-call league hustle endpoints) + 12 calls for team tracking (5 measure types + 1 passing + 6 defense distance buckets) ≈ ~7s wall-clock added to nightly cron.
- New `backend/data/weekly_sync.sh` wraps a heavier player tracking refresh: `sync_player_tracking_stats(player_ids=None)` syncs every active player (~450) for the season at 0.6s rate-limit ≈ 5 min wall-clock. Runs Sunday 8am UTC via new cron entry.
- `gravity_sync_service.sync_player_tracking_stats()` now accepts `player_ids=None` to mean "all active players for season+season_type" — derived from `PlayerGameLog` distinct query (~450 players currently).
- **Production backfill executed** post-deploy: player hustle 581 rows, team hustle 30 rows, team tracking 360 rows (NEW — Sprint 86 added the table; never had regular-season data). Player tracking backfill kicked off in background, completing over ~10 min.

### Stream B1 — Alembic migration `0023_sprint88_perf_indexes.py` (`4b53003`)

8 missing indexes on hot tables identified by the audit:

| Table | Index | Affects |
|-------|-------|---------|
| `season_stats` | `(season, is_playoff)` | 49 services filter on this combo |
| `season_stats` | `(player_id, season)` | covering for player-profile lookups |
| `player_game_logs` | `(season, season_type)` | 17 services + multi-million-row table |
| `play_by_play_events` | `(season,)` | 20 services + multi-million-row table |
| `lineup_stats` | `(season, is_playoff, minutes)` | top-lineup leaderboard |
| `player_on_off` | `(season, is_playoff, on_off_net)` | on-off leaderboard |
| `game_player_stats` | `(season,)` | season aggregate materialization |
| `game_team_stats` | `(game_id,)` | single-game lookups |

Defensive `_has_table` AND `_has_index` guards (Sprint 85 lesson — legacy-baseline test path stamps at 0001 without creating most tables; without the `_has_table` check the migration would `CREATE INDEX` on a missing table and fail).

### Stream B2 — N+1 query fixes (3 endpoints)

- `routers/advanced.py` top-lineups (`/api/advanced/lineups`): was 1 player query per lineup row × `limit` rows → now 1 batched query covering all unique players across all lineups (typical `limit=25` with 5 players each = up to 125 unique players, fetched in 1 query instead of 25).
- `routers/advanced.py` on-off leaderboard (`/api/advanced/on-off-leaderboard`): was 1 player query per row → 1 batch.
- `routers/stats.py` league-context position filter (`/api/stats/.../league-context`): was loading every Player row (~800+) into Python memory then filtering by `_POS_MAP` lookup → now pushed to SQL via `Player.position.in_(allowed_positions)`.

### Stream B3 — Explicit SQLAlchemy pool config

`db/database.py`: `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, `pool_recycle=3600`. With 2 gunicorn workers → 60 max concurrent connections (was 30 default). CPX11 Postgres `max_connections=100`, leaves 40 free for backups + cron + manual psql. `pool_recycle=3600` avoids Postgres idle-kill of stale connections.

### Stream B4 — Weekly Postgres VACUUM ANALYZE

New cron entry: Sunday 6am UTC runs `vacuumdb --analyze-in-stages --dbname=bip` after backups. Postgres autovacuum handles routine maintenance; this is the explicit weekly safety net for the multi-million-row tables (`player_game_logs`, `play_by_play_events`, `game_player_stats`).

### Stream C1 — Cache observability

- `data/cache.py` instrumented: `_stats: {"hit", "miss", "expired"}` per-process counter incremented on every `get()`. Plus `logger.debug()` for ad-hoc tracing without code changes.
- New endpoint `GET /api/health/cache-stats` returns `{hit, miss, expired, total, row_count, size_bytes}`. Public-safe (no key contents). First production hit returns `{"hit":0, "miss":0, "expired":0, "row_count": 20, "size_bytes": 1069056}` — counters reset per worker restart.
- `clear_expired()` now returns the deleted row count (was returning None) so the daily sync can log it meaningfully.

### Stream C2 — `clear_expired()` cleanup hooked into daily sync

`daily_sync.sh` end-of-run: Python heredoc invokes `CacheManager.clear_expired()` and prints the deleted count. Was defined but never called → SQLite `cache.db` would grow unboundedly. Now keeps cache.db bounded to active TTL window.

### Stream D — Frontend ISR (PARTIAL — see lessons below)

Added `revalidate` exports to 6 stable pages via a mix of direct page exports (server components) and sibling `layout.tsx` exports (client components):
- `/players/[id]` → `revalidate=3600` (player profile is server component; export went directly on page.tsx)
- `/teams/[abbr]` → `revalidate=3600` (extends Sprint 86 layout)
- `/mvp` → `revalidate=1800` (extends Sprint 86 layout)
- `/leaderboards` → `revalidate=3600` (NEW sibling layout)
- `/standings` → `revalidate=1800` (NEW sibling layout)
- `/milestones` → `revalidate=3600` (NEW sibling layout)
- `/bracket`, `/playoff-series/[id]`, `/games/[id]` kept dynamic (real-time data during playoffs)

**Real-world result is partial:** `npm run build` registered the ISR settings (build output shows `30m`, `1y` revalidate columns), but production responses still return `cache-control: max-age=0, must-revalidate` with no `x-vercel-cache: HIT` after multiple requests. Root cause: the underlying pages are `"use client"` components that do all data fetching client-side via SWR. Vercel's ISR caches the server-rendered HTML, but a client page's HTML shell is essentially data-free — there's nothing meaningful to cache at the edge; data still goes through the API on every browser request.

The proper fix is to convert these pages to server components that fetch data server-side (true ISR) instead of client components hydrating with SWR. That's a meaningful refactor — one Sprint 89 candidate per page family. The Sprint 88 export additions are correct + harmless and provide the foundation; they just don't deliver the perf win until the pages themselves move to server-side data fetching.

### Stream E — `infra/deploy.sh` auto-sync of service units

`deploy.sh` now diffs `infra/bip-api.service` against `/etc/systemd/system/bip-api.service` (and `infra/Caddyfile` against `/etc/caddy/Caddyfile`); copies + `systemctl daemon-reload` if different. Closes Sprint 87 workflow gap that needed manual `sudo cp + daemon-reload` after Sprint 87 Stream C2's service unit changes. Verified live during Sprint 88 deploy: the new `ExecStartPre` line went into effect without any manual intervention.

---

## Production smoke test results

All Sprint 88 changes verified live:

- **Stream A — completeness syncs** (the user-visible win):
  - `/api/players/1628983/hustle?season=2025-26` → returns `stats: {deflections: 198, ...}` (was empty before sprint)
  - `/api/teams/OKC/hustle?season=2025-26` → returns `stats` populated (was empty)
  - `/api/teams/OKC/tracking?season=2025-26` → returns `families: 3/3` populated (was empty)
  - Player tracking backfill in progress (52/~450 players done at smoke time, completing in background)
- **Stream B2 — N+1 fixes**: `/api/advanced/lineups` 200 in 98ms, `/api/advanced/on-off-leaderboard` 200 in 90ms (no regression in response shape, perf gain not directly measurable without before/after benchmarks but theoretical reduction is `limit+1` queries → 2 queries)
- **Stream C1 — cache observability**: `/api/health/cache-stats` returns `{"hit":0,"miss":0,"expired":0,"total":0,"row_count":20,"size_bytes":1069056}`. Counters reset per worker.
- **Stream E — deploy.sh auto-sync**: the deploy ran with the new service unit picked up automatically; no manual `sudo cp + daemon-reload` needed (was the Sprint 87 friction point).

---

## Deferred (with `Why deferred:`)

### Cloudflare `/api/health` bypass-cache rule
**Why deferred:** Cloudflare dashboard UI configuration step, not code. Per Deferral Policy "different domain" — infra UI config done outside the code repo. Documented in `infra/README.md` for the next Cloudflare-touch session. Adds a high-priority cache rule for `URI=/api/health` → "Bypass cache" so monitoring tools (UptimeRobot etc.) detect outages within the check interval (5 min) instead of up to 2 hours.

### True ISR via server-component data fetching (Sprint 88 D follow-on)
**Why deferred:** Real refactor. Stream D added the `revalidate` exports correctly per Next.js spec, but the underlying pages are `"use client"` components — Vercel can't apply meaningful edge caching to client-rendered pages because the HTML shell has no data baked in. Real fix requires converting each page to a server component that fetches data server-side (e.g. `await fetch(\`\${API}/api/players/\${id}\`)`) and renders the initial HTML with data. Then Vercel's edge can cache that filled-in HTML for the `revalidate` window. Per Deferral Policy "genuinely a different domain" — each page family (player, team, leaderboards, etc.) is a separate refactor unit, not polish on what Sprint 88 shipped.

---

## Coordination Lessons

- **Audit-driven sprint shape works well.** 3 parallel Explore agents produced ~3000 words of architectural findings before any implementation. The implementation was then mechanical execution of an already-validated plan, not discovery-as-you-go. ~12 hours of estimated work landed in one focused session.
- **Single-branch sequential commits scaled fine for 18 file changes.** Subagents would have added coordination overhead for streams that are file-disjoint anyway.

## Workflow Lessons

- **The Pre-merge Verification Checklist's Sprint 86 addition (no new `nba_client` wrapper without `_block_live_fetch_if_user_mode()` guard) was N/A for this sprint** because Sprint 88 only added new SYNC ops (`sync_*` functions in `gravity_sync_service`), not new wrappers. The existing wrappers added in Sprints 85/86 already have the guard. Sync ops correctly run with `NBA_API_USER_FETCH_DISABLED=false` exported in cron context.
- **The DB migration `_has_table` defensive guard is now load-bearing.** Sprint 85's lesson; Sprint 86 reused it for FK reflection; Sprint 88 reused it for index creation. The pattern: any operation that touches a table needs both `_has_table` AND `_has_index` (or equivalent) guards because the legacy-baseline test path stamps at `0001_base_schema` without creating most tables. Without both guards, the migration explodes on the legacy test path while running fine on production.
- **Stream D ISR honest-failure documentation matters.** Easy mistake would have been declaring Stream D "shipped" because the exports are in place + `npm run build` shows ISR registration. The harder, honest call is to verify the actual production cache behavior — and when it doesn't work, document why + file the real fix as a Sprint 89 candidate. Per the Deferral Policy: don't ship 60% solutions; either commit to the full server-component refactor in this sprint (would have doubled scope) or accept that Stream D's win is the foundation, not the deliverable.

## Technical Lessons

- **`infra/deploy.sh` auto-sync of service units is now load-bearing infra.** Sprint 87 surfaced the gap; Sprint 88 fixed it. Future service unit changes (or Caddyfile changes) will pick up automatically without manual VM steps. This is the kind of "boring" infra work that pays compounding dividends across all future deploys.
- **Pool size 30 → 60 conn was good defensive prep for ISR + cache stampede.** When (eventually) Stream D's ISR is fully realized, the first revalidate-after-stale window will spike many simultaneous backend requests. The 60-conn pool covers this.
- **`sync_player_tracking_stats(player_ids=None)`** uses a distinct query on `PlayerGameLog.player_id` to find active players. Key insight: there's no separate "is_active" flag on `Player`; we infer from "has appeared in a game this season" via `PlayerGameLog`. This is more accurate than maintaining a separate active-player roster.
- **Stream A NBA API call budget impact is small:** baseline ~654 calls/day → +14 calls/day from new daily syncs (3 hustle/tracking ops, mostly single-call league endpoints) → ~668 calls/day. Plus 450 calls/week for the weekly tracking sync = +64 calls/day amortized. Total: ~732 calls/day, still 27% of NBA's historical 600/5min rate limit. Comfortable headroom.

## Next Sprint Seeds (Sprint 89)

1. **Server-component refactor of /players/[id], /teams/[abbr], /leaderboards, /mvp, /standings, /milestones** to make Stream D's ISR exports actually deliver edge-cache wins. Each page family is a separate refactor unit; could be one big Sprint 89 or split.
2. **Cloudflare `/api/health` bypass-cache rule** (Sprint 88 deferred — Cloudflare UI step).
3. **R2 backup lifecycle rule** (carried from Sprint 87 — Cloudflare UI step).
4. **Cache-effectiveness measurement** — now that Stream C1 instrumented hit/miss, run a 24-hour observation in production, then tune cache TTLs based on actual hit rate (especially for the new tracking + hustle endpoints which now have data).
5. **`/api/health` bypass cache** can ship same-day with Cloudflare R2 lifecycle rule as a single "Cloudflare config sweep" Sprint.

## Backlog Refresh

Removed (shipped in Sprint 88):
- Player + team hustle + tracking sync gap (4 silent UI surfaces fixed)
- 8 missing DB indexes
- 3 N+1 query patterns
- Connection pool default config
- Postgres weekly maintenance
- Cache observability gap
- Unbounded SQLite cache.db growth
- `infra/deploy.sh` workflow gap (Sprint 87 carry)

Carried:
- R2 backup lifecycle rule (Cloudflare UI)
- Award calibration cohort expansion (data-blocked)

New:
- Server-component refactor of stable pages for true ISR
- Cloudflare `/api/health` bypass-cache rule
