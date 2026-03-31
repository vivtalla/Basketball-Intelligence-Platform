# Sprint Collaboration Guide

How to run a sprint with the repo's default **hybrid delivery model**:

`Architect -> Engineer -> Reviewer -> Optimizer -> Merge`

This guide supports both:
- dual-team parallel sprints for major feature work
- single-pipeline sprints for small, tightly coupled, or docs/ops work

---

## Core Model

The delivery stream is the unit of delivery.

- Every delivery stream moves through four roles in sequence
- Merge happens only after both required gates pass:
  - `Reviewer`
  - `Optimizer`
- Team count is chosen at sprint kickoff based on sprint shape

Named agents like Codex or Claude may still do the work, but they operate as one of the four roles at a time inside each delivery stream.

### Choose the sprint shape first

Use **dual-team** when:
- there are two independent user-facing features
- or one feature plus one bounded platform track

Use **single-pipeline** when:
- the work is tightly coupled
- the sprint is mostly docs/process/ops
- the sprint is too small to justify split coordination cost

Default:
- major product sprint = dual-team
- small or low-risk sprint = single-pipeline

---

## Phase 1 — Kickoff

**You do first:**
1. Define the sprint goal in `AGENTS.md`
2. Record the sprint shape decision in `AGENTS.md`
3. Create or name the sprint branch or branches
4. Assign the current role ownership in `AGENTS.md`
5. Set the first handoff target to `Ready for Engineer` once the architect spec is complete

**Then start the role sequence:**
- `Architect` reads the repo, explores the problem, and produces the build spec
- The spec or handoff artifact is marked `Ready for Engineer`

The key rule at kickoff:
- do not start implementation before the architect artifact is decision-complete

---

## Phase 2 — During the Sprint

Each delivery stream moves through the role pipeline in order.

### Architect
- designs the approach
- records interfaces, constraints, and acceptance criteria
- writes the handoff artifact

### Engineer
- implements from the architect artifact
- claims files in the lock table before editing
- marks the stream `Ready for Reviewer`

### Reviewer
- required correctness and convention gate
- either returns findings as `Blocked`
- or marks the stream `Ready for Optimizer`

### Optimizer
- required performance and efficiency gate
- either returns findings as `Blocked`
- or marks the stream `Ready to Merge`

### If multiple named agents are available

Multiple named agents can still participate, but they should preserve the same role order inside each stream.

Allowed pattern:
- Team A runs Architect -> Engineer -> Reviewer -> Optimizer
- Team B runs Architect -> Engineer -> Reviewer -> Optimizer
- or one named agent handles the single stream in role order for a small sprint

Not allowed:
- parallel implementation that skips the architect handoff
- merging after review but before optimization
- using person-to-person coordination rules that bypass the role statuses in `AGENTS.md`

### Worker usage inside a sprint

Spawned workers are optional and should be used selectively.

Good worker usage:
- bounded backend implementation
- bounded UI implementation
- isolated tests or fixtures
- isolated docs updates

Bad worker usage:
- vague codebase exploration
- duplicated analysis
- immediate blocking tasks the main agent is waiting on

Rule:
- keep worker tasks narrow, with explicit ownership and expected output
- prefer 1-2 workers per sprint track
- keep the main agent doing non-overlapping work while workers run

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

### Handoff artifact rule

Keep every artifact compact and decision-complete.

Architect spec:
- goal
- public interface changes
- behavior rules
- testing scenarios
- assumptions/defaults

Review note:
- findings
- fixes required
- final status

Optimizer note:
- findings
- fixes required
- final status

---

## Phase 3 — Closeout

Closeout begins only after:
- the delivery stream is `Ready to Merge`
- both `Reviewer` and `Optimizer` gates are complete

### Closeout sequence

1. Merge the sprint branch to `master`
2. Push `master`
3. Update `specs/sprint-N-closeout.md`
4. Refresh `specs/BACKLOG.md`
5. Update the matching sprint summary in `CLAUDE.md`
6. Reset `AGENTS.md` to the next sprint kickoff state while preserving the chosen hybrid workflow
7. Delete merged worktrees and stale merged branches

### The wrong way

- letting `Engineer` merge directly without review and optimization
- treating `Optimizer` as optional
- resetting `AGENTS.md` before the merged branch is reflected on `master`
- leaving stale worktrees and sprint branches behind after merge

### The right way

- finish Architect
- finish Engineer
- pass Reviewer
- pass Optimizer
- merge
- close out docs
- refresh backlog
- clean branches and worktrees

---

## Quick Reference

| Role | Purpose | Required output |
|------|---------|-----------------|
| Architect | Design the system and make implementation decision-complete | spec or handoff marked `Ready for Engineer` |
| Engineer | Build the approved design | stream marked `Ready for Reviewer` |
| Reviewer | Check quality, regressions, contracts, and conventions | findings or `Ready for Optimizer` |
| Optimizer | Check performance, efficiency, and operational quality | findings or `Ready to Merge` |

---

## The One Rule That Prevents Most Problems

> **Do not merge a sprint branch until it has passed both the Reviewer gate and the Optimizer gate.**

## The One Rule That Prevents Most Waste

> **Do not spend tokens on broad repeated context loading when a compact handoff artifact can carry the sprint forward.**
