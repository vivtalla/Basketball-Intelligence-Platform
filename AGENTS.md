# Agent Coordination

Last updated: 2026-03-30 by Codex (Sprint 14 kickoff)

> **Both agents read this file before touching any code at the start of every session.**
> Check sprint status, your branch, this sprint's work allocation, and the Merge Order.
> Then check the Handoff Queue. Then `git fetch origin`. Then begin work.
> All sprint implementation work happens on each agent's own branch or worktree, never directly on `master`; merge to `master` only after the sprint branch work is ready.
> At sprint close, create/update `specs/sprint-{NN}-closeout.md`, reset `AGENTS.md` for the next sprint, and update the matching sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field        | Value                                  |
|--------------|----------------------------------------|
| Sprint       | 14                                     |
| Goal         | Game summary API + data layer — expose GameTeamStat/GamePlayerStat via new endpoint; ship game box score UI in Game Explorer |
| Started      | 2026-03-30                             |
| Target merge | TBD                                    |

Sprint 13 is closed. See `specs/sprint-13-closeout.md` for shipped work and next-sprint seeds.

---

## Agent Assignments

### Claude
- Branch: `feature/sprint-14-game-summary-ui`
- Scope: `GameSummaryResponse` TS types + API fn + SWR hook; Game Explorer team box score section + player box score table; coverage page memo fix
- Status: Complete — merged to master
- PR: —

### Codex
- Branch: `codex-sprint-14-data-layer`
- Scope: `GameTeamBoxScore`/`GamePlayerBoxScore`/`GameSummaryResponse` Pydantic models; `game_summary_service.py` (new); `GET /api/games/{game_id}/summary` endpoint; SIGTERM fix in `warehouse_jobs.py`
- Status: Complete — merged to master
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
| `backend/models/game.py`                               | Codex      | Append GameTeamBoxScore, GamePlayerBoxScore, GameSummaryResponse |
| `backend/services/game_summary_service.py`             | Codex      | New service file                                                  |
| `backend/routers/games.py`                             | Codex      | Add GET /{game_id}/summary endpoint                               |
| `backend/data/warehouse_jobs.py`                       | Codex      | SIGTERM signal handler                                            |
| `frontend/src/lib/types.ts`                            | Claude     | Append GameTeamBoxScore, GamePlayerBoxScore, GameSummaryResponse  |
| `frontend/src/lib/api.ts`                              | Claude     | Append getGameSummary()                                           |
| `frontend/src/hooks/usePlayerStats.ts`                 | Claude     | Append useGameSummary()                                           |
| `frontend/src/app/games/[gameId]/page.tsx`             | Claude     | Team box score section + player box table                         |
| `frontend/src/app/coverage/page.tsx`                   | Claude     | Memo deps fix                                                     |
| `backend/main.py`                                      | —          |         |

---

## Handoff Queue

Specs written by one agent for the other. Check this before starting work — if a spec is marked "Ready" for you, read it before writing any code.

| Spec file | From | To | Status |
|-----------|------|----|--------|

---

## Merge Order (this sprint)

```
1. codex-sprint-14-data-layer          (Codex — backend; Claude reviews before merge)
2. feature/sprint-14-game-summary-ui   (Claude — frontend; depends on /summary endpoint; Codex reviews before merge)
```

---

## Sprint Work Allocation

Ownership is sprint-dependent, not permanent. The table below is rewritten each sprint to show who is currently driving which areas.

### This sprint's owned areas

| Files / Directories                                    | Assigned this sprint |
|--------------------------------------------------------|----------------------|
| `backend/models/game.py`                               | Codex                |
| `backend/services/game_summary_service.py`             | Codex                |
| `backend/routers/games.py`                             | Codex                |
| `backend/data/warehouse_jobs.py`                       | Codex                |
| `frontend/src/lib/types.ts`                            | Claude               |
| `frontend/src/lib/api.ts`                              | Claude               |
| `frontend/src/hooks/usePlayerStats.ts`                 | Claude               |
| `frontend/src/app/games/[gameId]/page.tsx`             | Claude               |
| `frontend/src/app/coverage/page.tsx`                   | Claude               |

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

2026-03-30 (Codex): Sprint 14 started on `codex-sprint-14-data-layer`. Current scope: warehouse-backed game summary endpoint for Game Explorer plus the small `warehouse_jobs.py` SIGTERM fix.
2026-03-30 (Claude): Sprint 13 closed. Codex shipped full scope solo (Claude token-limited). Warehouse reliability: distributed throttle, worker pool script, reset-stale + job-summary endpoints, auto-poll panel. YoY callouts on player + team pages. Game Explorer drill-down. Sprint 14 seeds: SIGTERM fix, coverage memo fix, pipeline metrics, game summary API.
