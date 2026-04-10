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

## Now — Shot/Data Platform

### Canonical Event Completeness and Backfill
Why it matters:
Sprint 38 proved the platform needs a durable completeness contract, not another one-off field expansion. We now have explicit completeness reporting and richer shot/game context, but older rows still need systematic backfill and reconciliation before future features can assume the full payload is always present.

Likely shape:
- define the final medium-term payload CourtVue should preserve for shot charts, play analysis, and 3D reconstruction, including timing, event identity, action context, lineup/team state, and any other high-value upstream fields we are likely to need
- keep completeness metadata attached to product reads so the UI can tell the difference between “no data exists upstream,” “data exists but has not been enriched yet,” and “legacy row missing newly required fields”
- maintain repeatable backfill and validation workflows that upgrade older persisted rows whenever the canonical payload expands
- prefer payload completeness and durable storage contracts over piecemeal feature-specific additions, so future analysis surfaces can launch without another reactive persistence redesign

### Alias Backfill for Edge-Case Players
Why it matters:
Sprint 28 shipped the unresolved ops UI, but the underlying identity gaps (two-way players, recently traded players, inactive roster edge cases) still need targeted alias expansion to prevent future unresolved rows accumulating.

Likely shape:
- identify players who regularly generate unresolved rows and add manual alias entries
- add a targeted roster-refresh path to `sync_player_aliases` for two-way and recently moved players
- keep stub-player creation gated until roster truth is more authoritative

### Migration Adoption and Operational Discipline
Why it matters:
Sprint 43 moved the backend onto Alembic-backed migrations and removed runtime schema mutation from app startup, but the repo still needs a final discipline pass so future schema work never slips back toward ad hoc helpers or drift.

Likely shape:
- document and standardize the exact local/dev/prod migration workflow across README, runbooks, and any setup scripts that still assume `ensure_schema.py`
- remove any remaining legacy documentation or ops habits that imply startup-time DDL is acceptable
- add one or two small operational guardrails so future schema work follows migrations by default

### Legacy Compatibility Retirement
Why it matters:
Sprint 43 isolated modern warehouse-first runtime paths from historical compatibility mode more clearly, but legacy reads are still present for some older-season workflows. The next cleanup should be narrower and more deliberate instead of letting compatibility stay fuzzy.

Likely shape:
- audit which historical product surfaces still depend on legacy tables and decide which ones truly matter
- keep compatibility explicit where it is still needed, but retire dead branches and stale source labels where it is not
- continue surfacing honest readiness/runtime-policy metadata instead of mixing compatibility logic into modern paths

### Shot Lab Refinement and Precision Follow-Ons
Why it matters:
Sprint 35 turned player and compare shot charts into a real shot lab, and Sprint 38 extended that model into team-defense, snapshots, and stronger completeness signaling. The remaining gains are more about polish and exactness than core coverage.

Likely shape:
- sharpen shot-lab replay and snapshot workflows so saved states feel fully staff-ready
- continue tightening exact shot-to-event handoff and any compare/team-defense parity gaps that still feel rough
- add light explanatory affordances where the richer shot surfaces need more interpretation help

### Shot Lab Visual Polish
Why it matters:
Sprint 36 gave the shot lab a much stronger editorial identity, but the final layer of trust and delight still depends on court geometry polish, heatmap calibration, and clearer chart storytelling.

Likely shape:
- Finish the shared `ShotCourt` silhouette so the three-point shell, baseline, lane, and free-throw geometry unmistakably match a real half-court
- Keep tuning shot-frequency heatmaps so the hottest pockets pop on neutral backgrounds without making the whole surface feel heavy
- Add lightweight annotations or explainer overlays that help users read sprawl/value/distance views faster
- Extend the new shot-lab visual language to any remaining chart surfaces that still feel older than the player and compare shot suites

### Replay Workflow Expansion
Why it matters:
Sprints 40 and 41 turned replay into a real workflow across Game Explorer, scouting, shot lab, trend cards, and What-If. The next gains come from broadening the remaining surfaces and making sequence review feel even more analytical.

Likely shape:
- extend focused replay handoffs deeper into the newly shipped prep and decision workflow, especially when a selected lever can be tied to a strong recent-game sequence
- deepen the 3D scene choreography beyond the current short sequence view without losing the exact/derived/timeline trust model
- keep sharpening sequence summaries, labels, and analyst controls so replay feels like a coaching tool rather than only a visual drill-down

### Visualization Follow-Ons (Sprint 31 seeds)
Why it matters:
Sprint 31 shipped the visual renaissance layer. Remaining follow-ons extend it to comparison surfaces and add interactivity.

Likely shape:
- `PerformanceCalendar` side-by-side in `ComparisonView` so game rhythm can be compared directly
- Trend arrows on `HomeLeagueLeaders` require a `delta` field on `LeaderboardEntry` from backend
- Entrance animation polish: stagger fade-up on platform area cards, skeleton loaders shaped to match final layout

### Team Prep Queue Follow-Ons
Why it matters:
Sprint 42 made the prep queue substantially more opponent-aware, but the workflow can still get more direct and more archival-ready without losing its current lightweight feel.

Likely shape:
- add direct replay targets for prep cards when a recommended lever has credible recent-game evidence
- save prep snapshots by team/opponent/date instead of relying only on live query-state share links
- continue tuning urgency and first-action summaries for local performance and edge-case matchups

---

## Now — Product Intelligence

### Counterfactual What-If Suggestions
Why it matters:
The directional scenario layer now includes replay evidence and source-aware compare continuity, but it still needs stronger calibration and richer matchup trust signals before it feels like a dependable coaching workflow.

