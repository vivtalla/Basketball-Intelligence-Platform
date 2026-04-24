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

### Shot Lab Court Geometry Polish
Why it matters:
Sprint 61 shipped richer hover affordances, replay-example chips, Shot Intelligence Ops panel, and baseline materialization — retiring the two prior Shot-Lab-centric backlog entries. What remains is the unfinished court-silhouette polish the earlier backlog noted.

Likely shape:
- Finish the shared `ShotCourt` silhouette so the three-point shell, baseline, lane, and free-throw geometry unmistakably match a real half-court
- Keep tuning shot-frequency heatmaps so the hottest pockets pop on neutral backgrounds without making the whole surface feel heavy

### Replay Workflow Follow-Ons
Why it matters:
Sprints 40, 41, and 63 turned replay into a real workflow across Game Explorer, scouting, shot lab, trend cards, Style X-Ray, prep, and related coaching handoffs. The next gains come from making sequence review feel more analytical and more selective, not merely broader.

Likely shape:
- deepen the 3D scene choreography beyond the current short sequence view without losing the exact/derived/timeline trust model
- improve sequence ranking and matchup-specific evidence selection so replay launches feel more intentional when multiple recent candidates exist
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
Sprints 42, 63, and 66 made the prep queue substantially more opponent-aware, replay-aware, and archival-ready. The next gains are less about basic save/reopen support and more about making packet archives easier to manage at staff scale.

Likely shape:
- add richer packet archive controls such as search, sort, season filters, and series/opponent grouping for staff prep libraries
- extend prep continuity into compare/export surfaces so a saved packet can become a fuller staff handoff
- continue tuning urgency and first-action summaries for local performance and edge-case matchups

### Team Shooting Split Workflow Expansion
Why it matters:
Sprints 62 and 63 shipped the canonical team shooting-splits foundation, team-page shooting dashboard, Style X-Ray shot-profile drivers, and deeper compare/prep/team-defense workflow use. The next gains come from tightening trust, expanding ops visibility, and improving how staff package those insights.

Likely shape:
- validate tricky official families such as assisted-shot semantics and expose honest trust notes when upstream meaning is ambiguous
- add stronger coverage-health and refresh visibility for the shooting-split families if they become a daily coaching dependency
- improve printable/shareable outputs for shot-profile matchup edges once the underlying trust framing is stable

---

## Now — Decision Intelligence (Sprint 67 follow-ons)

### Team-Fit Similarity Mode
Why it matters:
Sprint 67 shipped season + age similarity modes with archetype-labeled comps. The `team_fit` mode was spec'd and the service scaffold is in place, but the implementation was deferred to keep the sprint scope tight. `team_fit` is the variant a coach wants most — "which comps complement the current roster" — so finishing it has real staff value.

Likely shape:
- Implement the teammate-duplicate penalty described in `specs/sprint-67-archetype-rules.md` §1.7: for each feature, if the subject's z-score is within 0.5 of a same-team teammate's max z, multiply that feature's distance weight by 0.4.
- Replace the `NotImplementedError` in `similarity_service._build_candidate_pool` and the 501 in `routers/similarity.py`.
- Swap the frontend team-fit tab deferred-state card for real comps.

### Player Archetype Evolution Timeline
Why it matters:
Sprint 60 shipped the team Style X-Ray `MovementTimeline` for drift. The Sprint 67 player archetype engine is per-season; there's no multi-season archetype-drift surface yet. This is a natural extension once analysts start asking "how has this player's archetype changed?"

Likely shape:
- Port the team movement timeline pattern to players — classify each of a player's past seasons, render the sequence with transition markers and confidence bands.
- Keep the classifier deterministic; any time the archetype rules are retuned, every historical label can be recomputed instantly.

### Coaching Copy Polish for Diagnosis + Brief
Why it matters:
Sprint 67's shot diagnosis tag labels and scouting-brief headlines are accurate but not yet tuned for coaching ergonomics. Staff-facing copy should sound less like a data-science card and more like a pre-game note.

Likely shape:
- One pass on each of the 12 diagnosis tag labels and evidence templates for coaching phrasing.
- Similar pass on the five scouting-brief card summaries.
- Leave the methodology drawer factual; only the user-facing summary surfaces need the polish.

### Scouting Brief — Deep-Link Banners
Why it matters:
The Sprint 67 scouting brief cards carry `deep_link` fields that render as simple anchor links. The Sprint 65 inbound-context banner pattern (Compare and Pre-Read) is a better UX: when a user follows a brief card link, the destination surface should acknowledge the source context.

