# Agent Coordination

Last updated: 2026-03-30 by Codex (Sprint 18 Hardwood Editorial kickoff)

> **Every operator reads this file before touching any code at the start of every session.**
> Identify your current role first, then check sprint status, branch, role assignments, handoff queue, lock table, and merge gate.
> Then `git fetch origin`. Then begin work.
> All sprint implementation work happens on the sprint branch or its isolated worktree, never directly on `master`; merge to `master` only after the branch passes both the `Reviewer` and `Optimizer` gates.
> At sprint close, create/update `specs/sprint-{NN}-closeout.md`, reset `AGENTS.md` for the next sprint, and update the matching sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field        | Value |
|--------------|-------|
| Sprint       | 18 |
| Goal         | Hardwood Editorial platform refresh |
| Started      | 2026-03-30 |
| Target merge | After Engineer, Reviewer, and Optimizer gates |

Sprint 17 is closed. See `specs/sprint-17-closeout.md` for shipped work, deferred work, and next-sprint seeds.

---

## Role Assignments

All sprint execution uses a **single-branch pipeline**:

`Architect -> Engineer -> Reviewer -> Optimizer -> Merge`

Named agents like Codex or Claude may still operate inside this workflow, but the roles below are the primary operating model.

### Architect
- Branch: sprint branch (`sprint-18-{slug}` or equivalent) created fresh from current `master`
- Scope: design system and produce the decision-complete build spec
- Status: Complete
- Output artifact: architect spec or implementation note, marked `Ready for Engineer`
- Blocked on: —

### Engineer
- Branch: same sprint branch as Architect
- Scope: implement only from the architect-approved spec
- Status: In progress
- Output artifact: implementation branch marked `Ready for Reviewer`
- Blocked on: —

### Reviewer
- Branch: same sprint branch as Architect and Engineer
- Scope: correctness, regression, compatibility, and conventions gate
- Status: Unassigned
- Output artifact: reviewer findings note or explicit `Ready for Optimizer`
- Blocked on: Engineer handoff

### Optimizer
- Branch: same sprint branch as Architect, Engineer, and Reviewer
- Scope: performance, efficiency, and operational gate
- Status: Unassigned
- Output artifact: optimizer findings note or explicit `Ready to Merge`
- Blocked on: Reviewer pass

> ⚠️ **PERMANENT WARNING**: Do NOT use `codex-sprint-10-game-explorer-controls`. It is at a Sprint 9 commit and its diff against master deletes all warehouse infrastructure (2,700+ lines). It cannot be merged. It is dead.

---

## Role Workflow

### 1. Architect
- Read the sprint goal and current repo state.
- Explore the implementation area before proposing structure.
- Write or update the sprint spec in `specs/` when needed.
- Define the intended approach, interfaces, constraints, edge cases, and acceptance criteria.
- Mark the handoff `Ready for Engineer`.

### 2. Engineer
- Implement only from the architect-approved spec.
- Claim files in the Lock Table before editing.
- Keep work scoped to the approved sprint branch.
- Update role status as implementation progresses.
- Mark the branch or handoff `Ready for Reviewer`.

### 3. Reviewer
- Required gate before merge.
- Check correctness, regressions, compatibility, contracts, and repo conventions.
- Record findings in the Handoff Queue or a lightweight review note in `specs/` if needed.
- If issues exist, send the work back as `Blocked`.
- If clean, mark the handoff `Ready for Optimizer`.

### 4. Optimizer
- Required gate before merge, even if no code changes are needed.
- Check performance, operational efficiency, redundant work, and avoidable complexity.
- Record findings in the Handoff Queue or a lightweight optimization note in `specs/` if needed.
- If changes are needed, send the work back as `Blocked`.
- If no further action is needed, mark the branch `Ready to Merge`.

### Merge Rule

- No sprint branch merges until both `Reviewer` and `Optimizer` are complete.
- “No optimization changes required” is a valid Optimizer outcome, but the gate must still run.

---

## Shared File Lock Table

