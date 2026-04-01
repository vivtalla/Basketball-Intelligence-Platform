# Product Backlog

Future-only backlog for CourtVue Labs.

Use this file for:
- ideas that should survive beyond a single sprint closeout
- product opportunities that are promising but not yet scheduled
- internal platform work that matters enough to stay visible

Guidelines:
- keep entries product-facing and concrete
- explain why the idea matters
- sketch the likely shape without turning it into a full sprint spec
- keep shipped work out unless it becomes a clear follow-on opportunity

---

## Now

### Decision-Driven Coaching Tools
Why it matters:
CourtVue Labs is strongest when it answers "what should we do?" rather than only describing what already happened.

Likely shape:
- `Lineup Expected Points Dashboard`
  Estimate points gained or lost if a lineup gets more or fewer minutes, with views by quarter, opponent style, and recent form.
- `Play-Type Expected Value`
  Grade actions such as pick-and-roll, post-up, spot-up, and drive-and-kick by scoring efficiency, turnover cost, and offensive rebound impact.
- `Matchup Exploit Flags`
  Surface pregame offensive and defensive edges such as weak coverages, favorable fronts, or isolation mismatches against a specific opponent.

### Guided Game Follow-Through
Why it matters:
When the product detects a meaningful trend or tactical edge, it should also point the user to the right game to inspect next.

Likely shape:
- connect decision surfaces directly to Game Explorer
- attach short reasons such as role flip, scoring spike, or matchup exploit
- preserve context so the user does not have to reconstruct the investigation manually

---

## Next

### Pace and Style Profiles
Why it matters:
Teams need a way to describe identity beyond basic record and offensive rating.

Likely shape:
- define style through pace, shot mix, paint emphasis, transition rate, and three-point aggression
- let coaches test simple tempo or style shifts against historical outcomes
- frame the results as "if we play faster/slower, what tends to happen?"

### Counterfactual What-If Suggestions
Why it matters:
Minimal viable AI should make the product feel smarter without turning it into a black box.

Likely shape:
- use regression-style possession modeling to answer questions like reducing isolation or increasing pick-and-roll volume
- return directional efficiency changes rather than overconfident predictions
- keep the model explainable and coach-readable

### Play-Style X-Ray
Why it matters:
Clustering can help a team understand not just how good it is, but what kind of team it actually is.

Likely shape:
- cluster teams into offensive styles such as pick-and-roll-heavy, drive-and-kick, post-oriented, or iso-heavy
- show where a team sits today and what shifts correlate with more efficient archetypes
- make style movement feel like a practical coaching discussion, not a data-science artifact

### In-Season Trend Cards
Why it matters:
A weekly coach workflow needs a tight summary of what is drifting, improving, or breaking.

Likely shape:
- compact weekly team cards for shot profile, bench vs starter performance, late-game choices, and rotation drift
- emphasize direction and significance over raw stat volume
- make the cards easy to scan, export, and discuss

### Event-Based Clip Anchors
Why it matters:
CourtVue Labs can become more useful to coaching staffs before native video support exists by working alongside the video tools they already use.

Likely shape:
- tag possessions by event type, quarter, team, and play-type context
- export clip-ready lists for shot attempts, turnovers, free-throw trips, and similar events
- keep the workflow video-adjacent rather than trying to replace film tools

### Play-Type Scouting Report Builder
Why it matters:
Opposition prep is a natural bridge between analytics and coaching communication.

Likely shape:
- generate a one-page scouting report for an opponent
- include top actions, weakest coverages, and preferred rotation patterns
- tie every claim to data points that staff can cross-check in film

### Comparison Sandbox Follow-Ons
Why it matters:
The first team-vs-team sandbox is live, but coaches will get more value once compare expands beyond one static team lens.

Likely shape:
- add lineup-to-lineup and style-to-style compare modes
- improve printable and shareable compare outputs for staff workflows
- deepen story labels with opponent-aware context instead of season-only comparisons

### Focus Levers Follow-Ons
Why it matters:
The four-factor coach panel is now useful, but it should evolve from team-only heuristics into sharper opponent-aware decision support.

Likely shape:
- add matchup-aware framing against a specific opponent
- improve impact labels from simple heuristics toward margin and win-probability context
- connect focus levers directly into pre-read and game-review workflows

### Usage vs Efficiency Follow-Ons
Why it matters:
The dashboard now surfaces burden allocation, but it still needs richer recommendation quality and confidence framing.

Likely shape:
- improve redistribution suggestions with clearer role and shot-profile context
- add team-specific calibration and confidence indicators
- connect usage flags into player trend and compare workflows

### Pre-Read Deck Follow-Ons
Why it matters:
The browser deck is live, but staff workflows will want easier sharing, archiving, and reuse.

Likely shape:
- add export-friendly PDF or share links
- support saved pre-read snapshots by matchup and date
- add lineup-specific notes and game-film follow-through links

### Metrics Follow-Ons
Why it matters:
The metrics workspace is live, but it still needs stronger carryover and reuse to feel like a true analyst tool.

Likely shape:
- expand curated metric collections and public templates
- improve metric-to-compare and metric-to-player handoff
- explore whether saved state should stay URL-based or evolve toward richer reusable workspaces

### Player Stats Workspace Polish
Why it matters:
The platform now has stronger editorial surfaces elsewhere, so Player Stats should feel like a first-class workspace too.

Likely shape:
- improve layout, hierarchy, and legibility
- tighten labels and full-name consistency across high-traffic surfaces
- make the workspace feel more analytical and less table-first

---

## Later

### Research Review Library
Why it matters:
CourtVue Labs can become more valuable if it helps users connect product workflows to the broader basketball research ecosystem.

Likely shape:
- summarize outside basketball research and link original articles or papers
- organize research by topic, method, and practical use
- make it a companion layer rather than a disconnected content archive

### NBA Draft Workspace
Why it matters:
Draft research is a natural adjacent expansion, but it is a separate product lane and should be treated deliberately.

Likely shape:
- add a draft page with NCAA men's data, prospect profiles, and mock-draft views
- support player cards, comparables, archetype tags, and draft-board style exploration
- keep draft work separate from current NBA workflow assumptions

### Court-Level Onboarding and Product Story
Why it matters:
As the product expands, it needs a clearer first-run experience and a stronger explanation of who it is for.

Likely shape:
- guide new users into player research, team prep, metrics, or coaching workflows
- sharpen home-page positioning and workspace explanations
- make CourtVue Labs feel like a coherent product, not just a collection of tools

### Workspace and Git Hygiene
Why it matters:
Internal cleanup is not user-facing, but it protects sprint velocity and reduces operational mistakes.

Likely shape:
- continue branch cleanup, remote cleanup, and worktree discipline
- keep AGENTS.md branch-maintenance policy current
- reduce stale branch risk and workspace confusion before each sprint kickoff

### Warehouse Visibility and Readiness UX
Why it matters:
Data reliability will remain a product feature, especially as decision-support surfaces get more ambitious.

Likely shape:
- improve worker visibility, backlog monitoring, and readiness messaging
- tighten runbooks around recovery and backfill operations
- help analysts understand when a workflow is fully trustworthy versus partially covered
