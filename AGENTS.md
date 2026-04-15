# Agent Coordination

Last updated: 2026-04-12 by Codex (Sprint 45 closeout prepared; Sprint 46 kickoff)

> Both agents read this file before touching code at the start of every session.
> The canonical source of truth is the clean `master` checkout at `/Users/viv/Documents/Basketball Intelligence Platform`.
> If a future session starts from another branch or worktree, return to this canonical root first unless the sprint explicitly says otherwise.
> All new sprint implementation happens on sprint branches/worktrees, never directly on `master`.
> At sprint close, update the sprint closeout note, refresh `specs/BACKLOG.md`, reset this file for the next sprint, and update the sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field | Value |
|-------|-------|
| Sprint | 46 |
| Goal | TBD |
| Started | 2026-04-12 |
| Target merge | TBD |
| Sprint shape | TBD |
| Branch | `TBD` |
| Worker policy | TBD |

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
- Branch: `TBD`
- Scope: available for Sprint 46 planning / review / optimization roles across any stream
- Status: Available

### Codex
- Branch: `TBD`
- Scope: Sprint 46 kickoff, integration, and engineering lead across the next streams
- Status: Available

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
| `specs/sprint-32-closeout.md` | Sprint 32 | Next sprint | Reference — warehouse team-prep follow-ons and DB-first team intelligence notes |

---

## Merge Order

1. Team 1 — TBD
2. Team 2 — TBD
3. Team 3 — TBD
4. Final integration / verification / merge to `master`

---

## Sprint Work Allocation

| Files / Directories | Assigned this sprint |
|---------------------|----------------------|
| `TBD` | TBD |
| `TBD` | TBD |
| `frontend/package.json`, `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts` | Shared contract surface — edits must stay additive and centrally coordinated |

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

