# Agent Coordination

Last updated: 2026-04-27 by Claude (Sprint 70 closeout reset)

> Both agents read this file before touching code at the start of every session.
> The canonical source of truth is the clean `master` checkout at `/Users/viv/Documents/Basketball Intelligence Platform`.
> If a future session starts from another branch or worktree, return to this canonical root first unless the sprint explicitly says otherwise.
> All new sprint implementation happens on sprint branches/worktrees, never directly on `master`.
> At sprint close, update the sprint closeout note, refresh `specs/BACKLOG.md`, reset this file for the next sprint, and update the sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field | Value |
|-------|-------|
| Sprint | 71 |
| Goal | TBD at kickoff |
| Started | — |
| Target merge | — |
| Sprint shape | TBD at kickoff |
| Branch | TBD at kickoff |
| Worker policy | TBD at kickoff |

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
- Branch: TBD at kickoff
- Scope: No active sprint assignment
- Status: Not started

### Codex
- Branch: TBD at kickoff
- Scope: No active sprint assignment
- Status: Not started

---

## Shared File Lock Table

Claim a shared file here before editing. If a file is already claimed, read that branch before planning and do not edit until the claim is released or the work merges.

`frontend/src/lib/types.ts` and `frontend/src/lib/api.ts` are append-only.
`backend/db/models.py` and `backend/db/ensure_schema.py` are always claimed together.

| File | Claimed by | Purpose |
|------|------------|---------|
| — | — | No active claims; claim here at the next sprint kickoff before editing shared files |

---

## Handoff Queue

Specs or review notes written by one stream for another. Check this before starting work.

| Spec file | From | To | Status |
|-----------|------|----|--------|
| `specs/data-architecture.md` | Sprint 26 | Next sprint | Reference — read before touching data layer |
| `specs/sprint-55-closeout.md` | Sprint 55 | Next sprint | Reference — Shot Lab Intelligence baseline |
| `specs/sprint-history.md` | Sprint 60 | Next sprint | Reference — Sprint 60 section for X-Ray promotion + explainability parity baseline |
| `specs/sprint-63-closeout.md` | Sprint 63 | Next sprint | Reference — Team/Insights workflow expansion baseline |
| `specs/sprint-65-closeout.md` | Sprint 65 | Next sprint | Reference — Opportunity caching/handoff + scouting inference confidence baseline |

---

## Merge Order

TBD at kickoff. Next sprint branch/worktree is created at kickoff and merges back to `master` at closeout.

---

## Sprint Work Allocation

TBD at kickoff. Define areas and owners when the next sprint is scoped.

| Area | Files | Owner |
|------|-------|-------|
| — | — | — |

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

1. Stop local dev/test servers started during the sprint and confirm relevant ports/resources are free (`lsof -iTCP:8000`, `lsof -iTCP:3000`, warehouse workers, import jobs, or other long-running processes)
2. Create or update `specs/sprint-{NN}-closeout.md` with shipped work, deferred work, workflow lessons, and next-sprint seeds
3. Refresh `specs/BACKLOG.md` so shipped items are removed or rewritten as follow-ons
4. Reset `AGENTS.md` for the next sprint kickoff state
5. Update `CLAUDE.md` "Recent Sprints" section (keep last 2 sprints inline; move the oldest out)
6. Append the completed sprint summary to `specs/sprint-history.md`
7. Merge the sprint branch back into `master` locally and push `master` to `origin`
8. Confirm `master` contains the sprint closeout commit(s) before declaring the sprint closed

---

## Notes

*Free-form, dated, newest first. Use this for coordination and repo-state exceptions.*

