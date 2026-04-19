# Shot Chart / Shot Lab Synopsis

This synopsis summarizes the current Shot Chart and Shot Lab platform so it can be used as source material for planning a future sprint focused on shot charts, shot visualization, and shooting analysis.

## Current Product Surfaces

The Basketball Intelligence Platform already has a mature Shot Lab foundation. It is DB-first, player-centered, and designed around persisted NBA shot chart data enriched with local warehouse context.

The main shot chart experience lives on player pages through the `ShotChart` component. It lets users inspect a player's shooting profile for a selected season and season type, with multiple visualization modes and contextual filters.

Supporting shot chart surfaces include:

- Player Shot Lab: player-level shot distribution, zones, value, distance, action profile, and context.
- Compare Shot Lab: player-vs-player shooting comparison.
- Team Defense Shot Lab: opponent shot chart profile for a team defense.
- Zone Profile panels: compact zone summaries for player pages and team defense.
- Shot Season Evolution: career/season filmstrip of shooting profile changes.
- Shot Context Panel: contextual shot metadata and Game Explorer handoffs.
- Shot Lab Snapshots: saved/shareable shot lab states.

## Primary Backend Files

Core backend pieces:

- `backend/routers/shotchart.py`
- `backend/models/shotchart.py`
- `backend/services/shot_lab_service.py`
- `backend/services/shotchart_service.py`
- `backend/services/bulk_sync_service.py`
- `backend/data/backfill_shot_lab.sh`
- `backend/tests/test_shotchart_db_first.py`

Primary database models:

- `PlayerShotChart`
- `ShotLabSnapshot`

`PlayerShotChart` stores one persisted shot chart payload per player, season, and season type. It has a uniqueness constraint on `player_id`, `season`, and `season_type`, plus `shots` JSON, `shot_count`, `fetched_at`, and `expires_at`.

`ShotLabSnapshot` stores saved Shot Lab views with `snapshot_id`, subject kind/id, season, season type, route path, payload JSON, and timestamps.

## Data Feeds

The core shot feed is NBA shot chart data persisted into `player_shot_charts`. The raw payload is stored as JSON, then enriched at read time where possible.

The shot chart system uses these local data sources:

- `player_shot_charts`: raw shot locations and shot metadata.
- `warehouse_games`: game date, teams, matchup context, season, and season type.
- `game_player_stats`: player-team-game participation and opponent context.
- `play_by_play`: used where available to link shots to event/order/action context.
- Team/player tables: names, teams, abbreviations, and IDs.

The platform is intentionally DB-first. The frontend should not depend on live NBA calls. Refresh endpoints queue warehouse jobs that sync or re-sync shot data.

## Backend API Surface

Current shot chart router endpoints:

- `GET /api/shotchart/{player_id}`
  - Returns persisted player shot chart payload.
- `GET /api/shotchart/{player_id}/zones`
  - Returns player zone profile.
- `POST /api/shotchart/{player_id}/refresh`
  - Queues player shot chart sync.
- `GET /api/shotchart/team-defense/{team_id}`
  - Returns team defense opponent shot chart.
- `GET /api/shotchart/team-defense/{team_id}/zones`
  - Returns team defense zone profile.
- `POST /api/shotchart/team-defense/{team_id}/refresh`
  - Queues refresh jobs for relevant opponent/player shot charts.
- `GET /api/shotchart/completeness/{season}`
  - Returns shot-context completeness report.
- `POST /api/shotchart/snapshots`
  - Saves a Shot Lab snapshot.
- `GET /api/shotchart/snapshots/{snapshot_id}`
  - Loads a saved Shot Lab snapshot.

Frontend API helpers exist in `frontend/src/lib/api.ts`, including player shot chart, zone profile, team defense shot chart, situational/window reads, refresh helpers, and snapshot helpers.

## Shot Payload Shape

A shot can include:

- Location: `loc_x`, `loc_y`
- Result: `shot_made`
- Type/action: `shot_type`, `action_type`
- Zone: `zone_basic`, `zone_area`
- Distance: `distance`
- Game context: `game_id`, `game_date`, `period`, `clock`
- Clock breakdown: `minutes_remaining`, `seconds_remaining`
- Shot value: `2` or `3`
- Team/opponent: `team_id`, `team_abbreviation`, `opponent_team_id`, `opponent_team_abbreviation`
- Score context: `home_score`, `away_score`, `score_margin`
- Event linkage: `shot_event_id`, `event_order_index`, `action_number`, `linkage_mode`

The system tracks whether a shot has contextual metadata and whether it has exact or derived linkage to play-by-play.

## Completeness Model

The Shot Lab has an explicit completeness layer.

A shot payload can be classified as:

- `ready`: contextual and linked data is strong.
- `partial`: context exists but linkage is incomplete or derived.
- `legacy`: raw shot chart exists but contextual enrichment is missing.
- `missing`: no persisted shot chart data.
- `stale`: persisted data exists but TTL has expired.

Completeness fields include total shots, contextual shots, linked shots, exact-linked shots, derived-linked shots, completeness percentage, linked percentage, and missing context fields.

This is important because future shot visualization work should respect data confidence rather than implying all charts are equally precise.

## Current Filters

The Shot Lab supports:

- Season
- Season type
- Date range
- Period bucket: all, Q1, Q2, Q3, Q4, OT
- Shot result: all, made, missed
- Shot value: all, 2PT, 3PT

These filters are used across player shot charts and team defense views. Compare views also use shared filter state.

## Current Visualizations

The main player Shot Lab supports several visualization modes:

