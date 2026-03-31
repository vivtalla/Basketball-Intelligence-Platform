# Agent Coordination

Last updated: 2026-03-30 by Codex (Sprint 21 kickoff)

> **Every operator reads this file before touching any code at the start of every session.**
> Check sprint status, branch, shared-file locks, handoff queue, and merge notes first.
> Then `git fetch origin`. Then begin work.
> Sprint work happens on isolated sprint branches or worktrees, never directly on `master`.
> At sprint close, create/update `specs/sprint-{NN}-closeout.md`, reset `AGENTS.md` for the next sprint kickoff state, and update the matching sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field | Value |
|-------|-------|
| Sprint | 21 |
| Goal | Split `Metrics` and `Player Stats` into dedicated workspaces, add local metric presets, and clean up visible player-name consistency |
| Started | 2026-03-30 |
| Target merge | After Team A and Team B both pass Reviewer and Optimizer, then merge through the Sprint 21 integration branch |

Sprint 20 is closed. See `specs/sprint-20-closeout.md` for shipped work, verification, lessons, and next-sprint seeds.

---

## Team Workflow

Sprint 21 runs as two parallel teams, each using:

`Architect -> Engineer -> Reviewer -> Optimizer`

### Team A — Metrics Workspace Team
- Branch: `codex-sprint-21-metrics-workspace`
- Scope:
  - `/metrics`
  - built-in starter presets
  - local saved presets
  - metric-builder component and supporting hook-layer adjustments
- Status: Ready to Merge

### Team B — Player Stats + Name Consistency Team
- Branch: `codex-sprint-21-player-stats-name-consistency`
- Scope:
  - `/player-stats`
  - `/leaderboards` compatibility redirect
  - nav and home-page route updates
  - visible full-name cleanup
- Status: Ready to Merge

### Integration
- Branch: `codex-sprint-21-kickoff`
- Purpose:
  - carry shared sprint coordination docs
  - merge Team A and Team B when both are `Ready to Merge`
  - run integrated verification before final merge to `master`

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

| File | Claimed by | Purpose |
|------|------------|---------|
| `backend/db/models.py` | — | Shared schema changes if any become necessary |
| `backend/db/ensure_schema.py` | — | Shared schema changes if any become necessary |
| `frontend/src/lib/types.ts` | — | Shared frontend contracts; append-only by default |
| `frontend/src/lib/api.ts` | — | Shared frontend API functions; append-only by default |
| `backend/main.py` | — | Shared router registration if needed |

Shared integration note:
- If both teams need one of the shared files above, land changes in a coordinated order and keep append-only guarantees intact where already required.
- Prefer new isolated files for sprint helpers instead of expanding shared files unless the route truly needs it.

---

## Handoff Queue

Use this queue for Sprint 21 only.

Allowed statuses:
- `Ready for Engineer`
- `Ready for Reviewer`
- `Ready for Optimizer`
- `Ready to Merge`
- `Blocked`

| Team | Artifact / Spec file | From role | To role | Status | Notes |
|------|----------------------|-----------|---------|--------|-------|
| Team A | `specs/sprint-21-team-a-metrics-workspace.md` | Optimizer | Merge | Ready to Merge | Verified with `npm run lint`, `npm run build`, and live `/metrics` route checks |
| Team B | `specs/sprint-21-team-b-player-stats-name-consistency.md` | Optimizer | Merge | Ready to Merge | Verified with `npm run lint`, `npm run build`, `/leaderboards` redirect, and live `/player-stats` checks |

---

## Merge Order

```
1. Team A branch reaches Ready to Merge
2. Team B branch reaches Ready to Merge
3. Merge both into codex-sprint-21-kickoff
4. Run integrated verification on codex-sprint-21-kickoff
5. Merge Sprint 21 to master only after both team branches land cleanly
```

---

## Sprint Work Allocation

| Files / Directories | Assigned this sprint |
|---------------------|----------------------|
| `frontend/src/app/metrics/**` | Team A |
| `frontend/src/components/CustomMetricBuilder.tsx` | Team A |
| `frontend/src/hooks/useCustomMetric.ts` | Team A |
| `frontend/src/app/player-stats/**` | Team B |
| `frontend/src/app/leaderboards/page.tsx` | Team B |
| `frontend/src/app/layout.tsx` | Team B |
| `frontend/src/app/page.tsx` | Team B |
| `frontend/src/components/ComparisonView.tsx` | Team B |
| route/link cleanup on other frontend surfaces | Team B |

---

## Session Start Checklist

```
1. Read this file — sprint number, branch expectations, locks, handoff queue, merge order
2. Confirm I am on the correct sprint branch or isolated worktree
3. Read the latest Sprint 21 team spec if it is marked Ready for me
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
- Sprint 21 uses Team A and Team B branches plus the integration branch

---

## Sprint Closeout Checklist

```
1. Confirm what actually landed in master
2. Create or update specs/sprint-21-closeout.md with shipped work, deferred work, lessons, and next-sprint seeds
3. Clean AGENTS.md for the next sprint kickoff state
4. Update the matching sprint summary in CLAUDE.md
5. Leave the next sprint kickoff readable from AGENTS.md + latest closeout note + CLAUDE.md
```

---

## Cross-Agent Review

Before any Sprint 21 branch merges to `master`, do a quick convention spot-check:

- Python 3.8 compatibility
- schema changes go through `ensure_schema.py`
- no direct `stats.nba.com` calls outside the existing wrapper approach
- shared-file claim compliance
- router registration in `main.py` if new routers are added

---

## Notes

*Free-form, dated, newest first. For cross-agent coordination mid-sprint.*

2026-03-30 (Codex): Sprint 21 implementation is complete on `codex-sprint-21-kickoff`. Team A and Team B both passed integrated verification and are marked Ready to Merge.
2026-03-30 (Codex): Sprint 21 kicked off as a dual-team frontend sprint. Team A owns the Metrics workspace and presets. Team B owns the Player Stats split, nav updates, redirect behavior, and visible full-name cleanup.
2026-03-30 (Codex): Sprint 20 closed. The dual-team workflow proved workable and is now the default template for future multi-feature sprints.
2026-03-30 (Codex): Sprint 19 closed and merged to `master`. See `specs/sprint-19-closeout.md`.
