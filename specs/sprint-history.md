# Sprint History Archive

Sprints 1–43. Current sprint summaries also live in `CLAUDE.md` under "Recent Sprints".

For detailed per-sprint records, see the individual closeout files in this directory:
`specs/sprint-09-closeout.md` through `specs/sprint-43-closeout.md`

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
