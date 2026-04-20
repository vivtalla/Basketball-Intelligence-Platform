# Agent Coordination

Last updated: 2026-04-20 by Claude (Sprint 61 kickoff)

> Both agents read this file before touching code at the start of every session.
> The canonical source of truth is the clean `master` checkout at `/Users/viv/Documents/Basketball Intelligence Platform`.
> If a future session starts from another branch or worktree, return to this canonical root first unless the sprint explicitly says otherwise.
> All new sprint implementation happens on sprint branches/worktrees, never directly on `master`.
> At sprint close, update the sprint closeout note, refresh `specs/BACKLOG.md`, reset this file for the next sprint, and update the sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field | Value |
|-------|-------|
| Sprint | 61 |
| Goal | Shot Lab visual polish + replay examples AND Shot Intelligence Ops + baseline materialization |
| Started | 2026-04-20 |
| Target merge | TBD |
| Sprint shape | Single-stream Claude-only (no Codex parallel track) |
| Branch | `feature/sprint-61-shot-lab-polish-and-ops` |
| Worker policy | Explore agents for research only; main rollout does all implementation |

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
- Branch: `feature/sprint-61-shot-lab-polish-and-ops`
- Scope: (1) Richer hover tooltips on ShotValueMap/Sprawl/Distance surfacing attempts/expected/delta/confidence; (2) "Show me examples" replay handoffs from quality/creation bins into Game Explorer; (3) Factor ShotIdentityBadges into player/compare/prep surfaces; (4) New Shot Intelligence Ops panel on `/coverage` with team readiness, stale players, missing-context warnings; (5) `shot_quality_baselines` materialization table with `get_or_build_baseline`; (6) Backfill control endpoints + action buttons.
- Status: In progress

### Codex
- Branch: —
- Scope: Not staffed this sprint
- Status: Idle

---

## Shared File Lock Table

Claim a shared file here before editing. If a file is already claimed, read that branch before planning and do not edit until the claim is released or the work merges.

`frontend/src/lib/types.ts` and `frontend/src/lib/api.ts` are append-only.
`backend/db/models.py` and `backend/db/ensure_schema.py` are always claimed together.

| File | Claimed by | Purpose |
|------|------------|---------|
| `backend/routers/shotchart.py` | Claude | Replay examples on quality/creation; ops + refresh endpoints |
| `backend/services/shot_quality_service.py` | Claude | Baseline materialization path + replay sampling |
| `backend/services/shot_intelligence_ops_service.py` | Claude | NEW — ops aggregation across roster |
| `backend/models/shotchart.py` | Claude | `ShotReplayExample`, ops response types |
| `backend/db/models.py` | Claude | `ShotQualityBaseline` ORM (append) |
| `backend/alembic/versions/` | Claude | `shot_quality_baselines` migration |
| `frontend/src/components/ShotValueMap.tsx` | Claude | Hover tooltip + examples drawer |
| `frontend/src/components/ShotSprawlMap.tsx` | Claude | Grid-cell hover overlay |
| `frontend/src/components/ShotDistanceProfile.tsx` | Claude | Extended Recharts tooltip |
| `frontend/src/components/ShotIntelligencePanel.tsx` | Claude | Mount chips; factor out identity badges |
| `frontend/src/components/PlayerHeader.tsx` | Claude | Mount ShotIdentityBadges |
| `frontend/src/components/ComparisonView.tsx` | Claude | Mount ShotIdentityBadges |
| `frontend/src/app/coverage/page.tsx` | Claude | Mount ShotIntelligenceOpsPanel |
| `frontend/src/lib/api.ts` | Claude | Append-only: ops hooks, replay_examples shape |
| `frontend/src/lib/types.ts` | Claude | Append-only: replay example, ops types |

New components created this sprint (no prior claim needed):
`ShotHoverTooltip.tsx`, `ShotExamplesChips.tsx`, `ShotIdentityBadges.tsx`, `ShotIntelligenceOpsPanel.tsx`, `useShotIntelligenceOps` hook.

---

## Handoff Queue

Specs or review notes written by one stream for another. Check this before starting work.

| Spec file | From | To | Status |
|-----------|------|----|--------|
| `specs/data-architecture.md` | Sprint 26 | Next sprint | Reference — read before touching data layer |
| `specs/sprint-55-closeout.md` | Sprint 55 | Sprint 61 | Reference — Shot Lab Intelligence baseline |
| `specs/sprint-60-closeout.md` | Sprint 60 | Next sprint | Reference — X-Ray promotion + explainability parity baseline |

---

## Merge Order

Single-stream sprint — `feature/sprint-61-shot-lab-polish-and-ops` merges directly to `master` at sprint close.

---

## Sprint Work Allocation

Sprint 61 is single-stream (Claude only). Six workstreams executed sequentially:

