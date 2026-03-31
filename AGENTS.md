# Agent Coordination

Last updated: 2026-03-30 by Codex (Sprint 22 kickoff)

> **Every agent reads this file before touching code at the start of a session.**
> Check sprint status, your team branch, the lock table, the Handoff Queue, and the Merge Order.
> Then `git fetch origin`. Then begin work.
> All sprint implementation happens on sprint branches or isolated worktrees, never directly on `master`.
> At sprint close, create/update `specs/sprint-22-closeout.md`, reset `AGENTS.md` for the next sprint, and update the matching sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field        | Value |
|--------------|-------|
| Sprint       | 22 |
| Goal         | CourtVue launch rebrand plus two analyst workflows: CourtVue Metrics and Trajectory Tracker |
| Started      | 2026-03-30 |
| Target merge | Merge Team A and Team B independently after Reviewer + Optimizer pass; sprint closes only after both land |

---

## Team Assignments

### Team A — CourtVue Metrics Team
- Branch: `codex-sprint-22-courtvue-metrics`
- Roles: Architect -> Engineer -> Reviewer -> Optimizer
- Scope:
  - CourtVue app-shell and user-facing rebrand
  - `/metrics` workspace polish and URL-shareable metric state
  - `POST /api/metrics/custom`
  - metric result handoff into player and compare workflows
- Status: In progress
- PR: —

### Team B — CourtVue Trajectory Team
- Branch: `codex-sprint-22-courtvue-trajectory`
- Roles: Architect -> Engineer -> Reviewer -> Optimizer
- Scope:
  - `/insights` recent-window trajectory workflow
  - `GET /api/insights/trajectory`
  - player-pool controls, exclusions, context flags, and CourtVue copy updates inside touched surfaces
- Status: In progress
- PR: —

### Integration
- Branch: `codex-sprint-22-kickoff`
- Scope:
  - kickoff docs
  - shared-file coordination
  - final integration, verification, and merge prep

> ⚠️ **PERMANENT WARNING**: Do NOT use `codex-sprint-10-game-explorer-controls`. It is at a Sprint 9 commit and its diff against master deletes warehouse infrastructure. It cannot be merged.

---

## Shared File Lock Table

Claim a file here before writing code. If a file is already claimed by the other team, read their branch first and do not edit it until their work lands or the claim is reassigned.

`frontend/src/lib/types.ts` and `frontend/src/lib/api.ts` are **append-only**. Add new interfaces/functions at the bottom only.

| File | Claimed by | Purpose |
|------|------------|---------|
| `frontend/src/app/layout.tsx` | Team A | CourtVue branding in app shell |
| `frontend/src/app/page.tsx` | Team A | CourtVue hero and workspace copy |
| `frontend/src/app/metrics/page.tsx` | Team A | Metrics workspace |
| `frontend/src/components/CustomMetricBuilder.tsx` | Team A | Metric builder UX, URL state, handoff links |
| `frontend/src/hooks/useCustomMetric.ts` | Team A | Metrics client hook |
| `backend/routers/metrics.py` | Team A | New metrics route |
| `backend/services/custom_metric_service.py` | Team A | Metric validation and scoring |
| `frontend/src/app/insights/page.tsx` | Team B | Trajectory page shell |
| `frontend/src/components/TrajectoryTracker.tsx` | Team B | Trajectory UX |
| `frontend/src/hooks/useTrajectory.ts` | Team B | Trajectory client hook |
| `backend/routers/insights.py` | Team B | Trajectory endpoint + legacy breakouts handoff |
| `backend/services/trajectory_service.py` | Team B | Recent-window trajectory report |
| `frontend/src/lib/types.ts` | Shared | Append-only Sprint 22 contracts |
| `frontend/src/lib/api.ts` | Shared | Append-only Sprint 22 API helpers |
| `backend/main.py` | Shared | Router registration + CourtVue API title |

---

## Handoff Queue

| Spec file | From | To | Status |
|-----------|------|----|--------|
| `specs/sprint-22-team-a-courtvue-metrics.md` | Architect | Team A | Ready |
| `specs/sprint-22-team-b-courtvue-trajectory.md` | Architect | Team B | Ready |

---

## Merge Order (this sprint)

```
1. Team A lands CourtVue app-shell branding, `/metrics` upgrades, and `POST /api/metrics/custom`
2. Team B rebases if shared copy or shared types moved, then lands Trajectory Tracker upgrades on `/insights`
3. Shared file edits stay append-only where required
4. Final sprint merge is complete only after both team branches land and integrated verification passes
```

---

## Sprint Work Allocation

### Team A owned areas

| Files / Directories | Assigned this sprint |
|---------------------|----------------------|
| `frontend/src/app/layout.tsx` | Team A |
| `frontend/src/app/page.tsx` | Team A |
| `frontend/src/app/metrics/page.tsx` | Team A |
| `frontend/src/components/CustomMetricBuilder.tsx` | Team A |
| `frontend/src/hooks/useCustomMetric.ts` | Team A |
| `backend/routers/metrics.py` | Team A |
| `backend/services/custom_metric_service.py` | Team A |

### Team B owned areas

| Files / Directories | Assigned this sprint |
|---------------------|----------------------|
| `frontend/src/app/insights/page.tsx` | Team B |
| `frontend/src/components/TrajectoryTracker.tsx` | Team B |
| `frontend/src/hooks/useTrajectory.ts` | Team B |
| `backend/routers/insights.py` | Team B |
| `backend/services/trajectory_service.py` | Team B |

### Shared files — claim before editing

- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `backend/main.py`

### Shared integration note

- If both teams need shared files, land Team A first and keep shared changes additive.
- Prefer new isolated modules over reshaping existing shared files unless the contract requires it.

---

## Session Start Checklist

```
1. Read this file — sprint, team branch, lock table, Merge Order
2. Confirm I am on my assigned sprint branch or isolated worktree
3. Check Handoff Queue and read any spec marked Ready for my team
4. git fetch origin && git log origin/master --oneline -5
5. Claim shared files before editing
6. Update status here if team state changes materially
7. Begin work
```

---

## Sprint Closeout Checklist

```
1. Confirm what landed in master
2. Create or update specs/sprint-22-closeout.md with shipped work, deferred work, lessons, and sprint seeds
3. Reset AGENTS.md for the next sprint kickoff state
4. Update Sprint 22 summary in CLAUDE.md
5. Leave the next kickoff readable from AGENTS.md + closeout + CLAUDE.md
```

---

## Cross-Team Review

Before either team branch merges to `master`, the other team should spot-check the diff for:

- Python 3.8-compatible typing
- no raw schema edits or Alembic
- shared files claimed before edit
- new FastAPI routers registered in `backend/main.py`
- append-only updates in `frontend/src/lib/types.ts` and `frontend/src/lib/api.ts`

---

## Notes

*Free-form, dated, newest first.*

2026-03-30 (Codex): Sprint 22 kickoff. Product baseline on `master` already includes `/metrics`, `/player-stats`, legacy `/leaderboards` redirect, custom metric service, and trajectory service. This sprint is about CourtVue rebrand, metrics contract/path alignment, URL-shareable metric state, and trajectory workflow completion.
