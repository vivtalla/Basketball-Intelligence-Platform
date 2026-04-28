# Sprint History Archive

Archived sprint summaries through Sprint 75. The two most recent sprint summaries also stay inline in `CLAUDE.md` under "Recent Sprints".

For detailed per-sprint records, see the individual closeout files in this directory where available:
`specs/sprint-09-closeout.md` through `specs/sprint-59-closeout.md`, plus `specs/sprint-62-closeout.md` and `specs/sprint-67-closeout.md` onward.

---

### Sprint 75 — Playoff Command Center & Series Intelligence
**Branch:** `codex-sprint-75-playoff-command-center` (Codex, single-stream)

- Upgraded `/bracket` from static bracket view into a coach/analyst Playoff Command Center with selected-series rail, today's slate strip, Series Pulse, Four Factors Edge, Tactical Edges, Adjustment Signals, Star Burden, Shot Diet Pressure, Lineup Chess, simulator, and reliability card.
- Added `playoff_series_intelligence_v1` via `GET /api/playoffs/series/{series_id}/intelligence`, composing existing playoff rows only: `playoff_series`, `game_logs`, playoff/regular `team_season_stats`, playoff `season_stats`, `lineup_stats`, and `team_shooting_split_stats`.
- Added a new `playoffs` methodology registry domain and updated `specs/platform-methodology.md` with formulas, reliability scoring, confidence gates, assumptions, and limitations.
- Extended the series simulator with non-mutating `override_top_wins` / `override_bottom_wins`, and wired `<SeriesWPSimulator>` what-if buttons to real hypothetical re-simulation plus reset.
- Added backend tests for intelligence payload shape, thin-data warnings, star burden/position buckets, metadata, and simulator override non-mutation.
- Verified with **293 backend tests**, targeted playoff tests, `npm run lint` (7 pre-existing warnings), `npm run build`, and `git diff --check`. Closeout: `specs/sprint-75-closeout.md`.

---

### Sprint 74 — Methodology Reliability Rollout + Team-Fit/Shot Lab vNext
**Branch:** `codex-sprint-74-methodology-upgrades` (Codex, single-stream)

- Promoted methodology reliability from backend-only metadata into a product-wide trust pattern. Registry upgraded to `methodology_registry_v2` with model stage, season-type support, validation notes, and implementation references.
- Added `GET /api/methodology/validation` plus golden fixtures for Team-Fit and Shot Lab cases including Tatum/BOS overlap, traded/TOT handling, thin playoff samples, specialist shooters, low-attempt hot streaks, and role-player fit.
- Added shared frontend methodology types, API helpers, SWR hooks, and `<MethodologyEvidenceCard>`; wired it into Team-Fit, Shot Intelligence, Opportunity, Archetype/Similarity, Trend/Trajectory, Style X-Ray, MVP/Gravity, Scouting Brief, and Custom Metrics.
- Upgraded Shot Lab to `shot_quality_v2`: hierarchical baseline blending, empirical Bayes stabilized FG%/PPS/PPS delta, Wilson FG% intervals, PPS-delta uncertainty bands, and sustainability labels.
- Upgraded Team-Fit to `team_fit_v3`: current fit vs theoretical best usage, fit-gap interpretation, reliability notes, reliability-gated better-fit thresholds, analysis-context confidence warnings, and playoff low-sample notes.
- Updated `specs/platform-methodology.md`, `specs/methodology-validation.md`, and backlog follow-ons for the next calibration/model-upgrade layer.
- Verified with **290 backend tests**, `npm run lint`, `npm run build`, and `git diff --check`. Closeout: `specs/sprint-74-closeout.md`.

---

### Sprint 73 — Playoffs Platform
**Branches:** `feature/sprint-73a-playoffs-data` (Stream A) → `feature/sprint-73b-playoffs-features` (Stream B); two-team parallel, Architect → 8 Engineers → Reviewer → Optimizer

- Centered the platform on the 2026 NBA first-round playoffs while preserving the regular-season scope. Every playoff surface gates behind a new `useSeasonPhase()` SWR hook backed by an auto-detect service so the platform reverts cleanly outside the playoff window.
- Stream A (data foundation) shipped: Alembic `0012_playoffs_data_layer` (new `playoff_series` table + `is_playoff` on `lineup_stats` + `season_type`/`series_id`/`series_game_num`/`playoff_seed` on game_logs and warehouse games); `nba_client` + `sync_service` + `daily_sync.sh` got `season_type` pass-through, a 2h `PLAYOFF_CACHE_TTL` during the playoff window, and a new `--post-game` cron path; `services/season_phase_service.get_current_phase()` auto-detects from date+data; new `services/playoff_bracket_service` and `playoff_simulator_service` (deterministic Monte-Carlo); 5 services unblocked from `is_playoff=False` filters; new routes `/api/season-phase`, `/api/playoffs/bracket|series/{id}|today|series-simulation/{id}`.
- Stream B (frontend) shipped: `/bracket` route + `<PlayoffBracketView>` + `<SeriesCard>` + `useSeasonPhase` hook; series-mode Pre-Read pivot with `<CoachingAdjustmentsTimeline>` (finally surfaces `data.adjustments` deferred from Sprint 72) + `<SeriesWPChart>`; home shift with `<DailyPlayoffSlate>` + `<SeriesNarrative>` carousel; leaderboards Regular/Playoffs toggle; `<SeriesWPSimulator>` on MVP; `<PostseasonHeatmap>` on leaderboards; `<OpponentLineupMatchupMatrix>` tab on team detail.
- Reviewer signed off no-blockers; Optimizer addressed DST-aware Pacific timezone (`pytz` for `/api/playoffs/today`) and memoized WP simulator chart geometry in one defensive-fixes commit.
- Verified with **286 backend tests** (was 266, +20 new), `npm run build` + `npm run lint` clean (7 pre-existing warnings).

---

### Sprint 72 — Design System Closeout + Visual Polish
**Branch:** `feature/sprint-72-design-system-closeout` (Claude, single-stream Architect → Engineers → Reviewer → Optimizer)

- Closed every Sprint 70 backlog item (Design System Follow-Ons + API Payload Audit) plus polished the home-page basketballs. After this sprint the front-end design work from the design tarball is fully closed out.
- New `GET /api/leaderboards/{stat}/trends` endpoint + `backend/services/leaderboard_trends.py` + `<Sparkline>` SVG primitive drives a TREND column on the home league-leaders.
- Compare PlayerCard headers wrap with low-opacity `<HeroHardwood>` and color-coded names; MVP candidate cards wrap with team-tinted `<HeroHardwood>` plus a ★#1 chrome treatment while preserving all existing pillars/modifiers/radar/clutch/sig-games (per user decision).
- New `/learn/design-system` showcase page consolidates Sprint 70+72 primitives. Pre-Read print stylesheet (`@media print` rules in `globals.css` + `print:hidden` + `data-print-break-before`) makes `Cmd+P` produce a clean coach-handoff PDF.
- Pre-Read API audit wins: urgency badge above matchup card, headline callout under focus levers (both fields were returned by `/api/pre-read` but previously unrendered). MVP `support_burden` "Teammate quality" sub-card. Player archetype `reason` tooltip. RoleFitCard hint discoverability icon.
- FloatingBall polish: specular shine, varied seam stroke widths/opacity, two-layer drop shadow, four-stop fill gradient with off-center origin. `useId` for collision-safe per-instance gradient IDs. Optimizer pass moved `prefers-reduced-motion` rule into a global `globals.css` block.
- Architecture used the sequential `Architect → 4 parallel Engineers → Reviewer → Optimizer` pattern. Reviewer found no blocking issues; Optimizer addressed 3 of 6 non-blocking concerns in one defensive-fixes commit.
- Verified with **266 backend tests** (was 263, +3 sparkline), `npm run build` + `npm run lint` clean, `git diff --check` clean.

---

### Sprint 71 — Methodology Rigor Layer
**Branch:** `codex-sprint-71-methodology-rigor` (Codex, backend/docs-only)

- Added shared methodology registry, methodology Pydantic contracts, `GET /api/methodology`, and `GET /api/methodology/{domain}`.
- Added shared reliability primitives: empirical Bayes shrinkage, reliability scoring, confidence labels, Wilson/normal uncertainty bands, robust z-scores, winsorized z-scores, sample context.
- Added optional `analysis_metadata` to Shot Lab, Team-Fit, and Opportunity responses, preserving current frontend contracts while making reliability, drivers, limitations, and validation notes available to clients.
- Updated `specs/platform-methodology.md`, added `specs/methodology-validation.md`, and refreshed backlog/coordination docs around calibration follow-ons.
- Verified with **263 backend tests**, `git diff --check`, methodology doc coverage checks, FastAPI `main` import smoke.
- Frontend intentionally untouched because Claude had a parallel independent frontend sprint in flight.

