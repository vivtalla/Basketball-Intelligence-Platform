# Agent Coordination

Last updated: 2026-04-02 by Codex (Sprint 30 closeout)

> Both agents read this file before touching code at the start of every session.
> The canonical source of truth is the clean `master` checkout at `/Users/viv/Documents/Basketball Intelligence Platform`.
> If a future session starts from another branch or worktree, return to this canonical root first unless the sprint explicitly says otherwise.
> All new sprint implementation happens on sprint branches/worktrees, never directly on `master`.
> At sprint close, update the sprint closeout note, refresh `specs/BACKLOG.md`, reset this file for the next sprint, and update the sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field | Value |
|-------|-------|
| Sprint | 32 |
| Goal | TBD — awaiting Vivek's sprint kickoff |
| Started | TBD |
| Target merge | TBD |
| Sprint shape | TBD |
| Branch | not created yet |
| Worker policy | Unassigned until kickoff |

---

## Canonical Workspace

- Canonical repo root: `/Users/viv/Documents/Basketball Intelligence Platform`
- Canonical branch: `master`
- Canonical remote: `origin/master`
- Extra temporary worktrees should only exist during an active sprint and must be removed at sprint close

If repo state, sprint numbering, or shipped features appear to disagree across locations, trust this workspace on `master` first and reconcile from there.

---

## Current Assignments

### Claude
- Branch: not assigned
- Scope: available for Sprint 32 kickoff
- Status: Not started

### Codex
- Branch: not assigned
- Scope: available for Sprint 32 kickoff
- Status: Not started

---

## Shared File Lock Table

Claim a shared file here before editing. If a file is already claimed, read that branch before planning and do not edit until the claim is released or the work merges.

`frontend/src/lib/types.ts` and `frontend/src/lib/api.ts` are append-only.
`backend/db/models.py` and `backend/db/ensure_schema.py` are always claimed together.

| File | Claimed by | Purpose |
|------|------------|---------|
| `frontend/src/lib/types.ts` | — |  |
| `frontend/src/lib/api.ts` | — |  |
| `backend/main.py` | — |  |

---

## Handoff Queue

Specs or review notes written by one stream for another. Check this before starting work.

| Spec file | From | To | Status |
|-----------|------|----|--------|
| `specs/data-architecture.md` | Sprint 26 | Next sprint | Reference — read before touching data layer |
| `specs/sprint-31-closeout.md` | Sprint 31 | Next sprint | Reference — visual renaissance follow-ons and viz seeds |

---

## Merge Order

1. TBD at Sprint 32 kickoff

---

## Sprint Work Allocation

| Files / Directories | Assigned this sprint |
|---------------------|----------------------|
| To be defined at Sprint 32 kickoff | — |

---

## Session Start Checklist

1. Review `tasks/lessons.md` — apply any standing rules before touching code
2. Read this file: canonical root, sprint status, branch/worktree rules, shared locks
3. Confirm you are in `/Users/viv/Documents/Basketball Intelligence Platform` on `master`, or on the explicitly assigned sprint branch/worktree
4. Check the lock table before editing shared files
5. Check the handoff queue for any ready spec or review note
6. `git fetch origin` and inspect recent `origin/master`
7. Update your status here if it changed materially
8. Begin work

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

- `master` is the only durable source of truth
- Every active sprint branch must have a clearly named worktree
- Every worktree maps to exactly one active branch
- Temporary merge/testing worktrees should be deleted right after merge
- Do not leave a stale feature branch as the default repo root
- At sprint close:
  1. prune merged worktrees
  2. delete merged or superseded local branches
  3. delete merged or superseded remote branches
  4. `git fetch --prune origin`

---

## Sprint Closeout Checklist

1. Confirm what actually landed in `master`
2. Create or update `specs/sprint-{NN}-closeout.md` with shipped work, deferred work, workflow lessons, and next-sprint seeds
3. Refresh `specs/BACKLOG.md` so shipped items are removed or rewritten as follow-ons
4. Reset `AGENTS.md` for the next sprint kickoff state
5. Update `CLAUDE.md` "Recent Sprints" section (keep last 2 sprints inline; move the oldest out)
6. Append the completed sprint summary to `specs/sprint-history.md`

