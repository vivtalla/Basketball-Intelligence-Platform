# Sprint 11 Closeout

**Sprint:** 11
**Date:** 2026-03-29
**Owner:** Shared (Claude + Codex)
**Status:** Final

---

## Shipped

**Codex — Warehouse ingestion foundation (`codex-sprint-11-warehouse-foundation` → PR #7):**
- ORM models: SourceRun, IngestionJob, RawSchedulePayload, WarehouseGame, RawGamePayload, GameTeamStat, GamePlayerStat, PlayByPlayEvent
- `ensure_schema.py` updated to create all new tables and columns
- `warehouse_service.py`: idempotent job pipeline, `WarehouseGame` completeness flags (has_box_score, has_pbp_payload, has_parsed_pbp, materialized)
- `warehouse_jobs.py` CLI: `--season`, `--max-jobs`, `--dry-run` flags
- `warehouse.py` router: `/health/{season}`, `/jobs`, `/queue/season-backfill`, `/queue/current-season`, `/run-next`
- Reworked canonical PBP pipeline to write `PlayByPlayEvent` (warehouse model)

**Claude — Coverage dashboard frontend (`feature/sprint-11-coverage-dashboard` → closed, carried into PR #9):**
- `types.ts`: SourceRunResponse, IngestionJobResponse, WarehouseSeasonHealth, WarehouseGameHealth interfaces
- `api.ts`: getWarehouseSeasonHealth, getWarehouseJobs, queueSeasonBackfill, queueCurrentSeason, runNextWarehouseJob
- `usePlayerStats.ts`: useWarehouseSeasonHealth, useWarehouseJobs SWR hooks
- `WarehousePipelinePanel`: pipeline funnel display, job queue stat cards, action buttons, collapsible recent runs table
- `coverage/page.tsx`: integrates WarehousePipelinePanel

## Deferred / Not Finished

- Season-scoped `/run-next` endpoint (backend passed global queue only)
- Retry/backoff logic for failed jobs
- Daily cron script
- Retry Failed UI button → deferred to Sprint 12

## Coordination Lessons

- Sprint 11 Claude frontend branch (PR #8) was not merged before Sprint 12 branched; Sprint 12 had to carry all Sprint 11 frontend work forward. Prefer merging promptly rather than letting open PRs accumulate across sprints.
- Cross-agent code review caught two real issues in the Sprint 11 panel (global "Run Next Job" label, Sync Today shown for historical seasons). Checklist process validated.

## Technical Lessons

- `codex-sprint-10-game-explorer-controls` was identified as unsafe (Sprint 9 commit base, deletes 2,700+ warehouse lines if merged). Added permanent warning to AGENTS.md.
- Three-layer warehouse model (raw payloads → normalized facts → derived analytics) with idempotent jobs and completeness flags on WarehouseGame is the correct foundation for reliable ingestion.

## Next Sprint Seeds

- Season-scoped `/run-next` endpoint (backend already supported it, just needed HTTP wiring)
- Retry/backoff for failed jobs (exponential: 5m/10m/15m, permanent fail at attempt_count ≥ 3)
- Daily cron via `daily_sync.sh`
- Retry Failed button in WarehousePipelinePanel
- Game Explorer controls rebuild (from fresh branch, not Sprint 10 branch)
