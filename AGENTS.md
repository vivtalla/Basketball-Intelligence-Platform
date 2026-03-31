# Agent Coordination

Last updated: 2026-03-30 by Codex (Sprint 20 dual-team kickoff)

> **Every operator reads this file before touching any code at the start of every session.**
> Identify your team and role first, then check sprint status, branch, file ownership, handoff queue, and merge gate.
> Then `git fetch origin`. Then begin work.
> Sprint 20 runs as **two parallel four-role teams**. Each team must pass its own `Reviewer` and `Optimizer` gates before merging.
> At sprint close, create/update `specs/sprint-{NN}-closeout.md`, reset `AGENTS.md` for the next sprint, and update the matching sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field        | Value |
|--------------|-------|
| Sprint       | 20 |
| Goal         | Dual Team Analyst Workflows: Team A `Custom Metric Builder`, Team B `Recent Trajectory Tracker` |
| Started      | 2026-03-30 |
| Target merge | After both Team A and Team B pass Reviewer and Optimizer gates |

Sprint 19 is closed. See `specs/sprint-19-closeout.md` for shipped work, deferred work, and next-sprint seeds.

---

## Team Structure

Sprint 20 uses two parallel teams with the same four-role workflow:

`Architect -> Engineer -> Reviewer -> Optimizer`

### Team A — Metric Builder Team
- Branch: `codex-sprint-20-metric-builder`
- Goal: build `Build Your Own Metric` inside `Leaderboards`
- Current status: Engineer, Reviewer, and Optimizer complete; ready to merge

Roles:
- Architect: Complete
- Engineer: Complete
- Reviewer: Complete
- Optimizer: Complete

### Team B — Trajectory Team
- Branch: `codex-sprint-20-trajectory-tracker`
- Goal: evolve `Insights` into a 2025-26 recent-window trajectory workflow
- Current status: Engineer, Reviewer, and Optimizer complete; ready to merge

Roles:
- Architect: Complete
- Engineer: Complete
- Reviewer: Complete
- Optimizer: Complete

### Shared Integration
- Shared kickoff branch: `codex-sprint-20-kickoff`
- `master` remains the integration branch only
- Each team merges independently after passing its gates
- Sprint 20 is complete only after both Team A and Team B land in `master`

> ⚠️ **PERMANENT WARNING**: Do NOT use `codex-sprint-10-game-explorer-controls`. It is at a Sprint 9 commit and its diff against master deletes all warehouse infrastructure (2,700+ lines). It cannot be merged. It is dead.

---

## Team Workflow

### Architect
- Explore the current implementation area before proposing changes
- Write a decision-complete spec in `specs/`
- Mark the handoff `Ready for Engineer`

### Engineer
- Implement only from the architect-approved team spec
- Respect team-owned areas and shared-file lock rules
- Mark the branch `Ready for Reviewer`

### Reviewer
- Check correctness, contract alignment, regressions, compatibility, and repo conventions
- Record findings in a team review note or mark `Blocked`
- If clean, mark the branch `Ready for Optimizer`

### Optimizer
- Check avoidable N+1 work, duplicate fetches, unnecessary complexity, and efficiency issues
- Record findings in a team optimizer note or mark `Blocked`
- If clean, mark the branch `Ready to Merge`

### Merge Rule
- Team A and Team B each need Reviewer and Optimizer completion before merge
- No team merges directly from an in-progress branch state
- Final sprint merge state is reached only when both team branches are in `master`

---

## Shared File Lock Table

Claim a file here before writing a single line. If a file is already claimed, read the owning team branch before planning.

`types.ts` and `api.ts` are **append-only** — add new interfaces/functions at the bottom only.

`models.py` and `ensure_schema.py` are always claimed together.

| File                                                   | Claimed by | Purpose |
|--------------------------------------------------------|------------|---------|
| `backend/db/models.py`                                 | —          | Shared schema changes if any become necessary |
| `backend/db/ensure_schema.py`                          | —          | Shared schema changes if any become necessary |
| `frontend/src/lib/types.ts`                            | Shared Integration | Shared frontend contracts for both teams; append-only |
| `frontend/src/lib/api.ts`                              | Shared Integration | Shared frontend API functions for both teams; append-only |
| `backend/main.py`                                      | —          | Shared router registration if needed |

