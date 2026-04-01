# CourtVue Labs

CourtVue Labs is a full-stack NBA analytics platform for player evaluation, team analysis, advanced metrics, and play-by-play insights. It is built for analysts and basketball enthusiasts who need rigorous, data-driven basketball context.

---

## Tech Stack

- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS 4, Recharts, SWR
- **Backend**: FastAPI (Python), async endpoints, Pydantic v2 for validation
- **Database**: PostgreSQL (primary via SQLAlchemy 2.0), SQLite (`cache.db` — NBA API response cache only)
- **Data Sources**: `nba_api` (NBA.com Stats API), CSV imports for external metrics (LEBRON, RAPTOR, PIPM, EPM, RAPM)
- **Schema Management**: `db/ensure_schema.py` (no Alembic — project uses `Base.metadata.create_all` + manual `ALTER TABLE` helpers)

---

## Architecture

```
backend/
  main.py                   → FastAPI app entry, CORS, router registration
  config.py                 → Env config (DB URL, cache TTLs, NBA API settings)
  routers/                  → Route handlers (players, stats, shotchart, leaderboards, teams, advanced, gamelogs)
  services/                 → Business logic (sync, PBP processing, advanced metrics)
  models/                   → Pydantic response schemas
  db/
    database.py             → SQLAlchemy engine & session factory (get_db dependency)
    models.py               → ORM models — see table below
    ensure_schema.py        → Schema creation: run `python -m db.ensure_schema` to apply
  data/
    nba_client.py           → NBA API wrapper (rate limiting, CacheManager, _cache_ttl_for_season)
    cache.py                → SQLite CacheManager (get/set/delete)
    pbp_import.py           → CLI: play-by-play data import
    epm_rapm_import.py      → CLI: external metric CSV import
    bulk_import.py          → CLI: bulk player/season data import

frontend/
  src/
    app/                    → Next.js pages (home, players/[id], leaderboards, compare, learn, teams, standings)
    components/             → React components (see component inventory below)
    hooks/                  → usePlayerStats, usePlayerSearch
    lib/
      api.ts                → All backend API calls (single source of truth)
      types.ts              → TypeScript interfaces mirroring backend Pydantic schemas
```

### ORM Models (`backend/db/models.py`)

| Model | Table | Purpose |
|-------|-------|---------|
| `Team` | `teams` | NBA team metadata |
| `Player` | `players` | Player profiles (NBA person_id as PK) |
| `SeasonStat` | `season_stats` | Season averages + advanced metrics per player/season/team |
| `PlayerGameLog` | `player_game_logs` | Per-game stats, persisted to avoid repeat API calls |
| `GameLog` | `game_logs` | Game metadata (date, teams, score) — PBP parent |
| `PlayByPlay` | `play_by_play` | Individual PBP events |
| `PlayerOnOff` | `player_on_off` | On/off splits derived from PBP stints |
| `LineupStats` | `lineup_stats` | 5-man lineup ratings derived from PBP |

---

## Commands

### Development

```bash
# Backend — run from backend/
uvicorn main:app --reload                    # FastAPI dev server :8000

# Frontend — run from frontend/
npm run dev                                  # Next.js dev server :3000
npm run build                                # Production build
npm run lint                                 # ESLint
```

### Schema Updates

```bash
# Run from backend/ — creates new tables, adds missing columns
python -m db.ensure_schema
```

> **Note:** There is no Alembic setup. New ORM models are picked up by `Base.metadata.create_all()` inside `ensure_schema.py`. New columns on existing tables require an `ensure_column_exists()` call in `apply_schema_updates()`.

### Data Import

```bash
# Play-by-play sync — run from backend/
python data/pbp_import.py --season 2024-25
python data/pbp_import.py --season 2024-25 --player-id 123456 --force-refresh

# External metrics CSV import — run from backend/
python data/epm_rapm_import.py data.csv --metrics epm,rapm
python data/epm_rapm_import.py data.csv --metrics lebron,raptor,pipm

# Bulk import — run from backend/
python data/bulk_import.py --season 2024-25
```

Cron:
`0 6 * * * /path/to/backend/data/daily_sync.sh`

