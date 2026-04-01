# Agent Coordination

Last updated: 2026-03-31 by Codex (post-Sprint-23 closeout)

> Both agents read this file before touching code at the start of every session.
> Check sprint status, sprint shape, your branch/worktree, shared-file locks, and merge order.
> Then check the handoff queue. Then `git fetch origin`. Then begin work.
> All new sprint implementation happens on sprint branches/worktrees, never directly on `master`.
> At sprint close, update the sprint closeout note, refresh `specs/BACKLOG.md`, reset this file for the next sprint, and update the sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field | Value |
|-------|-------|
| Sprint | 24 |
| Goal | Planning state — choose the next sprint from `specs/BACKLOG.md` and current product gaps |
| Started | 2026-03-31 |
| Target merge | TBD at Sprint 24 kickoff |
| Sprint shape | Not chosen yet |
| Reason | To be decided at kickoff |
| Worker policy | Selective bounded by default |

---

## Sprint Shape Decision

- Default repo policy remains hybrid:
  - major product sprints: two parallel teams
  - smaller or tightly coupled sprints: one sequential four-role stream
- The exact sprint shape is chosen at kickoff and recorded here before implementation starts.
- Spawned workers are allowed only for bounded, independent, non-blocking subtasks with clear ownership.

---

## Current Assignments

### Claude
- Branch: `master` or next assigned sprint branch
- Scope: available for Sprint 24 planning, review, or bounded implementation work
- Status: Available

### Codex
- Branch: `master` or next assigned sprint branch/worktree
- Scope: Sprint 24 planning, kickoff, and next implementation stream
- Status: Available

> Permanent warning: do not use `codex-sprint-10-game-explorer-controls`. It is stale and unsafe against current `master`.

---

## Shared File Lock Table

Claim a shared file here before editing. If a file is already claimed, read that branch before planning and do not edit until the claim is released or the work merges.

`frontend/src/lib/types.ts` and `frontend/src/lib/api.ts` are append-only.
`backend/db/models.py` and `backend/db/ensure_schema.py` are always claimed together.

| File | Claimed by | Purpose |
|------|------------|---------|
| `frontend/src/lib/types.ts` | — | |
| `frontend/src/lib/api.ts` | — | |
| `backend/main.py` | — | |
| `backend/db/models.py` | — | |
| `backend/db/ensure_schema.py` | — | |

---

## Handoff Queue

Specs or review notes written by one stream for another. Check this before starting work.

| Spec file | From | To | Status |
|-----------|------|----|--------|

---

## Merge Order

1. Sprint 23 merged to `master`
2. Next sprint should rewrite this section at kickoff

---

## Sprint Work Allocation

| Files / Directories | Assigned this sprint |
|---------------------|----------------------|
| To be defined at Sprint 24 kickoff | — |

---

## Session Start Checklist

1. Read this file: sprint number, sprint shape, branch/worktree, shared locks, merge order
2. Confirm you are on your assigned sprint branch or isolated worktree, never `master`
3. Check the lock table before editing shared files
4. Check the handoff queue for any ready spec or review note
5. `git fetch origin` and inspect recent `origin/master`
6. Update your status here if it changed materially
7. Begin work

---

## Worker Deployment Rules

- Use spawned workers only for bounded, independent, non-blocking subtasks
- Do not spawn workers for the immediate blocking task
- Do not spawn workers for vague “explore the codebase” requests
- Every worker prompt must include:
  - exact ownership
  - allowed files or subsystem
  - expected output artifact
  - reminder not to revert others’ changes
- Prefer 1-2 workers per sprint track, not unconstrained fan-out
- The main rollout keeps moving on non-overlapping integration work while workers run

---

## Token Efficiency Rules

- Read the minimum files needed before planning or coding
- Prefer one compact architect spec per stream over repeated chat re-explanation
- Keep handoff artifacts short and decision-complete
- Append to shared contracts instead of reshaping them when possible
- Treat `specs/BACKLOG.md` as the durable future-ideas layer; do not rely on long chat history
- Reviews should focus on regressions, contract mismatches, and missing tests before summarizing changes

---

## Branch and Worktree Discipline

- Every active sprint branch must have a clearly named worktree
- Every worktree maps to exactly one active branch
- Temporary merge/testing worktrees should be deleted right after merge
- Dirty worktrees that block cleanup must be called out in Notes
- At sprint close:
  1. prune merged worktrees
  2. delete merged local branches
  3. delete merged remote branches
  4. `git fetch --prune origin`

---

## Sprint Closeout Checklist

1. Confirm what actually landed in `master`
2. Create or update `specs/sprint-{NN}-closeout.md` with shipped work, deferred work, workflow lessons, and next-sprint seeds
3. Refresh `specs/BACKLOG.md` so shipped items are removed or rewritten as follow-ons
4. Reset `AGENTS.md` for the next sprint kickoff state
5. Update the matching sprint summary in `CLAUDE.md`

---

## Notes

*Free-form, dated, newest first. Use this for cross-team coordination during the sprint.*

2026-03-31 (Codex): Sprint 23 shipped four coach-facing workflows: team-vs-team compare, focus levers, usage vs efficiency, and pre-read deck. Resetting `AGENTS.md` to Sprint 24 planning state after closeout.
2026-03-31 (Codex): Sprint 23 kickoff ran from clean worktree `/private/tmp/bip-sprint23-kickoff` on branch `codex-sprint-23-kickoff`. Main working directory remained on old dirty `feature/sprint-12-warehouse-frontend` and was not used for Sprint 23 implementation.
