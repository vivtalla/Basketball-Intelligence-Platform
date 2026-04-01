# CourtVue Labs — Data Architecture

**Sprint 26 artifact. Last updated: 2026-04-01.**

This document is the canonical reference for the platform's data architecture: where data comes from, what gets stored, what is derived, what each product surface reads, and where the system is going.

---

## 1. Data Sources

| Source | URL / Method | Auth | Data |
|--------|-------------|------|------|
| NBA CDN Schedule | `cdn.nba.com/static/json/staticData/scheduleLeagueV2.json` | None | Full season game schedule |
| NBA CDN Box Score | `cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json` | None | Per-game team + player box scores |
| NBA CDN Play-by-Play | `cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json` | None | Per-game PBP event stream |
| NBA CDN Injuries | `cdn.nba.com/static/json/liveData/injuries/injuries.json` | None | Current league-wide injury report |
| nba_api (stats.nba.com) | Python library | None | Player bio, career stats, shot charts |
| External CSV | Manual import | Manual | EPM, RAPTOR, PIPM, LEBRON, RAPM |

All CDN endpoints are rate-limited via `nba_client.py` (0.6s delay, PostgreSQL-backed distributed lock).

---

## 2. Ingestion Pipelines

### Pipeline A — Warehouse (Canonical)

The warehouse pipeline is the primary, durable data path. It uses a job queue (`ingestion_jobs`) and processes data in stages:

```
CDN fetch → RawSchedulePayload / RawGamePayload (raw JSON archive)
          → WarehouseGame (game registry + status flags)
          → GameTeamStat (per-game team box score)
          → GamePlayerStat (per-game player box score)
          → PlayByPlayEvent (normalized PBP events)
          → [derived] PlayerOnOff, LineupStats (from PBP stints)
          → [aggregated] SeasonStat (season totals from game stats)
```

**Orchestration:** `warehouse_service.py` + `warehouse_jobs.py` + `warehouse_worker_pool.sh`
**Job types (in priority order):**
| Job Type | Priority | Produces |
|----------|----------|----------|
| `backfill_season` | 10 | queues all other jobs for a season |
| `sync_date` | 20 | schedule for recent dates |
| `sync_injuries` | 25 | `player_injuries` (daily refresh) |
| `sync_game_boxscore` | 30 | `GameTeamStat`, `GamePlayerStat` |
| `sync_game_pbp` | 31 | `PlayByPlayEvent`, `PlayByPlay` (legacy) |
| `materialize_game_stats` | 32 | `GameLog` update, PBP-derived metrics |
| `materialize_season_aggregates` | 80 | `SeasonStat`, `PlayerOnOff`, `LineupStats` |

### Pipeline B — Legacy Bulk Sync

Predates the warehouse. Still used to bootstrap player profiles and season stats when the warehouse hasn't yet materialized aggregates.

```
nba_api.stats → Player, Team (player bio + roster)
CDN box scores → SeasonStat (aggregated season totals + advanced metrics)
CDN schedule  → PlayerGameLog (per-game player lines, lazy-populated per request)
```

**Orchestration:** `bulk_sync_service.py`, `pbp_sync_service.py`, `sync_service.py`
**CLI:** `python data/bulk_import.py --season 2024-25`

### Pipeline C — External Metrics (Manual)

```
CSV file → epm_rapm_import.py → SeasonStat (updates epm, raptor, pipm, lebron, rapm columns)
```

Requires a manually downloaded CSV. Not automated. RAPTOR is available free; EPM/PIPM/LEBRON require licensing.

---

## 3. Storage Layer

### 3a. PostgreSQL (Primary Datastore)

#### Reference Tables

| Table | Model | Canonical? | Notes |
|-------|-------|-----------|-------|
| `teams` | `Team` | Yes | Upserted by both pipelines |
| `players` | `Player` | Yes | Upserted by both pipelines |

#### Legacy Tables (Pipeline B)