### Re-Sync PBP Stats (after schema or logic changes)

```bash
# Recompute on/off and lineup stats for a season
POST /api/advanced/sync-season   body: {"season": "2024-25"}
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql://localhost/bip` | PostgreSQL connection |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL for frontend |

---

## Data Conventions

- Stats stored as per-100-possessions or per-36-minute rates with raw totals alongside. Never raw totals without context.
- Player IDs: NBA.com `person_id` as canonical identifier. Names are NOT unique.
- Season format: always `"2024-25"` string — never `2024` or `2025` alone.
- Game dates: ISO 8601 (`YYYY-MM-DD`), stored as `date` type.
- All timestamps UTC. Convert to local only at display layer.
- Always surface sample size with any rate stat. Flag stats with <200 possessions or <20 games.

---

## Analytics Domain Rules

- Cross-era player comparisons must adjust for pace and league-average efficiency of that season.
- Lineup data requires ≥100 possessions together to be reportable.
- Offensive and defensive ratings use opponent-adjusted values for cross-team comparison.
- Clutch = last 5 minutes, score within 5 points.
- On/off splits come from PBP stint data, not box scores. Stint minutes are measured from clock timestamps (not estimated from possessions).
- External metrics (LEBRON, RAPTOR, EPM, PIPM, RAPM) are imported. Never present as platform-original. Always attribute source.
- Possession counting: FGA + TOV + last-FT-in-sequence (excluding and-ones and technical FTs).

---

## Code Style

- Python: type hints on all function signatures. Use `Annotated` types for FastAPI dependencies.
- Python version is **3.8** — use `Optional[X]` / `List[X]` from `typing`, not `X | None` / `list[X]`.
- TypeScript: strict mode, no `any`. Prefer `unknown` + type narrowing.
- API responses always use Pydantic schemas — never return raw dicts or ORM objects.
- Database queries go through the service layer, never directly in route handlers.
- Frontend data fetching uses SWR hooks — never raw `fetch` in components.
- React hooks must be pre-allocated at the top level (no conditional hooks). For compound filters with dynamic slot counts, allocate a fixed maximum number of hook slots.

---

## Caching Strategy

| Data | Storage | TTL |
|------|---------|-----|
| Game logs (per player/season) | PostgreSQL `player_game_logs` | Historical: never re-fetch. Current season: 24h. |
| Shot chart data | SQLite `cache.db` | Historical: 30 days. Current season: 6h. |
| Season/team game IDs | SQLite `cache.db` | Same TTL rules via `_cache_ttl_for_season()` |
| PBP events | PostgreSQL `play_by_play` | Fetched once per game, never re-fetched |

`_cache_ttl_for_season(season)` in `nba_client.py` returns `CURRENT_SEASON_CACHE_TTL` if `season == _active_nba_season()`, else `HISTORICAL_SEASON_CACHE_TTL`.

---

## Gotchas

- **Read `AGENTS.md` at session start before touching any code.** It contains the current sprint scope, your branch, this sprint's work allocation, the shared file Lock Table, and the Handoff Queue. If `AGENTS.md` doesn't reflect the current sprint, that is the first thing to fix.
- **nba_api rate limits aggressively** — `nba_client.py` enforces 0.6s delays. Never call `nba_api` directly outside this wrapper.
- **Player names are not unique.** Multiple players share names (e.g., Marcus Morris Sr./Jr.). Always resolve to `person_id`.
- **The salary cap changes every season.** Never hardcode cap numbers.
- **External metrics are proprietary.** RAPTOR, EPM, LEBRON, etc. are imported. Always attribute source.
- **SQLite `cache.db` is for NBA API response caching only** — PostgreSQL is the primary datastore.
- **No Alembic.** Schema changes go through `ensure_schema.py`. New tables: add model + run `python -m db.ensure_schema`. New columns on existing tables: add `ensure_column_exists()` call.
- **Python 3.8.** No union type syntax (`X | Y`), no `list[X]` subscripting at runtime in type hints.

---

## Core Principles

- **Data integrity over speed**: Never ship a pipeline without output schema validation.
- **Context is everything**: A stat without context (sample size, opponent adjustment, era normalization) is misleading.
- **Simplicity first**: The simplest model that captures the signal wins.
- **Only touch what's necessary**: Don't refactor adjacent code while fixing a bug. Scope changes tightly.

