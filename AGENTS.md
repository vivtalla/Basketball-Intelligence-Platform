# Agent Coordination

Last updated: 2026-03-30 by Codex (post-Sprint-22 closeout)

> **Every agent reads this file before touching code at the start of a session.**
> Check sprint status, your branch/worktree, the lock table, the Handoff Queue, and the Merge Order.
> Then `git fetch origin`. Then begin work.
> All implementation happens on sprint branches or isolated worktrees, never directly on `master`.
> At sprint close, create/update `specs/sprint-{NN}-closeout.md`, reset `AGENTS.md`, and update the matching sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field | Value |
|-------|-------|
| Sprint | 23 |
| Goal | Planning state — next sprint not kicked off yet |
| Started | — |
| Target merge | — |

---

## Agent Assignments

### Claude
- Branch: next assigned sprint branch
- Scope: TBD at Sprint 23 kickoff
- Status: Available
- PR: —

### Codex
- Branch: next assigned sprint branch/worktree
- Scope: TBD at Sprint 23 kickoff
- Status: Available
- PR: —

> ⚠️ **PERMANENT WARNING**: Do NOT use `codex-sprint-10-game-explorer-controls`. It is at a Sprint 9 commit and its diff against master deletes warehouse infrastructure. It cannot be merged.

---

## Shared File Lock Table

Claim a file here before writing code. If a file is already claimed, read that branch before planning and do not edit it until the claim is released or reassigned.

`frontend/src/lib/types.ts` and `frontend/src/lib/api.ts` are **append-only** unless the sprint explicitly overrides that rule.

| File | Claimed by | Purpose |
|------|------------|---------|
| `frontend/src/lib/types.ts` | — | |
| `frontend/src/lib/api.ts` | — | |
| `backend/main.py` | — | |
| `backend/db/models.py` | — | |
| `backend/db/ensure_schema.py` | — | |

---

## Handoff Queue

| Spec file | From | To | Status |
|-----------|------|----|--------|

---

## Merge Order

```
1. Sprint 22 is merged and closed
2. Rewrite this section at Sprint 23 kickoff
```

---

## Session Start Checklist

```
1. Read this file — sprint state, branch, lock table, Merge Order
2. Confirm I am on my assigned sprint branch or isolated worktree
3. Check Handoff Queue for any Ready spec
4. git fetch origin && git log origin/master --oneline -5
5. Claim shared files before editing
6. Update status here if the sprint setup changes materially
7. Begin work
```

---

## Sprint Closeout Checklist

```
1. Confirm what landed in master
2. Create or update specs/sprint-{NN}-closeout.md
3. Reset AGENTS.md for the next sprint kickoff state
4. Update the matching sprint summary in CLAUDE.md
5. Leave the next kickoff readable from AGENTS.md + closeout + CLAUDE.md
```

---

## Notes

*Free-form, dated, newest first.*

2026-03-30 (Codex): Sprint 22 is complete and merged. CourtVue Labs is now the user-facing product name, `/api/metrics/custom` is live, the Metrics workspace supports URL-shareable state and compare/player handoff, and the recency-first Trajectory Tracker remains active on `/insights`.