---

### Sprint 70 — Design System Integration
**Branch:** `feature/sprint-70-design-system-integration` (Claude, single-stream)

- Pure-frontend sprint bringing the CourtVue Labs design system (cream/forest-green/gold palette, Source Serif 4 / Source Sans 3 / JetBrains Mono) deeper into Teams, Metrics, Pre-Read, and Compare. No backend changes; backend test count unchanged at 257 passing.
- Teams directory (`/teams`) full redesign: two-column layout with conference filter pills (All/East/West) backed by a static `TEAM_META` map, sort dropdown, sticky directory rows with colored abbreviation badges, and a right `TeamDetailPreview` panel with quick-access tab links to the full `/teams/[abbr]` dashboard.
- Metrics page hero leader card inside `CustomMetricBuilder.tsx`: `<HeroHardwood>` woodgrain texture, metric label kicker, #1 ranked player + team, composite score in 72pt `bip-display` type — appears whenever `data.player_rankings.length > 0`.
- Pre-Read page added three sections: visual matchup header card with home/vs/away team boxes; six bilateral `MatchupBar` comparison bars (OFF RTG, DEF RTG, PACE, EFG%, TS%, NET RTG) fed by team analytics; "Three things to win" focus levers section that surfaces `data.focus_levers` from the existing Pre-Read deck API which had been returned but never rendered on the page.
- Compare page added "The deltas" 5-card grid (Scoring, True shooting, Playmaking, Rebounding, Impact BPM with leader's last name and delta in display type) and "Key takeaways" 3-bullet plain-language summary inside `ComparisonView` for `mode !== "percentile" && mode !== "arc"`.
- Shipped 9 new design-system primitives: `HeroHardwood`, `Reveal`, `LiveTicker`, `FloatingBall`, `SpotlightCursor`, `Parallax`, `LiveShotPulse`, `StandingsLadder`, `WinProbabilityChart`, plus `HomeLiveCourt` composing them on the home page.
- Verified with `npm run build` clean and `npm run lint` clean (7 pre-existing `usePlayerStats.ts` warnings).
- Workflow lesson: subagent fan-out across 4 parallel page-group implementation agents hit the API rate limit. Inline implementation in the main session was more reliable than parallel subagents for an 8-page design pass.

---

### Sprint 69 — Team-Fit Intelligence and Injury-Aware Context
**Branch:** `codex-sprint-69-team-fit-intelligence`

- Added `team_fit_v2` with current-team value explanation, teammate overlap, alternate-team ranking, methodology, score deltas, component scores, confidence notes, and frontend `<TeamFitPanel>`.
- Added `GET /api/team-fit/{player_id}` plus Team-Fit similarity response context so the UI can explain covered/penalized features and the teammate responsible.
- Added latest-qualified-season fallback for incomplete current-season rows so strict feature requirements do not silently hide Team-Fit intelligence.
- Added persisted `player_analysis_contexts` via Alembic `0011_player_analysis_contexts`, manual context CRUD routes, automatic injury/recovery windows from `player_injuries`, and a player-page settings drawer.
- Made Player Trend Intelligence injury-aware: injury/recovery/availability-overlapped role drops now surface `adjusted_role_status="injury_context"` while keeping raw deltas visible.
- Verified with 257 backend tests, frontend lint/build, local migration, `git diff --check`, and closeout cleanup of backend/frontend servers plus ports 8000/3000.

---

### Sprint 68 — Decision Intelligence Follow-Ons
**Branch:** `feature/sprint-68-decision-intelligence-followups`

- Closed the five Sprint-67 deferrals on a single branch: Opportunity `usg_pct` precision, Team-Fit similarity mode, Scouting Brief deep-link banners, coaching copy polish, and Player Archetype Evolution Timeline.
- Added Team-Fit similarity mode with teammate-duplicate feature penalties: same-team features within 0.5 z-score get a `0.4x` weight multiplier so duplicate strengths contribute less to comp ranking.
- Added `GET /api/archetype/{player_id}/history` and `<ArchetypeEvolutionTimeline>` with confidence-coded season dots and transition pills.
- Added scouting brief deep-link banners for player-page archetype and shot-lab anchors when URLs carry `source=brief`.
- Polished coaching copy across diagnosis tags and brief cards, including cleaner labels and evidence-row formatting.
- Verified with 4 new backend tests, 247 backend tests passing, frontend lint/build/typecheck, and live-DB smokes.

---

### Sprint 67 — Decision Intelligence: Archetypes, Shot Diagnosis, Scouting Brief
**Branch:** `feature/sprint-67-decision-intelligence`

- Shipped a deterministic 15-archetype Player Archetype Engine with z-score feature extraction, parsed height, confidence bands, contributor fingerprints, cached peer-pool frames, and TOT-preferred subject-row selection for mid-season trades.
- Upgraded similarity with `mode ∈ {season, age, team_fit}`, a 13-feature V2 distance, archetype labels on comps, and preserved legacy `find_similar_players(cross_era=...)` behavior.
- Added `/api/archetype/{player_id}`, `/api/players/{player_id}/scouting-brief`, and `/api/shotchart/{player_id}/diagnosis`.
- Added Shot Profile Diagnosis with 12 graded tags, sustainability labels, creation burden, and 50-shot minimum-sample fallback.
- Added `<PlayerArchetypeProfile>`, `<ShotDiagnosisPanel>`, and `<ScoutingBrief>` to the player page.
- Verified with 47 new backend tests (243 passing), frontend lint/build, and live-DB smokes against Jokić, SGA, and Tatum.

---

### Sprint 62 — Style Intelligence + Team Shooting Splits
**Branch:** `feature/sprint-62-style-intelligence-and-team-shooting-splits`

- Added canonical persisted official team shooting splits with new `team_shooting_split_stats` storage, Alembic `0009_team_shooting_split_stats`, `nba_client.get_team_shooting_splits`, and `sync_official_team_shooting_splits`.
- Updated `backend/data/daily_sync.sh` so shooting splits refresh with the rest of the official team dashboard stack.
- Added DB-first `GET /api/teams/{abbr}/shooting-splits` plus additive backend/frontend contracts for `TeamShootingSplitRow`, `TeamShootingSplitsResponse`, `StyleShotProfileDriver`, and `StyleXRayResponse.shot_profile_drivers`.
- Upgraded the team `Splits` tab into a dual-mode workspace with `Situational` and `Shooting` views via the new `TeamShootingSplitsPanel`.
- Deepened Style X-Ray with persisted shot-profile drivers, dynamic scenario links, shot-profile-aware label reasons, richer neighbor summaries, and a new `ShotProfileDriversCard`.
- Fixed a follow-up split-tab selection bug so the team-page mode toggle respects the user’s explicit choice.
- Verified with targeted backend tests, frontend `npm run lint`, frontend `npm run build`, and `git diff --check` clean.

---

### Sprint 61 — Shot Lab Polish + Shot Intelligence Ops
**Branch:** `feature/sprint-61-shot-lab-polish-and-ops`

- Added richer hover affordances across Shot Lab: shared `ShotHoverTooltip` surfaces attempts, expected FG%, actual FG%, Δ, and `sample_confidence` band on `ShotValueMap`, `ShotSprawlMap`, and `ShotDistanceProfile`, with low-sample pills.
- Shipped "Show me examples" replay chips: backend samples up to 3 highest-|delta| shots per quality/creation bin with `linkage_quality` (exact/derived/timeline) and `deep_link_url`; new `ShotExamplesChips` component mounted in `ShotIntelligencePanel` quality/creation bins.
- Factored `IdentityCards()` into standalone `ShotIdentityBadges`; mounted in `PlayerHeader` and `ComparisonView` summary — full `IdentityCards()` drawer preserved on the Shot Lab tab.
- **Shot Intelligence Ops panel** on `/coverage`: new `shot_intelligence_ops_service`, `GET /shotchart/ops/{season}` with per-team readiness (ready/partial/stale/missing), stale-player list, missing-context histogram, baseline status, methodology version.
- **Baseline materialization**: new `shot_quality_baselines` table (Alembic `0008_shot_quality_baselines`) + `get_or_build_baseline(season, methodology_version, force_refresh)` — reads cached baseline, builds + persists on miss, rebuilds on `force_refresh`.
- **Backfill controls**: `POST /shotchart/ops/{season}/refresh-baseline` and `.../refresh-stale-players` endpoints wired through the warehouse job framework; action buttons in ops panel.
- Retired two backlog items (Shot Lab Visual Polish + Shot Intelligence Ops/Materialization) after completion.
- Verified with 172 backend tests passing, frontend `npm run lint` and `npm run build` clean, `git diff --check` clean.

---

### Sprint 60 — Insights X-Ray + Explainability + MVP Team Impact
**Branch:** `feature/sprint-60-insights-xray-explainability`

- Promoted **Play-Style X-Ray** from a What-If stub to a dedicated Insights tab: 9 rule-based archetypes with confidence, neighbor quality bands, feature-delta movement narrative, methodology drawer, and Compare/Prep/What-If handoffs.
- Raised **Trajectory** and **Trends** to Opportunity's explainability bar: trajectory driver tooltips (`SIGNAL_DESCRIPTIONS`), new `TrajectoryMethodologyDrawer`, trends confidence + thin-sample pills on player movers, supporting-stat hover descriptions, expanded trends methodology drawer with significance bands.
- Added **lineup-aware teammate on/off swings** to MVP Team Impact: new `MvpTeammateSwing` model, `_teammate_on_off_swings` helper (top 3 partners by shared minutes, both-on vs candidate-only nets, confidence from shared possessions, ≥100-possession gate), rendered in `MvpRacePanel` with thin-sample caveats.
- Verified with 37 backend tests (15 style x-ray + 7 teammate swings + 15 MVP service), frontend `npm run lint`, `npm run build`, and `git diff --check` clean.

---

### Sprint 56 — Player Impact + Profile Clarity
**Branch:** `codex/sprint-56-player-impact-profile-clarity`

- Added additive MVP Team Impact contracts and payloads with team net, candidate game W-L, on/off net swing, on/off ORTG/DRTG, minutes, confidence, and notes.
- Added a dedicated Team Impact lens to `/mvp` candidate detail and Team Impact evidence to Voter Room comparisons.
- Reworked player-page play-by-play context into **Team Impact & Clutch** with net-rating and on/off caveats.
- Cleaned the player profile by removing default `ShotSeasonEvolution` and standalone `ZoneProfilePanel`.
- Preserved important Shot Lab functions inside the right views: action fingerprint and distance profile in Diet, recent filtered shots and Game Explorer links in Creation.
- Verified with targeted MVP backend tests, frontend lint/build, and `git diff --check`.

---

### Sprint 55 — Shot Lab Intelligence
**Branch:** `codex/sprint-55-shot-lab-intelligence`

- Added `shot_quality_v1`, an on-demand DB-first Shot Lab intelligence service for expected shot quality, actual shot making, PPS/eFG deltas, and fallback smoothing.
- Added player and team-defense endpoints for shot quality, creation-context proxies, scouting identity cards, and compact coverage/trust state.
- Added additive Pydantic and TypeScript contracts plus SWR/API helpers for quality, creation, identity, methodology, and coverage.
- Upgraded player Shot Lab, Compare Shot Lab, and Team Defense Shot Lab with Quality, Making, Creation, and Scout Summary views while preserving classic chart modes.
- Tracked the shot chart synopsis and Shot Lab Intelligence sprint spec as durable planning inputs.
- Verified with targeted shotchart/schema backend tests, frontend lint/build, and `git diff --check`.

---

### Sprint 53 — MVP Race Timeline And Refined Methodology
**Branch:** `codex/sprint-53-mvp-race-timeline`

- Added DB-first MVP race snapshot tables, idempotent snapshot materialization, manual snapshot CLI, and `materialize_mvp_snapshot` warehouse dispatch.
- Added `GET /api/mvp/timeline` with weekly reconstructed voter timeline series, movement reasons, methodology labels, and horizon metadata.
- Upgraded `/mvp` with the Voter Timeline chart, hoverable candidate paths, candidate selection, non-overlapping labels, and standalone methodology explanations.
- Implemented refined MVP methodology v3 with Basketball Value Score, Award Case Score, confidence, award modifiers, and structured qualitative lenses.
- Fixed game-log-derived MVP rates so zero-minute/DNP rows do not dilute PPG in timeline and split displays.
- Verified with targeted MVP/schema backend tests, frontend lint/build, live API smoke, and `git diff --check`.

---

### Sprint 51 — MVP Gravity Foundation
**Branch:** `codex-sprint-51-mvp-gravity-foundation` — stacked on Sprint 50

- Added DB-first MVP context tables for play-type, tracking, hustle, and gravity through Alembic revision `0005_player_gravity_context`.
- Added official NBA Gravity probing plus CourtVue proxy Gravity fallback with a shared `gravity_profile` contract.
- Extended MVP race, candidate case, context map, and new `GET /api/mvp/gravity` reads with Gravity and capped `context_adjusted_score`.
- Updated `/mvp` with a Gravity axis, Gravity case section, Box Score vs Gravity comparison strip, and methodology copy separating official NBA Gravity from CourtVue proxy Gravity.
- Verified with targeted MVP/gravity/schema/backend suites, official season sync/materialization/standings/shotchart tests, frontend lint/build, and `git diff --check`.

---

### Sprint 50 — MVP Context Map
**Branch:** `codex-sprint-50-mvp-context-map`

- Expanded MVP case payloads with award eligibility, opponent-quality splits, support-burden context, optional external impact coverage, and visual map coordinates.
- Added `GET /api/mvp/context-map` for lightweight MVP map points and quick evidence.
- Added the `/mvp` Case Map with axis toggles, availability/minutes bubble sizing, momentum color, selected-candidate evidence, and methodology language calling out box-score bias.
- Verified with MVP/backend targeted tests, frontend lint/build, and local context-map smoke checks.

---

### Sprint 49 — MVP Case Platform
**Branch:** `codex-sprint-49-mvp-case-platform`

- Expanded the MVP tracker from a ranked list into a case-building workspace with score pillars, case summaries, team context, on/off lift, advanced profile, clutch/pace fields, and inferred play-style proxy rows.
- Added `GET /api/mvp/candidates/{player_id}/case` for focused candidate case payloads.
- Versioned the MVP scoring profile as `mvp_case_v1`, added WS/48, updated shared TypeScript/API/hooks, rebuilt `/mvp`, and refreshed the home MVP teaser.
- Filled the local `2025-26` data foundation before Sprint 50 planning.

---

### Sprint 48 — MVP Award Race Tracker
**Branch:** `feature/sprint-48-mvp-tracker`

- Added the first MVP race endpoint, score model, TypeScript contracts, SWR hook, `/mvp` page, and navigation entry.
- Shipped ranked MVP candidate cards with composite score bars, stat chips, recent momentum, and player-profile links.
- Verified with frontend lint/build and backend smoke checks.

---

### Sprint 46 — CourtVue Ask Workspace
**Branch:** `feature/sprint-46-ask-workspace` — closeout pending merge

- Added DB-first query endpoints for CourtVue Ask: `POST /api/query/ask`, `GET /api/query/examples`, and `GET /api/query/metrics`
- Added a canonical query metric registry with aliases, descriptions, formats, entity support, source metadata, and higher/lower-is-better behavior
- Added deterministic interpretation for player leaderboards, team rankings, threshold filters, explicit seasons, player/team lookup fallbacks, recent player/team form, and player compare deep links
- Added the `/ask` workspace with URL-backed questions, example chips, answer cards, sortable metric tables, hover explanations, source context, suggestions, and workflow links
- Added `Ask` to the top navigation and homepage workspace grid
- Verified with full backend `pytest`, frontend `npm run lint`, and frontend `npm run build`

---

### Sprint 45 — Canonical Team General Splits
**Branch:** `feature/sprint-45-team-general-splits` — closeout pending merge

- Added canonical persisted official `TeamDashboardByGeneralSplits` rows through `team_split_stats` and Alembic migration `0004_team_split_stats`
- Normalized supported team general split families for location, wins/losses, days rest, month, and pre/post All-Star rows
- Added `sync_official_team_general_splits()` and daily-sync coverage after official team season stats, with stale cleanup limited to teams that returned fresh official payloads
- Added persisted-only `GET /api/teams/{abbr}/splits?season=2025-26` plus `TeamSplitsResponse` / `TeamSplitRow` response models
- Updated official-data and backlog docs so team general splits moved from gap to shipped, while team shooting splits remain the next split-dashboard follow-on
- Verified with targeted parsing/sync/API/migration tests, the wider official-data backend suite, full backend `pytest`, compileall, and `git diff --check`

---

### Sprint 44 — Official Data Canonicalization and Player Stats Overhaul
**Branch:** `master` (direct)

- Added canonical persisted official team-season dashboards via `team_season_stats`, Alembic migration `0003`, and daily-sync support for both official player and team season rows
- Shifted team analytics reads onto the persisted official team-season layer and documented the official-domain ownership model in `specs/official-data-source-matrix.md`
- Expanded leaderboard payloads to expose the full sortable stat library through `metric_values`, then fixed shooting percentages to derive from raw counts when stored percent columns are missing
- Rebuilt the `Player Stats` workspace around metric groups, quick metric switching, spotlight cards, stronger mobile scan-ability, richer loading/empty states, and URL-backed state sharing for filters plus table preferences
- Verified the sprint with targeted official-data and leaderboard backend tests plus frontend `npm run lint` and `npm run build`

---

### Sprint 43 — Foundation Hardening and Architecture Audit
**Branch:** `feature/sprint-43-foundation-hardening`

- Replaced startup-time schema mutation with an Alembic-backed migration workflow and added audited baseline plus legacy-drift revisions for the current backend schema
- Removed runtime reliance on `ensure_schema.py` by turning it into a compatibility wrapper and moving the app startup path off serving-time DDL
- Removed the remaining request-time player bootstrap from the advanced PBP sync flow so DB-first/runtime discipline is clearer
- Collapsed lineup-impact, play-type EV, matchup-flags, and follow-through logic behind one canonical decision-support service, then reduced the decision router to transport-only handlers
- Added a durable Sprint 43 architecture audit note and explicit `runtime_policy` metadata so warehouse-first versus legacy-compatibility behavior is documented in both code and specs
- Verified the sprint with targeted migration/decision/prep tests, full backend `pytest`, `python -m compileall backend`, frontend `npm run lint`, and frontend `npm run build`

---

### Sprint 42 — Opponent-Aware Prep and Decision Workflow
**Branch:** `feature/sprint-42-opponent-aware-prep-decision`

- Upgraded prep cards with opponent-aware urgency, best-edge, and first-adjustment rationale so the queue now answers “why now?” and “what is the first action?” more directly
- Extended focus levers with coaching prompts, projected impact framing, and opponent context so prep, pre-read, and decision tools now share one coaching story
- Rebuilt the team `decision` tab onto backend lineup-impact, matchup-flags, play-type pressure, and follow-through reports so opponent changes meaningfully alter the workflow
- Preserved prep-to-pre-read, prep-to-compare, and prep-to-replay continuity through additive URL/state context instead of introducing a new persistence layer
- Verified the sprint with targeted prep/decision/coaching backend tests, full backend `pytest`, frontend `npm run build`, and local prep/decision route smoke checks

---

### Sprint 41 — Replay Adoption Across Insights
**Branch:** `feature/sprint-41-replay-adoption-insights`

- Extended the shared replay contract into the insights workspace by making trend cards and What-If emit additive replay targets, source-aware launch context, and honest `derived` versus `timeline` trust labels
- Switched the trend cards UI onto the backend cards API so replay evidence, supporting stats, and drilldown behavior are all driven by one backend source of truth
- Added replay evidence links to What-If and carried that replay thread into compare through additive URL/state context, so compare can reopen the attached Game Explorer evidence
- Expanded Game Explorer source context with additive `source_surface` metadata so insight-launched sessions explain why the user landed on a sequence
- Verified the sprint with targeted replay/scenario backend tests, full backend `pytest`, and frontend `npm run build`

---

### Sprint 40 — Event-Centered Replay and Scouting Workflow
**Branch:** `feature/sprint-40-event-replay-scouting`

- Turned Game Explorer into an event-centered replay workflow with focused event targets, highlighted action numbers, short surrounding sequences, and additive source-aware replay context
- Expanded the 3D visualizer into a sequence-aware analytical replay surface with lead-in, focus, and follow-through navigation while keeping exact, derived, and timeline trust labels explicit
- Upgraded scouting clip anchors into event-backed replay candidates with richer event metadata, anchor-quality labeling, and export-ready claim context
- Preserved replay continuity across shot lab and scouting through additive URL/state parameters instead of introducing a new persistence layer
- Verified the sprint with full backend `pytest`, targeted replay/scouting backend tests, and frontend `npm run build`

---

### Sprint 39 — Canonical Shot Enrichment + Product Follow-Through
**Branch:** `master` (closeout prepared)

- Canonicalized the persisted shot payload around the fields current shot-lab, team-defense, Game Explorer, and 3D consumers actually use, then routed both queue-backed and legacy bulk shot writes through one shared enrichment and validation flow
- Tightened shot completeness semantics so `legacy` now means missing canonical context while `partial` captures non-exact or incomplete linkage, and refused to promote ambiguous timing fallback matches into exact links
- Carried exact/derived/timeline linkage quality through shot-lab and Game Explorer behavior, including more honest 3D and event-drill-down trust signals
- Normalized What-If scenario identifiers, improved bounded coaching framing, and added stronger source-aware follow-through between What-If, Style X-Ray, compare, scouting, and Game Explorer
- Refreshed the backlog structure by splitting `Now` into shot/data-platform versus product-intelligence tracks and adding a standalone MVP Tracking section

---

### Sprint 38 — Platform Overhaul: Data Foundation, Shot-Lab Follow-Through, and 3D Visualizer
**Branch:** `feature/sprint-38-platform-overhaul`

- Established a canonical shot/event completeness surface with ready/partial/legacy/missing reporting so the platform can reason about data freshness instead of treating every older row the same
- Added team-defense shot surfaces, shareable shot-lab snapshots, and stronger Game Explorer 3D entry points on top of the shared shot-lab contract
- Built the first 3D shot/game visualizer foundation with a procedural court, reconstructed shot arcs, event markers, and a safe WebGL fallback
- Verified the sprint with backend `pytest`, frontend `npm run lint`, frontend `npm run build`, and local route/API smoke checks

---

### Sprint 37 — Situational Shot Intelligence + 3D Foundation
**Branch:** `feature/sprint-37-situational-shot-intelligence`

- Widened persisted shot payloads with situational context fields and added shared `period_bucket`, `result`, and `shot_value` filters on the shot and zone APIs
- Added a product-facing shot refresh endpoint backed by the warehouse queue path, then wired refresh actions into player and compare shot-lab states
- Added the player `ShotContextPanel` with top-action summaries and recent filtered shots that deep-link into Game Explorer
- Updated Game Explorer to accept shot-lab query state and verified the sprint with full backend `pytest`, frontend `npm run lint`, and frontend `npm run build`

### Sprint 36 — Shot Lab Visual Renaissance
**Branch:** `feature/sprint-36-shot-lab-renaissance`

- Rebuilt the shot lab into a shared editorial-luxe visual system across player, compare, and evolution surfaces
- Turned `ShotSprawlMap` into the hero surface with layered organic density fields, softer footprint treatment, and richer story stats
- Restyled the heat, value, distance, compare, duel, zone, and evolution shot views so they read as one premium suite without changing Sprint 35 filter behavior
- Added a shared `ShotCourt` foundation for the major shot views and verified the sprint with frontend `npm run lint` and `npm run build`

### Sprint 35 — Shot Lab Expansion
**Branch:** `feature/sprint-35-shot-lab-expansion`

- Enriched persisted shot-chart payloads with `game_id` / `game_date` and added optional date-window filters on the shot-chart and zone-profile APIs
- Upgraded the player `ShotChart` into a shared-filter shot lab across scatter, heat, hex, value, sprawl, zone, and distance views
- Added a dedicated compare-page `CompareShotLab` with synchronized season, season-type, and date-window controls plus side-by-side advanced shot views
- Upgraded `ShotSeasonEvolution` with playoff support while keeping missing playoff seasons visible as empty cards
- Verified the sprint with full backend `pytest` plus frontend `npm run lint` and `npm run build`

### Sprint 34 — SprawlBall Edition
**Branch:** `feature/sprint-34-goldsberry-shot-charts`

- Shipped `ShotValueMap`, `ShotSprawlMap`, `ShotDistanceProfile`, and the first version of `ShotSeasonEvolution`
- Expanded the shot-chart surface from scatter/heat/hex into a broader Goldsberry-inspired visualization system

### Sprint 33 — Coaching System Expansion
**Branch:** `feature/sprint-33-coaching-system`

- Expanded the coaching intelligence layer with deeper play-style, decision-support, and scouting-linked surfaces
- See `specs/sprint-33-closeout.md` for the full shipped scope

---

### Sprint 32 — Warehouse Team Prep Core
**Branch:** `master` (direct)

- Canonicalized modern-season team intelligence onto warehouse `games`, canonical `play_by_play_events`, and latest `team_standings`
- Added readiness metadata on team intelligence so the UI can distinguish `ready`, `partial`, `limited`, and `missing` states safely
- Added DB-first `GET /api/teams/{abbr}/prep-queue` to assemble upcoming-opponent prep cards from schedule, standings, availability, compare stories, and focus levers
- Added the team-page `prep` tab with urgency framing, scouting-mode launch, and copyable pre-read share links
- Verified the sprint with full backend `pytest` plus frontend `npm run lint` and `npm run build`

### Sprint 30 — DB-First Player Reads + Signature Visualization System
**Branch:** `feature/sprint-30-dbfirst-viz`

- Removed request-time `nba_api` rescue from the core player profile, career stats, game-log, and standings read paths
- Standardized readiness metadata for key user reads and added coverage/refresh support in warehouse ops
- Shipped the first CourtVue chart-system layer plus premium visuals across player, compare, and insights surfaces
- Added backend coverage for DB-first read behavior and verified the frontend build/lint pipeline

---

### Sprint 1 — MVP
**Branch:** `feature/mvp-initial` → PR #1

Core platform foundation:
- Player profiles with season stats, shot charts, leaderboards
- Player comparison view
- PostgreSQL migration from SQLite cache
- Teams and learn pages

---

### Sprint 2 — PBP Sync + Advanced Dashboards
**Branch:** `codex-play-by-play-sync-and-dashboards` → PR #2

- Play-by-play sync pipeline (`pbp_import.py`, `pbp_service.py`, `pbp_sync_service.py`)
- On/off splits and lineup stats from PBP stints
- Advanced stats dashboard (clutch, second-chance, fast-break)
- PBP coverage status on player profiles
- Per-game log view on player profiles
- Team explorer and roster intelligence pages
- Player similarity engine (statistical comps across eras)

---

### Sprint 3 — Platform Enrichment
**Branch:** `master` (direct)

- League standings page + dynamic home page
- Team analytics dashboard with efficiency ratings and four factors
- Breakout Tracker (YoY improvement/decline rankings)
- Aging curve overlay + percentile comparison mode on player profiles
- Favorites/Watchlist feature
- Shot chart heatmap view + enhanced zone breakdown
- Monthly splits + streak detection on player profiles

---

### Sprint 4 — Playoff Mode + Team Lineups
**Branch:** `master` (direct)

- Playoff mode toggle across player and team views
- Team lineups tab (5-man lineup stats from PBP)
- League context on player cards (percentile positioning)
- PBP advanced stats: clutch FGA sample size, on/off ORTG/DRTG display, loading skeletons

---

### Sprint 5 — Compound Leaderboard Filters
**Branch:** `feature/compound-leaderboard-filters` → PR #3

- Multi-stat compound filtering on leaderboards (filter by multiple stat thresholds simultaneously)
- Multi-column stat display in leaderboard table
- Fixed React hooks rules violation: pre-allocated fixed SWR hook slots for dynamic filter count

---

### Sprint 6 — External Metrics + Career Arc Comparison
**Branch:** `feature/sprint6-external-metrics-compare` → PR #4

- `ExternalMetricsPanel` component on player profiles — shows EPM, RAPTOR, PIPM, LEBRON, RAPM per season with color coding and source attribution
- `DualCareerArcChart` component — overlays two players' career trajectories across BPM, PPG, PER, WS, TS%, VORP with age alignment
- `ComparisonView` updated: new "Arc" tab, EPM/RAPTOR/PIPM rows in advanced table, external metric footnotes
- Game Explorer page for synced PBP data

---

### PBP Accuracy Fix
**Branch:** `feature/pbp-accuracy-fix` → PR #5

Fixed two systematic errors in PBP-derived stats:

1. **Free-throw possession counting** — possessions ending in last FT (no prior FGA in that possession) were not counted. Added `_poss_had_fga` flag + `_LAST_FT_RE` regex to `build_stints()`. Also fixed edge case: DREB resets `_poss_had_fga` so a subsequent foul→FT sequence isn't skipped.

2. **Actual stint duration from clock** — `Stint.seconds` was always `0.0` (unused stub). Wired up clock tracking in `build_stints()` using `_parse_clock_seconds()`. NBA clock counts DOWN, so `duration = clock_start - clock_end`. `PlayerOnOffAccumulator.on_seconds/off_seconds` and `LineupAccumulator.seconds` (also stubs) are now accumulated. `_upsert_on_off()` and `_upsert_lineup()` use real seconds with fallback to possession estimate.

After merging: run `POST /api/advanced/sync-season {"season": "2024-25"}` to recompute with accurate numbers.

---

### Sprint 7 — Team Intelligence + PBP Coverage Dashboard
**Branch:** `codex-team-intelligence-dashboard`, `codex-pbp-coverage-dashboard` (Codex)

- Team Intelligence Dashboard: full team season analytics, efficiency breakdowns, roster on/off splits
- PBP Coverage Dashboard: visibility into which games/players have synced play-by-play data

---

### Sprint 8 — Data Persistence
**Branch:** `feature/data-persistence` → PR #6

Eliminated live NBA API calls on every player profile load:

- **`PlayerGameLog` ORM model + `player_game_logs` table** — stores per-game stats in PostgreSQL. Unique on `(player_id, game_id, season_type)` with `synced_at` timestamp.
- **Lazy-populate gamelogs router** — serves from DB if present and fresh. Falls back to NBA API, stores result. Historical seasons cached forever; current season refreshes after 24h.
- **Shot chart SQLite caching** — `get_shot_chart_data()` wrapped with `CacheManager.get/set` using `_cache_ttl_for_season()`.

---

### Sprint 9 — Leaderboards, Team Ops, And Workflow Hardening
**Branch:** `feature/sprint9-leaderboard-enhancements` (Claude), `codex-sprint-9-team-sync-dashboard` (Codex)

**Claude — Leaderboard enhancements + historical data:**
- **Career Leaders tab** — career averages (pts, reb, ast, bpm, ws, vorp, per, ts%) ranked across all seasons in DB; shows Seasons + GP columns
- **Team filter** — dropdown filters Player Stats leaderboard to a single team; backed by new `GET /api/leaderboards/teams` endpoint
- **Multi-column table** — primary stat highlighted + always-visible Pts/Reb/Ast/TS%/PER/BPM context columns (no extra fetches)
- **Stat tooltips** — one-sentence definition on every column header
- **URL state persistence** — `useSearchParams` + `useRouter` deep-link to any leaderboard view
- **Historical data pipeline** — added `_historical_schedule_game_ids()` to `nba_client.py` using `data.nba.com` mobile schedule feed (avoids blocked `stats.nba.com`); synced 2021-22, 2022-23, 2023-24 (~595–633 players per season, 1230 games each)
- New Pydantic models: `CareerLeaderboardEntry`, `CareerLeaderboardResponse`; `LeaderboardEntry` enriched with context columns

**Codex — Team/PBP sync operations dashboard:**
- Coverage page season sync actions and team detail handoff
- Team Intelligence Panel improvements and lineup visibility

**Workflow hardening (Codex):**
- Sprint-dependent work allocation table in `AGENTS.md` (replaces permanent ownership)
- Explicit branch isolation rule — all sprint work on assigned branch, never directly on `master`
- Sprint closeout checklist + `specs/CLOSEOUT_TEMPLATE.md`
- `specs/sprint-09-closeout.md` written as first closeout record

---

### Sprint 10 — Branch-Only Work, Not Merged
**Branch:** `feature/sprint-10-yoy-trends` (Claude), `codex-sprint-10-game-explorer-controls` (Codex)

- Claude implemented player-profile year-over-year trend indicators and season-selector work on branch
- Codex implemented Game Explorer controls and backend game-summary improvements on branch
- Neither Sprint 10 branch landed in `master`; see `specs/sprint-10-closeout.md` for deferred follow-up
- `codex-sprint-10-game-explorer-controls` was **UNSAFE to merge** — deleted in Sprint 24 branch audit

---

### Sprint 11 — Warehouse Ingestion Foundation
**Branch:** `codex-sprint-11-warehouse-foundation` (Codex) → PR #7; `feature/sprint-11-coverage-dashboard` (Claude) → carried into Sprint 12

**Codex — Warehouse foundation:**
- ORM models: SourceRun, IngestionJob, RawSchedulePayload, WarehouseGame, RawGamePayload, GameTeamStat, GamePlayerStat, PlayByPlayEvent
- Three-layer warehouse model: raw payloads → normalized facts → derived analytics
- Idempotent job pipeline with `WarehouseGame` completeness flags (has_box_score, has_pbp_payload, has_parsed_pbp, materialized)
- `warehouse_jobs.py` CLI, `warehouse.py` router, `warehouse_service.py` service layer
- Reworked canonical PBP pipeline to write to warehouse `PlayByPlayEvent` model

**Claude — Coverage dashboard frontend (carried forward into Sprint 12):**
- `WarehousePipelinePanel` component with pipeline funnel, job stats, action buttons, collapsible recent runs table
- SWR hooks and API functions for warehouse health and job management
- Integrated into `/coverage` page

---

### Sprint 12 — Warehouse Completion + Operational Hardening
**Branch:** `codex-sprint-12-warehouse-ops`, `codex-sprint-12-game-explorer` (Codex); `feature/sprint-12-warehouse-frontend` (Claude) → PR #9

**Codex — Warehouse ops hardening:**
- Season-scoped `/run-next` endpoint
- Retry/backoff in `run_next_job()`: exponential backoff (5m/10m/15m), permanent FAILED at attempt_count ≥ 3
- `retry_failed_jobs()` service + `POST /api/warehouse/retry-failed?season=` endpoint
- `backend/data/daily_sync.sh` cron wrapper

**Codex — Game Explorer rebuild:**
- `frontend/src/app/games/[gameId]/page.tsx` rebuilt fresh from master (not the unsafe Sprint 10 branch)
- Dual-write to legacy `play_by_play` + idempotent `PlayerGameLog` upsert during warehouse migration window

**Claude — Frontend hardening:**
- Season-scoped Run Next Job button (passes season to `/run-next`)
- Retry Failed button + `retryFailedJobs()` API function
- Collapsible Failed Jobs panel (job_type, job_key, last_error, attempt_count)
- Sync Today hidden for historical seasons
- Server-side season filtering for failed jobs fetch; SWR invalidation covers pbp-dashboard keys

---

### Sprint 13 — Warehouse Reliability + Ops Visibility
**Branch:** `codex-sprint-13-warehouse-reliability` (Codex) → PR #10

**Codex — Warehouse reliability + ops visibility:**
- `ApiRequestState` ORM model: DB-backed distributed rate limiter (`SELECT FOR UPDATE`) serializes NBA API calls across parallel worker processes
- `warehouse_jobs.py --loop` mode: workers poll indefinitely with configurable idle sleep and progress logging
- `warehouse_worker_pool.sh`: start/stop/restart/status for N workers with PID files + per-worker log rotation
- `POST /api/warehouse/reset-stale`: re-queues stalled running jobs (expired lease)
- `GET /api/warehouse/jobs/summary`: full queue snapshot by status, job type, stalled/failed jobs, throttle state
- `WarehousePipelinePanel` auto-poll (15s while jobs active) + ops snapshot on coverage page
- YoY trend callouts: `PlayerHeader` (PPG, TS%, AST, REB deltas) and `TeamIntelligencePanel` (net rating, scoring, assist-rate trends)
- Game Explorer event drill-down: click PBP event → score context, formatted clock, player profile link
- Coverage page memo stabilization

**Claude — Session token limit; original tasks (auto-poll, expandable rows) shipped by Codex in broader form.**

---

### Sprint 14 — Game Summary API + Game Explorer Box Score
**Branch:** `codex-sprint-14-data-layer` (Codex), `feature/sprint-14-game-summary-ui` (Claude)

**Codex — Backend data layer:**
- `GET /api/games/{game_id}/summary` backed by warehouse `games`, `game_team_stats`, and `game_player_stats`
- `GameTeamBoxScore`, `GamePlayerBoxScore`, and `GameSummaryResponse` backend models
- `game_summary_service.py` for home/away team box scores plus sorted player rows
- `warehouse_jobs.py` SIGTERM exit-through-Python fix

**Claude — Game Explorer frontend:**
- `getGameSummary()` API client + `useGameSummary()` SWR hook
- Game Explorer box score section with team stat comparison and per-team player tables
- Coverage page memo dependency fix

**Merge note:** Claude's branch needed a final contract-alignment fix before merge so the frontend matched the shipped backend response shape (`home_team_stats`, `away_team_stats`, `players`, `materialized`).

---

### Sprint 15 — Data Completion + Warehouse Hardening
**Branch:** `codex-sprint-15-data-completion` (Codex)

**Codex — Data completion + warehouse hardening:**
- Formal Sprint 15 kickoff for launch-window data completion (`2022-23` through `2025-26`)
- `player_on_off` / `lineup_stats` rematerialization idempotency hotfix merged to `master`
- Duplicate-safe raw payload persistence in `warehouse_service.py` for retried `raw_game_payloads` inserts
- `reset_stale_jobs()` made durable from the service layer
- External metric strategy corrected: `RAPTOR` as primary free external metric; `EPM`, `LEBRON`, `PIPM` treated as source-gated/licensed-only

**Claude — No major shipped branch in Sprint 15; support/validation role remained available.**

---

### Sprint 16 — Data Foundation Closeout
**Branch:** `codex-sprint-16-data-foundation` (Codex)

- Fixed player-page backend crash in `backend/routers/gamelogs.py` (Python 3.8-incompatible nested `list[...]` annotations)
- Fixed insights breakout prior-season helper in `backend/routers/insights.py`
- Made `retry_failed_jobs()` durable from the service layer in `backend/services/warehouse_service.py`
- Removed lingering import-first messaging from leaderboards; made historical team intelligence guidance season-aware
- Cleaned up the live `2025-26` worker lane before merge

---

### Sprint 17 — Team Rotation Intelligence
**Branch:** `codex-sprint-17-team-rotation-intelligence` (Codex)

- Added `GET /api/teams/{abbr}/rotation-report?season=...` endpoint
- Added `Rotation Intelligence` team-page surface: starter stability, minute risers/fallers, impact anchors, recommended games
- Scoped to warehouse-backed modern seasons with limited-state fallback for historical seasons
- Fixed pre-existing React hook-order issue in `frontend/src/components/SeasonSplits.tsx`

---

### Sprint 18 — Hardwood Editorial Refresh
**Branch:** `codex-sprint-18-hardwood-editorial` (Codex)

- Chose `Hardwood Editorial` palette and shipped it as the active platform theme
- Added shared theme tokens and reusable utility classes in `frontend/src/app/globals.css`
- Refreshed app shell + primary workflow pages across home, teams, players, compare, standings, insights, and learn
- Strengthened text contrast and signal hierarchy

---

### Sprint 28 — Compare Availability + Injury Identity Cleanup
**Branch:** `feature/sprint-28-compare-availability` — merged

- Added `GET /api/compare/player-availability` and wired compare-page injury status into the player-vs-player workflow
- Shipped `InjuryStatusBadge`, compare warning banner, and supporting `useCompareAvailability` hook
- Added unresolved-injury ops endpoints plus `/admin/injuries/unresolved` resolve/dismiss workflow
- Fixed a pre-existing Next.js state-initialization lint issue on the pre-read page during verification

---

### Sprint 29 — Standings History + Shot Zone Analytics
**Branch:** `feature/sprint-29-standings-zones` — closeout pending merge

- Added daily standings snapshots, standings history API, and standings-page trend sparklines
- Added player and compare shot-zone profile surfaces from persisted shot-chart data
- Made shot-chart reads DB-first with explicit `ready` / `stale` / `missing` states and `last_synced_at`
- Added queue-backed shot-chart ingestion jobs and daily-sync scheduling so shot-chart freshness no longer depends on request-time fallback

---

### Sprint 19 — Player Trend Intelligence
**Branch:** `codex-sprint-19-player-trend-intelligence` (Codex)

- Added `GET /api/players/{player_id}/trend-report?season=...` endpoint
- Added `Player Trend Intelligence` player-page surface: role-status strip, recent-vs-season comparison, trust signals, impact snapshot, recommended games
- Removed `next/font/google`; replaced with deterministic local font stacks

---

### Sprint 20 — Dual Team Analyst Workflows
**Branch:** `codex-sprint-20-kickoff`

- Team A: `Custom Metric Builder` on Leaderboards — `POST /api/leaderboards/custom-metric`, z-score normalization, composite rankings, anomaly detection
- Team B: `Trajectory Tracker` on Insights — `GET /api/insights/trajectory`, recent-window vs baseline, breakout/decline rankings, trajectory labels
- Established dual-team sprint structure with parallel four-role flow

---

### Sprint 21 — Metrics Workspace, Player Stats Split, and Name Consistency
**Branch:** `codex-sprint-21-kickoff`

- Split `Leaderboards` into two dedicated top-level workspaces: `Metrics` and `Player Stats`
- Added built-in starter presets and local saved presets to Metrics page
- Replaced `/leaderboards` with compatibility redirect to `/player-stats`
- Fixed visible player-name shortening on high-traffic UI including compare-page legend labels

---

### Sprint 22 — CourtVue Labs Rebrand + Metrics + Trajectory
**Branch:** `codex-sprint-22-kickoff`

- Renamed product to `CourtVue Labs` across app shell, metadata, API title, and operational banners
- Added primary custom-metric route `POST /api/metrics/custom`
- Upgraded Metrics workspace: URL-shareable state, direct player-page links, direct Compare handoff for top two results
- Extended custom-metric ranking rows with player identifiers for frontend handoffs

---

### Sprint 23 — Coach Decision Support Quartet
**Branch:** `codex-sprint-23-kickoff`

- Added team-vs-team Comparison Sandbox mode on `/compare`
- Added coach-facing Four-Factor Focus Levers on team pages
- Added Usage vs Efficiency as a second `/insights` workflow
- Added printable `/pre-read` game-day deck built from focus levers and matchup context
- Post-closeout hotfixes: compare loading, local dev CORS, full-name normalization, usage-efficiency deduplication, selected-tab readability

---

### Sprint 24 — Branch Audit and Workspace Canonicalization
**Branch:** `master`

- Restored `/Users/viv/Documents/Basketball Intelligence Platform` as the canonical clean `master` workspace
- Audited all remaining local and remote sprint branches against current `master`
- Removed stale temporary worktrees and deleted merged, superseded, or abandoned sprint branches
- Deleted stale remote feature branches so `origin/master` is the only remote source of truth
- Updated `AGENTS.md` and Sprint 24 closeout docs so future sessions start from canonical `master`

---

### Sprint 25 — Platform Intelligence Core
**Branch:** `codex-sprint-25-kickoff`

- Added the first platform-intelligence layer across team pages, insights, compare, pre-read, and Game Explorer
- Shipped team decision tools, guided game follow-through, pace/style profiles, and in-season trend cards
- Added beta/foundation workflows for what-if scenarios, play-style x-ray, play-type scouting, and lineup/style compare follow-ons
- Added new backend analytics/report services, routers, response models, and Sprint 25 QA coverage
- Post-sprint patch: home-page league leaders canonical full names; TrajectoryTracker/CustomMetricBuilder error rendering fixes; Next dev config localhost support

---

### Sprint 26 — Data Foundation Maturation
**Branch:** `feature/sprint-26-data-foundation` — merge commit `689b2ae`

- Architecture document (`specs/data-architecture.md`): full ingestion lineage map, canonical table designations, legacy deprecation markers, missing domain registry
- Injuries (new data domain): `player_injuries` table, `get_injuries_payload()` CDN function, `sync_injuries()` service, `GET /api/injuries/current` + `/player/{id}` + `POST /api/injuries/sync`, injury status badge on `PlayerHeader`
- Shot chart persistence: `player_shot_charts` table, DB-first cache in shotchart router with TTL from `_cache_ttl_for_season()` (6h current, 30d historical)
- Standings materialization: `team_standings` table, `materialize_standings()` service, standings router reads DB first with live fallback, `daily_sync.sh` wired to run all three pipeline steps

---

### Sprint 27 — Availability + Upcoming Schedule
**Branch:** `feature/sprint-27-availability-schedule`

- Added `GET /api/schedule/upcoming` backed by warehouse `games` for future schedule visibility
- Shipped team-page roster availability and structured pre-read availability summaries using the injuries pipeline
- Added official NBA injury-report PDF fallback when the live injuries JSON feed returns `403`
- Hardened injury identity resolution with alias-backed matching, persisted unresolved rows, and `GET /api/injuries/unresolved`
---

### Sprint 53 — MVP Race Timeline And Refined Methodology
**Branch:** `codex/sprint-53-mvp-race-timeline` (Codex)

- Added DB-first MVP race snapshots through Alembic revision `0007_mvp_race_timeline`, including idempotent materialization, manual CLI, and warehouse job dispatch.
- Added `GET /api/mvp/timeline` with weekly reconstructed voter timeline output, movement reasons, methodology labels, and top-candidate rank/score/stat series.
- Rebuilt `/mvp` movement into a larger Voter Timeline with hoverable rank paths, candidate selection, non-overlapping labels, and explanatory methodology copy.
- Implemented refined MVP methodology v3: Basketball Value Score, Award Case Score, ranks, confidence, award modifiers, and structured qualitative lenses.
- Demoted legacy scoring profiles into sensitivity comparison while keeping API compatibility.
- Fixed game-log-derived MVP PPG by excluding zero-minute/DNP rows from timeline and split denominators.

---

### Sprint 54 — MVP Platform+
**Branch:** `codex/sprint-54-mvp-platform-plus` (Codex)

- Added MVP Voter Room case comparison inside `/mvp`, backed by `GET /api/mvp/voter-room`.
- Added compact MVP player-page embeds for current candidate-pool players.
- Added MVP source/snapshot coverage ops through `GET /api/mvp/coverage` and a `/coverage` MVP Coverage panel.
- Operationalized daily snapshots with `POST /api/warehouse/queue/mvp-snapshot`, current-season queue inclusion, `/api/mvp/snapshot-freshness`, and a `/mvp` freshness badge.
- Verified with targeted MVP/schema backend tests, frontend lint/build, API/page smokes, and `git diff --check`.

---

### Sprint 57 — Insights Revamp: Trajectory Depth + Lineup Context
**Branch:** `feature/sprint-57-insights-revamp` (Claude, single-stream)

- Redesigned Trajectory Tracker into a two-column multi-signal workspace: ranked player list with inline driver-decomposition bars (left), detail panel with rolling Recharts sparklines, full driver decomp card, clutch split, on/off swing, shot-quality delta, and evidence-game chips linking to Game Explorer (right).
- Extended `TrajectoryPlayerRow` with position percentile (0–100 via normal CDF per-bucket z-scoring), all driver contributions sorted by abs weighted contribution, top evidence games, clutch context, on/off context, recent/baseline averages.
- Added `GET /api/insights/trajectory/{player_id}/series` for per-game sparkline time-series.
- Added `lineup_context_service.py` and `GET /api/insights/lineup-context/{player_id}` — top 5 teammates by shared possessions (≥100 poss gate, LIKE false-positive guard), possession-weighted net rating, confidence banding.
- Extracted shared `InsightsHeader` component with cross-tab handoff chips; all four insights tabs share the same team/season/opponent URL state.
- Integrated lineup context collapsibles into `MvpRacePanel` Team Impact section and `PlayerPbpInsights` Team Impact & Clutch panel.
- Verified with 17 backend tests (all pass), frontend `npm run lint`, frontend `npm run build`, and `git diff --check`.

---

### Sprint 58 — Usage vs Efficiency: Opportunity Workspace
**Branch:** `feature/sprint-58-usage-opportunity-workspace` (Claude, single-stream)

- Replaced two-lane USG/TS board with a multi-axis **Opportunity Workspace**: 5 capped z-scores (±2.0) per position bucket (G/F/C) — `efficiency_load_gap` (0.30), `team_impact_swing` (0.25), `lineup_synergy_lift` (0.20), `role_fit_gap` (0.15), `cohort_percentile` (0.10) — weighted into composite `opportunity_score` and separate `team_opportunity_score`.
- New `backend/services/opportunity_service.py`: bulk lineup synergy (single `LineupStats` query per season, Python partition by player), per-bucket z-scoring via `math.erf` normal CDF, confidence bands (high/medium/low), directional hints with structured `hint_basis` list, team roll-up of top 3 drivers across filtered roster.
- New `GET /api/insights/opportunity` (season, team, min_minutes, position params) returning ranked rows, methodology block (weights, z-score cap, gating thresholds, confidence definitions), warnings, and optional team rollup.
- Old `/api/insights/usage-efficiency` marked `deprecated=True` in FastAPI; kept live, no frontend callers remain.
- Full `UsageEfficiencyDashboard.tsx` rewrite: hero/filter panel (team, season, position, min MPG, signal filter chips), Team Rollup section, two-column layout (ranked list left, detail panel right).
- 8 new `opportunity/` components: `OpportunityDriverBar` (with `SIGNAL_LABELS` + `SIGNAL_DESCRIPTIONS` hover tooltips via `title` + `cursor-help` + dotted underline), `OpportunityRow`, `EfficiencyLoadCard` (CSS scatter dot), `TeamImpactCard`, `RoleFitCard` (shot diet vs cohort table), `CohortPositionCard`, `DirectionalHintBanner`, `MethodologyDrawer` (collapsible `<details>`), `TeamRollup`.
- Deleted `UsageLoadBoard.tsx` (retired).
- 13 new backend tests covering all z-score signal paths, capping, confidence bands, directional hint triggers, possession gate, team rollup, position filter, and empty-pool edge case.
- Verified with `npm run lint`, `npm run build`, and `git diff --check`.

---

### Sprint 59 — Insights Trend Intelligence Overhaul
**Branch:** `codex-sprint-59-insights-trend-overhaul` (Codex, single-stream)

- Rebuilt Insights Trend Cards into **Trend Intelligence**: team drift cards plus player movers and pinned-player foundation detail.
- Made `backend/services/trend_card_service.py` the canonical trend-card service; `/api/trends/cards` now accepts `team`, `season`, `window`, optional `player_id`, and optional `signal`.
- Expanded the trend contract with `data_status`, `overview`, `player_movers`, `pinned_player`, `methodology`, card scope, driver signal, related player IDs, and foundation coverage states.
- Added team cards for shot profile, efficiency, turnover pressure, foul pressure, pace/scoring, rotation drift, and clutch context while preserving Game Explorer replay targets.
- Scored player movers from existing persisted data: game logs, season baselines, on/off, lineup, clutch, shot charts / `shot_quality_v1`, play-type, tracking, hustle, and gravity where available.
- Wired shared `player_id` and `signal` URL state through `InsightsHeader`, Trends, Opportunity, and Trajectory.
- Made Opportunity Team Roll-Up tiles active: clicking a driver filters the workspace and pins the first qualifying player into the detail panel.
- Hard-deleted deprecated `/api/insights/usage-efficiency`, its backend service/models, frontend API/hook/types, and orphan `UsageBurdenMatrix`.
- Verified with 30 targeted backend tests, frontend `npm run lint`, frontend `npm run build`, local API/page smoke checks, and `git diff --check`.

---

### Sprint 60 — Insights X-Ray Explainability Promotion
**Branch:** `feature/sprint-60-insights-xray-explainability` (Claude)

- Promoted Play-Style X-Ray into the main Insights workflow and brought its explainability depth up to parity with the stronger Insights tabs.
- Added trajectory/trends explainability parity and MVP lineup-aware teammate on/off swings.
- Closed on branch and merged to `master`; reference remains in earlier closeout artifacts plus this history log.

---

### Sprint 61 — Shot Lab Polish + Shot Intelligence Ops
**Branch:** `feature/sprint-61-shot-lab-polish-and-ops` (Claude, single-stream)

- Added shared `ShotHoverTooltip`, replay-example chips with linkage-quality gating, `ShotIdentityBadges` in PlayerHeader + Compare, and a `/coverage` Shot Intelligence Ops panel.
- Materialized `shot_quality_baselines` with refresh controls so baseline computation moved off the hot path and into an explicit ops workflow.
- Verified with 172 backend tests, frontend `npm run lint`, frontend `npm run build`, and `git diff --check`.

---

### Sprint 62 — Style Intelligence + Team Shooting Splits
**Branch:** `feature/sprint-62-style-intelligence-and-team-shooting-splits` (Codex, merged via `ad94ce0`)

- Added canonical persisted official team shooting splits with `team_shooting_split_stats`, DB-first API reads, and daily sync coverage.
- Upgraded the team Splits tab with a new shooting workspace and expanded Style X-Ray with persisted shot-profile drivers, stronger label reasons, and richer neighbor summaries.
- Laid the Team/Insights foundation Sprint 63 later extended into compare, prep, team-defense, and replay-connected workflows.

---

### Sprint 63 — Team/Insights Workflow Expansion
**Branch:** `feature/sprint-63-team-insights-workflow-expansion` (Codex, single-stream)

- Added a canonical team shot-profile service and extended persisted official shooting-split families into Compare, Prep, pre-read, team-defense, and Style X-Ray.
- Expanded Style X-Ray with short-horizon history, drift narratives, stronger neighbor context, and direct compare/prep/what-if/replay handoff payloads.
- Added replay-aware coaching follow-through and prep snapshot continuity keyed by matchup/date, while preserving evidence source and exact/derived/timeline trust state.
- Added trust-note handling for ambiguous official split families, including assisted-shot caution wording and weaker-claim gating.
- Verified with targeted backend tests, frontend `npm run lint`, frontend `npm run build`, and `git diff --check`.

---

### Sprint 65 — Scouting & Opportunity Fit
**Branch:** `feature/sprint-65-scouting-opportunity-fit` (Claude, single-stream)

- Added in-process TTL cache on `build_opportunity_report`, compare-handoff peers per row, and AST/G + TOV/G role-fit depth so Opportunity became more reusable inside staff workflows.
- Added `ClaimInferenceConfidence` on every scouting claim, opponent-specific anchored-play counts, confidence-order ranking inside sections, and claim-level Compare handoff with inbound-context banners on Compare and Pre-Read.
- Renamed `UsageEfficiencyDashboard.tsx` to `OpportunityDashboard.tsx`, deleted stale pre-Sprint-58 usage scaffolding, and fixed compound position bucketing so hybrid-position players stop falling into `other`.
- Verified with 14 new backend tests, frontend `npm run lint`, frontend `npm run build`, and live dev-server exercise.

---

### Sprint 66 — Staff Packet And Coaching Handoff
**Branch:** `codex-sprint-66-staff-packet-handoff` (Codex, single-stream)

- Upgraded `pre_read_snapshots` into named staff packets with Alembic revision `0010_pre_read_packet_metadata`, editable packet metadata (`title`, `note`), and frozen packet payload preservation.
- Added packet-aware Pre-Read snapshot contracts and service flows for create/list/get/update, matchup/team-history packet summaries, and markdown export generated from the saved snapshot.
- Rebuilt `/pre-read` around a packet workflow: packet library tabs, inline packet metadata editing, scouting-packet rendering, and snapshot-level `Open` / `Copy share link` / `Export markdown` actions.
- Added ScoutingReportView packet pinning so analysts can carry up to 3 claims with confidence pills and ranked clip anchors directly into the saved Pre-Read packet.
- Verified with targeted Sprint 66 backend tests, full backend `pytest` (196 passing), frontend `npm run build`, frontend `npm run lint` with pre-existing warnings only, and a live manual smoke walkthrough after applying the local Postgres migration.

---

### Sprint 69 — Team-Fit Intelligence and Injury-Aware Context
**Branch:** `codex-sprint-69-team-fit-intelligence` (Codex, single-stream)

- Shipped Team-Fit Intelligence v2 with `GET /api/team-fit/{player_id}`, current-team fit scoring, alternate-team ranking, score components, warnings, methodology, and frontend `<TeamFitPanel>`.
- Added Team-Fit overlap explanations in similarity/player-page surfaces, including teammate-covered feature chips and latest-qualified-season fallback for incomplete current-season rows.
- Added persisted analysis contexts, manual context CRUD routes, automatic injury/recovery windows from `player_injuries`, and a player-page settings drawer.
- Made Player Trend Intelligence injury-aware so injury/recovery/availability windows can adjust `losing_trust` reads without hiding raw deltas.
- Verified with 257 backend tests, frontend build/lint, `git diff --check`, local Alembic migration, and server cleanup.

---

### Sprint 71 — Methodology Rigor Layer
**Branch:** `codex-sprint-71-methodology-rigor` (Codex, backend/docs-only)

- Added shared methodology contracts, registry service, and `GET /api/methodology` / `GET /api/methodology/{domain}`.
- Added reliability primitives for empirical Bayes shrinkage, reliability scoring, confidence mapping, uncertainty bands, robust z-scores, winsorized z-scores, and sample context.
- Added optional `analysis_metadata` to Shot Lab, Team-Fit, and Opportunity responses so clients can inspect reliability, drivers, limitations, and validation notes without breaking existing consumers.
- Updated `specs/platform-methodology.md`, added `specs/methodology-validation.md`, refreshed backlog/coordination docs, and intentionally avoided frontend files during Claude's parallel frontend sprint.
- Verified with 263 backend tests, `git diff --check`, methodology doc coverage checks, and FastAPI `main` import smoke.