## Sprint Process

- CourtVue Labs uses a hybrid sprint model: major feature sprints typically run as two parallel teams, while small or tightly coupled sprints can use one sequential `Architect -> Engineer -> Reviewer -> Optimizer` stream.
- Compact handoff artifacts, selective bounded worker usage, and branch/worktree cleanup are part of the default operating model.

---

## Sprint History

### Sprint 23 — Coach Decision Support Quartet
**Branch:** `codex-sprint-23-kickoff`

- Added team-vs-team Comparison Sandbox mode on `/compare`
- Added coach-facing Four-Factor Focus Levers on team pages
- Added Usage vs Efficiency as a second `/insights` workflow
- Added printable `/pre-read` game-day deck built from focus levers and matchup context
- Post-closeout hotfixes improved compare loading, local dev CORS, full-name normalization, usage-efficiency deduplication, and selected-tab readability
- Validation: backend compile, frontend lint/build, and DB-backed smoke checks on the four new reports
### Sprint 1 — MVP
**Branch:** `feature/mvp-initial` → PR #1

Core platform foundation:
- Player profiles with season stats, shot charts, leaderboards
- Player comparison view
- PostgreSQL migration from SQLite cache
- Teams and learn pages

---

### Sprint 2 — PBP Sync + Advanced Dashboards
**Branch:** `codex-play-by-play-sync-and-dashboards` → PR #2

- Play-by-play sync pipeline (`pbp_import.py`, `pbp_service.py`, `pbp_sync_service.py`)
- On/off splits and lineup stats from PBP stints
- Advanced stats dashboard (clutch, second-chance, fast-break)
- PBP coverage status on player profiles
- Per-game log view on player profiles
- Team explorer and roster intelligence pages
- Player similarity engine (statistical comps across eras)

---

### Sprint 3 — Platform Enrichment
**Branch:** `master` (direct)

- League standings page + dynamic home page
- Team analytics dashboard with efficiency ratings and four factors
- Breakout Tracker (YoY improvement/decline rankings)
- Aging curve overlay + percentile comparison mode on player profiles
- Favorites/Watchlist feature
- Shot chart heatmap view + enhanced zone breakdown
- Monthly splits + streak detection on player profiles

---

### Sprint 4 — Playoff Mode + Team Lineups
**Branch:** `master` (direct)

- Playoff mode toggle across player and team views
- Team lineups tab (5-man lineup stats from PBP)
- League context on player cards (percentile positioning)
- PBP advanced stats: clutch FGA sample size, on/off ORTG/DRTG display, loading skeletons

---

### Sprint 5 — Compound Leaderboard Filters
**Branch:** `feature/compound-leaderboard-filters` → PR #3

- Multi-stat compound filtering on leaderboards (filter by multiple stat thresholds simultaneously)
- Multi-column stat display in leaderboard table
- Fixed React hooks rules violation: pre-allocated fixed SWR hook slots for dynamic filter count

---

### Sprint 6 — External Metrics + Career Arc Comparison
**Branch:** `feature/sprint6-external-metrics-compare` → PR #4

- `ExternalMetricsPanel` component on player profiles — shows EPM, RAPTOR, PIPM, LEBRON, RAPM per season with color coding and source attribution
- `DualCareerArcChart` component — overlays two players' career trajectories across BPM, PPG, PER, WS, TS%, VORP with age alignment
- `ComparisonView` updated: new "Arc" tab, EPM/RAPTOR/PIPM rows in advanced table, external metric footnotes
- Game Explorer page for synced PBP data

---

### PBP Accuracy Fix
**Branch:** `feature/pbp-accuracy-fix` → PR #5

Fixed two systematic errors in PBP-derived stats:

1. **Free-throw possession counting** — possessions ending in last FT (no prior FGA in that possession) were not counted. Added `_poss_had_fga` flag + `_LAST_FT_RE` regex to `build_stints()`. Also fixed edge case: DREB resets `_poss_had_fga` so a subsequent foul→FT sequence isn't skipped.

