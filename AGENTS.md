# Agent Coordination

Last updated: 2026-03-30 by Codex (Sprint 15 data completion kickoff)

> **Both agents read this file before touching any code at the start of every session.**
> Check sprint status, your branch, this sprint's work allocation, and the Merge Order.
> Then check the Handoff Queue. Then `git fetch origin`. Then begin work.
> All sprint implementation work happens on each agent's own branch or worktree, never directly on `master`; merge to `master` only after the sprint branch work is ready.
> At sprint close, create/update `specs/sprint-{NN}-closeout.md`, reset `AGENTS.md` for the next sprint, and update the matching sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field        | Value                                  |
|--------------|----------------------------------------|
| Sprint       | 15                                     |
| Goal         | Data completion and warehouse hardening for launch-window seasons (`2022-23` through `2025-26`) |
| Started      | 2026-03-30                             |
| Target merge | Rolling hotfix merges to `master`; sprint closes when launch-window data matrix is cleared or explicitly accepted |

Sprint 14 is closed. See `specs/sprint-14-closeout.md` for shipped work and next-sprint seeds.
Sprint 15 is a stabilization/data sprint. No new end-user feature scope should start until the data-gap matrix is cleared or explicitly accepted.

---

## Agent Assignments

### Claude
- Branch: `feature/sprint-15-data-validation`
- Scope: Page-by-page validation, frontend empty-state audit, documenting remaining data dependencies, small null/partial-data UI fixes only
- Status: Available / support role
- PR: —

### Codex
- Branch: `codex-sprint-15-data-completion`
- Scope: Warehouse worker lifecycle, queue cleanup and retry semantics, historical PBP repair, raw payload/rematerialization idempotency, data completeness instrumentation, external-metrics ingestion support
- Status: In progress
- PR: —

> ⚠️ **PERMANENT WARNING**: Do NOT use `codex-sprint-10-game-explorer-controls`. It is at a Sprint 9 commit and its diff against master deletes all warehouse infrastructure (2,700+ lines). It cannot be merged. It is dead.

---

## Shared File Lock Table

Claim a file here before writing a single line. If a file is already claimed, read that agent's branch before planning — do not edit a claimed file until their PR merges (then rebase), or until Vivek reassigns the claim.

`types.ts` and `api.ts` are **append-only** — add new interfaces/functions at the bottom only. Never edit lines written by the other agent.

`models.py` and `ensure_schema.py` are always claimed together.

| File                                                   | Claimed by | Purpose |
|--------------------------------------------------------|------------|---------|
| `backend/db/models.py`                                 | —          |         |
| `backend/db/ensure_schema.py`                          | —          |         |
| `backend/routers/warehouse.py`                         | Codex      | Queue operations, stale reset semantics, summary verification |
| `backend/services/warehouse_service.py`                | Codex      | Queue cleanup, retry semantics, rematerialization idempotency |
| `backend/data/warehouse_jobs.py`                       | Codex      | Worker execution mode and operational summaries |
| `backend/data/warehouse_worker_pool.sh`                | Codex      | Worker pool behavior / operational support |
| `backend/data/epm_rapm_import.py`                      | Codex      | External metrics ingestion support |
| `frontend/src/app/players/[playerId]/page.tsx`         | Claude     | Player-page validation follow-ups |
| `frontend/src/app/teams/[abbr]/page.tsx`               | Claude     | Team-page validation follow-ups |
| `frontend/src/app/leaderboards/page.tsx`               | Claude     | Empty-state and data-gap validation follow-ups |
| `frontend/src/app/coverage/page.tsx`                   | Claude     | Coverage-page validation follow-ups |
| `backend/main.py`                                      | —          |         |

---

## Handoff Queue

Specs written by one agent for the other. Check this before starting work — if a spec is marked "Ready" for you, read it before writing any code.

| Spec file | From | To | Status |
|-----------|------|----|--------|

---

## Merge Order (this sprint)

1. `codex-sprint-15-data-completion` (Codex — backend/data hardening first)
2. `feature/sprint-15-data-validation` (Claude — validation and UI follow-ups after backend/data artifacts exist)
3. Optional closeout/docs-only branch if needed

---

## Sprint Work Allocation

Ownership is sprint-dependent, not permanent. The table below is rewritten each sprint to show who is currently driving which areas.

### This sprint's owned areas

| Files / Directories                                    | Assigned this sprint |
|--------------------------------------------------------|----------------------|
| `backend/services/warehouse_service.py`                | Codex                |
| `backend/routers/warehouse.py`                         | Codex                |
| `backend/data/warehouse_jobs.py`                       | Codex                |
| `backend/data/warehouse_worker_pool.sh`                | Codex                |
| `backend/data/epm_rapm_import.py`                      | Codex                |
| `frontend` validation / empty-state follow-ups         | Claude               |

### Shared files — claim in Lock Table before editing

- `backend/db/models.py` + `backend/db/ensure_schema.py` (always claimed together)
- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `backend/main.py`

---

## Session Start Checklist

