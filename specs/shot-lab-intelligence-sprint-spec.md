# Shot Lab Intelligence Sprint Spec

## Executive summary

This sprint should focus on turning Shot Lab from an already feature-rich shot visualization suite into a more analytically decisive, scouting-ready product surface. The platform already has a mature DB-first foundation with player, compare, team-defense, zone, value, sprawl, distance, season-evolution, 3D, context, and snapshot features, all powered by persisted shot chart JSON and warehouse enrichment rather than live NBA dependencies.[cite:3]

The highest-impact next sprint is a **Shot Lab Intelligence** sprint centered on four linked upgrades:

- Shot Quality vs Shot Making
- Creation-context splits
- Coverage-aware visual language
- Scouting summaries and methodology explainability[cite:3]

This is the best next sprint because the current platform already exceeds a basic charting tool, while the synopsis identifies the biggest remaining gaps as shot-quality modeling, unified shooting identity, stronger methodology/explanation, partial/legacy coverage handling, and polish that makes the system more precise, legible, and useful for real basketball analysis.[cite:3]

## Sprint title

**Shot Lab Intelligence Sprint: Quality, Creation, and Scouting Layer**[cite:3]

## Sprint objective

Build a coverage-aware scouting layer that separates shot diet, shot quality, and shot-making skill, then presents that information through a unified premium court system with explicit trust labels and stronger methodological explanation.[cite:3]

## Why this sprint now

The platform already supports persisted player shot charts, zone profiles, team-defense shot charts, compare mode, Shot Value Map, Shot Sprawl Map, distance profile, season evolution, shot context, 3D shot arcs, and snapshots. That means another net-new chart mode would be less valuable than making the current system answer sharper basketball questions with more reliable interpretation.[cite:3]

The synopsis also makes clear that current data is strong enough to support a meaningful next step. Persisted shot payloads include location, result, type, action, zone, distance, game context, score context, and play-by-play linkage metadata, while warehouse games and game player stats provide matchup and participation context, and play-by-play can enrich linked subsets where available.[cite:3]

This sprint therefore fits both product need and implementation reality. It extracts more value from data the system already stores rather than depending on future optical-tracking feeds or live external APIs.[cite:3]

## Success criteria

The sprint is successful if it enables users to answer the following questions more clearly than the current product:

- Where does this player get shots?
- How favorable are those shots relative to league expectation?
- How much does the player overperform or underperform the quality of those shots?
- Which parts of the player’s shooting profile are self-created versus context-assisted?
- How much of the advanced view is based on ready data versus partial or legacy coverage?[cite:3]

Success should also be visible in the product experience itself:

- Advanced shot views feel more coherent and legible.
- The court system feels premium and consistent across modes.
- Partial/legacy coverage is obvious, not hidden.
- Candidate scouting takeaways are faster to extract without losing methodological honesty.[cite:3]

## In scope

This sprint should include the following workstreams.

### 1. Shot Quality vs Shot Making

This is the core analytical deliverable of the sprint. The synopsis explicitly identifies “Shot Quality vs Shot Making” as the top high-value direction and notes that current shot value uses zone-level league-average style comparisons rather than a deeper contextual expected-value model.[cite:3]

This module should separate three concepts:

- **Shot Diet**: where and what types of shots a player takes.
- **Shot Quality**: how favorable those attempts are based on available location and context.
- **Shot Making**: how much the player outperforms or underperforms that expected baseline.[cite:3]

Deliverables:

- Expected FG%, eFG%, and points-per-shot baselines from persisted shot/location/context data.[cite:3]
- Actual versus expected summary cards.[cite:3]
- Court overlays for expected value and actual-minus-expected performance.[cite:3]
- Zone and hex-level breakdowns of quality versus conversion.[cite:3]

### 2. Creation-context splits

This is the core scouting deliverable of the sprint. The synopsis explicitly calls out assisted vs self-created, pull-ups, catch-and-shoot, drives, transition, and late-clock attempts as strong next directions where data allows.[cite:3]

