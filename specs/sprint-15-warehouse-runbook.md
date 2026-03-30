# Sprint 15 Warehouse Runbook

**Purpose:** Canonical local workflow for starting, pausing, resuming, and validating warehouse backfill during Sprint 15.

## Official Local Worker Mode

For this machine, the official supported mode is:

- attached long-running workers launched from `backend/venv`
- one worker for `2024-25`
- three workers for `2025-26`

The `warehouse_worker_pool.sh` script remains useful for reference and future verification, but attached workers are the canonical local path until the pool script is proven reliable in this environment.

## Start Commands

Run from `backend/` with `backend/venv`:

```bash
"/Users/viv/Documents/Basketball Intelligence Platform/backend/venv/bin/python" data/warehouse_jobs.py --season 2024-25 --max-jobs 5000
"/Users/viv/Documents/Basketball Intelligence Platform/backend/venv/bin/python" data/warehouse_jobs.py --season 2025-26 --max-jobs 5000
"/Users/viv/Documents/Basketball Intelligence Platform/backend/venv/bin/python" data/warehouse_jobs.py --season 2025-26 --max-jobs 5000
"/Users/viv/Documents/Basketball Intelligence Platform/backend/venv/bin/python" data/warehouse_jobs.py --season 2025-26 --max-jobs 5000
```

## Pause / Resume Workflow

### Pause

1. Stop the live `warehouse_jobs.py` worker processes.
2. Requeue any remaining `running` jobs for `2024-25` and `2025-26`.
3. Confirm no live loop workers remain.

### Resume

1. Requeue stale or paused `running` jobs before launching new workers.
2. Restart the attached workers using the official counts above.
3. Verify:
   - `running` matches live processes
   - `stalled_running_count = 0`
   - no immediate `failed` jobs appear

## Operational Checks

Use these checks before and after any restart:

- process list for live workers
- queued/running/complete/failed counts by season
- `stalled_running_count`
- recent failed jobs
- `global_request_throttle`

## Known Risks To Watch

- `2024-25`: season-level rematerialization deadlocks from aggressive parallel PBP work
- `2025-26`: duplicate raw payload inserts during retries
- stale leased jobs after pause/resume if workers are interrupted mid-run

## Sprint 15 Success Criteria For This Runbook

- restart flow does not leave misleading stale leases
- queue summaries match actual live worker counts
- `2024-25` remains healthy with no new failed jobs
- `2025-26` continues to climb without repeated duplicate-key failure loops