- Scatter plot: every shot as a court-location point.
- Heatmap: density-style shot distribution.
- Hex map: binned shot frequency/efficiency.
- Shot Value Map: zone bubbles sized by frequency and colored by value above/below league average.
- Shot Sprawl Map: organic territory/density visualization showing where a player's shot diet lives.
- 3D Shot Lab: WebGL shot arc visualization using generated shot paths.

Additional supporting components:

- `ShotCourt`: shared court-rendering foundation.
- `ZoneProfilePanel`: zone-by-zone summary.
- `ZoneAnnotationCourt`: annotated court by zone.
- `ShotDistanceProfile`: distance-frequency and field-goal percentage profile.
- `ShotActionSignature`: action-type mix.
- `ShotSeasonEvolution`: season-by-season mini court filmstrip.
- `ShotContextPanel`: shot context, replay links, and Game Explorer handoffs.
- `ShotProfileDuel`: compare-mode shooting profile duel.
- `ShotProfileFingerprint`: compact player shooting identity display.
- `TeamDefenseShotLab`: opponent shooting profile allowed by team defense.

## Team Defense Shot Logic

Team defense shot charts are built by finding games involving the selected team, identifying opponent players from `GamePlayerStat`, reading those players' persisted shot charts, and filtering shots to games against the selected team.

This means team defense shot charts depend on both:

- Opponent player shot chart availability.
- Local warehouse game/player-stat coverage.

The system returns team defense shot data with the same broad visual language as player Shot Lab.

## Share / Snapshot System

Shot Lab views can be saved as snapshots. A snapshot stores subject type, subject ID, compare subject, team ID, season, season type, active view, route path, filters, and metadata.

This supports sharing or returning to a specific Shot Lab state without reconstructing the UI manually.

## Historical Work Completed

Recent shot-chart-focused work included:

- DB-first persisted shot chart system.
- Player shot chart route and refresh queueing.
- Zone profile routes.
- Team defense opponent shot charts.
- Compare Shot Lab.
- Shot Value Map.
- Shot Sprawl Map.
- Distance Profile.
- Season Evolution filmstrip.
- Shared `ShotCourt`.
- Shot context/completeness metadata.
- Shot-to-Game Explorer handoffs.
- 3D shot arc visualization.
- Shot Lab snapshots.

The product is already beyond a basic scatter plot. The next sprint should probably focus on clarity, precision, storytelling, and higher-value basketball interpretation.

## Known Limitations / Debt

The main limitations are:

- Raw shot locations exist, but not every shot has full contextual/play-by-play linkage.
- Some shot payloads are `legacy` or `partial`, so advanced context should be confidence-labeled.
- Heatmap and court geometry still have polish opportunities.
- Team defense charts depend on opponent player shot chart completeness.
- Shot value currently uses zone-level league-average style comparisons, not necessarily fully contextual expected value.
- 3D arcs are generated visual interpretations, not official optical-tracking trajectories.
- Shot quality is not yet modeled deeply: defender distance, contest level, touch time, dribbles, shot clock, play type, and creation type are not all first-class inputs unless available through future feeds.
- There is no unified "shot diet identity" score or "shot quality vs shot making" split yet.
- The system has visual richness, but some methodology/explanation layers could be stronger for standalone users.

## Strong Sprint Opportunities

High-value directions for a shot chart enhancement sprint:

1. Shot Quality vs Shot Making
   - Separate where a player gets shots from how well they finish them.
   - Add expected eFG/points per shot by zone, distance, and context.
   - Show overperformance/underperformance.

2. Creation Context
   - Add assisted vs self-created where data allows.
   - Split pull-ups, catch-and-shoot, drives, paint touches, post-ups, transition, and late-clock attempts if feeds support it.

3. Defensive Shot Profile
   - Turn team defense shot charts into a clearer "what this defense allows" scouting surface.
   - Add rim frequency allowed, corner 3 frequency allowed, midrange baiting, above-break 3 volume, opponent shot value.

4. Shot Diet Identity
   - Create compact player archetypes: rim pressure, movement shooter, pull-up engine, midrange creator, corner spacer, paint finisher, etc.
   - Use current zones, distances, action types, and frequency.

5. Better Timeline / Evolution
   - Improve `ShotSeasonEvolution` into a real developmental timeline.
   - Show changes in rim rate, 3PA rate, midrange share, shot value, and efficiency by season or rolling window.

6. Contextual Filters
   - Add clutch, score margin, home/away, opponent, rest, playoffs, and shot-clock filters if data supports them.
   - Make missing context visible through completeness labels.

7. Visual Explainability
   - Add methodology copy and inline tooltips.
   - Explain what each map answers: "Where does he shoot?", "Where does he add value?", "How spread out is the shot diet?", "How has it changed?"

8. Court / Visualization Polish
   - Finish shared court geometry.
   - Improve label placement, legends, density scaling, mobile readability, and hover affordances.
   - Make visual modes feel like one coherent Shot Lab rather than separate charts.

9. Replay Integration
   - Improve shot-to-play linkage and Game Explorer handoffs.
   - For linked shots, let users jump directly to sequence context.
   - Add "show me examples" from selected zones or action types.

10. Shot Chart Ops
    - Add coverage/freshness panels for shot chart data.
    - Show which seasons/players/teams have complete, partial, stale, or missing shot data.
    - Add bulk backfill controls for shot chart context.

## Suggested Research Prompt

Given an existing DB-first Shot Lab with player, compare, team-defense, zone, value, sprawl, distance, season-evolution, 3D, context, and snapshot features, what is the highest-impact next sprint to make shot charts more analytically useful, visually legible, and scouting-ready?

Prioritize features that can be built from persisted shot chart JSON, warehouse games, game player stats, and available play-by-play context, while clearly labeling partial/legacy data coverage.