The sprint should implement a practical version built from currently available fields rather than waiting for perfect feed coverage.

Deliverables:

- Assisted vs unassisted or linked self-created inference where available.[cite:3]
- Action-family views using `action_type`, `shot_type`, and available linked event context.[cite:3]
- Early-clock, late-clock, and period/game-state shot buckets using current game context fields.[cite:3]
- Context labels that make clear whether the split is full-coverage, linked-subset only, or partially inferred.[cite:3]

### 3. Unified visual grammar

The synopsis notes that heatmap and court geometry still have polish opportunities and that visual modes should feel like one coherent Shot Lab rather than a set of separate charts.[cite:3]

This sprint should establish one unified visual language across all current and new shot views.

Deliverables:

- Shared court geometry and typography across scatter, hex, value, quality, and creation views.[cite:3]
- Consistent color semantics for frequency, efficiency, expected value, and overperformance.[cite:3]
- Better label placement, legends, hover affordances, and mobile readability.[cite:3]
- Coverage chips and methodology tooltips embedded directly into advanced views.[cite:3]

### 4. Scouting summaries and methodology layer

The synopsis notes that there is no unified “shot diet identity” score yet and that methodology/explanation could be stronger for standalone users.[cite:3]

This sprint should make the product more scouting-ready by converting raw chart reading into concise interpretable takeaways.

Deliverables:

- Shot Diet Identity cards (for example: rim pressure, movement shooter, pull-up engine, midrange creator, corner spacer, paint finisher).[cite:3]
- Shot Quality Profile cards (clean diet, neutral diet, tough-shot diet).[cite:3]
- Shot Making Signal cards (overperformer, in-line finisher, underperformer versus expected).[cite:3]
- Inline methodology copy that explains what each court answers and what the confidence limits are.[cite:3]

## Out of scope

The following items should not be sprint priorities.

### Full optical-tracking shot quality model

The synopsis explicitly notes that defender distance, contest level, touch time, dribbles, shot clock, play type, and creation type are not all first-class inputs yet unless future feeds are added. That means a tracking-grade shot-quality model is not the right target for this sprint.[cite:3]

The sprint should instead ship a warehouse-safe expected shot model built from persisted shot location and available context, with language that clearly states it is not a full contest-based optical-tracking model.[cite:3]

### Major 3D expansion

The platform already includes 3D shot arcs, but the synopsis states those arcs are generated visual interpretations rather than official optical-tracking trajectories. That makes 3D more of a presentation layer than the most urgent analytical layer for the next sprint.[cite:3]

Only minor consistency and visual integration work should be considered here. Major 3D roadmap work should wait until the analytical foundation is sharper.[cite:3]

### Full team-defense rebuild

Team-defense charts are valuable, but the synopsis notes that they depend on opponent player shot chart availability as well as local warehouse game/player-stat coverage. Because of that dependency, the best use of this sprint is to build the new language and modeling on player surfaces first, then port it to defense surfaces after the product grammar is proven.[cite:3]

## User personas and user stories

### Primary personas

- **Basketball analyst**: wants to diagnose how a player gets shots and whether efficiency is sustainable.[cite:3]
- **Scout/content creator**: wants a sharp visual surface with fast, defensible takeaways.[cite:3]
- **Advanced fan**: wants a clear and compelling explanation without needing to reverse-engineer the chart methodology.[cite:3]

### User stories

- As an analyst, the product should separate shot quality from shot making so that clean diet and difficult shot conversion are not conflated.[cite:3]
- As a scout, the product should show whether a player’s jumpers are self-created, assisted, late-clock, or context-aided when the data supports that split.[cite:3]
- As a user comparing players, the product should present the same visual language and trust labels across views so charts are easy to compare quickly.[cite:3]
- As a standalone user, the product should explain what each map means and how much of the result is based on fully linked versus partial or legacy data.[cite:3]

## Product requirements

### Core product experience

The revised Shot Lab should guide users through five primary analytical questions.

