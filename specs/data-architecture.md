# CourtVue Labs — Data Architecture

**Last updated: 2026-04-30 (Sprint 81 — data foundation closeout).**

This document is the canonical reference for the platform's data architecture: where data comes from, what gets stored, what is derived, what each product surface reads, and where the system is going.

---

## 1. Infrastructure Topology

```
┌─────────────────────────────┐         ┌──────────────────────────────────────┐
│  Vivek's MacBook (Dev)      │         │  Hetzner CX22 — Ashburn VA            │
│                             │         │  5.78.114.15  (PRODUCTION)             │
│  - FastAPI (dev uvicorn)    │──TCP────▶│  - Postgres 16.13 (port 5432)         │
│  - Next.js dev server       │  5432   │  - cron: daily_sync.sh  (6am UTC)     │
│  - Local Postgres (fallback)│         │  - cron: post-game      (*/30)        │
│  - source ~/.bip-env        │         │  - cron: bip-backup.sh  (4am UTC)     │
│                             │         │  - cron: bip-backup-verify.sh (Sun 5am)│
└─────────────────────────────┘         │  - /home/ubuntu/bip  (repo clone)     │
                                         │  - venv: /home/ubuntu/bip/backend/venv│
                                         │  - secrets: /etc/bip/env  (chmod 600) │
                                         │  - logs: /var/log/bip-*.log           │
                                         └──────────────────┬───────────────────┘
                                                            │
                                                    nightly pg_dump | gzip
                                                            │
                                                            ▼
                                         ┌──────────────────────────────────────┐
                                         │  Cloudflare R2 — bip-backups bucket  │
                                         │  bip-YYYYMMDD.dump.gz                │
                                         │  Retention: 7 daily + 4 weekly +     │
                                         │             3 monthly                │
                                         │  (10 GB free tier — ~1 year runway)  │
                                         └──────────────────────────────────────┘
```

**Cost:** ~€4.51/month (Hetzner CX22) + $0 (R2 within free tier) ≈ **$5/month total.**

**Firewall:** Hetzner Cloud Firewall restricts port 5432 to laptop IP only. Port 22 (SSH) same restriction.

**Secrets path:**
- Laptop: `~/.bip-env` → `export DATABASE_URL="postgresql://bip:…@5.78.114.15:5432/bip"`
- VM: `/etc/bip/env` → holds `DATABASE_URL`, `PGPASSWORD`, R2 credentials (chmod 600)
- Operational runbook: `specs/db-hosting.md`

---

## 2. Data Sources

| Source | URL / Method | Auth | Data |
|--------|-------------|------|------|
| NBA CDN Schedule | `cdn.nba.com/static/json/staticData/scheduleLeagueV2.json` | None | Full season game schedule |
| NBA CDN Box Score | `cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json` | None | Per-game team + player box scores |
| NBA CDN Play-by-Play | `cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game_id}.json` | None | Per-game PBP event stream |
| NBA CDN Injuries | `cdn.nba.com/static/json/liveData/injuries/injuries.json` | None | Current league-wide injury report |
| nba_api (stats.nba.com) | Python library | None | Official player bio, career stats, current-season player dashboards, team dashboards, game logs, shot charts |
| Seed CSV — Salaries | `backend/data/seed/contracts_2025_26.csv` | Manual | 514-player contract data (24 known-exact, 490 estimated). `salary_source` field distinguishes origin. |
| Seed CSV — Draft Prospects | `backend/data/seed/draft_prospects_2026.csv` | Manual | Draft board with measurements and stats (stub Sportradar interface). |
| Seed CSV — Injury History | `backend/data/seed/injury_history.csv` | Manual | Historical injury records (stub ProSportsTransactions interface). |
| Seed CSV — Award Voting | `backend/data/seed/award_voting_seed.csv` | Manual | 57 MVP ballot rows across 13 races (2012-13 → 2024-25) for award calibration. |
| External CSV | Manual import | Manual | EPM, RAPTOR, PIPM, LEBRON, RAPM |

**Rule:** `stats.nba.com` is frequently rate-limited or blocked. All NBA API access goes through `nba_client.py` (0.6s delay, cache-first). CDN endpoints are preferred for live/game data.

---

## 3. Ingestion Pipelines

### Pipeline A — Warehouse (Canonical)

The warehouse pipeline is the primary, durable data path. It uses a job queue (`ingestion_jobs`) and processes data in stages:

```
CDN fetch → RawSchedulePayload / RawGamePayload (raw JSON — TTL 30 days)
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

### Pipeline C — External Metrics (Manual)

```
CSV file → epm_rapm_import.py → SeasonStat (updates epm, raptor, pipm, lebron, rapm columns)
```

Requires a manually downloaded CSV. Not automated.

### Pipeline D — DB-first Enrichment Queue

Sprint 30 formalized app-critical player reads as DB-first. User-facing GET routes never call `stats.nba.com` directly; they return stable `ready` / `stale` / `missing` states and rely on queued enrichment.

| Job Type | Priority | Produces |
|----------|----------|----------|
| `sync_player_profile` | 40 | `players` |
| `sync_player_career` | 41 | `season_stats` |
| `sync_player_gamelogs` | 42 | `player_game_logs` |
| `sync_season_shot_charts` | 45 | fan-out only |
| `sync_player_shot_chart` | 46 | `player_shot_charts` |

### Pipeline E — Seed CSV Upserts (Daily Cron)

Sprint 78+ added idempotent CSV-driven upserts for Front Office data domains. These run nightly in `daily_sync.sh` after the warehouse pass.

```
contracts_2025_26.csv    → player_contracts     (salary_ingestion_service.py)
draft_prospects_2026.csv → draft_prospects + draft_prospect_stats + draft_prospect_measurements
injury_history.csv       → player_injury_history
award_voting_seed.csv    → award_voting          (one-time; does not re-run nightly)
```

### Pipeline F — Nightly Materializations

Derived tables rebuilt after each daily sync:

```
season_stats + player profiles      → role_expansion_observations  (opportunity_v2 KNN dataset)
game_logs + season_stats            → player_streaks + milestone_snapshots  (CF5 leaderboard)
season_stats + award_voting         → award_case_candidates → mvp_case_v5 calibrated weights
                                      (data/materialize_award_modifiers.py +
                                       services/award_calibration_service.py)
season_stats                        → team_standings  (materialize_standings)
playerdashboardbygeneralsplits      → player_split_stats  (sync_official_player_general_splits)
synergyplaytypes                    → play_type_stats     (sync_official_play_type_stats)
```

### Pipeline G — Playoff Slice (Conditional)

Runs during postseason only, gated by `season_phase_service.get_current_phase()`:

```
CDN scoreboard → sync_today_playoff_finals.py  (final-status game ingestion)
               → sync_playoff_full.py           (playoff season_stats + splits)
               → sync_playoff_pbp.py            (PBP events + on/off + lineup derivations)
               → build_or_refresh_bracket()     (bracket state)
