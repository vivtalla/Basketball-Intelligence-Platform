# Agent Coordination

Last updated: 2026-04-17 by Claude (Sprint 52 kickoff — MVP Holistic Case Engine)

> Both agents read this file before touching code at the start of every session.
> The canonical source of truth is the clean `master` checkout at `/Users/viv/Documents/Basketball Intelligence Platform`.
> If a future session starts from another branch or worktree, return to this canonical root first unless the sprint explicitly says otherwise.
> All new sprint implementation happens on sprint branches/worktrees, never directly on `master`.
> At sprint close, update the sprint closeout note, refresh `specs/BACKLOG.md`, reset this file for the next sprint, and update the sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field | Value |
|-------|-------|
| Sprint | 52 |
| Goal | MVP Holistic Case Engine — impact-consensus, clutch, opponent-adjusted context, scoring profiles, and four signature visuals |
| Started | 2026-04-17 |
| Target merge | TBD |
| Sprint shape | Single-stream Claude — data layer + backend scoring profiles + frontend viz expansion |
| Branch | `feature/sprint-52-mvp-holistic-case` |
| Worker policy | Single-stream Claude implementation unless bounded independent subtasks emerge |

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
- Branch: `feature/sprint-52-mvp-holistic-case`
- Scope: External impact metric ingestion + attribution, clutch/opponent-adjusted tables, scoring profiles refactor (`mvp_service.py`), new `/api/mvp/sensitivity` endpoint, and four new MVP page visuals (Impact Consensus Radar, Weighting-Sensitivity Slope, Clutch Card, Signature Games timeline)
- Status: In progress

### Codex
- Branch: —
- Scope: —
- Status: Not assigned

---

## Shared File Lock Table

Claim a shared file here before editing. If a file is already claimed, read that branch before planning and do not edit until the claim is released or the work merges.

`frontend/src/lib/types.ts` and `frontend/src/lib/api.ts` are append-only.
`backend/db/models.py` and `backend/db/ensure_schema.py` are always claimed together.

| File | Claimed by | Purpose |
|------|------------|---------|
| `frontend/src/lib/types.ts` | Claude | Sprint 52 additive MVP case contracts (impact consensus, clutch, opponent-adjusted, sensitivity) |
| `frontend/src/lib/api.ts` | Claude | Sprint 52 MVP profile + sensitivity API helpers |
| `backend/db/models.py` | Claude | Sprint 52 clutch/opponent-splits ORM + metric attribution columns |
| `backend/db/ensure_schema.py` | Claude | Paired with models.py |
| `backend/services/mvp_service.py` | Claude | Sprint 52 scoring profiles refactor |
| `backend/routers/mvp.py` | Claude | Sprint 52 profile query + sensitivity endpoint |
| `frontend/src/app/mvp/page.tsx` | Claude | Sprint 52 profile selector + sensitivity chart mount |
| `frontend/src/components/MvpRacePanel.tsx` | Claude | Sprint 52 case detail extensions |

---

## Handoff Queue

Specs or review notes written by one stream for another. Check this before starting work.

| Spec file | From | To | Status |
|-----------|------|----|--------|
| `specs/data-architecture.md` | Sprint 26 | Next sprint | Reference — read before touching data layer |
| `specs/sprint-48-closeout.md` | Sprint 48 | Sprint 52 | Reference — MVP Race Tracker baseline |

---

## Merge Order

1. Claude — `feature/sprint-52-mvp-holistic-case`
2. Final integration / verification / merge to `master`

---

## Sprint Work Allocation

Sprint 52 allocation — single-stream Claude