2026-04-27 (Claude): Sprint 70 closed on `feature/sprint-70-design-system-integration` and merged to `master`. Design System Integration sprint: shipped Teams directory two-column redesign with conference filter and team detail preview, Metrics hero leader card with HeroHardwood texture (#1 ranked player, 72pt composite score), Pre-Read visual matchup header card with 6 bilateral MatchupBar comparison bars and a "Three things to win" Focus Levers section that surfaces previously-unrendered `data.focus_levers` from the API, and Compare deltas/takeaways panels (5 stat-delta cards + 3 plain-language bullets). Pure-frontend sprint with no backend changes; backend test count unchanged at 257 passing. Frontend `npm run build` and `npm run lint` clean (7 pre-existing warnings). Subagent rate-limit hit forced inline implementation — see closeout for the workflow lesson. Closeout: `specs/sprint-70-closeout.md`.

2026-04-27 (Codex): Sprint 69 implementation complete on `codex-sprint-69-team-fit-intelligence`. Shipped Team-Fit v2 explainability, `/api/team-fit/{player_id}`, Team-Fit similarity context pills, player analysis contexts with manual settings, automatic injury/recovery context from `player_injuries`, and injury-aware Trend Intelligence. Verification: 257 backend tests passing, `npm run build`, `npm run lint`, `git diff --check`, local Alembic migration `0011_player_analysis_contexts`; local backend/frontend servers killed and ports 8000/3000 confirmed clear. Closeout: `specs/sprint-69-closeout.md`.

2026-04-25 (Claude): Sprint 68 closeout on `feature/sprint-68-decision-intelligence-followups`. Closed all five Sprint-67 deferrals on one branch in one session: Opportunity `usg_pct` precision, Team-Fit similarity mode (with teammate-duplicate penalty), Scouting Brief deep-link banners (`source=brief`), coaching copy polish across 12 diagnosis tags + 5 brief cards, and the Player Archetype Evolution Timeline (new `/api/archetype/{id}/history` endpoint + `<ArchetypeEvolutionTimeline>` component). 4 new backend tests; full suite 247 passing. Closeout: `specs/sprint-68-closeout.md`.

2026-04-24 (Claude): Sprint 67 closeout on `feature/sprint-67-decision-intelligence`. Shipped the 15-archetype Player Archetype Engine, role-aware similarity (season + age modes), 12-tag Shot Profile Diagnosis, and the 5-card Scouting Brief. Three spec tune passes before code caught two routing bugs and one coverage gap; live-DB smoke caught two more bugs before merge. 47 new backend tests (243 passing). Closeout: `specs/sprint-67-closeout.md`. Cleaned up four untracked Sprint-65 leftover files that were silently breaking `npm run build`.

2026-04-23 (Claude): Sprint 67 kickoff on `feature/sprint-67-decision-intelligence`. Theme: Decision Intelligence — make the player page answer "Who is this player, how do they create value, and what should I do with that?" Three features: Player Archetype + Similarity Engine (Stream A, Claude), Shot Profile Diagnosis Panel + Scouting Summary Cards (Stream B, Codex). Plan file: `~/.claude/plans/you-are-acting-as-gentle-tiger.md`. Merge order A → B. Starting on A1 (archetype taxonomy spec).

2026-04-23 (Codex): Sprint 66 closed on `codex-sprint-66-staff-packet-handoff` and merged to `master`. Shipped named Pre-Read staff packets with editable title/note metadata, scouting claim pinning into frozen packets, packet library/history on `/pre-read`, markdown export, Prep Queue save continuity, and a manual smoke walkthrough that surfaced and resolved the missing live DB migration. Closeout: `specs/sprint-66-closeout.md`.
2026-04-23 (Claude): Sprint 65 closed on `feature/sprint-65-scouting-opportunity-fit` and merged to `master`. Shipped opportunity TTL cache + compare-handoff peers + role-fit AST/TOV depth, scouting claim inference confidence + opponent-aware ranking, `UsageEfficiencyDashboard.tsx` → `OpportunityDashboard.tsx` rename with stale scaffolding deletion, Compare + Pre-Read inbound-context banners, compound-position bucketing bugfix, and a Sprint-64 Tooltip formatter type fix. 14 new backend tests (193 total). Closeout: `specs/sprint-65-closeout.md`.
2026-04-23 (Claude): Sprint 65 kickoff on `feature/sprint-65-scouting-opportunity-fit`. Theme: Scouting & Opportunity Fit. Plan file: `~/.claude/plans/plan-next-sprint-you-jazzy-duckling.md`. Three workstreams sequenced A (opportunity caching + compare handoff + role-fit depth) → B (scouting inference confidence + opponent-aware ranking) → C (cross-tab glue + Usage* cleanup including rename of `UsageEfficiencyDashboard.tsx` → `OpportunityDashboard.tsx` and deletion of stale untracked Usage* scaffolding).
2026-04-22 (Codex): Sprint 63 closed on `feature/sprint-63-team-insights-workflow-expansion` and merged to `master`. Shipped canonical shot-profile reuse across compare/prep/pre-read/team-defense/X-Ray, richer X-Ray history + drift + handoffs, replay-aware coaching continuity, prep snapshots, and trust-note handling for ambiguous official split families. Closeout: `specs/sprint-63-closeout.md`.
2026-04-21 (Codex): Sprint 62 closeout prepared on `feature/sprint-62-style-intelligence-and-team-shooting-splits`. Added canonical `team_shooting_split_stats`, DB-first team shooting-splits API, team-page `Shooting` splits workspace, and shot-profile-driven Style X-Ray follow-ons. Verification passed (`pytest`, `npm run lint`, `npm run build`, `git diff --check`). Merged to `master` on 2026-04-22.
2026-04-20 (Claude): Sprint 61 implementation complete on `feature/sprint-61-shot-lab-polish-and-ops`. Shipped shared `ShotHoverTooltip`, replay-example chips with linkage-quality gating, `ShotIdentityBadges` in PlayerHeader + Compare, Shot Intelligence Ops panel on `/coverage`, `shot_quality_baselines` materialization (Alembic 0008) with `get_or_build_baseline`, and refresh-baseline / refresh-stale-players endpoints. 172 backend tests, frontend lint + build clean. Ready to merge.
2026-04-20 (Claude): Sprint 61 kickoff on `feature/sprint-61-shot-lab-polish-and-ops`. Plan file: `~/.claude/plans/plan-sprint-related-to-foamy-corbato.md`. Two backlog themes taken to completion in one sequential single-stream sprint: Shot Lab Visual Polish + Replay Examples, and Shot Intelligence Ops + Materialization. Six workstreams sequenced A1→A2→A3→B1→B2→B3.
2026-04-19 (Claude): Sprint 60 closed on `feature/sprint-60-insights-xray-explainability` and merged to `master`. Shipped Play-Style X-Ray tab promotion, Trajectory + Trends explainability parity, and MVP lineup-aware teammate on/off swings. 37 new backend tests. Reference summary: `specs/sprint-history.md` (Sprint 60 section).
2026-04-19 (Codex): Sprint 59 implementation complete on `codex-sprint-59-insights-trend-overhaul`. Shipped Insights Trend Intelligence overhaul with canonical trend card service, expanded team/player trend contract, shared `player_id`/`signal` URL pinning across Trends/Opportunity/Trajectory, active Team Roll-Up tile pinning, and hard deletion of deprecated `/api/insights/usage-efficiency`.
2026-04-19 (Claude): Sprint 58 closed. Shipped multi-axis Opportunity Workspace replacing USG/TS two-lane board: 5-signal capped z-score service, new /api/insights/opportunity endpoint, full UsageEfficiencyDashboard rewrite, 8 opportunity/ components with hover driver descriptions, and 13 backend tests. Deprecated (not deleted) old usage-efficiency endpoint. Next: hard-delete deprecated endpoint, cross-tab chip in InsightsHeader, opportunity score caching.
2026-04-19 (Claude): Sprint 57 closed on `feature/sprint-57-insights-revamp` and merged to `master`. Shipped Trajectory two-column revamp with rolling sparklines, driver decomp, clutch/on-off/shot-quality cards, evidence games, lineup context service, shared InsightsHeader, and lineup context integration in MVP + player profile. Closeout: `specs/sprint-57-closeout.md`.
2026-04-19 (Codex): Sprint 56 closed on `codex/sprint-56-player-impact-profile-clarity` and prepared for merge to `master`. Shipped MVP Team Impact, Voter Room team-impact evidence, Team Impact & Clutch profile panel, player profile cleanup, and Shot Lab tab relocation for action/distance/context workflows. Closeout: `specs/sprint-56-closeout.md`.
2026-04-19 (Codex): Sprint 55 closed on `codex/sprint-55-shot-lab-intelligence` and prepared for merge to `master`. Shipped Shot Lab Intelligence with `shot_quality_v1`, player and team-defense quality/creation/identity/coverage endpoints, compare and team-defense parity, snapshot intelligence metadata, and coverage-aware methodology. Closeout: `specs/sprint-55-closeout.md`.