| Surface | Primary question | Data basis |
|---|---|---|
| Diet Map | Where does the player shoot from most often? | Persisted shot locations, zones, distance [cite:3] |
| Quality Map | How favorable are the player’s shot attempts? | Location, shot value, context buckets, league baselines [cite:3] |
| Making Map | Where does the player outperform or underperform expectation? | Actual result versus expected baseline [cite:3] |
| Creation Map | Which shots are self-created or context-created? | `action_type`, `shot_type`, available linked play context [cite:3] |
| Scout Summary | What kind of shooter and shot creator is this? | Frequency, zones, distance, action mix, quality/making summaries [cite:3] |

### Shared UX rules

- Each advanced view must show a visible coverage state.[cite:3]
- Each advanced view must have a one-sentence explanation of what it answers.[cite:3]
- Visual semantics must remain consistent across all shot surfaces.[cite:3]
- New modes must reuse the shared `ShotCourt` foundation unless there is a compelling technical exception.[cite:3]

## Functional requirements

### A. Shot Quality vs Shot Making module

#### Inputs

- Persisted shot JSON: location, result, shot value, zone, distance, shot type, action type, game/date, period, clock, score context, team/opponent, linkage metadata.[cite:3]
- Warehouse games: matchup, season, season type, date context.[cite:3]
- Game player stats: player participation, opponent context, team context.[cite:3]
- Play-by-play when linked or partially linked.[cite:3]

#### Outputs

- Expected FG%
- Expected eFG%
- Expected points per shot
- Actual FG%
- Actual eFG%
- Actual points per shot
- Delta versus expected by player, zone, and bin[cite:3]

#### Requirements

- Model must work without live API calls because the platform is intentionally DB-first.[cite:3]
- Model must degrade gracefully for partial/legacy payloads.[cite:3]
- Model must expose methodology copy and confidence note.[cite:3]
- Deltas must be viewable on summary cards, zone panels, and court overlays.[cite:3]

### B. Creation-context module

#### Inputs

- `action_type`
- `shot_type`
- linked play-by-play fields such as event order, action number, and linkage mode where available
- game clock, period, score margin, opponent context[cite:3]

#### Outputs

- Assisted/unassisted or self-created proxy split
- Catch-and-shoot / pull-up / drive / transition-adjacent / late-clock buckets where support exists
- Coverage note per split[cite:3]

#### Requirements

- No split should imply full precision when it is derived from partial linkage.[cite:3]
- Each filter and chart must indicate whether it uses all shots, linked subset only, or inferred subset.[cite:3]
- Context filters must be compatible with existing season, season type, date range, period bucket, result, and shot value filters.[cite:3]

### C. Coverage and methodology layer

#### Inputs

- Existing completeness model states: `ready`, `partial`, `legacy`, `missing`, `stale`.[cite:3]
- Completeness fields: contextual shots, linked shots, exact-linked shots, derived-linked shots, completeness percentage, linked percentage, missing context fields.[cite:3]

#### Outputs

- Coverage chip on every advanced module
- Detail tooltip with breakdown of coverage and missing fields
- Advanced-mode gating logic where necessary
- Completeness panel in Shot Lab header or side rail[cite:3]

#### Requirements

- Partial/legacy states must not be buried in a separate admin area.[cite:3]
- Coverage should affect visual treatment, such as reduced opacity or warning chip, but should not make charts unusable if the base raw shot chart still exists.[cite:3]
- Snapshot payloads should preserve coverage metadata so shared links retain trust context.[cite:3]

### D. Visual system polish

#### Requirements

- Court geometry should be consistent across all views.[cite:3]
- Legends should be standardized and compact.[cite:3]
- Label placement must avoid overlap on dense courts.[cite:3]
- Mobile readability must improve versus current heatmap/geometry debt.[cite:3]
- Hover states must surface exact values, sample size, and confidence where relevant.[cite:3]

## Data model and methodology design

### Expected shot model v1