```

**Note:** `sync_playoff_pbp.py` is is_playoff-aware — it will not clobber regular-season lineup/on-off rows. The `is_playoff` field cascades through all five PBP sync helpers.

---

## 4. Storage Layer

### 4a. PostgreSQL — Hetzner CX22 (Production)

**Current state:** 50 tables, 4,558,469 rows, alembic_version `0017_sprint80_raw_payload_ttl`. ~1.84 GB uncompressed.

#### Reference Tables

| Table | Model | Notes |
|-------|-------|-------|
| `teams` | `Team` | NBA team metadata. Upserted by both pipelines. |
| `players` | `Player` | Player profiles, NBA person_id as PK. |

#### Game / PBP Tables (Warehouse — Canonical)

| Table | Model | Notes |
|-------|-------|-------|
| `games` | `WarehouseGame` | Canonical game registry with ingestion status flags. |
| `game_team_stats` | `GameTeamStat` | Per-game team box score. Prefer over legacy. |
| `game_player_stats` | `GamePlayerStat` | Per-game player box score. Prefer over `player_game_logs`. |
| `play_by_play_events` | `PlayByPlayEvent` | **Canonical PBP table.** Has `action_family`, `is_playoff`. ~2.1M rows. |
| `raw_schedule_payloads` | `RawSchedulePayload` | Raw JSON audit. Not read by product surfaces. |
| `raw_game_payloads` | `RawGamePayload` | Raw JSON audit. TTL 30 days (migration 0017). ~9 MB post-cleanup. |
| `source_runs` | `SourceRun` | Ingestion audit log. |
| `ingestion_jobs` | `IngestionJob` | Warehouse job queue. |

#### Legacy Tables (Pipeline B — deprecated-in-place)

| Table | Model | Status | Notes |
|-------|-------|--------|-------|
| `season_stats` | `SeasonStat` | **Shared** | Fed by both pipelines. 50+ columns. Read target for season-level player stats. |
| `player_game_logs` | `PlayerGameLog` | **Persisted legacy-backed** | Per-game player stats. Queued enrichment. Overlaps with `game_player_stats`. |
| `game_logs` | `GameLog` | **Deprecated-in-place** | Game metadata. Overlaps with `warehouse_games`. Keep for PBP FK compat. |
| ~~`play_by_play`~~ | ~~`PlayByPlay`~~ | **Retired (Sprint 81)** | Legacy PBP table dropped via migration `0018_sprint81_drop_legacy_pbp`. All 11+ readers migrated to `play_by_play_events`. ~677 MB freed. |
| `player_on_off` | `PlayerOnOff` | Shared | Written by pbp_sync (is_playoff-aware as of Sprint 79) and warehouse. |
| `lineup_stats` | `LineupStats` | Shared | Same. Warehouse version authoritative for modern seasons. |

#### Analytics Tables (Sprint 26–28)

| Table | Model | Notes |
|-------|-------|-------|
| `player_injuries` | `PlayerInjury` | Current + historical injury status. Daily CDN refresh. |
| `player_shot_charts` | `PlayerShotChart` | Persisted shot chart data (JSONB). Eliminates live API calls. |
| `team_standings` | `TeamStanding` | Materialized standings per team per season. |
| `team_season_stats` | `TeamSeasonStat` | Official team Base + Advanced dashboards. |
| `team_split_stats` | `TeamSplitStat` | Official team general split stats (Location, W/L, Days Rest, Month). |
| `player_on_off` | `PlayerOnOff` | On/off splits from PBP stints. |
| `lineup_stats` | `LineupStats` | 5-man lineup net ratings from PBP stints. |

#### Front Office Tables (Sprint 78)

| Table | Model | Notes |
|-------|-------|-------|
| `player_contracts` | `PlayerContract` | Salary data. `source` column: `"actual"` / `"seed_csv"` / `"estimated"`. 514 players for 2025-26. |
| `draft_prospects` | `DraftProspect` | Draft board entries. |
| `draft_prospect_stats` | `DraftProspectStats` | Per-prospect stats (pace-adjusted NCAA → NBA projection). |
| `draft_prospect_measurements` | `DraftProspectMeasurements` | Height, wingspan, athletic testing. |
| `draft_pick_assets` | `DraftPickAsset` | Team pick asset tracking for Trade Machine + Arc. |
| `player_injury_history` | `PlayerInjuryHistory` | Historical injury records (tiered duration model). |
| `player_streaks` | `PlayerStreak` | Active streak tracking (CF5 nightly snapshot). |
| `milestone_snapshots` | `MilestoneSnapshot` | Career milestone proximity snapshots (CF5 nightly). |

#### Analytics / ML Tables (Sprint 78–81)

| Table | Model | Notes |
|-------|-------|-------|
| `award_voting` | `AwardVote` | Historical MVP ballot data (57 rows, 13 races). Feeds award calibration. |
| `role_expansion_observations` | `RoleExpansionObservation` | 286 player-season pairs for opportunity_v2 KNN. Nightly materialization. |
| `award_case_candidates` | `AwardCaseCandidate` | **Sprint 81.** Materialized Basketball Value + 5-pillar modifier vectors per (player, season). Activates `mvp_case_v5` calibrated weights when LOO-CV Spearman ≥ 0.7. |
| `player_split_stats` | `PlayerSplitStat` | **Sprint 81.** Per-player Location / W-L / Days Rest / Month / Pre-Post All-Star slices. |
| `play_type_stats` | `PlayTypeStat` | **Sprint 81.** Per-player Synergy archetype rows (11 families). |

#### Operational Tables

| Table | Model | Notes |
|-------|-------|-------|
| `sync_status` | `SyncStatus` | Legacy pipeline progress tracking. |
| `api_request_state` | `ApiRequestState` | PostgreSQL-backed distributed rate limiter. |

### 4b. SQLite `cache.db` (L1 API Response Cache)

Key-value TTL cache for raw nba_api responses. Not a primary datastore. Lives in `backend/cache.db`. TTL: 6h current season, 30 days historical. Transient — safe to clear. Not backed up (re-populatable from NBA API).

### 4c. Cloudflare R2 `bip-backups` Bucket

Nightly `pg_dump --format=custom -Z0 | gzip -9` output streamed to R2. Object name: `bip-YYYYMMDD.dump.gz`. Current compressed size: ~140 MB. Retention: 7 daily + 4 weekly + 3 monthly.

**Restore procedure** (from `specs/db-hosting.md`):
```bash
aws --endpoint=$R2_ENDPOINT s3 cp s3://bip-backups/bip-YYYYMMDD.dump.gz - \
  | gunzip | pg_restore --dbname=bip_restore --no-owner --no-acl