Claim a file here before writing a single line. If a file is already claimed, read the current sprint branch state before planning — do not edit a claimed file until the claim is released or reassigned.

`types.ts` and `api.ts` are **append-only** — add new interfaces/functions at the bottom only.

`models.py` and `ensure_schema.py` are always claimed together.

| File                                                   | Claimed by | Purpose |
|--------------------------------------------------------|------------|---------|
| `backend/db/models.py`                                 | —          |         |
| `backend/db/ensure_schema.py`                          | —          |         |
| `frontend/src/lib/types.ts`                            | —          |         |
| `frontend/src/lib/api.ts`                              | —          |         |
| `backend/main.py`                                      | —          |         |

---

## Handoff Queue

Use this queue to move the sprint branch through the four-role pipeline.

Allowed statuses:
- `Ready for Engineer`
- `Ready for Reviewer`
- `Ready for Optimizer`
- `Ready to Merge`
- `Blocked`

Required artifact convention:
- Architect may attach a spec file in `specs/`
- Reviewer may attach a findings note in `specs/`
- Optimizer may attach a findings note in `specs/`
- For small sprints, the queue row itself can be the artifact if it is decision-complete

| Artifact / Spec file | From role | To role | Status | Notes |
|----------------------|-----------|---------|--------|-------|
| `specs/sprint-18-hardwood-editorial-refresh.md` | Architect | Engineer | Ready for Engineer | Hardwood Editorial direction selected for Sprint 18 visual refresh |

---

## Merge Order (this sprint)

Single-branch pipeline:

1. `Architect`
2. `Engineer`
3. `Reviewer`
4. `Optimizer`
5. Merge sprint branch to `master`

If multiple named agents participate, they still preserve this role order on the same sprint branch.

---

## Sprint Work Allocation

Ownership is sprint-dependent, not permanent. Rewrite this table at sprint kickoff to match the current plan.

### This sprint's owned areas

| Files / Directories                                    | Assigned role |
|--------------------------------------------------------|---------------|
| `frontend/src/app/globals.css`                         | Engineer |
| `frontend/src/app/layout.tsx`                          | Engineer |
| `frontend/src/app/page.tsx`                            | Engineer |
| `frontend/src/app/compare/page.tsx`                    | Engineer |
| `frontend/src/app/coverage/page.tsx`                   | Engineer |
| `frontend/src/app/games/[gameId]/page.tsx`             | Engineer |
| `frontend/src/app/insights/page.tsx`                   | Engineer |
| `frontend/src/app/leaderboards/page.tsx`               | Engineer |
| `frontend/src/app/learn/page.tsx`                      | Engineer |
| `frontend/src/app/players/[playerId]/page.tsx`         | Engineer |
| `frontend/src/app/standings/page.tsx`                  | Engineer |
| `frontend/src/app/teams/[abbr]/page.tsx`               | Engineer |
| `frontend/src/app/teams/page.tsx`                      | Engineer |
| `frontend/src/components/NavSearch.tsx`                | Engineer |
| `frontend/src/components/PlayerSearchBar.tsx`          | Engineer |
| `frontend/src/components/FavoritesList.tsx`            | Engineer |
| `frontend/src/components/HomeLeagueLeaders.tsx`        | Engineer |
| `frontend/src/components/PlayerHeader.tsx`             | Engineer |
| `frontend/src/components/ComparisonView.tsx`           | Engineer |
| `frontend/src/components/PlayerDashboard.tsx`          | Engineer |
| `frontend/src/components/StatCard.tsx`                 | Engineer |
| `frontend/src/components/StatTable.tsx`                | Engineer |
| `frontend/src/components/TeamAnalyticsPanel.tsx`       | Engineer |
| `frontend/src/components/TeamIntelligencePanel.tsx`    | Engineer |
| `frontend/src/components/TeamLineupsPanel.tsx`         | Engineer |
| `frontend/src/components/TeamRotationIntelligencePanel.tsx` | Engineer |

### Shared files — claim in Lock Table before editing

