# Agent Coordination

Last updated: 2026-03-28 by Claude

> **Both agents read this file before touching any code at the start of every session.**
> Check sprint status, your branch, what the other agent owns, and the Merge Order.
> Then check the Handoff Queue. Then `git fetch origin`. Then begin work.

---

## Sprint Status

| Field        | Value                                    |
|--------------|------------------------------------------|
| Sprint       | 9                                        |
| Goal         | TBD — awaiting Vivek's sprint kickoff    |
| Started      | —                                        |
| Target merge | —                                        |

---

## Agent Assignments

### Claude
- Branch: `feature/sprint-9-[slug]`
- Scope: TBD
- Status: Not started
- PR: —
- Blocked on: nothing

### Codex
- Branch: `codex-sprint-9-[slug]`
- Scope: TBD
- Status: Not started
- PR: —
- Blocked on: nothing

---

## Shared File Lock Table

Claim a file here before writing a single line. If a file is already claimed, read that agent's branch before planning — do not edit a claimed file until their PR merges (then rebase), or until Vivek reassigns the claim.

`types.ts` and `api.ts` are **append-only** — add new interfaces/functions at the bottom only. Never edit lines written by the other agent.

`models.py` and `ensure_schema.py` are always claimed together.

| File                             | Claimed by | Purpose |
|----------------------------------|------------|---------|
| `backend/db/models.py`           | —          |         |
| `backend/db/ensure_schema.py`    | —          |         |
| `frontend/src/lib/types.ts`      | —          |         |
| `frontend/src/lib/api.ts`        | —          |         |
| `backend/main.py`                | —          |         |

---

## Handoff Queue

Specs written by one agent for the other. Check this before starting work — if a spec is marked "Ready" for you, read it before writing any code.

| Spec file | From | To | Status |
|-----------|------|----|--------|

---

## Merge Order (this sprint)

TBD at sprint kickoff. Format:

```
1. feature/sprint-9-[claude-work] (Claude) — no dependencies
2. codex-sprint-9-[codex-work] (Codex) — depends on Claude's PR merging first
```

---

## File Ownership

### Hard ownership — do not touch the other agent's files

| Files / Directories | Owner |
|---------------------|-------|
| `frontend/src/components/PlayerDashboard.tsx` | Claude |
| `frontend/src/components/ComparisonView.tsx` | Claude |
| `frontend/src/components/DualCareerArcChart.tsx` | Claude |
| `frontend/src/components/ExternalMetricsPanel.tsx` | Claude |
| `frontend/src/components/CareerArcChart.tsx` | Claude |
| `frontend/src/components/StatTable.tsx` | Claude |
| `frontend/src/app/leaderboards/` | Claude |
| `frontend/src/app/compare/` | Claude |
| `CLAUDE.md` | Claude |
| `frontend/src/components/TeamIntelligencePanel.tsx` | Codex |
| `frontend/src/components/TeamAnalyticsPanel.tsx` | Codex |
| `frontend/src/components/TeamLineupsPanel.tsx` | Codex |
| `frontend/src/app/teams/` | Codex |
| `frontend/src/app/coverage/` | Codex |
| `backend/services/pbp_service.py` | Codex |
| `backend/services/pbp_sync_service.py` | Codex |
| `backend/routers/teams.py` | Codex |

### Shared files — claim in Lock Table before editing

- `backend/db/models.py` + `backend/db/ensure_schema.py` (always claimed together)
- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `backend/main.py`

---

## Session Start Checklist

```
1. Read this file — sprint number, my branch, what the other agent owns, Merge Order
2. Check Lock Table — if the other agent claimed a file I need, read their branch first
3. Check Handoff Queue — if a spec is "Ready" for me, read it before writing code
4. git fetch origin && git log origin/master --oneline -5 — rebase if master advanced
5. Update my status row if it changed, commit: "docs: update [Claude|Codex] status in AGENTS.md"
6. Begin work
```

---

## Branch Naming Convention

| Agent | Format | Example |
|-------|--------|---------|
| Claude | `feature/sprint-N-{slug}` | `feature/sprint-9-player-contracts` |
| Codex | `codex-sprint-N-{slug}` | `codex-sprint-9-team-sync-v2` |

Sprint number prefix makes `git branch -a` immediately readable.

---

## Notes

*Free-form, dated, newest first. For cross-agent communication mid-sprint.*

2026-03-28 (Claude): Workflow system initialized. Sprint 8 (data persistence) is complete and merged to master. Awaiting Vivek's Sprint 9 kickoff. See `specs/` for archived specs from past sprints.
