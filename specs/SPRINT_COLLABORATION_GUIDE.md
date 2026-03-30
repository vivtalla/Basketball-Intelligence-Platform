# Sprint Collaboration Guide

How to run a sprint with the repo’s default **four-role delivery pipeline**:

`Architect -> Engineer -> Reviewer -> Optimizer -> Merge`

This guide replaces the older two-agent parallel model as the primary workflow.

---

## Core Model

The sprint branch is the unit of delivery.

- One sprint branch is created from current `master`
- The branch moves through four roles in sequence
- Merge happens only after both required gates pass:
  - `Reviewer`
  - `Optimizer`

Named agents like Codex or Claude may still do the work, but they operate as one of the four roles at a time.

---

## Phase 1 — Kickoff

**You do first:**
1. Define the sprint goal in `AGENTS.md`
2. Create or name the sprint branch
3. Assign the current role ownership in `AGENTS.md`
4. Set the first handoff target to `Ready for Engineer` once the architect spec is complete

**Then start the role sequence:**
- `Architect` reads the repo, explores the problem, and produces the build spec
- The spec or handoff artifact is marked `Ready for Engineer`

The key rule at kickoff:
- do not start implementation before the architect artifact is decision-complete

---

## Phase 2 — During the Sprint

The branch moves through the role pipeline in order.

### Architect
- designs the approach
- records interfaces, constraints, and acceptance criteria
- writes the handoff artifact

### Engineer
- implements from the architect artifact
- claims files in the lock table before editing
- marks the branch `Ready for Reviewer`

### Reviewer
- required correctness and convention gate
- either returns findings as `Blocked`
- or marks the branch `Ready for Optimizer`

### Optimizer
- required performance and efficiency gate
- either returns findings as `Blocked`
- or marks the branch `Ready to Merge`

### If multiple named agents are available

Multiple named agents can still participate, but they should preserve the same role order.

Allowed pattern:
- one named agent acts as `Architect`
- another acts as `Engineer`
- either one can later act as `Reviewer` or `Optimizer`

Not allowed:
- parallel implementation that skips the architect handoff
- merging after review but before optimization
- using person-to-person coordination rules that bypass the role statuses in `AGENTS.md`

---

## Handoffs and Locks

Use `AGENTS.md` as the source of truth for:
- current role ownership
- file locks
- handoff status
- merge readiness

### Handoff statuses

- `Ready for Engineer`
- `Ready for Reviewer`
- `Ready for Optimizer`
- `Ready to Merge`
- `Blocked`

### Locking

Shared files still require explicit lock claims before editing.

The important change is:
- claims are recorded by **role**
- not by named agent

---

## Phase 3 — Closeout

Closeout begins only after:
- the sprint branch is `Ready to Merge`
- both `Reviewer` and `Optimizer` gates are complete

### Closeout sequence

1. Merge the sprint branch to `master`
2. Push `master`
3. Update `specs/sprint-N-closeout.md`
4. Update the matching sprint summary in `CLAUDE.md`
5. Reset `AGENTS.md` to the next sprint kickoff state while preserving the same four-role workflow

### The wrong way

- letting `Engineer` merge directly without review and optimization
- treating `Optimizer` as optional
- resetting `AGENTS.md` before the merged branch is reflected on `master`

### The right way

- finish Architect
- finish Engineer
- pass Reviewer
- pass Optimizer
- merge
- close out docs

---

## Quick Reference

| Role | Purpose | Required output |
|------|---------|-----------------|
| Architect | Design the system and make implementation decision-complete | spec or handoff marked `Ready for Engineer` |
| Engineer | Build the approved design | branch marked `Ready for Reviewer` |
| Reviewer | Check quality, regressions, contracts, and conventions | findings or `Ready for Optimizer` |
| Optimizer | Check performance, efficiency, and operational quality | findings or `Ready to Merge` |

---

## The One Rule That Prevents Most Problems

> **Do not merge a sprint branch until it has passed both the Reviewer gate and the Optimizer gate.**