This sprint should ship an interpretable expected-shot model rather than an opaque black-box score. The synopsis already points toward expected eFG and points per shot by zone, distance, and context as the right direction.[cite:3]

Recommended v1 feature buckets:

- Zone
- Distance bucket
- Shot value (2PT / 3PT)
- Broad action family where available
- Period bucket
- Clock bucket
- Home/road and season-type context if coverage is sufficient[cite:3]

Recommended v1 outputs:

- Expected FG%
- Expected eFG%
- Expected PPS
- Delta to actual
- Sample-size confidence band or bucket[cite:3]

Method note to display in product:

> Expected shot value is estimated from persisted shot location and available game/context fields. It is not a full tracking-based contest model and should be interpreted accordingly.[cite:3]

### Shot identity framework

The sprint should introduce a first-pass shot identity framework using current zones, distances, action types, and frequency distributions, because the synopsis specifically notes the absence of a unified shot diet identity system.[cite:3]

Initial identity families can include:

- Rim pressure finisher
- Paint touch scorer
- Midrange creator
- Pull-up engine
- Movement shooter
- Above-break volume spacer
- Corner specialist
- Balanced perimeter scorer[cite:3]

This framework should be descriptive, not prescriptive. It is intended to speed understanding and scouting interpretation rather than replace the underlying charts.[cite:3]

## API and backend spec

### Existing reusable foundation

The sprint should build on the current shot chart router and service layer, especially the persisted DB-first route structure and completeness endpoint.[cite:3]

Relevant existing endpoints include:

- `GET /api/shotchart/{player_id}`
- `GET /api/shotchart/{player_id}/zones`
- `GET /api/shotchart/team-defense/{team_id}`
- `GET /api/shotchart/completeness/{season}`
- snapshot save/load routes[cite:3]

### Proposed endpoint additions

#### `GET /api/shotchart/{player_id}/quality`

Returns player-level shot quality summary and bins.

Suggested response shape:

```json
{
  "player_id": 123,
  "season": "2025-26",
  "season_type": "Regular Season",
  "coverage_state": "partial",
  "methodology_version": "quality_v1",
  "summary": {
    "shots": 642,
    "actual_fg_pct": 0.492,
    "expected_fg_pct": 0.468,
    "actual_efg_pct": 0.561,
    "expected_efg_pct": 0.529,
    "actual_pps": 1.123,
    "expected_pps": 1.061,
    "pps_delta": 0.062
  },
  "bins": [],
  "zones": [],
  "coverage": {}
}
```

#### `GET /api/shotchart/{player_id}/creation`

Returns creation-context summary and shot subsets.

Suggested response shape:

```json
{
  "player_id": 123,
  "season": "2025-26",
  "season_type": "Regular Season",
  "coverage_state": "ready",
  "summary": {
    "linked_share": 0.71,
    "assisted_share": 0.38,
    "self_created_share": 0.44,
    "inferred_share": 0.18
  },
  "splits": {
    "catch_and_shoot": {},
    "pull_up": {},
    "late_clock": {},
    "transition_adjacent": {}
  },
  "coverage": {}
}
```

#### `GET /api/shotchart/{player_id}/identity`

Returns shot-diet identity summary cards.

#### `GET /api/shotchart/{player_id}/coverage`

Returns a compact, chart-focused completeness object for UI badging and tooltips.[cite:3]

### Backend tasks

- Add service-layer computation for expected shot baselines using persisted JSON and warehouse context.[cite:3]
- Add feature-engineering helpers for zone, distance, period, clock, score, and action buckets.[cite:3]
- Build linked-subset logic for creation splits using linkage metadata and play-by-play fields.[cite:3]
- Persist or cache computed summaries where expensive enough to justify precomputation.[cite:3]
- Add tests covering ready, partial, legacy, and stale scenarios.[cite:3]

## Frontend spec

### New UI modules

- `ShotQualitySummaryCard`
- `ShotQualityCourt`
- `ShotMakingDeltaCourt`
- `ShotCreationProfile`
- `ShotCoverageBadge`
- `ShotMethodologyPopover`
- `ShotIdentityCards`[cite:3]