python infra/verify_migration.py --source $DATABASE_URL --target postgresql://localhost/bip_restore --tolerance 100
```

---

## 5. Cron Schedule (VM — Hetzner 5.78.114.15)

All jobs run as root. Each sources `/etc/bip/env` before executing.

| Time (UTC) | Job | Log |
|------------|-----|-----|
| Daily 4am | `bip-backup.sh` → R2 | `/var/log/bip-backup.log` |
| Daily 6am | `daily_sync.sh` (full pipeline) | `/var/log/bip-sync.log` |
| Every 30 min | `daily_sync.sh --post-game` (playoff gate) | `/var/log/bip-sync.log` |
| Sunday 5am | `bip-backup-verify.sh` (restore drill) | `/var/log/bip-backup.log` |

**`daily_sync.sh` full pipeline order:**
1. `queue_season_shot_charts` — shot chart job fan-out
2. `warehouse_jobs.py` — game box scores, PBP events, materialization
3. `sync_injuries` — CDN injury refresh
4. `sync_injury_history` seed CSV upsert
5. `materialize_standings`
6. `sync_official_season_stats` + team stats + splits
7. `sync_today_playoff_finals.py` + `sync_playoff_full.py` + `sync_playoff_pbp.py` *(playoffs only)*
8. `sync_role_expansion.py` — role_expansion_observations materialization
9. `sync_streaks_milestones.py` — player_streaks + milestone_snapshots
10. `sync_salaries.py` — player_contracts upsert
11. `sync_draft_prospects.py` — draft_prospects upsert

---

## 6. Product Surface → Data Dependency Map

| Product Surface | Read Path | Notes |
|----------------|-----------|-------|
| Player profile | `players` | DB-first (Sprint 30). Returns `data_status` metadata. |
| Season stats / leaderboards | `season_stats`, `players` | Warehouse feeds into `season_stats`. |
| Career stats | `season_stats` (all seasons) | DB-first with `data_status` + `last_synced_at`. |
| Game logs | `player_game_logs` | DB-first. Queued enrichment for freshness. |
| Shot chart | `player_shot_charts` | DB-first (Sprint 29). |
| Standings | `team_standings` | Materialized. |
| Team analytics | `team_season_stats`, `teams` | Persisted official dashboards. |
| Team splits | `team_split_stats` | Persisted official splits (Location / W-L / Days Rest / Month). |
| On/off splits | `player_on_off` | PBP-derived. `is_playoff` distinguishes slices. |
| Lineup stats | `lineup_stats` | PBP-derived. `is_playoff` distinguishes slices. |
| Injuries | `player_injuries` | CDN-backed, persisted daily. |
| Game Explorer | `warehouse_games`, `game_team_stats`, `play_by_play_events` | Fully warehouse-backed. |
| Pre-read deck | composed: team style / scouting / rotation | Warehouse-backed. |
| Team style / archetype | `game_team_stats`, `play_by_play_events`, `warehouse_games` | Warehouse-backed. |
| Trajectory / Insights | `season_stats`, `players` | DB-first, persisted legacy-backed. |
| Trade Machine | `player_contracts`, `season_stats`, `lineup_stats` | `salary_source` surfaced to UI (amber `est.` badge). |
| Free Agency | `player_contracts`, `season_stats` | Expiring-contract tier bucketing. |
| Draft Board | `draft_prospects`, `draft_prospect_stats`, `draft_prospect_measurements` | Seed CSV, stub Sportradar interface. |
| Team Arc (3-year projection) | `player_contracts`, `draft_pick_assets`, `season_stats` | Aging curve + cap state overlay. |
| Injury Impact | `player_injury_history`, `player_injuries`, `season_stats` | Tiered duration model. |
| MVP Race | `season_stats`, `award_voting` | `mvp_case_v5` with calibrated weights from award history. |
| Opportunity | `season_stats`, `role_expansion_observations`, `player_on_off`, `lineup_stats` | `opportunity_v2`: shrunk-Mahalanobis KNN (K=20). |
| Playoff Command Center | `play_by_play_events`, `lineup_stats`, `player_on_off`, `player_contracts` | `is_playoff=True` slices only. |
| Streaks & Milestones | `player_streaks`, `milestone_snapshots` | Nightly snapshot. Tolerates stale reads. |
| Bracket Pick'em | `playoff_bracket` (computed), `picks_scoring_service` | localStorage-only, single-user. |
| Career HOF | `season_stats` (all seasons) | Era-adjusted PPG + TS%-vs-league delta. |

---

## 7. Schema Management

**Rule:** All schema changes land as Alembic revisions. No runtime startup DDL.

| Migration | Contents |
|-----------|----------|
| `0001` – `0012` | Historical: warehouse tables, PBP indexes, enrichment queue, team splits, splits index |
| `0013_sprint78_phase0_schemas` | 8 new Front Office + Casual Fan tables (player_contracts, draft_prospects family, draft_pick_assets, player_injury_history, player_streaks, milestone_snapshots) |
| `0014_sprint79_playoff_pbp_indexes` | `ix_lineup_stats_playoff_team`, `ix_player_on_off_playoff`, NULL backfills for `is_playoff` |
| `0015_sprint79_role_expansion` | `role_expansion_observations` table |
| `0016_sprint79_award_voting` | `award_voting` table |
| `0017_sprint80_raw_payload_ttl` | TTL `raw_game_payloads` rows older than 30 days (freed 184 MB) |
| `0018_sprint81_drop_legacy_pbp` | **Sprint 81.** Drop legacy `play_by_play` table (frees ~677 MB). |
| `0019_sprint81_award_case_candidates` | **Sprint 81.** `award_case_candidates` table for `mvp_case_v5` calibration. |
| `0020_sprint81_player_splits_play_types` | **Sprint 81.** `player_split_stats` + `play_type_stats` tables. |

**Head revision:** `0020_sprint81_player_splits_play_types`

**Run migrations:**
```bash
source ~/.bip-env
cd backend && python -m alembic upgrade head
```

---

## 8. Migration Status: Legacy → Warehouse

| Item | Status |
|------|--------|
| Warehouse as game registry (`warehouse_games`) | Done |
| Warehouse box scores (`game_team_stats`, `game_player_stats`) | Done |
| Warehouse PBP events (`play_by_play_events`) | Done |
| Warehouse-fed season aggregates (`season_stats`) | Partial (warehouse materializes into it) |
| `play_by_play` legacy table retirement | **Done (Sprint 81)** — all 11+ readers migrated, table dropped, CI guard locks in retirement |
| `game_logs` legacy table retirement | **Sprint 81** — route reads to `warehouse_games` |
| `player_game_logs` → `game_player_stats` | Future |
| Standings from materialized table | Done (Sprint 26) |
| Shot charts persisted to DB | Done (Sprint 26) |
| Injuries as first-class domain | Done (Sprint 26) |
| DB-first profile / career / gamelog reads | Done (Sprint 30) |
| Alembic as canonical schema workflow | Done (Sprint 43) |
| `raw_game_payloads` TTL cleanup | Done (Sprint 80) |
| DB + cron off the laptop | **Done (Sprint 80)** |

---

## 9. Sprint 82+ Roadmap (Infrastructure / Data)

| Item | Notes |
|------|-------|
| Frontend rendering for `player_splits` + `play_types` | Endpoints shipped in Sprint 81; UI components deferred. |
| FastAPI public deploy | Render / Railway / fly.io — same `DATABASE_URL` env-var pattern, no code changes. |
| Frontend public deploy (Vercel + Cloudflare) | `NEXT_PUBLIC_API_URL` → hosted FastAPI URL. |
| Custom domain (courtvuelabs.com) | Cloudflare DNS, SSL termination. |
| Tracking / hustle / passing dashboards | Deferred from Sprint 81 to keep scope sane. |
| Cloudscraper / Playwright fallback for Spotrac | Only if Sprint 81's basic scraper fails repeatedly in production. |
| `game_logs` legacy table retirement | Lower urgency than `play_by_play`; needs separate audit pass. |
| `player_game_logs` → `game_player_stats` migration | Not blocking. |
| DPOY / MIP / 6MOY award calibration | Same code path as MVP — extend `award_voting` seed to other award types. |
| Hetzner logical replication read replica | Only if >200ms p95 query latency becomes problematic. |
| Postgres 17 upgrade | In-place via `pg_upgrade`, ~30 min downtime. |
| VM → CX32 upgrade | One-click in Hetzner console when DB exceeds 30 GB. |