2. **Actual stint duration from clock** — `Stint.seconds` was always `0.0` (unused stub). Wired up clock tracking in `build_stints()` using `_parse_clock_seconds()`. NBA clock counts DOWN, so `duration = clock_start - clock_end`. `PlayerOnOffAccumulator.on_seconds/off_seconds` and `LineupAccumulator.seconds` (also stubs) are now accumulated. `_upsert_on_off()` and `_upsert_lineup()` use real seconds with fallback to possession estimate.

After merging: run `POST /api/advanced/sync-season {"season": "2024-25"}` to recompute with accurate numbers.

---

### Sprint 7 — Team Intelligence + PBP Coverage Dashboard
**Branch:** `codex-team-intelligence-dashboard`, `codex-pbp-coverage-dashboard` (Codex)

- Team Intelligence Dashboard: full team season analytics, efficiency breakdowns, roster on/off splits
- PBP Coverage Dashboard: visibility into which games/players have synced play-by-play data

---

### Sprint 8 — Data Persistence
**Branch:** `feature/data-persistence` → PR #6

Eliminated live NBA API calls on every player profile load:

- **`PlayerGameLog` ORM model + `player_game_logs` table** — stores per-game stats in PostgreSQL. Unique on `(player_id, game_id, season_type)` with `synced_at` timestamp.
- **Lazy-populate gamelogs router** — serves from DB if present and fresh. Falls back to NBA API, stores result. Historical seasons cached forever; current season refreshes after 24h.
- **Shot chart SQLite caching** — `get_shot_chart_data()` wrapped with `CacheManager.get/set` using `_cache_ttl_for_season()`.

---

### Sprint 9 — Leaderboards, Team Ops, And Workflow Hardening
**Branch:** `feature/sprint9-leaderboard-enhancements` (Claude), `codex-sprint-9-team-sync-dashboard` (Codex)

**Claude — Leaderboard enhancements + historical data:**
- **Career Leaders tab** — career averages (pts, reb, ast, bpm, ws, vorp, per, ts%) ranked across all seasons in DB; shows Seasons + GP columns
- **Team filter** — dropdown filters Player Stats leaderboard to a single team; backed by new `GET /api/leaderboards/teams` endpoint
- **Multi-column table** — primary stat highlighted + always-visible Pts/Reb/Ast/TS%/PER/BPM context columns (no extra fetches)
- **Stat tooltips** — one-sentence definition on every column header
- **URL state persistence** — `useSearchParams` + `useRouter` deep-link to any leaderboard view
- **Historical data pipeline** — added `_historical_schedule_game_ids()` to `nba_client.py` using `data.nba.com` mobile schedule feed (avoids blocked `stats.nba.com`); synced 2021-22, 2022-23, 2023-24 (~595–633 players per season, 1230 games each)
- New Pydantic models: `CareerLeaderboardEntry`, `CareerLeaderboardResponse`; `LeaderboardEntry` enriched with context columns

**Codex — Team/PBP sync operations dashboard:**
- Coverage page season sync actions and team detail handoff
- Team Intelligence Panel improvements and lineup visibility

**Workflow hardening (Codex):**
- Sprint-dependent work allocation table in `AGENTS.md` (replaces permanent ownership)
- Explicit branch isolation rule — all sprint work on assigned branch, never directly on `master`
- Sprint closeout checklist + `specs/CLOSEOUT_TEMPLATE.md`
- `specs/sprint-09-closeout.md` written as first closeout record

---

### Sprint 10 — Branch-Only Work, Not Merged
**Branch:** `feature/sprint-10-yoy-trends` (Claude), `codex-sprint-10-game-explorer-controls` (Codex)

- Claude implemented player-profile year-over-year trend indicators and season-selector work on branch
- Codex implemented Game Explorer controls and backend game-summary improvements on branch
- Neither Sprint 10 branch landed in `master`; see `specs/sprint-10-closeout.md` for deferred follow-up
- `codex-sprint-10-game-explorer-controls` is **UNSAFE to merge** — it is at a Sprint 9 commit and its diff deletes all warehouse infrastructure

---

