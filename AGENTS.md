# Agent Coordination

Last updated: 2026-03-29 by Codex (Sprint 12 Game Explorer kickoff)

> **Both agents read this file before touching any code at the start of every session.**
> Check sprint status, your branch, this sprint's work allocation, and the Merge Order.
> Then check the Handoff Queue. Then `git fetch origin`. Then begin work.
> All sprint implementation work happens on each agent's own branch or worktree, never directly on `master`; merge to `master` only after the sprint branch work is ready.
> At sprint close, create/update `specs/sprint-{NN}-closeout.md`, reset `AGENTS.md` for the next sprint, and update the matching sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field        | Value                                                                 |
|--------------|-----------------------------------------------------------------------|
| Sprint       | 12                                                                    |
| Goal         | Warehouse completion — retry/backoff, season-scoped dispatch, daily cron, frontend hardening |
| Started      | 2026-03-29                                                            |
| Target merge | TBD                                                                   |

---

## Agent Assignments

### Claude
- Branch: `feature/sprint-12-warehouse-frontend`
- Scope: Season-scoped Run Next Job button, Retry Failed button + endpoint call, failed job details panel
- Status: Paused — session limit reached before frontend follow-up
- PR: —
- Blocked on: nothing

### Codex
- Branch: `codex-sprint-12-warehouse-ops`
- Scope: Season-scoped `/run-next` endpoint, retry/backoff logic in `run_next_job`, `retry_failed_jobs()` service + `/retry-failed` endpoint, `daily_sync.sh` cron script
- Optional second branch: `codex-sprint-12-game-explorer` (Game Explorer rebuild — only if warehouse-ops scope allows)
- Status: Warehouse ops complete on `codex-sprint-12-warehouse-ops`; Game Explorer rebuild in progress on `codex-sprint-12-game-explorer`
- PR: —
- Blocked on: nothing

> ⚠️ **IMPORTANT FOR CODEX**: Do NOT use or reference the `codex-sprint-10-game-explorer-controls` branch. It is at a Sprint 9 commit and its diff against master deletes all warehouse infrastructure (2,700+ lines including warehouse_service.py, warehouse.py router, warehouse_jobs.py). It cannot be merged. If building Game Explorer features, create `codex-sprint-12-game-explorer` fresh from current master.

---

## Shared File Lock Table

Claim a file here before writing a single line. If a file is already claimed, read that agent's branch before planning — do not edit a claimed file until their PR merges (then rebase), or until Vivek reassigns the claim.

`types.ts` and `api.ts` are **append-only** — add new interfaces/functions at the bottom only. Never edit lines written by the other agent.

`models.py` and `ensure_schema.py` are always claimed together.

| File                                                   | Claimed by | Purpose                                              |
|--------------------------------------------------------|------------|------------------------------------------------------|
| `backend/db/models.py`                                 | —          |                                                      |
| `backend/db/ensure_schema.py`                          | —          |                                                      |
| `backend/routers/warehouse.py`                         | Codex      | Season-scoped /run-next, /retry-failed endpoint      |
| `backend/services/warehouse_service.py`                | Codex      | retry_failed_jobs(), backoff logic in run_next_job   |
| `backend/data/daily_sync.sh`                           | Codex      | Daily warehouse cron wrapper                         |
| `frontend/src/app/games/[gameId]/page.tsx`             | Codex      | Game Explorer controls rebuild                       |
| `frontend/src/lib/types.ts`                            | —          |                                                      |
| `frontend/src/lib/api.ts`                              | Claude     | retryFailedJobs(), runNextWarehouseJob(season?)      |
| `frontend/src/components/WarehousePipelinePanel.tsx`   | Claude     | Retry Failed button, season-scoped run-next          |
| `backend/main.py`                                      | —          |                                                      |

---

## Handoff Queue

Specs written by one agent for the other. Check this before starting work — if a spec is marked "Ready" for you, read it before writing any code.

| Spec file | From | To | Status |
|-----------|------|----|--------|

---

## Merge Order (this sprint)

```
1. codex-sprint-12-warehouse-ops          (Codex) — backend first; Claude reviews before merge
2. feature/sprint-12-warehouse-frontend   (Claude) — depends on /retry-failed endpoint; Codex reviews before merge
3. codex-sprint-12-game-explorer          (Codex, optional) — independent; can merge in any order
```

---

## Sprint Work Allocation

Ownership is sprint-dependent, not permanent. The table below is rewritten each sprint to show who is currently driving which areas.

### This sprint's owned areas

| Files / Directories                                    | Assigned this sprint |
|--------------------------------------------------------|----------------------|
| `backend/routers/warehouse.py`                         | Codex                |
| `backend/services/warehouse_service.py`                | Codex                |
| `backend/data/daily_sync.sh` (new)                     | Codex                |
| `frontend/src/app/games/[gameId]/page.tsx`             | Codex                |
| `frontend/src/lib/api.ts`                              | Claude               |
| `frontend/src/components/WarehousePipelinePanel.tsx`   | Claude               |

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

2026-03-29 (Codex): Optional Game Explorer rebuild started on fresh branch `codex-sprint-12-game-explorer` from current `origin/master`. Unsafe Sprint 10 branch is not being used.

2026-03-29 (Codex): Warehouse ops backend completed on `codex-sprint-12-warehouse-ops` with season-scoped `/run-next`, retry/backoff, `/retry-failed`, and `daily_sync.sh`.

2026-03-29 (Claude): Sprint 12 kicked off. Codex owns warehouse-ops backend (retry logic, season-scoped /run-next, /retry-failed, cron). Claude owns frontend hardening (season-scoped button, retry failed UI) — blocked on Codex's /retry-failed endpoint. Game Explorer branch is UNSAFE to merge — must rebuild from master if pursued this sprint.

2026-03-29 (Claude): Sprint 11 closed. Warehouse foundation shipped across two Codex phases + Claude coverage dashboard. See `specs/sprint-11-closeout.md`. Deferred to Sprint 12: season-scoped /run-next endpoint, daily cron, retry logic, Game Explorer controls (carry from Sprint 10).