Shared integration note:
- If both teams need shared files, coordinate the order first in this file and keep append-only rules intact
- Prefer team-local helper files over reshaping shared files mid-sprint

---

## Handoff Queue

Use this queue to move each team through the four-role pipeline.

Allowed statuses:
- `Ready for Engineer`
- `Ready for Reviewer`
- `Ready for Optimizer`
- `Ready to Merge`
- `Blocked`

| Team | Artifact / Spec file | From role | To role | Status | Notes |
|------|----------------------|-----------|---------|--------|-------|
| Team A | `specs/sprint-20-metric-builder.md` | Optimizer | Shared / Merge | Ready to Merge | Review + optimizer notes recorded; integration complete |
| Team B | `specs/sprint-20-trajectory-tracker.md` | Optimizer | Shared / Merge | Ready to Merge | Review + optimizer notes recorded; integration complete |

---

## Merge Order (this sprint)

Parallel team flow:

1. Shared kickoff docs land on `codex-sprint-20-kickoff`
2. Team A completes on `codex-sprint-20-metric-builder`
3. Team B completes on `codex-sprint-20-trajectory-tracker`
4. Team A merges to `master` after its Reviewer and Optimizer gates
5. Team B merges to `master` after its Reviewer and Optimizer gates
6. Sprint 20 closes after both merges land

---

## Sprint Work Allocation

### Team A owned areas

| Files / Directories                                    | Assigned team |
|--------------------------------------------------------|---------------|
| `backend/routers/leaderboards.py`                      | Team A |
| `backend/services/` custom-metric logic                | Team A |
| `frontend/src/app/leaderboards/page.tsx`               | Team A |
| `frontend/src/components/` metric-builder UI           | Team A |

### Team B owned areas

| Files / Directories                                    | Assigned team |
|--------------------------------------------------------|---------------|
| `backend/routers/insights.py`                          | Team B |
| `backend/services/` trajectory logic                   | Team B |
| `frontend/src/app/insights/page.tsx`                   | Team B |
| `frontend/src/components/` trajectory UI               | Team B |

### Shared files — claim in Lock Table before editing

- `backend/db/models.py` + `backend/db/ensure_schema.py`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `backend/main.py`

---

## Session Start Checklist

```
1. Read this file — sprint number, team, role, branch, ownership, handoff queue
2. Confirm I am on the correct team branch or isolated worktree
3. Read my team's latest handoff artifact before editing
4. Check the Shared File Lock Table before touching any shared file
5. git fetch origin && git log origin/master --oneline -5
6. Confirm the prior role for my team is complete
7. Update this file first if ownership or lock status changes
8. Begin work
```

---

## Branch Isolation Rule

- Team A work happens on `codex-sprint-20-metric-builder`
- Team B work happens on `codex-sprint-20-trajectory-tracker`
- Shared kickoff coordination happens on `codex-sprint-20-kickoff`
- `master` is integration only
- Do not implement Sprint 20 feature work on `master`

## Cross-Team Review

Before either team branch merges to `master`, the other team should do a quick convention spot-check:

- Python 3.8 compatibility
- shared-file claim compliance
- router registration if new router wiring is needed
- no raw schema changes outside `ensure_schema.py`
- append-only compliance in `types.ts` and `api.ts`

---

## Notes

*Free-form, dated, newest first. For cross-team coordination mid-sprint.*

2026-03-30 (Architect): Sprint 20 kicked off as a dual-team sprint. Team A owns `Custom Metric Builder` in `Leaderboards`; Team B owns `Recent Trajectory Tracker` in `Insights`.
2026-03-30 (Codex): Team A and Team B implementations are integrated on `codex-sprint-20-kickoff`. Verification passed: backend compile, both backend test files, `npm run lint`, and `npm run build` (build required elevated execution due sandbox Turbopack restrictions).
2026-03-30 (Codex): Sprint 19 closed and merged to `master`. See `specs/sprint-19-closeout.md`.