### Sprint 11 — Warehouse Ingestion Foundation
**Branch:** `codex-sprint-11-warehouse-foundation` (Codex) → PR #7; `feature/sprint-11-coverage-dashboard` (Claude) → carried into Sprint 12

**Codex — Warehouse foundation:**
- ORM models: SourceRun, IngestionJob, RawSchedulePayload, WarehouseGame, RawGamePayload, GameTeamStat, GamePlayerStat, PlayByPlayEvent
- Three-layer warehouse model: raw payloads → normalized facts → derived analytics
- Idempotent job pipeline with `WarehouseGame` completeness flags (has_box_score, has_pbp_payload, has_parsed_pbp, materialized)
- `warehouse_jobs.py` CLI, `warehouse.py` router, `warehouse_service.py` service layer
- Reworked canonical PBP pipeline to write to warehouse `PlayByPlayEvent` model

**Claude — Coverage dashboard frontend (carried forward into Sprint 12):**
- `WarehousePipelinePanel` component with pipeline funnel, job stats, action buttons, collapsible recent runs table
- SWR hooks and API functions for warehouse health and job management
- Integrated into `/coverage` page

---

### Sprint 12 — Warehouse Completion + Operational Hardening
**Branch:** `codex-sprint-12-warehouse-ops`, `codex-sprint-12-game-explorer` (Codex); `feature/sprint-12-warehouse-frontend` (Claude) → PR #9

**Codex — Warehouse ops hardening:**
- Season-scoped `/run-next` endpoint
- Retry/backoff in `run_next_job()`: exponential backoff (5m/10m/15m), permanent FAILED at attempt_count ≥ 3
- `retry_failed_jobs()` service + `POST /api/warehouse/retry-failed?season=` endpoint
- `backend/data/daily_sync.sh` cron wrapper

**Codex — Game Explorer rebuild:**
- `frontend/src/app/games/[gameId]/page.tsx` rebuilt fresh from master (not the unsafe Sprint 10 branch)
- Dual-write to legacy `play_by_play` + idempotent `PlayerGameLog` upsert during warehouse migration window

**Claude — Frontend hardening:**
- Season-scoped Run Next Job button (passes season to `/run-next`)
- Retry Failed button + `retryFailedJobs()` API function
- Collapsible Failed Jobs panel (job_type, job_key, last_error, attempt_count)
- Sync Today hidden for historical seasons
- Server-side season filtering for failed jobs fetch; SWR invalidation covers pbp-dashboard keys

---

### Sprint 13 — Warehouse Reliability + Ops Visibility
**Branch:** `codex-sprint-13-warehouse-reliability` (Codex) → PR #10

**Codex — Warehouse reliability + ops visibility:**
- `ApiRequestState` ORM model: DB-backed distributed rate limiter (`SELECT FOR UPDATE`) serializes NBA API calls across parallel worker processes
- `warehouse_jobs.py --loop` mode: workers poll indefinitely with configurable idle sleep and progress logging
- `warehouse_worker_pool.sh`: start/stop/restart/status for N workers with PID files + per-worker log rotation
- `POST /api/warehouse/reset-stale`: re-queues stalled running jobs (expired lease)
- `GET /api/warehouse/jobs/summary`: full queue snapshot by status, job type, stalled/failed jobs, throttle state
- `WarehousePipelinePanel` auto-poll (15s while jobs active) + ops snapshot on coverage page
- YoY trend callouts: `PlayerHeader` (PPG, TS%, AST, REB deltas) and `TeamIntelligencePanel` (net rating, scoring, assist-rate trends)
- Game Explorer event drill-down: click PBP event → score context, formatted clock, player profile link
- Coverage page memo stabilization

**Claude — Session token limit; original tasks (auto-poll, expandable rows) shipped by Codex in broader form.**

---

### Sprint 14 — Game Summary API + Game Explorer Box Score
**Branch:** `codex-sprint-14-data-layer` (Codex), `feature/sprint-14-game-summary-ui` (Claude)

**Codex — Backend data layer:**
- `GET /api/games/{game_id}/summary` backed by warehouse `games`, `game_team_stats`, and `game_player_stats`
- `GameTeamBoxScore`, `GamePlayerBoxScore`, and `GameSummaryResponse` backend models
- `game_summary_service.py` for home/away team box scores plus sorted player rows
- `warehouse_jobs.py` SIGTERM exit-through-Python fix

