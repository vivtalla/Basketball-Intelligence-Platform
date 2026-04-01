# Sprint 26 Closeout — Data Foundation Maturation

**Branch:** `feature/sprint-26-data-foundation` → merged to `master`
**Merge commit:** `689b2ae`
**Dates:** 2026-03-31

---

## What Shipped

### Deliverable 1: Architecture Document
- `specs/data-architecture.md` — full ingestion lineage map, canonical table designations, legacy deprecation markers, missing domain registry, hosting model and schema management notes
- Written contract that future sprints can reference before touching the data layer

### Deliverable 2: Injuries Ingestion (new data domain)
- `PlayerInjury` ORM model → `player_injuries` table (UNIQUE on `player_id, report_date`)
- `get_injuries_payload()` in `nba_client.py` — CDN fetch for `liveData/injuries/injuries.json`
- `sync_injuries(db, season)` in `sync_service.py` — upserts current injury rows, resolves NBA PersonID → our player.id
- `backend/routers/injuries.py` — `GET /api/injuries/current`, `GET /api/injuries/player/{id}`, `POST /api/injuries/sync`
- `sync_injuries` dispatch in `warehouse_service.py` job table
- `PlayerHeader.tsx` — injury status badge (Out=red, Questionable/Doubtful=orange) using SWR + `getPlayerInjuries()`
- `frontend/src/lib/types.ts` — `InjuryEntry`, `InjuryReportResponse` interfaces
- `frontend/src/lib/api.ts` — `getCurrentInjuries()`, `getPlayerInjuries()` functions

### Deliverable 3: Shot Chart Persistence
- `PlayerShotChart` ORM model → `player_shot_charts` table (UNIQUE on `player_id, season, season_type`)
- `backend/routers/shotchart.py` — DB-first pattern: check `player_shot_charts` for non-expired row; on miss call `nba_api`, persist with TTL from `_cache_ttl_for_season()` (6h current, 30d historical)
- Non-fatal persistence: rolls back on DB error, returns data anyway; returns stale cache if API fails

### Deliverable 4: Standings Materialization
- `TeamStanding` ORM model → `team_standings` table (UNIQUE on `team_id, season`)
- `backend/services/standings_service.py` — `compute_standings_data()` (core computation) + `materialize_standings()` (upserts to DB)
- `backend/routers/standings.py` — reads `team_standings` first, falls back to live computation if empty
- `backend/data/daily_sync.sh` — three-step script: warehouse jobs → injuries sync → standings materialization

---

## Verified

- `python -m db.ensure_schema` → all 3 new tables confirmed in DB
- `materialize_standings('2024-25')` → 30 teams upserted successfully
- All injury routes registered: `/api/injuries/current`, `/api/injuries/player/{id}`, `/api/injuries/sync`
- ESLint clean on frontend
- Note: `sync_injuries` CDN returns 403 from local IP — same CDN restriction as box scores, expected behavior, will work in hosted env

---

## Deferred (not in scope)

- Full legacy → warehouse migration (too risky, future sprint)
- Alembic setup (separate initiative)
- External metrics automation (licensing constraints)
- Upcoming schedule endpoint (fast follow-on after standings)
- PlayerGameLog → GamePlayerStat router migration (defer until warehouse coverage verified complete)

---

## Next-Sprint Seeds

- Upcoming schedule endpoint: `warehouse_games` has future games, expose via `GET /api/schedule/upcoming`
- Injury-aware player cards: surface return timelines on team pages, not just player profiles
- Shot chart analytics: with shots now in PG, query league-wide shot distributions, zone efficiency, etc.
- Standing delta cards: show week-over-week standing movement using the materialized history
- Warehouse coverage audit: identify which games still lack `has_parsed_pbp = True` and backfill priority

---

## Workflow Notes

- Python 3.8 `Optional[X]` / `List[X]` from `typing` — no union syntax, no list subscripting
- Read shared files before editing (warehouse_service.py edit blocked until read)
- Commit messages should not include Co-Authored-By attribution
- `cdn.nba.com/liveData/*` 403 from local IP is expected; test by running ensure_schema + unit-level imports, not live CDN calls