---

## Notes

*Free-form, dated, newest first. Use this for coordination and repo-state exceptions.*

2026-04-03 (Claude): Sprint 31 closed on `feature/sprint-31-visual-renaissance`. Shipped hexbin shot chart, ZoneAnnotationCourt, PerformanceCalendar, full chart harmonization (CareerArcChart/DualCareerArcChart/RadarChart), homepage visual redesign, and StandingsBumpChart. Frontend-only sprint, no Codex branch. See `specs/sprint-31-closeout.md` before Sprint 32 kickoff.
2026-04-02 (Codex): Sprint 30 closed on `feature/sprint-30-dbfirst-viz`. Shipped DB-first player/career/gamelog/standings reads with readiness metadata, queue-backed enrichment coverage, and the first CourtVue signature visualization layer across player, compare, and insights. See `specs/sprint-30-closeout.md` before Sprint 31 kickoff.
2026-04-02 (Codex): Sprint 29 closeout prepared on `feature/sprint-29-standings-zones`. Shipped standings history/trend lines plus shot zone analytics, then hardened shot-chart reads to be DB-first with queued warehouse-backed sync. Local closeout verification covered backend standings/shot-chart APIs and frontend route smoke checks; `pytest` was still unavailable in `backend/venv`, so backend test execution remains a noted gap.
2026-04-01 (Claude): Sprint 28 closed. Shipped compare availability layer (injury badge + warning banner in ComparisonView, GET /api/compare/player-availability) and unresolved injury identity ops UI (/admin/injuries/unresolved with resolve/dismiss endpoints). Standings trend and shot zone analytics deferred to Sprint 29.
2026-04-01 (Codex): Sprint 27 closed on branch `feature/sprint-27-availability-schedule` pending merge. Shipped scope: upcoming schedule API, team/pre-read availability surfaces, official injury-report fallback, and injury identity hardening (`player_name_aliases`, `injury_sync_unresolved`). See `specs/sprint-27-closeout.md` before Sprint 28 kickoff.
2026-04-01 (Codex): Post-closeout patch pass is complete and pushed on `master` in commit `18d9a13` (`fix: patch local testing regressions`). This bundled four small fixes discovered during manual QA: home-page league leaders now use canonical full names, `TrajectoryTracker` no longer renders raw `Error` objects, `CustomMetricBuilder` got the same error rendering fix, and `frontend/next.config.ts` now allows `127.0.0.1` / `localhost` in local dev. Use `specs/sprint-25-post-closeout-patches.md` as the handoff note before doing more patch work or Sprint 26 planning.
2026-04-01 (Codex): Local manual-testing assumptions changed during the patch pass: the frontend local env is intentionally pointed at `http://127.0.0.1:8001` via ignored `frontend/.env.local`, and manual testing should use `http://127.0.0.1:3001` for frontend and `http://127.0.0.1:8001` for backend. If pages look blank, verify those two processes first before assuming a product regression.
2026-04-01 (Codex): Sprint 24 completed a full branch audit and canonicalized the repo root back to `master` at `/Users/viv/Documents/Basketball Intelligence Platform`. All stale temporary worktrees and stale remote sprint branches should now be treated as cleanup targets, not alternate truths.
2026-04-01 (Codex): The prior confusion came from starting in stale `feature/sprint-12-warehouse-frontend` while the real product history had advanced on `master` through Sprint 23. Future sessions should never plan from a stale worktree when `master` is available.
2026-04-01 (Codex): Sprint 25 shipped the first platform-intelligence layer across team pages, insights, compare, pre-read, and Game Explorer. Use `specs/sprint-25-closeout.md`, `specs/sprint-25-review-note.md`, and `specs/BACKLOG.md` as the next-sprint starting point.