1. **WS-A1 hover affordances** — Shared `ShotHoverTooltip.tsx`; extend ShotValueMap / ShotSprawlMap / ShotDistanceProfile tooltips with attempts, expected FG%, delta, `sample_confidence` band.
2. **WS-A2 replay examples** — Backend: sample ≤3 highest |delta| shots per `ShotQualityBin` with `game_id`+`event_num`, attach as `replay_examples` on `/quality` and `/creation`. Frontend: `ShotExamplesChips.tsx` rendering Game Explorer deep links.
3. **WS-A3 identity surfaces** — Factor `IdentityCards()` out of `ShotIntelligencePanel` into standalone `ShotIdentityBadges.tsx`; mount in `PlayerHeader`, `ComparisonView` summary, prep card detail.
4. **WS-B1 ops panel** — `GET /shotchart/ops/{season}` + `shot_intelligence_ops_service.py` + `ShotIntelligenceOpsPanel.tsx` + `useShotIntelligenceOps` hook on `/coverage`.
5. **WS-B2 baseline materialization** — New `shot_quality_baselines` table + Alembic migration + `get_or_build_baseline(season, methodology_version)` with `shot_quality_v1` default.
6. **WS-B3 backfill controls** — `POST /shotchart/ops/{season}/refresh-baseline` and `.../refresh-stale-players` endpoints through the existing warehouse job framework; action buttons in ops panel.

Reused patterns (do not rebuild):
- Hover tooltip pattern: `opportunity/OpportunityDriverBar.tsx` + `SIGNAL_DESCRIPTIONS`
- Replay chip pattern: `trajectory/EvidenceGames.tsx`, `TrendCardsPanel.tsx` `replay_target.deep_link_url`
- Methodology drawer: `opportunity/MethodologyDrawer.tsx`
- Ops dashboard shell: `coverage/page.tsx` with `WarehousePipelinePanel` + `MvpCoveragePanel`

Plan file: `~/.claude/plans/plan-sprint-related-to-foamy-corbato.md`.

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

2026-04-20 (Claude): Sprint 61 kickoff on `feature/sprint-61-shot-lab-polish-and-ops`. Plan file: `~/.claude/plans/plan-sprint-related-to-foamy-corbato.md`. Two backlog themes taken to completion in one sequential single-stream sprint: Shot Lab Visual Polish + Replay Examples, and Shot Intelligence Ops + Materialization. Six workstreams sequenced A1→A2→A3→B1→B2→B3.
2026-04-19 (Claude): Sprint 60 closed on `feature/sprint-60-insights-xray-explainability` and merged to `master`. Shipped Play-Style X-Ray tab promotion, Trajectory + Trends explainability parity, and MVP lineup-aware teammate on/off swings. 37 new backend tests. Closeout: `specs/sprint-60-closeout.md`.
2026-04-19 (Codex): Sprint 59 implementation complete on `codex-sprint-59-insights-trend-overhaul`. Shipped Insights Trend Intelligence overhaul with canonical trend card service, expanded team/player trend contract, shared `player_id`/`signal` URL pinning across Trends/Opportunity/Trajectory, active Team Roll-Up tile pinning, and hard deletion of deprecated `/api/insights/usage-efficiency`.
2026-04-19 (Claude): Sprint 58 closed. Shipped multi-axis Opportunity Workspace replacing USG/TS two-lane board: 5-signal capped z-score service, new /api/insights/opportunity endpoint, full UsageEfficiencyDashboard rewrite, 8 opportunity/ components with hover driver descriptions, and 13 backend tests. Deprecated (not deleted) old usage-efficiency endpoint. Next: hard-delete deprecated endpoint, cross-tab chip in InsightsHeader, opportunity score caching.
2026-04-19 (Claude): Sprint 57 closed on `feature/sprint-57-insights-revamp` and merged to `master`. Shipped Trajectory two-column revamp with rolling sparklines, driver decomp, clutch/on-off/shot-quality cards, evidence games, lineup context service, shared InsightsHeader, and lineup context integration in MVP + player profile. Closeout: `specs/sprint-57-closeout.md`.
2026-04-19 (Codex): Sprint 56 closed on `codex/sprint-56-player-impact-profile-clarity` and prepared for merge to `master`. Shipped MVP Team Impact, Voter Room team-impact evidence, Team Impact & Clutch profile panel, player profile cleanup, and Shot Lab tab relocation for action/distance/context workflows. Closeout: `specs/sprint-56-closeout.md`.
2026-04-19 (Codex): Sprint 55 closed on `codex/sprint-55-shot-lab-intelligence` and prepared for merge to `master`. Shipped Shot Lab Intelligence with `shot_quality_v1`, player and team-defense quality/creation/identity/coverage endpoints, compare and team-defense parity, snapshot intelligence metadata, and coverage-aware methodology. Closeout: `specs/sprint-55-closeout.md`.
