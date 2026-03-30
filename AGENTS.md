# Agent Coordination

Last updated: 2026-03-30 by Codex (Sprint 16 kickoff)

> **Both agents read this file before touching any code at the start of every session.**
> Check sprint status, your branch, this sprint's work allocation, and the Merge Order.
> Then check the Handoff Queue. Then `git fetch origin`. Then begin work.
> All sprint implementation work happens on each agent's own branch or worktree, never directly on `master`; merge to `master` only after the sprint branch work is ready.
> At sprint close, create/update `specs/sprint-{NN}-closeout.md`, reset `AGENTS.md` for the next sprint, and update the matching sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field        | Value |
|--------------|-------|
| Sprint       | 16 |
| Goal         | Data foundation closeout for the current app |
| Started      | 2026-03-30 |
| Target merge | Rolling merges as data-hardening and validation branches become ready |

Sprint 15 is closed. See `specs/sprint-15-closeout.md`.
Sprint 16 closes the remaining data-foundation work for the launch window (`2022-23` through `2025-26`).
All external metrics are explicitly out of scope for this sprint.

---

## Agent Assignments

### Claude
- Branch: `feature/sprint-16-data-validation`
- Scope: Page-by-page validation, null/partial-data UI hardening, misleading empty-state cleanup, accepted-scope-limit documentation
- Status: Not started
- PR: —
- Blocked on: nothing

### Codex
- Branch: `codex-sprint-16-data-foundation`
- Scope: `2025-26` warehouse completion, worker lifecycle/runbook hardening, queue-state verification, page-blocking data bug fixes, selective historical support only if validation proves necessary
- Status: In progress
- PR: —
- Blocked on: nothing

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
| `backend/services/warehouse_service.py`                | Codex      | Data bug fixes, queue/state hardening, warehouse hotfixes |
| `backend/data/warehouse_jobs.py`                       | Codex      | Worker execution and queue dispatch verification |
| `backend/data/warehouse_worker_pool.sh`                | Codex      | Non-canonical worker helper / operational parity follow-up |
| `specs/sprint-16-data-gap-inventory.md`                | Codex      | Sprint 16 data baseline and gap tracking |
| `specs/sprint-16-validation-matrix.md`                 | Claude     | Page validation results and accepted scope limits |
| `frontend/src/app/players/[playerId]/page.tsx`         | Claude     | Player-page data validation follow-ups |
| `frontend/src/app/teams/[abbr]/page.tsx`               | Claude     | Team-page validation follow-ups |
| `frontend/src/app/leaderboards/page.tsx`               | Claude     | Leaderboard empty-state / partial-data follow-ups |
| `frontend/src/app/coverage/page.tsx`                   | Claude     | Coverage validation follow-ups |
| `frontend/src/app/games/[gameId]/page.tsx`             | Claude     | Game Explorer validation follow-ups |
| `backend/main.py`                                      | —          |         |

---

## Handoff Queue

Specs written by one agent for the other. Check this before starting work — if a spec is marked "Ready" for you, read it before writing any code.

| Spec file | From | To | Status |
|-----------|------|----|--------|
| `specs/sprint-16-data-gap-inventory.md` | Codex | Claude | Ready |

---

## Merge Order (this sprint)

1. `codex-sprint-16-data-foundation` (Codex — backend/data hardening and live data completion)
2. `feature/sprint-16-data-validation` (Claude — validation and UI hardening after the Sprint 16 baseline docs exist)
3. Optional closeout/docs-only branch if needed

---

## Sprint Work Allocation

Ownership is sprint-dependent, not permanent. Rewrite this table if work moves mid-sprint.

### This sprint's owned areas

| Files / Directories                                    | Assigned this sprint |
|--------------------------------------------------------|----------------------|
| `backend/services/warehouse_service.py`                | Codex                |
| `backend/data/warehouse_jobs.py`                       | Codex                |
| `backend/data/warehouse_worker_pool.sh`                | Codex                |
| `specs/sprint-16-data-gap-inventory.md`                | Codex                |
| `specs/sprint-16-warehouse-runbook.md`                 | Codex                |
| `specs/sprint-16-validation-matrix.md`                 | Claude               |
| Launch-window page validation / UI follow-ups          | Claude               |

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

2026-03-30 (Codex): Sprint 16 kickoff baseline: `2024-25` is warehouse-complete (`1230/1230/1230` box/PBP/materialized) with `2441 complete`, `1 running`, `1250 queued` jobs. `2025-26` is the main unfinished lane with `1119` box, `501` parsed PBP, `1119` materialized games, plus `1563 complete`, `4 running`, `1792 queued` jobs.
2026-03-30 (Codex): Historical support baseline remains strong enough for legacy-plus-derived handling: `2022-23` has `40931` game logs / `554` on-off / `17094` lineups, and `2023-24` has `43394` game logs / `595` on-off / `16190` lineups.
2026-03-30 (Codex): Sprint 15 closed. See `specs/sprint-15-closeout.md`.
