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

### Final DB-First Cleanup for Non-Core Reads
Why it matters:
Sprint 30 made the main player/profile/career/gamelog/standings surfaces DB-first, and Sprint 32 moved the modern team-intelligence workflow onto warehouse-backed reads, but a few secondary routes still lean on `sync_player_if_needed`. That leaves a smaller but still real upstream dependency gap.

Likely shape:
- remove remaining request-time live fetches from advanced/trend-report style routes
- standardize readiness metadata on any remaining legacy reads
- keep `nba_api` only in queued/admin enrichment and explicit recovery workflows

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

### 3D Shot Charts and Play Reconstruction
Why it matters:
Sprint 38 introduced the first 3D shot/game scaffold, but the platform still needs the next layer: richer possession playback and a more expressive analytical scene that remains truthful about what is exact versus inferred.

Likely shape:
- deepen the procedural 3D half-court into a fuller possession playback system
- keep using shot arcs, event markers, and camera presets, but expand the scene choreography where it adds real analysis value
- preserve the exact/inferred labeling contract so the 3D layer stays trustworthy rather than theatrical

### Shot-to-Event Precision Follow-Ons
Why it matters:
Sprint 37 and Sprint 38 both improved the shot-lab bridge into Game Explorer, but the most helpful next gain is to make that handoff more exact whenever the data supports it.

Likely shape:
- use `shot_event_id`, `period`, `clock`, and play-by-play descriptions to tighten shot-to-event matching where support is strong
- highlight the specific play row or sequence in Game Explorer when a shot-lab link resolves cleanly
- keep ambiguous cases honest instead of forcing false precision

### Visualization Follow-Ons (Sprint 31 seeds)
Why it matters:
Sprint 31 shipped the visual renaissance layer. Remaining follow-ons extend it to comparison surfaces and add interactivity.

Likely shape:
- `PerformanceCalendar` side-by-side in `ComparisonView` so game rhythm can be compared directly
- Trend arrows on `HomeLeagueLeaders` require a `delta` field on `LeaderboardEntry` from backend
- Entrance animation polish: stagger fade-up on platform area cards, skeleton loaders shaped to match final layout

### Team Prep Queue Follow-Ons
Why it matters:
Sprint 32 gave teams a strong upcoming-opponent queue, but staff workflows will want sharper urgency calibration and a way to preserve the exact prep state for later review.

Likely shape:
- save prep snapshots by team/opponent/date instead of relying only on live query-state share links
- calibrate prep urgency and first-action summaries with stronger opponent-aware logic
- connect prep cards more directly into follow-through film, compare, and game-review workflows

---

## Now — Product Intelligence

### Counterfactual What-If Suggestions
Why it matters:
The first directional scenario layer is live, but it still needs stronger calibration and better coaching trust signals before it feels like a dependable decision workflow.

Likely shape:
- improve the current bounded scenario engine with clearer confidence framing, stronger comparable-pattern outputs, and opponent-aware variants where support is strong
- connect recommendations directly into compare, trend cards, and Game Explorer follow-through
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
The sandbox is stronger after Sprint 25, but it still needs better printing, sharing, and follow-through to become a true staff workflow.

Likely shape:
- improve printable and shareable compare outputs for teams, lineups, and styles
- preserve source context more deeply when compare launches from decision tools, scouting, or scenarios
- deepen story labels with matchup-aware and trend-aware framing instead of season-only summaries

### Play-Type Scouting and Clip Workflow
Why it matters:
Sprint 25 proved that inferred action families can support coach-readable prep, but the workflow is still early and should become more actionable for staff review.

Likely shape:
- strengthen inferred action-family confidence and opponent-specific scouting claims
- add event-based clip anchors and clip-list export so reports connect more directly to film review
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
The new lineup-impact and matchup-flag layer is useful, but it should keep getting sharper before the product relies on it as a primary coaching surface.

Likely shape:
- improve minute-redistribution logic, uncertainty wording, and opponent-style adjustments
- connect lineup suggestions more directly into rotation review and game-prep workflows
- expand matchup exploit flags without losing explainability

### Trend Cards Follow-Ons
Why it matters:
The weekly card format is now live, and the next gain comes from making it more exportable and more useful for lineup and game-review workflows.

Likely shape:
- add lineup-level weekly cards where sample support is strong
- improve export/share formatting for staff review
- connect meaningful card changes directly into follow-through games and compare launches

### Event-Based Clip Anchors
Why it matters:
CourtVue Labs can become more useful to coaching staffs before native video support exists by working alongside the video tools they already use.

Likely shape:
- tag possessions by event type, quarter, team, and play-type context
- export clip-ready lists for shot attempts, turnovers, free-throw trips, and similar events
- keep the workflow video-adjacent rather than trying to replace film tools

### Focus Levers Follow-Ons
Why it matters:
The four-factor coach panel is now useful, but it should evolve from team-only heuristics into sharper opponent-aware decision support.

Likely shape:
- add matchup-aware framing against a specific opponent
- improve impact labels from simple heuristics toward margin and win-probability context
- connect focus levers directly into pre-read and game-review workflows

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

### Shot Data Enrichment
Why it matters:
The current shot-chart storage supports today’s visuals, but deeper shot-quality analysis will need richer context than x/y, make/miss, and basic zone tags.

Likely shape:
- evaluate storing shot-level `game_id`, game date, period/clock, and richer context fields when upstream data supports it
- decide whether those enrichments should live in the existing JSON payload or a more structured summary table
- keep the first follow-on targeted to real product use cases instead of collecting fields speculatively