2026-04-12 (Codex): Sprint 45 branch closeout prepared on `feature/sprint-45-team-general-splits`. Shipped canonical `TeamDashboardByGeneralSplits` persistence through `team_split_stats`, daily-sync refresh, thin persisted `GET /api/teams/{abbr}/splits`, parsing/sync/API/migration tests, and official-data/backlog docs. No UI work shipped; team shooting splits, player splits, play-type, and richer prep/compare consumers remain follow-ons. See `specs/sprint-45-closeout.md` before Sprint 46 kickoff.
2026-04-12 (Codex): Sprint 45 active on `feature/sprint-45-team-general-splits`. Scope is backend-first canonical official TeamDashboardByGeneralSplits persistence: `team_split_stats`, daily refresh, thin team splits read API, targeted tests, and official-data docs. No major UI work planned; shooting splits and play-type remain follow-ons.
2026-04-10 (Codex): Sprint 44 closed on `master`. Shipped canonical persisted official team season dashboards, daily-sync official player/team season refresh, a source-of-truth official-data matrix, leaderboard metric-library expansion plus NULL shooting-percent derivation, and a substantially stronger Player Stats workspace with grouped metrics, spotlight cards, denser table controls, richer empty/loading states, and URL-backed workspace state. Verification covered targeted backend official-data/leaderboard tests plus frontend `npm run lint` and `npm run build`. See `specs/sprint-44-closeout.md` before Sprint 45 kickoff.
2026-04-06 (Codex): Sprint 43 closed on `feature/sprint-43-foundation-hardening`. Shipped Alembic-backed schema management, removed startup-time schema mutation and the remaining request-time sync seam, consolidated decision intelligence behind `decision_support_service.py`, clarified warehouse-first vs `legacy-compatibility` runtime policy, and closed the live decision follow-through timeout with lighter service-owned style snapshots. Verification covered targeted migration/decision/prep backend tests, full backend `pytest`, `python -m compileall backend`, frontend `npm run lint`, frontend `npm run build`, and local decision/follow-through HTTP smoke checks. See `specs/sprint-43-closeout.md` and `specs/sprint-43-architecture-audit.md` before Sprint 44 kickoff.
2026-04-06 (Codex): Sprint 42 closeout prepared on `feature/sprint-42-opponent-aware-prep-decision`. Shipped opponent-aware prep rationale, richer focus levers, a backend-driven team decision workspace, and stronger prep/pre-read/compare/replay continuity. Verification covered targeted prep/decision/coaching backend tests, full backend `pytest`, frontend `npm run build`, and local prep/decision route smoke checks. See `specs/sprint-42-closeout.md` before Sprint 43 kickoff.
2026-04-05 (Codex): Sprint 41 closeout prepared on `feature/sprint-41-replay-adoption-insights`. Shipped replay adoption across insights by making trend cards and What-If emit source-aware replay targets, switching the trend cards UI onto the backend cards API, and preserving replay continuity into compare and Game Explorer. Verification covered targeted replay/scenario backend tests, full backend `pytest`, and frontend `npm run build`. See `specs/sprint-41-closeout.md` before Sprint 42 kickoff.
2026-04-05 (Codex): Sprint 40 closeout prepared on `feature/sprint-40-event-replay-scouting`. Shipped event-centered Game Explorer replay, sequence-aware 3D drill-down, source-aware replay handoffs from shot lab and scouting, and richer scouting clip anchors with event-backed export context. Verification covered full backend `pytest`, targeted replay/scouting backend tests, and frontend `npm run build`. See `specs/sprint-40-closeout.md` before Sprint 41 kickoff.
2026-04-05 (Codex): Sprint 39 closeout prepared on `master`. Shipped canonical shot-payload validation across both write paths, stricter completeness semantics, more honest exact/derived/timeline shot linkage, scenario-id normalization, source-aware compare/scouting follow-through, and backlog refresh with a standalone MVP Tracking section. Verification covered targeted backend `pytest` for shotchart/coaching/compare surfaces plus frontend `npm run build`. See `specs/sprint-39-closeout.md` before Sprint 40 kickoff.
2026-04-05 (Codex): Sprint 38 closed on `feature/sprint-38-platform-overhaul`. Shipped canonical shot/event completeness reporting, team-defense shot surfaces, shareable shot-lab snapshots, and the first 3D shot/game visualizer foundation. See `specs/sprint-38-closeout.md` before Sprint 39 kickoff.
2026-04-05 (Codex): Sprint 37 closed on `feature/sprint-37-situational-shot-intelligence`. Shipped situational shot filters, richer persisted shot context, self-service shot refresh, and the first shot-lab bridge into Game Explorer. Verification covered full backend `pytest`, frontend `npm run lint`, frontend `npm run build`, plus local route/API smoke checks. See `specs/sprint-37-closeout.md` before Sprint 38 kickoff.
2026-04-04 (Codex): Sprint 36 closed on `feature/sprint-36-shot-lab-renaissance`. Shipped the shot-lab visual renaissance across player, compare, and evolution surfaces, including the shared shot-lab surface system, hero `ShotSprawlMap` redesign, shot-frequency heatmap refresh, and a shared `ShotCourt` foundation. Verification covered frontend `npm run lint` and `npm run build`. See `specs/sprint-36-closeout.md` before Sprint 37 kickoff.
2026-04-03 (Codex): Sprint 35 closeout prepared on `feature/sprint-35-shot-lab-expansion`. Shipped enriched shot payloads with date windows, the player shot lab, compare shot lab, and playoff-capable ShotSeasonEvolution. Automated verification covered full backend `pytest` plus frontend `npm run lint` and `npm run build`. Live historical shot backfill was attempted via `backend/data/backfill_shot_lab.sh` but hit repeated `stats.nba.com` timeouts, so that ops run remains a follow-up. See `specs/sprint-35-closeout.md` before Sprint 36 kickoff.
2026-04-03 (Claude): Sprint 34 closed on `master`. Shipped all four Goldsberry shot chart features (ShotValueMap, ShotSprawlMap, ShotDistanceProfile, ShotSeasonEvolution). Single-stream frontend-only sprint, no Codex branch. See `specs/sprint-34-closeout.md` before Sprint 35 kickoff.
2026-04-03 (Codex): Sprint 32 closed on `master` as a single-stream sprint. Shipped warehouse-backed modern team intelligence, readiness metadata on team intelligence, the DB-first prep queue endpoint, and the new team-page prep workflow with urgency framing, scouting-mode launch, and share links. Closeout verification covered full backend `pytest` plus frontend `npm run lint` and `npm run build`. See `specs/sprint-32-closeout.md` before Sprint 33 kickoff.
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
