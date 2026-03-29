# Sprint 11 Closeout

**Sprint:** 11
**Goal:** Warehouse data foundation — ingestion pipeline, schema migration, PBP rework, coverage dashboard
**Closed:** 2026-03-29

---

## What Shipped

### Codex — Warehouse Foundation (Phase 1) — PR #7, merged
- **8 new ORM models** in `db/models.py`: `SourceRun`, `IngestionJob`, `RawSchedulePayload`, `WarehouseGame`, `RawGamePayload`, `GameTeamStat`, `GamePlayerStat`, `PlayByPlayEvent`
- **CDN fetch adapters** in `nba_client.py`: `get_schedule_payload_for_season`, `get_game_box_score_payload`, `get_play_by_play_payload` — all use `cdn.nba.com`
- **`warehouse_service.py`** (1,300 lines): full idempotent job pipeline — `sync_schedule`, `sync_game_boxscore`, `sync_game_pbp`, `materialize_game_stats`, `materialize_season_aggregates`, `rematerialize_pbp_derived_metrics`, job queue, backfill, health inspection
- **`routers/warehouse.py`**: admin endpoints for queue, manual sync, season/game health, job listing
- **`models/warehouse.py`**: Pydantic response schemas
- **`advanced.py`**: PBP coverage queries repointed to `WarehouseGame` completeness flags

### Codex — Canonical PBP Pipeline (Phase 2) — pushed to master
- **`ensure_schema.py`**: updated to pick up all 8 new warehouse tables via `create_all()`; comment documents no new columns on existing tables in this sprint
- **`pbp_service.py`**: added `load_pbp_events_for_game()` — reads from `PlayByPlayEvent` (canonical) with fallback to legacy `PlayByPlay` during migration window; fixed `list[dict]` / `set[int]` / `dict[str,int]` → `List`/`Set`/`Dict` from `typing` throughout (Python 3.8 compliance)
- **`warehouse_service.py`**: wired `load_pbp_events_for_game()` into `rematerialize_pbp_derived_metrics`; `_claim_next_job` now accepts optional `season` param for targeted dispatch
- **`warehouse_jobs.py`**: simplified to a season-scoped queue runner (`--season`, `--max-jobs`, `--bootstrap-backfill`); removes redundant subcommands in favor of the HTTP API for one-off operations

### Claude — Coverage Dashboard — PR #8, merged
- **`WarehousePipelinePanel` component**: 5-step pipeline funnel (Scheduled → Box Score → PBP Payload → Parsed PBP → Materialized), per-step count/total with color coding; job queue stat cards (pending/running/failed); action buttons — "Run Next Job (global)", "Sync Today" (current season only), "Queue Backfill"; collapsible recent runs table; loading skeleton; empty-state prompt with backfill trigger
- **`coverage/page.tsx`**: panel inserted between stat cards and team/player tables
- **`types.ts`**: `SourceRunResponse`, `IngestionJobResponse`, `WarehouseSeasonHealth`, `WarehouseGameHealth` interfaces
- **`api.ts`**: `getWarehouseSeasonHealth`, `getWarehouseJobs`, `queueSeasonBackfill`, `queueCurrentSeason`, `runNextWarehouseJob`
- **`usePlayerStats.ts`**: `useWarehouseSeasonHealth`, `useWarehouseJobs` SWR hooks

### Process — Shipped this sprint
- **Cross-Agent Review section** added to `AGENTS.md` — convention-violation checklist (Python 3.8, schema, CDN, lock table, router registration) run before each PR merges
- First sprint where cross-agent review caught real issues: Python 3.8 `list[dict]` annotations in Phase 1 code, and two frontend UX bugs (global queue mislabeled as season-local; "Sync Today" shown for historical seasons)

---

## What Was Deferred

- `sync_game_pbp` writing to `PlayByPlayEvent` in the primary sync path — Phase 2 wired the PBP loader to read from canonical events but the write path (`sync_game_pbp` in `warehouse_service.py`) still writes to legacy `play_by_play`. Games synced via the warehouse jobs runner will use canonical events; games previously synced via the old PBP import pipeline still fall back to legacy.
- On/off and lineup derivation still consumes legacy `PlayByPlay` for games not yet migrated to canonical events — the fallback in `load_pbp_events_for_game` bridges this but a full migration pass has not been run.
- No daily cron/scheduler wiring — the job runner CLI (`warehouse_jobs.py`) must be invoked manually or via external cron.

---

## Coordination Lessons

- **Cross-agent review worked.** The checklist caught Python 3.8 annotation regressions before merge and two UX bugs post-merge. Keep it; tighten it if new recurring violation patterns emerge.
- **Codex committing directly to master (Phase 2)** skipped the branch isolation rule. The code was sound, but it meant Claude's cross-agent review happened after the fact rather than before merge. For large backend changes (>100 lines) enforce the branch rule regardless of confidence.
- **The "blocked on Phase 1 merge" dependency** worked cleanly — Claude developed the frontend against the committed API contracts and integration was seamless.

---

## Technical Lessons

- `_claim_next_job` with `Optional[str] season` was added in Phase 2 but the HTTP `/run-next` endpoint doesn't expose a `?season=` query param yet. If the frontend ever needs true season-scoped dispatch (not just relabeling), the router needs a one-liner addition.
- `ensure_schema.py` comment pattern ("No new columns in Sprint N") is worth keeping — makes it fast to audit what each sprint changed at the schema level.

---

## Next Sprint Seeds

- **Run the first real backfill** — `python data/warehouse_jobs.py --season 2024-25 --bootstrap-backfill --max-jobs 200` to populate `WarehouseGame` and prove the pipeline end-to-end
- **Wire `sync_game_pbp` write path to `PlayByPlayEvent`** — complete the canonical write so all new syncs land in the warehouse table, not legacy
- **Season-scoped `/run-next` endpoint** — add `?season=` query param to `/api/warehouse/run-next` and thread it through the frontend button
- **Daily cron** — automate `warehouse_jobs.py --season 2024-25` to run nightly for current-season freshness
- **Game Explorer controls** (carried from Sprint 10) — Codex's `codex-sprint-10-game-explorer-controls` branch is still open
