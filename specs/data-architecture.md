# CourtVue Labs — Data Architecture

**Last updated: 2026-04-06 (manual QA data-foundation pass).**

This document is the canonical reference for the platform's data architecture: where data comes from, what gets stored, what is derived, what each product surface reads, and where the system is going.

---

## 1. Data Sources

| Source | URL / Method | Auth | Data |
|--------|-------------|------|------|
| NBA CDN Schedule | `cdn.nba.com/static/json/staticData/scheduleLeagueV2.json` | None | Full season game schedule |
| NBA CDN Box Score | `cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json` | None | Per-game team + player box scores |
| NBA CDN Play-by-Play | `cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json` | None | Per-game PBP event stream |
| NBA CDN Injuries | `cdn.nba.com/static/json/liveData/injuries/injuries.json` | None | Current league-wide injury report |
| nba_api (stats.nba.com) | Python library | None | Official player bio, career stats, current-season player dashboards, team dashboards, game logs, shot charts |
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
stats.nba.com → Player, Team (player bio + roster)
stats.nba.com → SeasonStat (official current-season player Base + Advanced dashboards)
stats.nba.com → TeamSeasonStat (official current-season team Base + Advanced dashboards)
stats.nba.com → PlayerGameLog (per-game player lines, queued/admin refresh)
stats.nba.com → PlayerShotChart (queued/admin refresh)
CDN box scores / warehouse → SeasonStat (historical or derived aggregate compatibility)
```

**Orchestration:** `bulk_sync_service.py`, `pbp_sync_service.py`, `sync_service.py`
**CLI:** `python data/bulk_import.py --season 2024-25`

### Pipeline D — DB-first Enrichment Queue

Sprint 30 formalized app-critical player reads as DB-first. User-facing GET routes no longer rescue missing data live from `stats.nba.com`; they return stable `ready` / `stale` / `missing` responses and rely on queued enrichment instead.

**Queue-backed enrichment domains:**
| Job Type | Priority | Produces |
|----------|----------|----------|
| `sync_player_profile` | 40 | `players` |
| `sync_player_career` | 41 | `season_stats` |
| `sync_player_gamelogs` | 42 | `player_game_logs` |
| `sync_season_shot_charts` | 45 | fan-out only |
| `sync_player_shot_chart` | 46 | `player_shot_charts` |

**Rule:** request-time user reads must never call these sources directly.

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
| `player_game_logs` | `PlayerGameLog` | **Persisted legacy-backed** | Per-game player stats. No longer lazy-populated per request. Filled by queued/admin enrichment and still overlaps with `game_player_stats`. Keep for compatibility while compare/player surfaces mature toward warehouse-first per-game reads. |
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
| `team_season_stats` | `TeamSeasonStat` | Persisted official team season Base + Advanced dashboards. Canonical team analytics source. |

#### Operational Tables

| Table | Model | Purpose |
|-------|-------|---------|
| `sync_status` | `SyncStatus` | Legacy pipeline progress tracking. |
| `api_request_state` | `ApiRequestState` | PostgreSQL-backed distributed rate limiter. |

### 3b. SQLite `cache.db` (L1 API Response Cache)

Key-value TTL cache for raw nba_api responses. Not a primary datastore. Lives in `backend/cache.db`. TTL: 6h current season, 30 days historical. Data here is transient and can be safely cleared.

---

## 4. Product Surface → Data Dependency Map

| Product Surface | Classification | Canonical Read Path | Notes |
|----------------|----------------|---------------------|-------|
| Player profile | queued enrichment required | `players` | DB-first as of Sprint 30. Missing profile returns stable empty payload with readiness metadata. |
| Season stats / leaderboards | persisted legacy-backed | `season_stats`, `players` | Warehouse feeds into `season_stats`; leaderboards remain DB-first. |
| Career stats | queued enrichment required | `season_stats` (all seasons) | DB-first as of Sprint 30 with `data_status` + `last_synced_at`. |
| Game logs | persisted legacy-backed | `player_game_logs` | DB-first as of Sprint 30. Refreshes happen via queued/admin enrichment. |
| Shot chart | queued enrichment required | `player_shot_charts` | DB-first as of Sprint 29. |
| Standings | warehouse-backed | `team_standings` | Live legacy fallback removed; empty materialized table now surfaces as empty state. |
| Compare dependencies | mixed: persisted legacy-backed + queued enrichment required | `players`, `season_stats`, `player_shot_charts`, `player_injuries` | Compare now renders explicit missing/stale states instead of live rescue assumptions. |
| Insights dependencies | mixed: warehouse-backed + persisted legacy-backed | `season_stats`, `game_team_stats`, `play_by_play_events`, `warehouse_games`, `players` | Trend and burden visuals remain DB-first even when some legacy-backed domains are sparse. |
| On/off splits | warehouse-backed | `player_on_off` | Derived from PBP stints. |
| Lineup stats | warehouse-backed | `lineup_stats` | Derived from PBP stints. |
| Clutch stats | warehouse-backed | `season_stats` clutch columns | PBP-derived, written by warehouse materialization. |
| PBP coverage | warehouse-backed | `warehouse_games`, `play_by_play_events`, `game_player_stats` | Coverage checks via `has_parsed_pbp` flag. |
| Team analytics | official persisted | `team_season_stats`, `teams` | DB-first. Reads from persisted official team dashboards rather than reconstructed player totals. |
| Team intelligence | still non-canonical | `game_logs`, `play_by_play`, `season_stats`, `player_on_off`, `lineup_stats` | Needs a future pass to finish moving legacy `game_logs` / `play_by_play` reads onto warehouse equivalents. |
| Team style profile | warehouse-backed | `game_team_stats`, `play_by_play_events`, `warehouse_games` | Fully warehouse-safe. |
| Scouting / decision | warehouse-backed | `game_player_stats`, `game_team_stats`, `play_by_play_events`, `lineup_stats` | Fully warehouse-safe. |
| Injuries | warehouse-backed | `player_injuries` | CDN-backed and persisted daily. |
| Trajectory / insights | persisted legacy-backed | `season_stats`, `players` | DB-first with no request-time sync. |
| Similarity | persisted legacy-backed | `season_stats` | DB-first. |
| Breakouts | persisted legacy-backed | `season_stats` | DB-first. |
| Game Explorer | warehouse-backed | `warehouse_games`, `game_team_stats`, `play_by_play_events` | Fully warehouse-backed. |
| Pre-read deck | warehouse-backed | composed from team style / scouting / rotation / focus levers | Warehouse-backed. |

### Surface status legend

- `warehouse-backed`: canonical reads already come from warehouse/materialized warehouse tables.
- `persisted legacy-backed`: canonical reads use persisted DB tables that predate the warehouse but no longer depend on live request-time fetch.
- `queued enrichment required`: canonical reads are DB-first, but freshness depends on background/admin queue jobs.
- `still non-canonical`: product surface still mixes in legacy read paths that should migrate in a future sprint.

---

## 5. Target Direction

**Goal: Warehouse as the single canonical source of truth for all game-derived data.**

| Migration Step | Status | Target |
|---------------|--------|--------|
| Warehouse as game registry | Done | `warehouse_games` |
| Warehouse box scores | Done | `game_team_stats`, `game_player_stats` |
| Warehouse PBP events | Done | `play_by_play_events` |
| Warehouse-fed season aggregates | Partial | `season_stats` (warehouse materializes into it) |
| Gamelogs router uses `game_player_stats` | Pending | Replace `player_game_logs` primary reads after compare/player UX is comfortable with warehouse per-game coverage |
| Standings from materialized table | Sprint 26 | `team_standings` |
| Shot charts persisted to DB | Sprint 26 | `player_shot_charts` |
| Injuries as a first-class data domain | Sprint 26 | `player_injuries` |
| Player profile / career / gamelog reads DB-first | Sprint 30 | request-time rescue removed |
| Readiness metadata on app-critical reads | Sprint 30 | `data_status`, `last_synced_at` |
| Deprecate `play_by_play` (legacy) | Future | Route all reads to `play_by_play_events` |
| Deprecate `game_logs` (legacy) | Future | Route all reads to `warehouse_games` |
| Migrate gamelog reads from `player_game_logs` | Future | Route to `game_player_stats` |
| Alembic migration management | Sprint 43 | Canonical migration workflow; startup schema mutation retired |

---

## 6. Missing Data Domains

| Domain | Priority | Source | Notes |
|--------|----------|--------|-------|
| Injuries / availability | **Integrated (Sprint 26)** | CDN injuries.json | Done |
| Shot chart persistence | **Integrated (Sprint 26)** | nba_api | Done |
| Standings materialization | **Integrated (Sprint 26)** | Derived from game stats | Done |
| Upcoming schedule | High | `warehouse_games` (status field) | Low effort — expose as endpoint |
| Player profile readiness dashboard | Integrated (Sprint 30) | `players` + `source_runs` | Coverage view now exposes ready / stale / missing counts |
| Career readiness dashboard | Integrated (Sprint 30) | `season_stats` | Coverage view now exposes ready / stale / missing counts |
| Game-log readiness dashboard | Integrated (Sprint 30) | `player_game_logs` | Coverage view now exposes ready / stale / missing counts |
| Team season dashboard sync | Integrated (manual QA pass) | stats.nba.com `LeagueDashTeamStats` | Persisted to `team_season_stats` and used by `/api/teams/{abbr}/analytics` |
| Team/player split dashboards | High | stats.nba.com split dashboards | Not yet persisted as first-class canonical tables |
| Play type / tracking / hustle dashboards | High | stats.nba.com play-type and tracking families | Needed for a truly comprehensive official-data foundation |
| Team opponent dashboards | Medium | stats.nba.com team dashboard variants | Useful for prep/decision context, not yet canonical |
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

**Current:** Alembic is the canonical schema workflow. `backend/db/ensure_schema.py` remains only as a compatibility wrapper and must not be used as a normal runtime schema-mutation path.
**Rule:** All repo-tracked schema changes must land as audited Alembic revisions. Runtime startup must not silently mutate schema.