Likely shape:
- Add an inbound-banner behavior to Shot Lab when the URL carries `source=brief` and a tag key, mirroring the Sprint 65 source=opportunity / source=scouting banners.
- Preselect the relevant diagnosis tag / Shot Lab view on arrival.

### Opportunity Row `usg_pct` Precision
Why it matters:
The live-DB smoke during Sprint 67 surfaced a cosmetic bug: `OpportunityPlayerRow.usg_pct` is rounded to `round(x, 1)`, which collapses 0.285/0.30/0.32 into the same 0.3 display. Jokić, SGA, and Tatum all render as "Usage 30.0%" despite having distinct usage values.

Likely shape:
- Bump `round(x, 1)` to `round(x, 3)` at the opportunity service, or defer the rounding entirely to the display layer.
- Small fix; call it out only because it's a visible quality issue on the scouting brief.

---

## Now — Product Intelligence

### Counterfactual What-If Suggestions
Why it matters:
The directional scenario layer now includes replay evidence and source-aware compare continuity, but it still needs stronger calibration and richer matchup trust signals before it feels like a dependable coaching workflow.

Likely shape:
- improve the current bounded scenario engine with clearer confidence framing, stronger comparable-pattern outputs, and opponent-aware variants where support is strong
- sharpen the replay-evidence selection logic so scenario follow-through feels more matchup-specific and less generic when support exists
- keep every scenario directional, bounded, and fully explainable

### Style Intelligence Follow-Ons
Why it matters:
Sprints 60, 62, and 63 turned Style X-Ray into a real team-identity surface with archetypes, neighbors, movement, shot-profile drivers, drift context, and workflow bridges. What remains is calibrating that identity layer so it feels more trustworthy over longer windows and more specific in matchup use.

Likely shape:
- extend history beyond the current short-horizon view and add clearer stability/scatter framing for noisy teams
- improve style-confidence explanations so analysts can tell when a neighbor or drift story is strong enough for coaching use
- keep improving shot-profile-aware explanations so the x-ray feels like a coaching identity tool rather than a standalone data-science card

### Comparison Sandbox Follow-Ons
Why it matters:
The sandbox is stronger after Sprint 25 and Sprint 42, but it still needs better printing, sharing, and story-specific follow-through to become a true staff workflow.

Likely shape:
- improve printable and shareable compare outputs for teams, lineups, and styles
- surface prep-selected levers and decision rationale more explicitly when compare launches from prep tools, scouting, or scenarios
- deepen story labels with matchup-aware and trend-aware framing instead of season-only summaries

### Play-Type Scouting and Clip Workflow
Why it matters:
Sprints 65 and 66 turned play-type scouting into a real staff handoff workflow: confidence-ranked claims, opponent-specific anchors, compare continuity, and packet pinning into Pre-Read. What remains is making claim curation and export more powerful once staff use rises.

Likely shape:
- improve clip-list export formatting, multi-claim curation controls, and workflow continuity with compare and broader staff packets
- surface inference-confidence analogs on focus-levers, what-if scenarios, and decision-tool rotation suggestions so the trust model is consistent across coaching surfaces
- explore richer clip packaging once staff need printable or bulk-shareable evidence bundles beyond the current packet markdown path

---

## MVP Tracking

### MVP Award-Race Follow-Ons
Why it matters:
Sprints 48-56 turned the MVP tracker into a case platform with eligibility, opponent context, support burden, Gravity context, refined Basketball Value/Award Case scoring, weekly voter timeline, Voter Room case comparison, player embeds, MVP coverage ops, and a Team Impact lens. The next gains are calibration, richer official-data coverage, lineup-aware on/off explanations, and more historically faithful longitudinal modeling.

Likely shape:
- decide when persisted daily snapshots should become a visible daily timeline toggle alongside weekly reconstruction
- add true voter-points ballot simulation once the Voter Room case-comparison foundation is stable
- formalize production automation policy for daily MVP snapshot jobs
- add historical dated rows for impact, Gravity, clutch, opponent-adjusted context, and signature-game leverage so the timeline can evolve beyond game-log-only reconstruction
- calibrate Award Case modifier caps after more live review of ranking movement
- broaden official play-type/tracking/hustle refresh coverage and improve coverage health explanations per candidate
- add lineup-with/without teammate context and dated on/off history so Team Impact explains why a candidate's team changes when he sits or plays