**Claude — Game Explorer frontend:**
- `getGameSummary()` API client + `useGameSummary()` SWR hook
- Game Explorer box score section with team stat comparison and per-team player tables
- Coverage page memo dependency fix

**Merge note:** Claude's branch needed a final contract-alignment fix before merge so the frontend matched the shipped backend response shape (`home_team_stats`, `away_team_stats`, `players`, `materialized`).

---

### Sprint 15 — Data Completion + Warehouse Hardening
**Branch:** `codex-sprint-15-data-completion` (Codex)

**Codex — Data completion + warehouse hardening:**
- Formal Sprint 15 kickoff for launch-window data completion (`2022-23` through `2025-26`)
- `player_on_off` / `lineup_stats` rematerialization idempotency hotfix merged to `master`
- Duplicate-safe raw payload persistence in `warehouse_service.py` for retried `raw_game_payloads` inserts
- `reset_stale_jobs()` made durable from the service layer
- Sprint 15 operations and planning artifacts:
  - `specs/sprint-15-data-gap-inventory.md`
  - `specs/sprint-15-validation-matrix.md`
  - `specs/sprint-15-warehouse-runbook.md`
- External metric strategy corrected to reflect real source availability:
  - `RAPTOR` as the primary free external metric
  - `RAPM` optional if a clean public source is chosen
  - `EPM`, `LEBRON`, and `PIPM` treated as source-gated / licensed-only rather than launch blockers

**Claude — No major shipped branch in Sprint 15; support/validation role remained available.**

---

### Sprint 16 — Data Foundation Closeout
**Branch:** `codex-sprint-16-data-foundation` (Codex)

**Codex — Data foundation closeout + validation fixes:**
- Fixed the player-page backend crash in `backend/routers/gamelogs.py` by removing Python 3.8-incompatible nested `list[...]` annotations
- Fixed the insights breakout prior-season helper in `backend/routers/insights.py`, restoring improvers/decliners across the launch-window seasons
- Made `retry_failed_jobs()` durable from the service layer in `backend/services/warehouse_service.py`
- Removed lingering import-first messaging from leaderboards and made historical team intelligence guidance season-aware
- Added Sprint 16 planning/ops artifacts:
  - `specs/sprint-16-data-gap-inventory.md`
  - `specs/sprint-16-validation-matrix.md`
  - `specs/sprint-16-warehouse-runbook.md`
  - `specs/sprint-16-handoff-claude-validation-followups.md`
- Cleaned up the live `2025-26` worker lane by restarting the attached pool from the clean worktree and normalizing stale leases before merge

**Sprint 16 result:** the remaining data-foundation bugs and validation ambiguity were closed in code and docs. The only remaining follow-through after merge is operational `2025-26` warehouse catch-up, not an unresolved app/data-foundation bug.

---

### Sprint 17 — Team Rotation Intelligence
**Branch:** `codex-sprint-17-team-rotation-intelligence` (Codex)

**Codex — team-page analyst workflow:**
- Added a dedicated team rotation report endpoint at `GET /api/teams/{abbr}/rotation-report?season=...`
- Added the `Rotation Intelligence` team-page surface with:
  - recent starter stability
  - minute risers and fallers
  - impact anchors
  - recommended games to inspect next
- Scoped the report to warehouse-backed modern seasons and added a precise limited-state fallback for historical seasons
- Fixed a pre-existing React hook-order issue in `frontend/src/components/SeasonSplits.tsx`
- Added Sprint 17 workflow artifacts:
  - `specs/sprint-17-team-rotation-intelligence.md`
  - `specs/sprint-17-review-note.md`
  - `specs/sprint-17-optimizer-note.md`
  - `specs/sprint-17-closeout.md`

**Sprint 17 result:** the platform shifted back into feature work with a single deep analyst workflow on team pages. The next likely product-facing step is visual-system refinement, especially a deliberate platform color refresh, while warehouse catch-up continues operationally in parallel.

---

### Sprint 18 — Hardwood Editorial Refresh
**Branch:** `codex-sprint-18-hardwood-editorial` (Codex)