Likely shape:
- improve the current bounded scenario engine with clearer confidence framing, stronger comparable-pattern outputs, and opponent-aware variants where support is strong
- sharpen the replay-evidence selection logic so scenario follow-through feels more matchup-specific and less generic when support exists
- keep every scenario directional, bounded, and fully explainable

### Play-Style X-Ray
Why it matters:
The first style-identity layer is live, but teams will want richer archetype movement, stronger nearest-neighbor context, and more useful bridges from archetype to action.

Likely shape:
- deepen archetype labels, neighbor quality, and movement explanations
- show how style changes connect to matchup prep, compare, and what-if scenarios
- make the x-ray feel like a coaching identity tool rather than a standalone data-science card

### Comparison Sandbox Follow-Ons
Why it matters:
The sandbox is stronger after Sprint 25 and Sprint 42, but it still needs better printing, sharing, and story-specific follow-through to become a true staff workflow.

Likely shape:
- improve printable and shareable compare outputs for teams, lineups, and styles
- surface prep-selected levers and decision rationale more explicitly when compare launches from prep tools, scouting, or scenarios
- deepen story labels with matchup-aware and trend-aware framing instead of season-only summaries

### Play-Type Scouting and Clip Workflow
Why it matters:
Sprint 40 turned scouting claims into event-backed replay targets and exportable clip candidates, but the workflow is still early and should become more actionable for staff review.

Likely shape:
- strengthen inferred action-family confidence and opponent-specific scouting claims
- improve clip-list export formatting, selection controls, and workflow continuity with pre-read and compare
- keep all action-family claims evidence-backed and explicit about inference quality

---

## MVP Tracking

### MVP Award-Race Tracker
Why it matters:
CourtVue Labs is increasingly good at telling player-value and team-context stories, which makes a future MVP lens feel natural. A dedicated award-race tracker could turn existing player, trend, and matchup context into a staff-readable season narrative without pretending the product is itself the official vote.

Likely shape:
- track a living MVP board with movement over time instead of a static leaderboard snapshot
- combine player value indicators, team success context, recent trend momentum, and evidence-backed narrative bullets
- make the workflow transparent about what is model-driven versus editorial framing so the race view stays interpretable
- connect award-race entries back into player pages, compare, and trend workflows rather than creating a disconnected microsite

---

## Next

### Decision-Tool Calibration and Opponent Context
Why it matters:
Sprint 42 turned the team decision tab into a real opponent-aware workspace, and Sprint 43 cleaned up the architecture and removed the live timeout regressions. The next gains are now about calibration and workflow sharpness rather than emergency responsiveness.

Likely shape:
- improve minute-redistribution logic, uncertainty wording, and opponent-style adjustments
- connect lineup suggestions more directly into replay and rotation review workflows
- expand matchup exploit flags without losing explainability

### Trend Cards Follow-Ons
Why it matters:
The weekly card format is now backend-driven and replay-aware, and the next gain comes from making it more exportable and more useful for lineup and game-review workflows.

Likely shape:
- add lineup-level weekly cards where sample support is strong
- improve export/share formatting for staff review
- deepen how card-level evidence gets summarized so replay launches and compare launches feel more specific than “recent game context”

### Focus Levers Follow-Ons
Why it matters:
Sprint 42 made focus levers opponent-aware and workflow-connected, but the panel should still get more precise and more replay-aware over time.

Likely shape:
- improve impact labels from margin/possession heuristics toward cleaner confidence and game-swing framing
- add direct lever-to-replay follow-through when evidence is strong enough
- keep sharpening how focus levers align with matchup flags, compare, and decision tools so one coaching story survives across surfaces

### Usage vs Efficiency Follow-Ons
Why it matters:
The dashboard now surfaces burden allocation, but it still needs richer recommendation quality, clearer formula communication, and a final readability pass.

Likely shape:
- improve redistribution suggestions with clearer role and shot-profile context
- add team-specific calibration and confidence indicators
- continue simplifying score explanation and presentation so the page is immediately readable
- connect usage flags into player trend and compare workflows

### Pre-Read Deck Follow-Ons
Why it matters:
The browser deck is stronger after Sprint 27 and Sprint 32, but staff workflows will still want deeper archiving and broader decision context than live links alone can provide.

Likely shape:
- support saved pre-read snapshots by matchup and date
- add lineup-specific notes, compare launches, and game-film follow-through links

### Metrics Follow-Ons
Why it matters:
The metrics workspace is live, but it still needs stronger carryover and reuse to feel like a true analyst tool.

Likely shape:
- expand curated metric collections and public templates
- improve metric-to-compare and metric-to-player handoff
- explore whether saved state should stay URL-based or evolve toward richer reusable workspaces

### Player Stats Saved Views and Workflow Follow-Ons
Why it matters:
Sprint 44 substantially upgraded the Player Stats workspace with better hierarchy, spotlighting, mobile scan-ability, and URL-backed workspace state. The next gains are no longer basic polish; they are workflow and reuse improvements.

Likely shape:
- add named saved views or presets on top of the current URL-backed state model
- improve export or copy-ready sharing so filters and board context are easier to hand off in staff workflows
- keep refining dense-table ergonomics only where real workflow friction remains, instead of reopening general visual polish

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

### Shot Data Enrichment
Why it matters:
The current shot-chart storage supports today’s visuals, but deeper shot-quality analysis will need richer context than x/y, make/miss, and basic zone tags.

Likely shape:
- evaluate storing shot-level `game_id`, game date, period/clock, and richer context fields when upstream data supports it
- decide whether those enrichments should live in the existing JSON payload or a more structured summary table
- keep the first follow-on targeted to real product use cases instead of collecting fields speculatively
