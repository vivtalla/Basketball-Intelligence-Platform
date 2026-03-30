# Basketball Intelligence Platform

Full-stack NBA analytics platform providing player evaluation, team analysis, advanced metrics, and play-by-play insights. Built for analysts and basketball enthusiasts who need rigorous, data-driven basketball insight.

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

---

## Sprint History

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

---

## Active Branches

| Branch | Owner | Status |
|--------|-------|--------|
| `master` | — | Stable |
| `feature/sprint-10-yoy-trends` | Claude | Open / not merged |
| `codex-sprint-10-game-explorer-controls` | Codex | Open / not merged |
| `feature/sprint9-leaderboard-enhancements` | Claude | Merged to master |
| `codex-sprint-9-team-sync-dashboard` | Codex | Merged to master |

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
