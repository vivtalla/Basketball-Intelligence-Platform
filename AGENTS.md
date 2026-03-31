# Agent Coordination

Last updated: 2026-03-30 by Codex (post-Sprint-20 closeout)

> **Every operator reads this file before touching any code at the start of every session.**
> Check sprint status, branch, shared-file locks, handoff queue, and merge notes first.
> Then `git fetch origin`. Then begin work.
> Sprint work happens on isolated sprint branches or worktrees, never directly on `master`.
> At sprint close, create/update `specs/sprint-{NN}-closeout.md`, reset `AGENTS.md` for the next sprint kickoff state, and update the matching sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field        | Value |
|--------------|-------|
| Sprint       | 21 |
| Goal         | Planning / not kicked off yet |
| Started      | — |
| Target merge | — |

Sprint 20 is closed. See `specs/sprint-20-closeout.md` for shipped work, verification, lessons, and next-sprint seeds.

---

## Team Workflow Template

Default sprint workflow:

`Architect -> Engineer -> Reviewer -> Optimizer`

If a sprint uses parallel teams again, copy this structure per team and give each team its own branch, handoff row, and merge gate.

### Architect
- Explore the current implementation area before proposing changes
- Write a decision-complete spec in `specs/`
- Mark the handoff `Ready for Engineer`

### Engineer
- Implement only from the architect-approved spec
- Respect file ownership and shared-file lock rules
- Mark the branch `Ready for Reviewer`

### Reviewer
- Check correctness, contract alignment, regressions, compatibility, and repo conventions
- Record findings in a review note or mark `Blocked`
- If clean, mark the branch `Ready for Optimizer`

### Optimizer
- Check avoidable N+1 work, duplicate fetches, unnecessary complexity, and efficiency issues
- Record findings in an optimizer note or mark `Blocked`
- If clean, mark the branch `Ready to Merge`

> ⚠️ **PERMANENT WARNING**: Do NOT use `codex-sprint-10-game-explorer-controls`. It is at a Sprint 9 commit and its diff against master deletes all warehouse infrastructure (2,700+ lines). It cannot be merged. It is dead.

---

## Shared File Lock Table

Claim a file here before writing a single line. If a file is already claimed, read the owning branch before planning.

`types.ts` and `api.ts` are **append-only** unless a sprint explicitly states otherwise.

`models.py` and `ensure_schema.py` are always claimed together.

| File                                                   | Claimed by | Purpose |
|--------------------------------------------------------|------------|---------|
| `backend/db/models.py`                                 | —          | Shared schema changes if any become necessary |
| `backend/db/ensure_schema.py`                          | —          | Shared schema changes if any become necessary |
| `frontend/src/lib/types.ts`                            | —          | Shared frontend contracts; append-only by default |
| `frontend/src/lib/api.ts`                              | —          | Shared frontend API functions; append-only by default |
| `backend/main.py`                                      | —          | Shared router registration if needed |

---

## Handoff Queue

Use this queue for the current sprint only.

Allowed statuses:
- `Ready for Engineer`
- `Ready for Reviewer`
- `Ready for Optimizer`
- `Ready to Merge`
- `Blocked`

| Team | Artifact / Spec file | From role | To role | Status | Notes |
|------|----------------------|-----------|---------|--------|-------|

---

## Merge Order

```
1. Sprint 20 is already closed
2. Next sprint should rewrite this section at kickoff
3. master remains the integration branch only
```

---

## Session Start Checklist

```
1. Read this file — sprint number, branch expectations, locks, and handoff queue
2. Confirm I am on the correct sprint branch or isolated worktree
3. Read the latest sprint spec or closeout note if relevant
4. Check the Shared File Lock Table before touching any shared file
5. git fetch origin && git log origin/master --oneline -5
6. Update this file first if ownership or lock status changes
7. Begin work
```

---

## Branch Isolation Rule

- Every sprint task is implemented on its assigned sprint branch, not on `master`
- If the current checkout is dirty or belongs to another sprint, create a fresh branch/worktree before editing
- `master` is the integration branch only
- When a sprint assigns multiple teams, each team gets its own branch/worktree

---

## Sprint Closeout Checklist

```
1. Confirm what actually landed in master
2. Create or update specs/sprint-{NN}-closeout.md with shipped work, deferred work, lessons, and next-sprint seeds
3. Clean AGENTS.md for the next sprint kickoff state
4. Update the matching sprint summary in CLAUDE.md
5. Leave the next sprint kickoff readable from AGENTS.md + latest closeout note + CLAUDE.md
```

---

## Cross-Agent Review

Before any sprint branch merges to `master`, do a quick convention spot-check:

- Python 3.8 compatibility
- schema changes go through `ensure_schema.py`
- no direct `stats.nba.com` calls outside the existing wrapper approach
- shared-file claim compliance
- router registration in `main.py` if new routers are added

---

## Notes

*Free-form, dated, newest first. For cross-agent coordination mid-sprint.*

2026-03-30 (Codex): Sprint 20 closed. The dual-team workflow proved workable and is now the default template for future multi-feature sprints.
2026-03-30 (Codex): Sprint 19 closed and merged to `master`. See `specs/sprint-19-closeout.md`.
