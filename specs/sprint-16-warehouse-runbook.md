# Sprint 16 Warehouse Runbook

**Purpose:** Official local workflow for finishing the remaining warehouse-backed data work during Sprint 16.

## Official Local Worker Mode

For this machine, the supported local mode remains:

- attached long-running workers launched from `backend/venv`
- one worker for `2024-25`
- three workers for `2025-26`

`warehouse_worker_pool.sh` remains non-canonical in this environment until it proves as reliable as the attached-worker path.

## Kickoff Baseline

- `2024-25`
  - `1230/1230/1230` box / parsed PBP / materialized
  - job state: `2441 complete`, `1 running`, `1250 queued`
- `2025-26`
  - `1119/501/1119` box / parsed PBP / materialized
  - job state: `1563 complete`, `4 running`, `1792 queued`

## Start Commands

Run from `backend/` using `backend/venv`:

```bash
"/Users/viv/Documents/Basketball Intelligence Platform/backend/venv/bin/python" data/warehouse_jobs.py --season 2024-25 --max-jobs 5000
"/Users/viv/Documents/Basketball Intelligence Platform/backend/venv/bin/python" data/warehouse_jobs.py --season 2025-26 --max-jobs 5000
"/Users/viv/Documents/Basketball Intelligence Platform/backend/venv/bin/python" data/warehouse_jobs.py --season 2025-26 --max-jobs 5000
"/Users/viv/Documents/Basketball Intelligence Platform/backend/venv/bin/python" data/warehouse_jobs.py --season 2025-26 --max-jobs 5000
```

## Pause / Resume Workflow

### Pause

1. Stop the live `warehouse_jobs.py` processes.
2. Requeue any remaining `running` jobs for `2024-25` and `2025-26`.
3. Confirm there are no live worker processes left.

### Resume

1. Requeue stale or paused `running` jobs before launching new workers.
2. Restart workers using the official counts above.
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