| Table | Model | Canonical? | Notes |
|-------|-------|-----------|-------|
| `season_stats` | `SeasonStat` | **Shared** | Fed by both pipelines. Warehouse materializes into it. 50+ columns including PBP-derived, external metrics, and computed advanced stats. Treat as the read target for season-level player stats until warehouse materialization is complete. |
| `player_game_logs` | `PlayerGameLog` | **Deprecated-in-place** | Per-game player stats. Lazy-populated per request from CDN. Overlaps with `game_player_stats`. Keep for compatibility (standings computation, gamelog router fallback). Migrate reads to `game_player_stats` when warehouse coverage is confirmed complete. |
| `game_logs` | `GameLog` | **Deprecated-in-place** | Game metadata. Overlaps with `warehouse_games`. Keep for PBP foreign key compatibility. |
| `play_by_play` | `PlayByPlay` | **Deprecated-in-place** | Legacy PBP event table. Overlaps with `play_by_play_events`. New writes go to `play_by_play_events`; legacy table is read-only for historical compatibility. |
| `player_on_off` | `PlayerOnOff` | Shared | Written by both pbp_sync and warehouse materialization. Warehouse version is authoritative for modern seasons. |
| `lineup_stats` | `LineupStats` | Shared | Same pattern as PlayerOnOff. |

#### Warehouse Tables (Pipeline A)

| Table | Model | Canonical? | Notes |
|-------|-------|-----------|-------|
| `games` | `WarehouseGame` | **Yes** | Canonical game registry. Has ingestion status flags. Use this for game status, coverage checks. |
| `game_team_stats` | `GameTeamStat` | **Yes** | Per-game team box score. Prefer over legacy. |
| `game_player_stats` | `GamePlayerStat` | **Yes** | Per-game player box score. Prefer over `player_game_logs` when available. |
| `play_by_play_events` | `PlayByPlayEvent` | **Yes** | Canonical PBP table. Has `action_family` classification. Use for all PBP analysis. |
| `raw_schedule_payloads` | `RawSchedulePayload` | Audit | Raw JSON archive. Not read by product surfaces. |
| `raw_game_payloads` | `RawGamePayload` | Audit | Raw JSON archive. Not read by product surfaces. |
| `source_runs` | `SourceRun` | Ops | Ingestion audit log. |
| `ingestion_jobs` | `IngestionJob` | Ops | Job queue. |

#### New Tables (Sprint 26)

| Table | Model | Purpose |
|-------|-------|---------|
| `player_injuries` | `PlayerInjury` | Current + historical injury status per player. Daily refresh from CDN. |
| `player_shot_charts` | `PlayerShotChart` | Persisted shot chart data (JSONB). Eliminates live API calls. |
| `team_standings` | `TeamStanding` | Materialized standings per team per season. Eliminates per-request computation. |

#### Operational Tables

| Table | Model | Purpose |
|-------|-------|---------|
| `sync_status` | `SyncStatus` | Legacy pipeline progress tracking. |
| `api_request_state` | `ApiRequestState` | PostgreSQL-backed distributed rate limiter. |

### 3b. SQLite `cache.db` (L1 API Response Cache)

Key-value TTL cache for raw nba_api responses. Not a primary datastore. Lives in `backend/cache.db`. TTL: 6h current season, 30 days historical. Data here is transient and can be safely cleared.

---

## 4. Product Surface → Data Dependency Map

| Product Surface | Primary Tables | Notes |
|----------------|---------------|-------|
| Player profile | `players`, `season_stats` | Falls back to NBA API sync if player missing |
| Season stats / leaderboards | `season_stats`, `players` | Reads legacy table; warehouse feeds into it |
| Career stats | `season_stats` (all seasons) | Deduplicates mid-season trades |
| Game logs | `player_game_logs` → `game_player_stats` | Legacy router; warehouse preferred when available |
| Shot chart | `player_shot_charts` → nba_api fallback | Persisted as of Sprint 26 |
| Standings | `team_standings` → `player_game_logs` fallback | Materialized as of Sprint 26 |
| On/off splits | `player_on_off` | Derived from PBP stints |
| Lineup stats | `lineup_stats` | Derived from PBP stints |
| Clutch stats | `season_stats` (clutch_pts, clutch_fg_pct columns) | PBP-derived, written by warehouse materialization |
| PBP coverage | `warehouse_games`, `play_by_play_events`, `game_player_stats` | Coverage checks via `has_parsed_pbp` flag |
| Team analytics | `season_stats`, `player_game_logs` | W/L from game logs |
| Team intelligence | `game_logs`, `play_by_play`, `season_stats`, `player_on_off`, `lineup_stats` | Mixed legacy + derived |
| Team style profile | `game_team_stats`, `play_by_play_events`, `warehouse_games` | Warehouse-backed |
| Scouting / decision | `game_player_stats`, `game_team_stats`, `play_by_play_events`, `lineup_stats` | Warehouse-backed |
| Injuries | `player_injuries` | New Sprint 26 |
| Trajectory / insights | `season_stats`, `players` | Window-based YoY analysis |
| Similarity | `season_stats` | Z-score Euclidean distance |
| Breakouts | `season_stats` | YoY z-score improvement |
| Game Explorer | `warehouse_games`, `game_team_stats`, `play_by_play_events` | Warehouse-backed |
| Pre-read deck | Composite of team style, scouting, rotation, focus levers | All warehouse-backed |