**Codex — platform visual system refresh:**
- Chose the `Hardwood Editorial` palette direction and shipped it as the active platform theme
- Added shared theme tokens and reusable utility classes in `frontend/src/app/globals.css`
- Refreshed the app shell plus primary workflow pages and panels across home, teams, players, compare, standings, insights, and learn
- Strengthened text contrast and signal hierarchy so headings, links, tables, and state messaging read more clearly within the new palette
- Added Sprint 18 workflow artifacts:
  - `specs/sprint-18-hardwood-editorial-refresh.md`
  - `specs/sprint-18-review-note.md`
  - `specs/sprint-18-optimizer-note.md`
  - `specs/sprint-18-closeout.md`

**Sprint 18 result:** the platform now has a deliberate visual identity instead of the prior default gray/blue look. The next likely follow-through is deeper cleanup of remaining legacy component styling while keeping product work and warehouse operations moving in parallel.

---

### Sprint 19 — Player Trend Intelligence
**Branch:** `codex-sprint-19-player-trend-intelligence` (Codex)

**Codex — player-page analyst workflow:**
- Added a dedicated player trend report endpoint at `GET /api/players/{player_id}/trend-report?season=...`
- Added the `Player Trend Intelligence` player-page surface with:
  - role-status summary strip
  - recent-vs-season comparison
  - trust signals
  - impact snapshot
  - recommended games to inspect next
- Scoped the workflow to regular-season windows and added precise playoff-mode and sparse-data limited-state fallbacks
- Removed `next/font/google` from the app shell and replaced it with deterministic local font stacks
- Added backend coverage for missing `player_on_off` degradation and sparse-data limited responses
- Added Sprint 19 workflow artifacts:
  - `specs/sprint-19-player-trend-intelligence.md`
  - `specs/sprint-19-review-note.md`
  - `specs/sprint-19-optimizer-note.md`
  - `specs/sprint-19-closeout.md`

**Sprint 19 result:** the platform now has parallel flagship decision workflows on both team and player pages. The next likely product step is connecting those workflows into a broader investigation path rather than adding another isolated panel.

---

### Sprint 20 — Dual Team Analyst Workflows
**Branch:** `codex-sprint-20-kickoff` (Codex integration branch with Team A + Team B feature branches)

**Codex — dual-team sprint execution + shipped workflows:**
- Reworked sprint operations around two parallel teams using the same four-role flow:
  - Team A `Metric Builder Team`
  - Team B `Trajectory Team`
- Added the Team A `Custom Metric Builder` workflow on `Leaderboards` with:
  - a dedicated `POST /api/leaderboards/custom-metric` backend contract
  - stat and weight validation
  - z-score normalization before weighting
  - composite rankings
  - metric naming / interpretation
  - anomaly detection for weight-sensitive outliers
- Added the Team B `Trajectory Tracker` workflow on `Insights` with:
  - a dedicated `GET /api/insights/trajectory` backend contract
  - recent-window vs out-of-window baseline comparisons
  - breakout and decline rankings
  - trajectory labels
  - context flags and exclusion handling
- Added Sprint 20 workflow artifacts:
  - `specs/sprint-20-metric-builder.md`
  - `specs/sprint-20-trajectory-tracker.md`
  - `specs/sprint-20-team-a-review-note.md`
  - `specs/sprint-20-team-a-optimizer-note.md`
  - `specs/sprint-20-team-b-review-note.md`
  - `specs/sprint-20-team-b-optimizer-note.md`
  - `specs/sprint-20-closeout.md`

**Sprint 20 result:** the platform now has two new analyst-facing investigation workflows and a proven dual-team sprint structure. The next likely product step is connecting those workflows with saved analyst state, deeper drill-down handoffs, or another two-track feature sprint using the same operating model.

---

### Sprint 21 — Metrics Workspace, Player Stats Split, and Name Consistency
**Branch:** `codex-sprint-21-kickoff` (Codex integration branch with Team A + Team B feature branches)

**Codex — dual-team frontend split + cleanup sprint:**
- Split the old `Leaderboards` surface into two dedicated top-level workspaces:
  - `Metrics`
  - `Player Stats`
