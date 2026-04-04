# Sprint 35 Shot Lab Runbook

**Purpose:** Official local workflow for finishing the live shot-lab backfill and review steps for Sprint 35 before merging PR #11.

## PR Target

- PR: `#11` — `[codex] shot lab expansion`
- Branch: `feature/sprint-35-shot-lab-expansion`
- Base: `master`

## Operational Reality

- The code path is verified by:
  - `pytest backend/tests`
  - `npm run lint`
  - `npm run build`
- The remaining risk is operational, not implementation-level:
  - historical shot-chart backfills still depend on `stats.nba.com`
  - long all-at-once runs are vulnerable to repeated timeouts
  - the right local pattern is controlled, one-lane-at-a-time execution with checkpointing

## Official Local Backfill Mode

Use **one season/type lane at a time** from `backend/`, and default to **non-force** first so successful rows are skipped on reruns.

Validated command shape:

```bash
python data/bulk_import.py --season 2025-26 --shot-charts --season-type "Regular Season"
python data/bulk_import.py --season 2025-26 --shot-charts --season-type "Playoffs"
python data/bulk_import.py --season 2024-25 --shot-charts --season-type "Regular Season"
python data/bulk_import.py --season 2024-25 --shot-charts --season-type "Playoffs"
python data/bulk_import.py --season 2023-24 --shot-charts --season-type "Regular Season"
python data/bulk_import.py --season 2023-24 --shot-charts --season-type "Playoffs"
python data/bulk_import.py --season 2022-23 --shot-charts --season-type "Regular Season"
python data/bulk_import.py --season 2022-23 --shot-charts --season-type "Playoffs"
```

Use `backend/data/backfill_shot_lab.sh` only after the lane-by-lane path proves stable enough for a longer unattended run.

## Controlled Sequence

1. Start with `2025-26` Regular Season.
2. Let the command run long enough to confirm:
   - eligible player count prints successfully
   - synced/skipped totals are climbing
   - failures are intermittent rather than immediate global blockage
3. If the lane completes, move to `2025-26` Playoffs.
4. Continue backward by season only after the current lane is stable.
5. Rerun incomplete lanes without `--force` first so completed players are skipped.
6. Use `--force` only for targeted repair passes after a lane has mostly landed.

## Stop Conditions

Stop the current lane and record the result if any of the following happen:

- repeated timeout warnings dominate the output for several consecutive players
- the command stalls without meaningful synced/skipped progress
- the endpoint appears blocked rather than merely slow
- the machine cannot be monitored during the run

If a lane is stopped manually, resume it later with the same command and no `--force`.

## What To Record Per Lane

For each season/type lane, capture:

- command run
- eligible player count
- final `synced / skipped / failed / total` summary if it completes
- whether the lane was interrupted due to timeouts
- whether a follow-up retry is still needed

Keep this in the PR thread or merge notes rather than relying on chat history.

## Manual QA Checklist

After at least the relevant `2025-26` data is in place:

1. Player page
   - open one active player with known shot volume
   - verify `ShotChart` responds to season, season-type, preset windows, and custom date range
   - verify empty-window messaging is distinct from missing-data messaging
   - verify `ShotSeasonEvolution` switches between Regular Season and Playoffs cleanly

2. Compare page
   - open two active players on `/compare`
   - verify `CompareShotLab` updates both sides together when season/type/window changes
   - verify value-map bubbles remain visually comparable side to side
   - verify distance-profile scaling feels synchronized
   - verify filtered `ShotProfileDuel` and `ZoneProfilePanel`s change with the shared window

3. Sanity checks
   - confirm no obvious raw-error rendering
   - confirm stale/missing badges still read sensibly
   - confirm pages still load with no selected custom date range

## Merge Gate

PR #11 is ready to merge when all of the following are true:

- automated validation remains green
- at least the primary current-season lane (`2025-26` Regular Season) has been backfilled to a usable level
- manual QA passes on player and compare shot-lab flows
- any remaining historical backfill work is documented explicitly as post-merge ops or fully completed

## Recommended Final Sequence

1. Run `2025-26` Regular Season lane.
2. Run `2025-26` Playoffs lane if the first lane is stable.
3. Perform manual QA on player + compare pages.
4. Update the PR with backfill/QA outcome.
5. Mark PR #11 ready for review or merge directly if that is the chosen workflow.