- `backend/db/models.py` + `backend/db/ensure_schema.py` (always claimed together)
- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `backend/main.py`

---

## Session Start Checklist

```
1. Read this file — sprint number, current role, sprint branch, handoff queue, merge rule
2. Confirm I know my current role: Architect, Engineer, Reviewer, or Optimizer
3. Confirm I am on the sprint branch or isolated worktree — do not implement on `master`
4. Read the latest upstream handoff artifact for my role
5. Check Lock Table — if the file I need is claimed, resolve that before editing
6. git fetch origin && git log origin/master --oneline -5
7. Confirm the prior role is complete before starting my own work
8. Update my role status if it changed, commit: "docs: update sprint role status in AGENTS.md"
9. Begin work
```

---

## Branch Isolation Rule

- Every sprint task is implemented on the sprint branch, not on `master`
- The default model is one sprint branch shared across the four roles
- If the current checkout is on another branch or has unsafe local changes, create an isolated worktree for the sprint branch before editing
- `master` is the integration branch only; it should receive completed sprint work only after the branch passes both required gates

## Work Allocation Rule

- File and directory ownership is decided per sprint, not as a permanent project rule
- Rewrite the Sprint Work Allocation table at sprint kickoff to match the current plan
- Lock ownership should be recorded by role, not by named agent
- If a task moves mid-sprint, update this file first so the reassignment is explicit before code changes begin

---

## Reviewer Gate

Before a branch can move to `Ready for Optimizer`, the Reviewer checks:

- correctness and regression risk
- API/backend/frontend contract alignment
- Python 3.8 compatibility
- schema / `ensure_schema.py` compliance
- shared-file claim compliance
- router registration / wiring
- test coverage or an explicit test gap note

The Reviewer either:
- marks the work `Blocked` with findings, or
- marks it `Ready for Optimizer`

---

## Optimizer Gate

Before a branch can move to `Ready to Merge`, the Optimizer checks:

- avoidable N+1 or repeated heavy queries
- unnecessary duplicate writes or fetches
- worker or process inefficiency
- queue / retry / backoff behavior if relevant
- frontend over-fetching or avoidable rerenders if relevant
- unnecessary complexity where a simpler implementation would preserve behavior

The Optimizer either:
- marks the work `Blocked` with findings, or
- marks it `Ready to Merge`

“No action needed” is valid, but the gate still must be recorded.

---

## Sprint Closeout Checklist

```
1. Confirm what actually landed in `master`
2. Confirm the sprint branch passed Reviewer and Optimizer
3. Create or update `specs/sprint-{NN}-closeout.md` with shipped work, deferred work, coordination lessons, technical lessons, and next-sprint seeds
4. Clean `AGENTS.md` for the next sprint kickoff state while preserving this four-role workflow
5. Update the matching sprint summary in `CLAUDE.md`
6. Leave the next sprint kickoff readable from `AGENTS.md` + latest closeout note + `CLAUDE.md`
```

---

## Branch Naming Convention

| Branch type | Format | Example |
|-------------|--------|---------|
| Sprint branch | `sprint-N-{slug}` | `sprint-17-role-workflow` |
| Codex sprint branch | `codex-sprint-N-{slug}` | `codex-sprint-17-role-workflow` |
| Claude sprint branch | `feature/sprint-N-{slug}` | `feature/sprint-17-role-workflow` |

The workflow is role-first, but existing branch naming conventions can still be used by the named operator if needed.

---

## Notes

*Free-form, dated, newest first. For cross-role communication mid-sprint.*

2026-03-30 (Engineer): Sprint 18 started on `codex-sprint-18-hardwood-editorial`. Selected direction: Hardwood Editorial. Initial scope is shared theme tokens plus home, nav, player, and team entry surfaces.
2026-03-30 (Codex): Sprint 17 closed and merged to `master`. See `specs/sprint-17-closeout.md`. Sprint 18 kickoff seed: consider a platform color refresh with explicit palette options rather than ad hoc style tweaks.
