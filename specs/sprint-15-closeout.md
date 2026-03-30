# Sprint 15 Closeout

**Sprint:** 15
**Date:** 2026-03-30
**Owner:** Shared
**Status:** Final

---

## Shipped

- Formalized Sprint 15 as a data-completion and warehouse-hardening sprint
- Merged the lineup/on-off idempotency hotfix so `rematerialize_pbp_derived_metrics()` safely updates existing `player_on_off` and `lineup_stats` rows during reruns
- Hardened raw payload persistence so duplicate `raw_game_payloads` inserts fall back cleanly on `IntegrityError` instead of failing repeated retries
- Made `reset_stale_jobs()` persist its queue changes from the service layer instead of depending on caller-side commit behavior
- Added Sprint 15 operational artifacts:
  - `specs/sprint-15-data-gap-inventory.md`
  - `specs/sprint-15-validation-matrix.md`
  - `specs/sprint-15-warehouse-runbook.md`
- Updated Sprint 15 planning to reflect the real source landscape for external metrics:
  - `RAPTOR` is the primary free external metric target
  - `RAPM` is optional if a clean public file is available
  - `EPM`, `LEBRON`, and `PIPM` are treated as source-gated / licensed-only rather than launch blockers

## Deferred / Not Finished

- `2025-26` warehouse/PBP completion remains an operational follow-through task rather than a finished code deliverable
- External metric imports were not completed because the free CSV source landscape is limited and no local files were available
- The Sprint 15 validation matrix was created, but not every launch-window page was fully validated inside this sprint closeout
- `warehouse_worker_pool.sh` remains secondary to attached workers in this environment; the runbook documents the supported local path instead of promoting the pool script

## Coordination Lessons

- A written page-to-data matrix made it much easier to separate true ingestion bugs from source gaps and product expectations
- Cross-agent review remained valuable even for mostly operational/backend work because it quickly confirmed Python 3.8 safety and contract consistency
- Keeping hotfixes small and merging them incrementally to `master` reduced risk while the live backfill work continued outside the git flow

## Technical Lessons

- Season-wide rematerialization needs idempotent writes at every unique-key boundary, not just retries at the job level
- Raw payload persistence also needs duplicate-safe behavior under worker retries; otherwise harmless duplicate fetches look like ingestion failures
- Free-data planning needs explicit source classification: recoverable from NBA/public feeds, recoverable from free CSVs, or licensed/manual only
- Operational docs are part of the product when the system depends on long-running local workers and restart/requeue workflows

## Next Sprint Seeds

- Finish operational validation of `2025-26` warehouse completeness and record final launch-window readiness by page
- Import `RAPTOR` and optionally `RAPM` if a clean public source is chosen
- Decide whether any remaining historical page gaps require selective warehouse backfill for `2022-23` / `2023-24`
- Promote or replace the local worker launcher only after it proves as reliable as the attached-worker path
