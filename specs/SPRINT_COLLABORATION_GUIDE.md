# Sprint Collaboration Guide

How to run a sprint with two agents (Claude + Codex) working in parallel.

---

## Phase 1 — Kickoff

**You do first:**
1. Define the sprint goal, assign scopes, and set the merge order in `AGENTS.md`
2. Make sure each agent has a clearly named branch and a clear list of owned files

**Then prompt each agent separately:**
> "Sprint N is starting. Run /sprint-kickoff."

Each agent reads `AGENTS.md`, gets on their branch, and starts work independently. You don't need to sync them to each other — `AGENTS.md` is the shared source of truth.

---

## Phase 2 — During the Sprint

Agents work in parallel. The only coordination needed:

- **Shared files** (`types.ts`, `api.ts`, `models.py`, `ensure_schema.py`, `main.py`) — each agent claims their files in the Lock Table before touching them. `types.ts` and `api.ts` are append-only: new interfaces and functions go at the bottom only.
- **Dependencies between agents** — if one agent needs the other's output first, they write a spec and mark it "Ready" in the Handoff Queue in `AGENTS.md`.

You can check in on each agent individually at any point. No need to coordinate them to each other mid-sprint unless there's an explicit dependency.

---

## Phase 3 — Closeout

**This is where things can go wrong.** The rule is: close one agent at a time, in the merge order defined in `AGENTS.md`.

### The wrong way
Prompting both agents to close out at the same time. If Claude's branch hasn't merged yet and you prompt Codex to close out, Codex will look at `master`, see the unmerged branch, and document it as "nothing shipped." The closeout doc, CLAUDE.md, and AGENTS.md all end up wrong — and you get merge conflicts on the push.

### The right way

**Step 1** — Prompt the first agent (per merge order):
> "Sprint N is closing. Run /sprint-closeout."

Wait for confirmation that the push succeeded. You can verify with:
```
git log origin/master --oneline -5
```

**Step 2** — Only after that commit is visible on origin, prompt the second agent:
> "Sprint N is closing. [Agent 1]'s branch is merged. Merge your branch and finish the closeout."

The second agent adds their section to the closeout doc and pushes on top.

**Step 3** — Verify:
- Both merges present in `git log origin/master`
- `specs/sprint-N-closeout.md` reflects both agents' actual shipped work
- `AGENTS.md` is reset to Sprint N+1 kickoff state

---

## Slash Commands

These skills are available to streamline the mechanical steps:

| Command | What it does |
|---------|-------------|
| `/sprint-kickoff` | Reads `AGENTS.md`, verifies branch, fetches, checks lock table and handoff queue, updates status row |
| `/sprint-closeout` | Merges sprint branch to master first, then writes closeout doc, updates CLAUDE.md, resets AGENTS.md, pushes |
| `/claim-file <path>` | Claims a shared file in the lock table with the append-only reminder |

---

## The One Rule That Prevents Most Problems

> **Never prompt both agents to close out at the same time. Trigger them sequentially — agent 1 confirms push, then agent 2 runs closeout.**

---

## Quick Reference: Who Does What

| Phase | Who acts | What triggers it |
|-------|----------|-----------------|
| Kickoff | You set scope in `AGENTS.md`, then prompt both agents | You decide sprint goals |
| Mid-sprint | Agents work independently | No trigger needed |
| Closeout — agent 1 | Prompt Claude (or whichever is first in merge order) | Sprint is done |
| Closeout — agent 2 | Prompt Codex | Agent 1's push confirmed on `origin/master` |