- Moved `Build Your Own Metric` onto the new `Metrics` page and added:
  - built-in starter presets
  - local saved presets stored in browser storage
  - direct follow-through back to `Player Stats`
- Moved the existing leaderboard experience onto the new `Player Stats` route without the metric builder
- Replaced `/leaderboards` with a compatibility redirect to `/player-stats`
- Updated app-shell and home-page navigation to feature `Metrics` and `Player Stats` as first-class workspaces
- Fixed visible player-name shortening on high-traffic UI, including the compare-page legend labels
- Added Sprint 21 workflow artifacts:
  - `specs/sprint-21-team-a-metrics-workspace.md`
  - `specs/sprint-21-team-b-player-stats-name-consistency.md`
  - `specs/sprint-21-team-a-review-note.md`
  - `specs/sprint-21-team-a-optimizer-note.md`
  - `specs/sprint-21-team-b-review-note.md`
  - `specs/sprint-21-team-b-optimizer-note.md`
  - `specs/sprint-21-closeout.md`

**Sprint 21 result:** the platform now has cleaner top-level analyst workspaces and more consistent player-name presentation, while preserving the Sprint 20 metric and ranking capabilities. The next likely product step is making saved metric state portable or shareable rather than browser-local only.

---

### Sprint 22 — CourtVue Labs Rebrand + Metrics + Trajectory
**Branch:** `codex-sprint-22-kickoff`

**Codex — CourtVue Labs launch sprint:**
- Renamed the product to `CourtVue Labs` across the app shell, metadata, Learn metadata, API title, and operational bulk-import banner
- Added the new primary custom-metric route:
  - `POST /api/metrics/custom`
- Upgraded the `Metrics` workspace to support:
  - URL-shareable metric state
  - direct player-page links from ranking rows
  - direct Compare handoff for the top two metric results
- Extended custom-metric ranking rows with player identifiers so frontend handoffs are linkable instead of name-only
- Kept the recency-first `Trajectory Tracker` on `/insights` and refreshed its CourtVue Labs-facing copy
- Added Sprint 22 workflow artifacts:
  - `specs/sprint-22-team-a-courtvue-metrics.md`
  - `specs/sprint-22-team-b-courtvue-trajectory.md`
  - `specs/sprint-22-closeout.md`

**Sprint 22 result:** the platform now has a cohesive CourtVue Labs brand and a stronger analyst loop around custom metrics, with shareable setup state and direct handoff into deeper player comparison. The next likely product step is deciding whether analyst state stays URL-first or moves into persistent saved workflows.

---

## Active Branches

| Branch | Owner | Status |
|--------|-------|--------|
| `master` | — | Stable |
| `feature/sprint-10-yoy-trends` | Claude | Open — YoY StatTable work already on master; can close |
| `codex-sprint-10-game-explorer-controls` | Codex | **UNSAFE — do not merge** |

---

## Component Inventory (Frontend)

| Component | Location | Purpose |
|-----------|----------|---------|
| `PlayerDashboard` | `components/` | Main player profile shell |
| `StatTable` | `components/` | Season stats table with sorting |
| `ShotChart` | `components/` | Shot chart with heatmap mode |
| `RadarChart` | `components/` | Multi-stat radar for player comparison |
| `CareerArcChart` | `components/` | Single-player career trajectory |
| `DualCareerArcChart` | `components/` | Two-player career arc overlay (Sprint 6) |
| `ExternalMetricsPanel` | `components/` | EPM/RAPTOR/PIPM/LEBRON/RAPM per season (Sprint 6) |
| `ComparisonView` | `components/` | Side-by-side player comparison (stats + arc + radar) |
| `LineupTable` | `components/` | 5-man lineup stats |
| `OnOffTable` | `components/` | Player on/off splits |
| `WarehousePipelinePanel` | `components/` | Warehouse ingestion funnel, job stats, action buttons, auto-poll (Sprint 11–13) |
| `PlayerHeader` | `components/` | Player profile header with YoY stat delta callouts (Sprint 13) |
| `TeamIntelligencePanel` | `components/` | Team season analytics with YoY trend signals (Sprint 13) |