### Existing module upgrades

- Extend `ShotCourt` to support shared legend, annotation, and hover semantics across all modes.[cite:3]
- Upgrade `ZoneProfilePanel` to include expected-versus-actual columns where available.[cite:3]
- Extend `ShotContextPanel` to expose context coverage and “linked subset only” notes.[cite:3]
- Update compare mode to allow side-by-side quality and making comparison, not just raw shot profile comparison.[cite:3]

### Interaction design

- Default landing view should be **Diet**, with tabs for **Quality**, **Making**, **Creation**, and **Scout Summary**.[cite:3]
- Hovering or tapping on a zone/hex should reveal frequency, actual efficiency, expected efficiency, delta, sample size, and coverage note where relevant.[cite:3]
- Coverage chips should be always visible on advanced views, not hidden in settings or footnotes.[cite:3]
- Methodology tooltips should be concise but explicit about what the view answers.[cite:3]

## Snapshot integration

The existing snapshot system already stores subject type, subject ID, compare subject, team ID, season, season type, active view, route path, filters, and metadata. The new sprint should extend that model rather than creating a separate sharing path.[cite:3]

Snapshot payloads should additionally preserve:

- active intelligence view (`diet`, `quality`, `making`, `creation`, `summary`)
- coverage state at save time
- methodology version
- active advanced filters and split mode[cite:3]

This ensures that shared scouting views remain reproducible and do not lose context about data quality or chart meaning.[cite:3]

## Completeness and trust rules

The current completeness model is one of the platform’s strongest assets because it already formalizes `ready`, `partial`, `legacy`, `missing`, and `stale`. The sprint should make that model visible to end users in a product-quality way.[cite:3]

### Trust rules

- **Ready**: all advanced modules available with standard confidence presentation.[cite:3]
- **Partial**: advanced modules available, but with visible caution chip and detailed tooltip.[cite:3]
- **Legacy**: base shot views remain available; advanced quality/creation modules may be reduced or partially disabled depending on missing fields.[cite:3]
- **Missing**: show polished empty state with refresh or backfill guidance.[cite:3]
- **Stale**: show stale badge and prompt refresh while still allowing chart read access.[cite:3]

### UI wording examples

- “Quality model based on persisted location and available context.”[cite:3]
- “Creation split shown on linked subset of shots only.”[cite:3]
- “This season uses legacy shot payloads; some scouting views are limited.”[cite:3]

## Design direction

The design goal should be to make Shot Lab feel like a premium scouting studio rather than a standard dashboard. The current product already has visual richness, and the synopsis specifically calls for clarity, precision, storytelling, and stronger standalone interpretation as the next frontier.[cite:3]

### Visual principles

- Deep neutral court surfaces and restrained accent colors.[cite:3]
- Consistent premium typography across all shot modules.[cite:3]
- One coherent legend language across all modes.[cite:3]
- Motion used for transitions between states, not decoration.[cite:3]
- Confidence and uncertainty expressed visually without degrading overall polish.[cite:3]

### Color semantics

- Frequency: size or density, not competing color usage.[cite:3]
- Efficiency: sequential warm/cool scale depending on mode.[cite:3]
- Expected value: disciplined neutral-to-accent ramp.[cite:3]
- Over/under expectation: diverging scale with a clear midpoint.[cite:3]
- Partial/legacy states: reduced saturation or explicit trust badge, not hidden.[cite:3]

## Engineering plan

### Backend work

1. Define v1 expected-shot methodology and feature buckets.[cite:3]
2. Implement service-layer quality aggregation on persisted shot JSON.[cite:3]
3. Build creation-context aggregations from action/linkage/game fields.[cite:3]
4. Expose new endpoints and tests.[cite:3]
5. Add caching or warehouse-side precomputation if query cost is high.[cite:3]

### Frontend work

