# Agent Coordination

Last updated: 2026-03-30 by Codex (Sprint 13 kickoff)

> **Both agents read this file before touching any code at the start of every session.**
> Check sprint status, your branch, this sprint's work allocation, and the Merge Order.
> Then check the Handoff Queue. Then `git fetch origin`. Then begin work.
> All sprint implementation work happens on each agent's own branch or worktree, never directly on `master`; merge to `master` only after the sprint branch work is ready.
> At sprint close, create/update `specs/sprint-{NN}-closeout.md`, reset `AGENTS.md` for the next sprint, and update the matching sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field        | Value                                  |
|--------------|----------------------------------------|
| Sprint       | 13                                     |
| Goal         | Warehouse reliability hardening — shared rate limiting, worker observability, long-running queue runner |
| Started      | 2026-03-30                             |
| Target merge | TBD                                    |

Sprint 12 is closed. See `specs/sprint-12-closeout.md` for shipped work and next-sprint seeds.

---

## Agent Assignments

### Claude
- Branch: TBD
- Scope: TBD
- Status: Idle — awaiting Sprint 13 kickoff
- PR: —

### Codex
- Branch: `codex-sprint-13-warehouse-reliability`
- Scope: Shared NBA request throttle, warehouse queue observability, long-running worker mode
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
| `backend/db/models.py`                                 | Codex      | Shared throttle state table / schema support |
| `backend/db/ensure_schema.py`                          | Codex      | Shared throttle state table / schema support |
| `backend/routers/warehouse.py`                         | Codex      | Operational warehouse summary endpoint |
| `backend/services/warehouse_service.py`                | Codex      | Queue summary helpers / reliability support |
| `frontend/src/lib/types.ts`                            | —          |         |
| `frontend/src/lib/api.ts`                              | —          |         |
| `frontend/src/components/WarehousePipelinePanel.tsx`   | —          |         |
| `backend/main.py`                                      | —          |         |

---

## Handoff Queue

Specs written by one agent for the other. Check this before starting work — if a spec is marked "Ready" for you, read it before writing any code.

| Spec file | From | To | Status |
|-----------|------|----|--------|

---

## Merge Order (this sprint)

1. `codex-sprint-13-warehouse-reliability` (Codex) — backend reliability hardening

---

## Sprint Work Allocation

Ownership is sprint-dependent, not permanent. The table below is rewritten each sprint to show who is currently driving which areas.

### This sprint's owned areas

| Files / Directories                                    | Assigned this sprint |
|--------------------------------------------------------|----------------------|
| `backend/data/nba_client.py`                           | Codex                |
| `backend/data/warehouse_jobs.py`                       | Codex                |
| `backend/db/models.py`                                 | Codex                |
| `backend/db/ensure_schema.py`                          | Codex                |
| `backend/services/warehouse_service.py`                | Codex                |
| `backend/routers/warehouse.py`                         | Codex                |

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

2026-03-30 (Claude): Sprint 12 closed. All branches merged to master. See `specs/sprint-12-closeout.md`. Warehouse is now fully operational with retry/backoff, season-scoped dispatch, daily cron, and a hardened frontend panel. Sprint 13 seeds: YoY trend indicators, warehouse auto-poll, Game Explorer PBP drill-down.
2026-03-30 (Codex): Sprint 13 started on `codex-sprint-13-warehouse-reliability`. Current focus: shared NBA request throttling across workers, better warehouse job summaries, and a loop mode for long-running queue workers.