---

## 5. Target Direction

**Goal: Warehouse as the single canonical source of truth for all game-derived data.**

| Migration Step | Status | Target |
|---------------|--------|--------|
| Warehouse as game registry | Done | `warehouse_games` |
| Warehouse box scores | Done | `game_team_stats`, `game_player_stats` |
| Warehouse PBP events | Done | `play_by_play_events` |
| Warehouse-fed season aggregates | Partial | `season_stats` (warehouse materializes into it) |
| Gamelogs router uses `game_player_stats` | Pending | Replace `player_game_logs` primary reads |
| Standings from materialized table | Sprint 26 | `team_standings` |
| Shot charts persisted to DB | Sprint 26 | `player_shot_charts` |
| Injuries as a first-class data domain | Sprint 26 | `player_injuries` |
| Deprecate `play_by_play` (legacy) | Future | Route all reads to `play_by_play_events` |
| Deprecate `game_logs` (legacy) | Future | Route all reads to `warehouse_games` |
| Migrate gamelog reads from `player_game_logs` | Future | Route to `game_player_stats` |
| Alembic migration management | Future | Replace `ensure_schema.py` pattern |

---

## 6. Missing Data Domains

| Domain | Priority | Source | Notes |
|--------|----------|--------|-------|
| Injuries / availability | **Integrated (Sprint 26)** | CDN injuries.json | Done |
| Shot chart persistence | **Integrated (Sprint 26)** | nba_api | Done |
| Standings materialization | **Integrated (Sprint 26)** | Derived from game stats | Done |
| Upcoming schedule | High | `warehouse_games` (status field) | Low effort — expose as endpoint |
| Roster transactions | Medium | nba_api.LeagueGameFinder or ESPN | Trade deadline context, roster moves |
| Draft data | Low | nba_api or separate CSV | Out of scope for current product |
| Referee data | Low | PBP event attributes | Very limited product value |
| Historical external metrics | Low | RAPTOR CSV archive | Manual import, licensing varies |

---

## 7. Hosting Model

**Current (local dev):**
- Backend: uvicorn on `:8000` / `:8001`
- Frontend: Next.js on `:3000` / `:3001`
- PostgreSQL: local instance (`bip` database)
- Workers: `warehouse_worker_pool.sh` (local processes, PID files in `backend/tmp/`)

**Target (hosted):**
- Backend: containerized FastAPI (Railway, Render, or Fly.io)
- Frontend: Vercel or similar
- PostgreSQL: managed instance (Railway Postgres, Supabase, or Neon)
- Workers: scheduled cron jobs via hosted runner (not persistent worker pools)
- `daily_sync.sh` → scheduled job (cron on VPS, or GitHub Actions)

The warehouse pipeline is already designed for this transition: job queue is DB-backed, rate limiter is DB-backed, no local file dependencies (PID files aside).

---

## 8. Schema Management

**Current:** `backend/db/ensure_schema.py` — `Base.metadata.create_all()` + manual `ensure_column_exists()` calls per new column.
**Limitation:** No rollback support, no migration history, no diff detection.
**Target:** Alembic (deferred — high value but requires dedicated sprint, no data risk in current approach for additive changes only).

**Rule:** All schema changes are additive only. Never drop columns or tables without explicit data migration. Always add `ensure_column_exists()` for new columns on existing tables.