### Gravity Calibration and Official Coverage
Why it matters:
Sprint 51 shipped DB-first Gravity contracts and CourtVue proxy Gravity, but the next step is proving the proxy against richer official tracking domains and official NBA Gravity rows when the source stabilizes.

Likely shape:
- add scheduled/backfill jobs for the new play-type, tracking, hustle, and gravity tables
- compare CourtVue proxy Gravity against official NBA Gravity wherever rows are available
- improve spacing-lift and off-ball components with teammate efficiency and lineup-with/without patterns
- keep Gravity as a capped context adjustment until validation shows it is stable enough for stronger scoring influence

---

## Next

### Decision-Tool Calibration and Opponent Context
Why it matters:
Sprint 42 turned the team decision tab into a real opponent-aware workspace, and Sprint 43 cleaned up the architecture and removed the live timeout regressions. The next gains are now about calibration and workflow sharpness rather than emergency responsiveness.

Likely shape:
- improve minute-redistribution logic, uncertainty wording, and opponent-style adjustments
- connect lineup suggestions more directly into replay and rotation review workflows
- expand matchup exploit flags without losing explainability

### Trend Intelligence Follow-Ons
Why it matters:
Sprint 59 turned Trend Cards into a team + player Trend Intelligence workspace with shared pins, foundation coverage notes, and replay-aware team cards. The next gain is making that story easier to share, archive, and extend into lineup-specific review.

Likely shape:
- add export/share formatting for selected team card + pinned player foundation context
- add lineup-level weekly cards where sample support is strong enough
- deepen card-level evidence summaries so replay and compare launches feel more specific than recent-game context
- add visual polish to pinned-player foundation cards, sparse-data states, and movement series

### Focus Levers Follow-Ons
Why it matters:
Sprint 42 made focus levers opponent-aware and workflow-connected, but the panel should still get more precise and more replay-aware over time.

Likely shape:
- improve impact labels from margin/possession heuristics toward cleaner confidence and game-swing framing
- add direct lever-to-replay follow-through when evidence is strong enough
- keep sharpening how focus levers align with matchup flags, compare, and decision tools so one coaching story survives across surfaces

### Opportunity Workspace Follow-Ons
Why it matters:
Sprint 65 closed out the core Opportunity follow-ons (TTL cache, compare-handoff peers, role-fit AST/TOV depth, directional-hint gating calibration, and the long-standing `UsageEfficiencyDashboard.tsx` → `OpportunityDashboard.tsx` rename). The remaining gains are about expanding the peer model beyond same-team scope and continuing to tune against real roster cases.

Likely shape:
- expand Compare handoff peer lookup to league-wide positional cohorts instead of only the currently-scoped team, so a same-team handoff on BOS can still surface league-wide G peers when that is the intent
- keep tuning directional hints and confidence labels against real roster cases
- lift `_position_bucket` out of `opportunity_service.py` into a shared helper and switch `trajectory_service` plus any future callers, so bucket rules cannot drift between surfaces

### Pre-Read Deck Follow-Ons
Why it matters:
The browser deck is materially stronger after Sprints 27, 32, 63, and 66: named packets, scouting claim carry-through, packet library/history, share links, and markdown export now exist. The next gains are about deeper archive management and broader packet-aware follow-through.

Likely shape:
- add lineup-specific notes, compare launches, and game-film follow-through links that preserve packet context
- add richer archive management such as search, filtering, packet presets, and season-long staff reuse workflows

### Metrics Follow-Ons
Why it matters:
The metrics workspace is live, but it still needs stronger carryover and reuse to feel like a true analyst tool.

Likely shape:
- expand curated metric collections and public templates
- improve metric-to-compare and metric-to-player handoff
- explore whether saved state should stay URL-based or evolve toward richer reusable workspaces

### Ask Workspace Follow-Ons
Why it matters:
Sprint 46 introduced the first StatMuse-inspired CourtVue Ask workspace with deterministic player/team query interpretation. The next value comes from expanding the grammar and making answers launch richer existing workflows with less manual setup.

Likely shape:
- preload Player Stats, Standings, Teams, Compare, and Game Explorer with interpreted query state instead of only linking to the broad destination
- add date windows, opponent filters, playoffs, positions, and "in a game" leaderboards
- add small recent-form visuals for player game logs and team last-10 margin answers
- keep improving alias coverage through the metric registry before adding any optional LLM-assisted interpreter
- expose enough query confidence/debug context in development to tune parser behavior safely

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
