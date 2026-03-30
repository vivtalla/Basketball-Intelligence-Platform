# Sprint 16 Warehouse Runbook

**Purpose:** Official local workflow for finishing the remaining warehouse-backed data work during Sprint 16.

## Official Local Worker Mode

For this machine, the supported local mode is now explicitly:

- attached long-running workers launched from the clean Sprint 16 worktree using `backend/venv`
- `2024-25` workers only on demand for targeted follow-up resyncs
- three workers for the active `2025-26` catch-up lane

Do **not** run the local recovery workers from the stale root checkout. The validated path is the clean worktree branch (`codex-sprint-16-data-foundation`) or current `master` once merged.

`warehouse_worker_pool.sh` remains non-canonical in this environment until it proves as reliable as the attached-worker path.

## Kickoff Baseline

- `2024-25`
  - `1230/1230/1230` box / parsed PBP / materialized
  - job state: `3692 complete`
- `2025-26`
  - `1119/579/1119` box / parsed PBP / materialized
  - job state: `1617 complete`, `1736 queued`

## Start Commands

Run from the clean worktree `backend/` using `backend/venv`:

```bash
"/Users/viv/Documents/Basketball Intelligence Platform/backend/venv/bin/python" data/warehouse_jobs.py --season 2025-26 --max-jobs 5000
"/Users/viv/Documents/Basketball Intelligence Platform/backend/venv/bin/python" data/warehouse_jobs.py --season 2025-26 --max-jobs 5000
"/Users/viv/Documents/Basketball Intelligence Platform/backend/venv/bin/python" data/warehouse_jobs.py --season 2025-26 --max-jobs 5000
```

## Pause / Resume Workflow

### Pause

1. Stop the live `warehouse_jobs.py` processes.
2. Requeue any remaining `running` jobs for the affected season(s).
3. Confirm there are no live worker processes left.

### Resume

1. Run `reset_stale_jobs()` for the affected season(s).
2. Run `retry_failed_jobs()` if the queue shows failed jobs that should be retried.
3. Restart workers using the official counts above.
3. Verify:
   - live process count matches `running` job counts
   - no immediate failed-job spike appears
   - stale-job reset leaves queue state consistent

## Required Operational Checks

- live worker process list
- queued / running / complete / failed counts by season
- parsed PBP / materialized counts for `2025-26`
- recent failed jobs
- duplicate-key or deadlock recurrence

## Sprint 16 Success Criteria

- `2024-25` stays healthy and complete
- `2025-26` current-season pages become warehouse-usable
- pause/resume/requeue behavior is repeatable and matches the runbook
- no recurring deadlock or duplicate-raw-payload failure loops reappear during normal catch-up