| Files / Directories | Assigned this sprint |
|---------------------|----------------------|
| `backend/alembic/versions/0006_mvp_impact_and_clutch.py` (new) | Claude — clutch + opponent-splits + attribution schema |
| `backend/db/models.py`, `backend/db/ensure_schema.py` | Claude — ORM additions paired with migration |
| `backend/data/mvp_impact_import.py` (new) | Claude — external metric CSV ingestion CLI |
| `backend/services/mvp_service.py` | Claude — scoring profiles + pillars refactor |
| `backend/services/mvp_clutch_service.py` (new, if needed) | Claude — clutch sync/materialization |
| `backend/routers/mvp.py` | Claude — profile param + `/api/mvp/sensitivity` |
| `backend/models/mvp.py` | Claude — Pydantic schema extensions |
| `frontend/src/app/mvp/page.tsx` | Claude — profile selector + sensitivity chart mount + methodology rewrite |
| `frontend/src/components/MvpRacePanel.tsx` | Claude — case detail wiring for new visuals |
| `frontend/src/components/MvpImpactRadar.tsx` (new) | Claude |
| `frontend/src/components/MvpSensitivitySlope.tsx` (new) | Claude |
| `frontend/src/components/MvpClutchCard.tsx` (new) | Claude |
| `frontend/src/components/MvpSignatureGames.tsx` (new) | Claude |
| `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts` | Claude — additive contract additions only |

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
- Do not spawn workers for vague "explore the codebase" requests
- Every worker prompt must include:
  - exact ownership
  - allowed files or subsystem
  - expected output artifact
  - reminder not to revert others' changes
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

2026-04-17 (Claude): Sprint 52 kicked off on `feature/sprint-52-mvp-holistic-case`. Plan file at `~/.claude/plans/i-want-to-plan-declarative-corbato.md`. Goal: remove box-score bias from MVP tracker by introducing transparent scoring profiles (Box-First / Balanced / Impact-Consensus), ingesting external impact metrics (EPM, LEBRON, RAPTOR, PIPM, DARKO, RAPM) with source attribution, adding clutch + opponent-adjusted tables, and shipping four signature visuals: Impact Consensus Radar, Weighting-Sensitivity Slope, Clutch & High-Leverage Card, Signature-Games Timeline. No weight tuning that favors any specific player.
2026-04-17 (Codex): Sprint 51 implemented on `codex-sprint-51-mvp-gravity-foundation`. Added DB-first MVP context tables for play-type, tracking, hustle, and gravity; official NBA Gravity source spike with CourtVue proxy fallback; MVP `gravity_profile`, `context_adjusted_score`, `/api/mvp/gravity`, Gravity map axis, Gravity case section, and methodology copy. Verification covered MVP/gravity/schema backend tests, official season sync/materialization/standings/shotchart targeted tests, frontend lint, frontend build, and `git diff --check`.
2026-04-17 (Claude): Sprint 48 closed on `feature/sprint-48-mvp-tracker`. Shipped MVP Award Race Tracker end-to-end: composite z-score service, GET /api/mvp/race endpoint, MvpRacePanel with ranked cards and momentum signals, /mvp page with season picker, and nav link. Single-stream Claude-only sprint. MVP home widget, position filter, and team shooting splits are top follow-ons for Sprint 49. See `specs/sprint-48-closeout.md` before Sprint 49 kickoff.
2026-04-17 (Claude): Sprint 47 closed on `feature/sprint-47-team-splits-ui`. Shipped full UI wiring of team general splits: TeamSplitsPanel, Splits tab on team page, and situational split signals on prep cards. Single-stream frontend-only sprint. Team shooting splits (DB pipeline) and ComparisonView splits wiring remain as top follow-ons.
2026-04-17 (Codex): Sprint 46 closeout prepared on `feature/sprint-46-ask-workspace`. Shipped the CourtVue Ask workspace: `POST /api/query/ask`, examples and metric registry endpoints, deterministic player/team query interpretation, threshold filters, recent player/team form, compare deep links, `/ask` UI, sortable/explainable result tables, and nav/home entry points. Verification covered full backend `pytest`, frontend `npm run lint`, and frontend `npm run build`. See `specs/sprint-46-closeout.md` before Sprint 47 kickoff.
2026-04-16 (Codex): Non-sprint live-QA standings pass completed on `master`. Shipped `2025-26` standings restoration by preferring official `team_season_stats` for totals/advanced metrics, preserving `team_standings` as snapshot fallback, enriching L10/home-away/streak/opponent PPG/recent trend from warehouse final-game rows, and rebuilding the standings page with side-by-side grouped stat views, sortable metric headers, hover definitions, corrected playoff/play-in separators, compact team abbreviations, and last-10 margin mini-graphs. Verification covered targeted `tests/test_standings_route.py`, frontend `npm run lint`, frontend `npm run build`, and local standings API/page smoke checks. See `specs/standings-live-qa-closeout-2026-04-16.md` before the next standings/UI pass.