1. Extend shared `ShotCourt` and legend system.[cite:3]
2. Add new Quality, Making, Creation, and Identity modules.[cite:3]
3. Integrate coverage chips/tooltips and methodology copy.[cite:3]
4. Update compare and snapshot flows.[cite:3]
5. QA on desktop and mobile for dense court states.[cite:3]

### Design work

1. Finalize unified court language and color semantics.[cite:3]
2. Improve label hierarchy, legends, and density readability.[cite:3]
3. Create premium summary-card presentation for scouting takeaways.[cite:3]
4. Validate interaction patterns for touch devices and hover fallback.[cite:3]

## QA plan

### Data QA

- Validate expected-shot outputs against known player archetypes and sanity-check edge cases.[cite:3]
- Validate partial/legacy behavior with controlled fixtures.[cite:3]
- Validate linked-subset creation splits do not silently inflate precision.[cite:3]

### Product QA

- Check every advanced view under `ready`, `partial`, `legacy`, `missing`, and `stale` states.[cite:3]
- Check snapshot restore fidelity across all new intelligence modes.[cite:3]
- Check compare mode consistency for shared filters and legends.[cite:3]
- Check mobile readability and tooltip fallback behavior.[cite:3]

### Visual QA

- Confirm consistent court geometry and annotation placement across all views.[cite:3]
- Confirm color meaning does not change between modules.[cite:3]
- Confirm partial/legacy badges are visible but not visually disruptive.[cite:3]

## Risks and mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| Expected-shot model is mistaken for a tracking-grade quality model | Users may overread precision | Explicit methodology note and versioning [cite:3] |
| Partial linkage weakens creation splits | Can create false confidence | Show linked-share, inferred-share, and coverage chips [cite:3] |
| Visual complexity overwhelms users | Too many modes can reduce clarity | Use narrative tab order and concise mode descriptions [cite:3] |
| Team-defense parity lags player views | Users may expect same intelligence layer immediately | Launch player-first and clearly mark team-defense as next phase [cite:3] |
| Query cost becomes high | Large shot payload aggregations may be expensive | Precompute summaries or cache by player/season/filter [cite:3] |

## Acceptance criteria

The sprint can be considered complete when all of the following are true:

- Player Shot Lab includes Quality, Making, Creation, and Scout Summary views in addition to current modes.[cite:3]
- Quality view shows expected versus actual outputs using only DB-first available data.[cite:3]
- Creation view clearly labels full, partial, or linked-subset coverage.[cite:3]
- Every advanced mode displays a visible coverage state and methodology tooltip.[cite:3]
- Shared court grammar, legends, labels, and hover behavior are standardized.[cite:3]
- Snapshot system preserves new intelligence state.[cite:3]
- Mobile and desktop QA pass for dense, sparse, partial, and stale payload scenarios.[cite:3]

## Recommended phase breakdown

### Phase 1: Analytical foundation

- Expected-shot v1 methodology
- Quality endpoint
- Zone/hex deltas
- Coverage objects and trust labels[cite:3]

### Phase 2: Scouting layer

- Creation endpoint
- Identity cards
- Scout Summary modules
- Methodology copy[cite:3]

### Phase 3: Visual unification

- Shared court geometry cleanup
- Legends and label hierarchy
- Compare-mode integration
- Snapshot integration[cite:3]

## Future follow-ons

After this sprint, the strongest follow-up opportunities are already implied by the synopsis.

- Port the intelligence layer to team-defense surfaces.[cite:3]
- Expand season evolution into a truer developmental shot timeline.[cite:3]
- Improve replay integration for linked shots and “show me examples” workflows.[cite:3]
- Add better operational visibility for freshness and backfill status across shot-chart coverage.[cite:3]
- Revisit 3D once the analytical layer is stronger.[cite:3]

## Final recommendation

This sprint should not be treated as a cosmetic chart pass. It should be treated as the point where Shot Lab becomes a clearer analytical product. The existing foundation is already mature, DB-first, and feature-rich; the most valuable next step is to convert that foundation into a sharper scouting and interpretation system built around quality, creation, trust, and visual coherence.[cite:3]