```
1. Read this file — sprint number, my branch, this sprint's work allocation, Merge Order
2. Confirm I am on my assigned sprint branch or isolated worktree — do not implement on `master`
3. Check Lock Table — if the other agent claimed a file I need, read their branch first
4. Check Handoff Queue — if a spec is "Ready" for me, read it before writing code
5. git fetch origin && git log origin/master --oneline -5 — rebase if master advanced
6. Update my status row if it changed, commit: "docs: update [Claude|Codex] status in AGENTS.md"
7. Begin work
```

---

## Branch Isolation Rule

- Every sprint task is implemented on the agent's assigned sprint branch, not on `master`
- If the current checkout is on another agent's branch or has their local changes, create your own branch/worktree before editing code
- `master` is the integration branch only; it should receive completed sprint work via merge or explicit final push after the branch work is done
- When `AGENTS.md` lists a branch for an agent, that branch is the source of truth for where their sprint work belongs

## Work Allocation Rule

- File and directory ownership is decided per sprint, not as a permanent project rule
- Rewrite the Sprint Work Allocation table at sprint kickoff to match the current plan and active agents
- If more agents are added, extend the current sprint table rather than creating permanent per-agent territories
- If a task needs to move mid-sprint, update this file first so ownership changes are explicit before code changes begin

---

## Sprint Closeout Checklist

```
1. Confirm what actually landed in `master`
2. Create or update `specs/sprint-{NN}-closeout.md` with shipped work, deferred work, coordination lessons, technical lessons, and next-sprint seeds
3. Clean `AGENTS.md` for the next sprint kickoff state (status, locks, merge order, notes)
4. Update the matching sprint summary in `CLAUDE.md`
5. Leave the next sprint kickoff readable from `AGENTS.md` + latest closeout note + `CLAUDE.md`
```

---

## Cross-Agent Review

Before either agent's branch merges to `master`, the *other* agent should do a quick spot-check of the diff. This is not a logic review — Vivek owns that. The goal is catching convention violations that are fast to check and easy to miss in a diff.

**Checklist:**
- [ ] Python 3.8 compatibility — no `list[X]` / `dict[X, Y]` subscript annotations, no `X | Y` union syntax; use `List[X]`, `Dict[X, Y]`, `Optional[X]` from `typing`
- [ ] Schema changes go through `ensure_schema.py` — no raw DDL, no Alembic
- [ ] No direct `stats.nba.com` calls — use `cdn.nba.com` or the `nba_client.py` wrapper
- [ ] Shared files (`models.py`, `ensure_schema.py`, `main.py`, `types.ts`, `api.ts`) were claimed in the Lock Table before editing
- [ ] New FastAPI routers are registered in `main.py`
- [ ] New ORM models have a corresponding `ensure_column_exists()` call in `ensure_schema.py` for any new columns on existing tables

**How:** Read the PR diff (or `git diff master...branch`) and tick the checklist. Add a note in the Handoff Queue or AGENTS.md Notes if anything needs fixing before merge.

---

## Branch Naming Convention

| Agent | Format | Example |
|-------|--------|---------|
| Claude | `feature/sprint-N-{slug}` | `feature/sprint-9-player-contracts` |
| Codex | `codex-sprint-N-{slug}` | `codex-sprint-9-team-sync-v2` |

Sprint number prefix makes `git branch -a` immediately readable.

---

## Notes

*Free-form, dated, newest first. For cross-agent communication mid-sprint.*

2026-03-30 (Codex): Sprint 15 formalized as a data-completion sprint. Primary deliverables: finish `2025-26` warehouse/PBP, complete historical `2022-23` / `2023-24` legacy-plus-derived coverage, harden queue restart/reset behavior, import external metrics, and maintain a written page-to-data gap matrix until launch-window seasons are complete.
2026-03-30 (Codex): `codex-sprint-15-lineup-idempotency` merged to `master` as a Sprint 15 hotfix. `rematerialize_pbp_derived_metrics()` now updates existing `player_on_off` / `lineup_stats` rows instead of relying on unique-key inserts during reruns.
2026-03-30 (Codex): Sprint 15 started on `codex-sprint-15-onoff-deadlock` to fix `player_on_off` deadlocks during parallel `sync_game_pbp` jobs and safely replay the failed 2024-25 jobs.
2026-03-30 (Codex): Sprint 14 closed. Warehouse-backed game summary endpoint and Game Explorer box score UI are now on master. See `specs/sprint-14-closeout.md`.
2026-03-30 (Codex): Sprint 14 started on `codex-sprint-14-data-layer`. Current scope: warehouse-backed game summary endpoint for Game Explorer plus the small `warehouse_jobs.py` SIGTERM fix.
2026-03-30 (Claude): Sprint 13 closed. Codex shipped full scope solo (Claude token-limited). Warehouse reliability: distributed throttle, worker pool script, reset-stale + job-summary endpoints, auto-poll panel. YoY callouts on player + team pages. Game Explorer drill-down. Sprint 14 seeds: SIGTERM fix, coverage memo fix, pipeline metrics, game summary API.
