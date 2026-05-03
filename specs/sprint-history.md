# Sprint History Archive

Archived sprint summaries through Sprint 83. The two most recent sprints also stay inline in `CLAUDE.md` under "Recent Sprints".

For detailed per-sprint records, see the individual closeout files in this directory where available:
`specs/sprint-09-closeout.md` through `specs/sprint-59-closeout.md`, plus `specs/sprint-62-closeout.md` and `specs/sprint-67-closeout.md` onward.

---

### Sprint 83 — MVP Launch Readiness
**Branches:** `feature/sprint-83a-blockers`, `feature/sprint-83b-launch-polish`, `feature/sprint-83c-playoff-polish` (all merged to master)

- Three-stream production polish sprint plus follow-ons (dynamic OG image + post-merge lint cleanup). 472 → 480 backend tests (+1 net new, from 83c regular-season fallback). `npx tsc --noEmit` clean. `npm run build` succeeds. No feature additions — pure polish for the public launch.
- **Stream A — Critical UX production blockers (9 commits):** leaderboards loading skeleton (was returning `null`), mobile hamburger nav + secondary "More ▾" dropdown, team detail tabs as native `<select>` on mobile, standings table 4-column mobile layout via `hidden md:table-cell`, `app/not-found.tsx` + `app/error.tsx` for graceful 404 + error boundary, localStorage hardening across `useFavorites` / `CustomMetricBuilder` / RegularHome, search dropdowns capped at 60vh with scroll, onboarding `bip-kicker` labels above PlayerDashboard's Gravity / Archetype / Team Fit panels.
- **Stream B — First-impression polish + SEO + analytics (5 commits):** home hero rewrite for casual audience + 3-bullet kicker affordances + `hidden sm:block` on platform-card descriptions; root-layout `Metadata` with full `openGraph` + `twitter` blocks; `@vercel/analytics` mounted in root layout; `app/robots.ts` + `app/sitemap.ts` (Next.js dynamic helpers, 20 routes); offseason "Between seasons" empty state on HomeLeagueLeaders; LiveTicker context label.
- **Sprint 83-followup — Dynamic OG image:** `app/og/route.tsx` returns a code-generated 1200×630 PNG via `next/og` `ImageResponse` using the existing `courtvue-mark.svg` geometry inlined and the brand palette. Replaces the `/og-home.png` placeholder. Workmanlike but not bespoke; logged to BACKLOG for Sprint 84 polish.
- **Stream C — Playoff surface polish** (Vivek pre-close walkthrough, single commit): Shot Diet Pressure copy + explainer paragraph, Lineup Chess empty-state with threshold context, From the Desk → series-aware `<Link>` to `/bracket?series_id=X` in `BroadsheetHero`, Four Factor Edge regular-season fallback in `_build_metric_edges` with per-team warnings rendered as caveat below `FourFactorsPanel` grid (panel always renders 8 metrics now; new `test_series_intelligence_falls_back_to_regular_season_baseline`), Story Rail tile deep-links via new `_resolve_player_active_series_href` helper, `bracket/page.tsx` reads `searchParams.series_id` for pre-selection, SeriesCard per-game G1–G7 chip strip with W/L coloring from top-seed perspective.
- **Deferred:** VM deploy execution (Sprint 82+83 hangover — Vivek hit Hetzner Cloud Console password issue), OG image polish, bracket auto-advancement (parent-slot mapping is a real feature, not polish), per-series detail page, lint cleanup pass for 4 pre-existing errors. All documented in BACKLOG. Closeout: `specs/sprint-83-closeout.md`.

---

### Sprint 82 — Public Platform + Player Depth + Scraper Hardening
**Branches:** `feature/sprint-82a-player-depth`, `feature/sprint-82b-hosting`, `feature/sprint-82c-scrapers`, `feature/sprint-82d-public-mode` (all merged to master)

- Four-stream sprint (A → B → C in parallel + a follow-on D for public-mode pivot). 464 → 479 backend tests (+15 net new). `npx tsc --noEmit` clean.
- **Stream A — Player splits + play-type UI:** `PlayerSplitsPanel.tsx` (Location/Win-Loss/Days-Rest/Month/Pre-Post-All-Star family toggle, 18-column stat table) and `PlayTypePanel.tsx` (Synergy archetypes with possession-share bars + PPP/percentile coloring), both wired into `PlayerDashboard` (regular-season only, self-fetching). Closes Sprint 81 deferred frontend work.
- **Stream B — Public hosting infra:** `infra/bip-api.service` (gunicorn + 2 uvicorn workers, loopback bind), `infra/Caddyfile` (auto-HTTPS + security headers + JSON logs), `infra/caddy-install.sh` (one-time bootstrap), `infra/deploy.sh` (idempotent post-pull), `infra/playwright-install.sh`, `infra/README.md` runbook. `gunicorn==23.0.0` added to requirements.
- **Stream C — Scraper hardening:** New `PlaywrightScraper` base class (headless Chromium via `playwright.sync_api`, ImportError guard, viewport spoofing, `wait_until="networkidle"` for Cloudflare JS challenges); PST switched from `HttpScraper` (bypasses 403). Sports Reference URL fixed (`-per-game.html` → `-leaders.html`); parser rewritten to target `div#leaders_pts_per_g` blocks with HTML Comment fallback for SR's anti-scrape wrapping; `_fetch_player_profile_stats()` follows player profile links for full stat lines.
- **Stream D — Public mode pivot:** Mid-sprint Vivek pivoted from FO-only basicauth to fully public read-only. (D1) Dropped Caddy basicauth, switched api.courtvue.app to read CF-Connecting-IP, runbook updated with Cloudflare WAF rate limiting + cache rules. (D2) New env flag `NBA_API_USER_FETCH_DISABLED` raises `LiveFetchBlockedError` on cache miss; 3 uncached user-facing methods wrapped with cache-first + guard; `daily_sync.sh` exports flag=false so cron always fetches normally; 7 new guard tests. (D3) New `frontend/src/lib/external-metrics.ts` is single source of truth for LEBRON/RAPTOR/EPM/PIPM/RAPM; new `<ExternalMetricsAttribution>` component; fixed three under-attributed surfaces (`StatTable`, `CustomMetricBuilder`, `ComparisonView`).
- **Deferred:** VM deploy execution (Hetzner Cloud Console password issue paused it; rescue-mode SSH recovery is the recommended path). Closeout: `specs/sprint-82-closeout.md`.

---

### Sprint 81 — Data Foundation Closeout
**Branch:** `master` (two-stream sprint, sequential commits on master)

- Two-stream parallel sprint replacing seed-CSV stubs with live data, retiring legacy `play_by_play` table, activating calibrated `mvp_case_v5` weights, and adding two new official data domains. 415 → 464 backend tests (+49 net new).
- **Stream A — Real Data Scrapers:** Spotrac salary scraper (replaces 490 estimated contracts in Trade Machine), ProSportsTransactions injury history scraper (replaces 220 synthetic rows), Sports Reference draft prospect scraper (replaces 30 hand-entered prospects). All three share `backend/data/scrapers/_base.py` (`HttpScraper` + `ScraperError`) with user-agent rotation, 2s rate-limit, retry/backoff. All three fall back transparently to the existing seed CSV on any failure so dependent surfaces never go dark.
- **Stream B1 — Legacy `play_by_play` retirement:** Migrated 9 service/router files + 2 sync scripts to `PlayByPlayEvent`. Halted dual-writes from `warehouse_service` and `pbp_sync_service`. Removed `PlayByPlay` ORM model + `GameLog.play_by_play` relationship. Migration `0018_sprint81_drop_legacy_pbp` drops the table (frees ~677 MB, 30% of DB). New CI guard test fails CI if anyone re-imports the retired model.
- **Stream B2 — `mvp_case_v5` calibration activation:** New table `award_case_candidates` (migration `0019`); new `data/materialize_award_modifiers.py` populates Basketball Value + 5-modifier vectors from `season_stats` + `team_season_stats`. `award_calibration_service.calibrate_award_case_weights()` now runs LOO-CV with ±0.04 drift cap, only flips `calibration_pending=False` when LOO-CV Spearman ≥ 0.7.
- **Stream B3 — New official data domains:** `player_split_stats` (per-player Location / W-L / Days Rest / Month / Pre-Post All-Star) and `play_type_stats` (Synergy archetype rows: Isolation / Transition / PRBallHandler / PRRollMan / Postup / Spotup / Handoff / Cut / OffScreen / Putbacks / Misc). Migration `0020`. Endpoints: `/api/players/{id}/splits` and `/api/players/{id}/play-types`. Frontend rendering deferred to Sprint 82.
- `daily_sync.sh` wired with three new scrapers + materializer + two new domain syncs. Closeout: `specs/sprint-81-closeout.md`.

---

### Sprint 80 — Cloud Migration: DB + Cron Off the Laptop
**Branch:** `master` (infra-only sprint, no feature branch)

- Single-stream infrastructure sprint migrating Postgres and the daily sync cron from Vivek's MacBook to a Hetzner CX22 VM (`5.78.114.15`, Ashburn VA) at ~$5/month. Cloudflare R2 free tier for nightly pg_dump backups. FastAPI deploy deferred to Sprint 81.
- **DB cleanup:** Alembic migration `0017_sprint80_raw_payload_ttl` TTLs `raw_game_payloads` rows older than 30 days (freed 184 MB). Legacy `play_by_play` table drop deferred — 11+ active service readers found.
- **Salary data improvement (Sprint 79 carry-over):** `contracts_2025_26.csv` expanded to 514-player coverage. `salary_source` field wired backend → router → frontend. Trade Machine shows amber `est.` badge per player and panel banner for estimated contracts.
- **Migration:** `pg_dump` → scp → `pg_restore`. Verified: PASS: 50 tables, 4,558,469 rows, `alembic_version=0017_sprint80_raw_payload_ttl`.
- **Cron:** Python venv + full requirements on VM. Crontab active: 4am UTC backup, 6am daily sync, */30 post-game, Sunday 5am restore drill. Each job sources `/etc/bip/env`.
- **Backup:** `infra/bip-backup.sh` → gzip → R2, `infra/bip-backup-prune.sh` (7d/4w/3m), `infra/bip-backup-verify.sh` (weekly drill). Manual backup confirmed: `bip-20260430.dump.gz` (140 MB) in R2.
- No test count change (infra-only). `npx tsc --noEmit` clean. Closeout: `specs/sprint-80-closeout.md`.

---

### Sprint 79 — Data Foundation: Playoff PBP Fix + Methodology Unblocks
**Branches:** `feature/sprint-79-*` (3 parallel streams)

- **Stream B — Playoff PBP Derivations:** Fixed `_upsert_lineup` bug where `filter_by` was missing `is_playoff`, which would silently clobber regular-season lineup rows. Added `is_playoff: bool = False` cascade to five helpers. Added `sync_pbp_for_playoffs_from_db()`. Fixed `bulk_sync_service.py` hardcoded `"Regular Season"` (lines 372, 424). Wired `sync_playoff_pbp.py` into `daily_sync.sh`. Migration `0014_sprint79_playoff_indexes` + NULL backfills.
- **Stream A2 — `opportunity_v2`:** Materialized `role_expansion_observations` — 286 observations from 1,063 players. New `opportunity_uplift_service.py`: shrunk-Mahalanobis KNN (K=20). `OpportunityUplift` as sibling `OpportunityRow.uplift` — no breaking change. Migration `0015_sprint79_role_expansion`. Registry bumped `opportunity_v1 → v2`.
- **Stream A1 — `mvp_case_v5`:** Seeded `award_voting` table (57 ballot rows, 13 MVP races). `award_calibration_service.py`: coordinate-descent fitter, drift cap ±0.04, leave-one-season-out CV. Migration `0016_sprint79_award_voting`. Registry bumped `mvp_case_v4 → v5`.
- **Bugs fixed:** `0013` boolean defaults (`sa.text("false"/"true")`), `salary_ingestion_service` bulk rollback on unique violation (per-row flush fix), Alembic revision name over varchar(32).
- Verified with **415 backend tests** (+18 new). Closeout: `specs/sprint-79-closeout.md`.

---

### Sprint 78 — 10-Team Parallel Sprint: Front Office + Casual Fan
**Branches:** `feature/sprint-78-phase0-schemas` + 10 feature branches (Claude, two streams of 5 teams)

- Largest sprint to date. **10 parallel feature teams** running the standard `Architect → Engineer → Reviewer → Optimizer` pipeline scaled up from Sprint 77's 8. Two streams of five — Front Office (NBA exec) features and Casual Fan engagement features. Three teams (FO1, FO3, FO5) got expanded engineering allocation for live-data ingestion.
- Phase 0 schema kickoff landed 8 new tables on `master` ahead of any team architect (player_contracts, draft_prospects + stats + measurements, draft_pick_assets, player_injury_history, player_streaks, milestone_snapshots) so 10 concurrent architects could spec services against stable types without colliding on `models.py`. Alembic migration `0013_sprint78_phase0_schemas` is idempotent.
- **Stream A — Front Office:**
  - **FO1 Trade Machine** with salary ingestion (seed CSV + stubbed Spotrac interface), ±125% salary-matching for up to 4-team packages with tax/apron/BYC/TPE flagged-not-enforced, trade impact via `lineup_impact_service`, new `/trade-machine` route.
  - **FO2 Free Agency Workspace** with tier bucketing + per-FA top-10 team fits via existing `team_fit_service`, new `/free-agency` route.
  - **FO3 Draft Prospect Workspace** with NCAA-pace → NBA-pace per-100 translation (confidence-scored), 5-NBA-comp grid via `similarity_service`, seed CSV + stubbed Sports Reference interface, new `/draft` board + `/draft/[prospectId]` detail.
  - **FO4 Multi-Year Team Arc** with position-bucketed empirical aging curves + 3-year roster projection layered with `PlayerContract` cap state + `DraftPickAsset` overlay + decision-lever sliders, new "Arc" tab on `/teams/[abbr]`.
  - **FO5 Injury Impact** with tiered (body_part × age × recurrence) duration distributions + hardcoded prior fallback + extended `team_availability_service` for rotation re-projection, seed CSV + stubbed ProSportsTransactions interface, new player-profile + team panels.
- **Stream B — Casual Fan:**
  - **CF1 Shareable Story Cards** — Pillow-based 1200×630 PNG renderer with broadsheet aesthetic, `/api/share/{type}/{id}.png` endpoints, `<ShareCardButton>` mounted on player / game / series surfaces, OG metadata wired.
  - **CF2 Bracket Pick'em** — localStorage-only single-user "you vs CourtVue's model" picks with model bracket comparison via `playoff_simulator_service`, new `/picks` route.
  - **CF3 Career Hall of Fame** — era-adjusted PPG (pace ratio) + TS%-vs-league delta + 12-milestone catalog + cross-era similarity peers + composite HOF projection, new "Legacy" tab on player profile.
  - **CF4 Game Story Mode** — frontend-led `<GameStoryTimeline>` reusing existing WP swing events + possession-diary + scoring events (`narrative_score = |wp_delta|*100 + lead_impact*0.5`), no new backend service.
  - **CF5 Streaks & Milestones** — 5-streak detection + 12-milestone proximity + percentile-ranked signature performances, new `/milestones` route + player streak chips + story-rail tile + nightly snapshot in `daily_sync.sh`.
- All 10 agents worked in dedicated git worktrees to avoid main-checkout contention. File-lock discipline was strict-additive only; merge coordinator resolved conflicts at integration time using a small Python `merge_resolve.py` helper for the "additive both sides" pattern.
- Verified with **397 backend tests** (was 360, +37 net new), `npx tsc --noEmit` clean, lint shows only the 8 pre-existing warnings unchanged. Closeout: `specs/sprint-78-closeout.md`.

---

### Sprint 77c — Broadsheet Live Data + Sync Hooks
**Branch:** `feature/sprint-77c-broadsheet-live-data` (Claude, single-stream conversational)

- Replaced hardcoded Sprint 77 prototype copy with live data across the playoff broadsheet. `/api/playoffs/today` now merges the live `cdn.nba.com` scoreboard so upcoming + in-progress games appear before nightly sync; new `tipoff_utc` and `broadcaster` fields on `PlayoffSeriesGameWithMatchup`. New `/api/playoffs/story-rail` endpoint with auto-generated tiles (Heat Check / Efficiency Desk / X-Factor) — internal links only, no external URLs. Hero + by-the-numbers strip on `/playoffs` now compute from live bracket + today endpoints (round label, headline templated by game count, prose subhead listing tonight's matchups, real broadcasters).
- Narrative Leaders ranks by composite impact score (`pts*0.35 + ast*0.20 + reb*0.10 + min(ts,0.65)*100*0.20 + net*0.15`) with qualifying thresholds (GP≥4, MIN≥22, PPG≥12) and a TS%-cap at 65 to neutralize small-sample shooting inflation. Dynamic 3-stat line picks AST vs RPG and TS% / NET / USG% based on what's most distinctive per player. Methodology popover (CSS group-hover) anchored to a ⓘ glyph reveals the formula + thresholds.
- Postseason heatmap fixes: USG% scaling bug (0..1 fraction → 0..100 axis), rotation thresholds bumped to gp≥4/min≥18 to match leaders, hover tooltip with player name + team · GP · MPG + 3-stat grid + regular-season TS% baseline. `TopLeadersTable` added on `/leaderboards` with stat-picker chips that respond to the seasonType toggle; heatmap gated to Playoffs only.
- Series tracker win-bar cells deep-link to `/games/{gameId}`; `BroadsheetGameCard` links to game detail directly (was sending every click to `/pre-read?series_id=...` which then defaulted to OKC vs BOS). `game_detail_assembler` returns a base response when PBP is missing instead of 404'ing the whole page. Mode toggle bug fixed: `useViewMode` now uses `useSyncExternalStore` over a shared module-level store so ModeToggle and HomePage re-render together.
- New `sync_today_playoff_finals.py` ingests final-status games from the live CDN scoreboard before `build_or_refresh_bracket`, wired into `daily_sync.sh` for both post-game (every 30 min) and morning paths. New `sync_playoff_pbp.py` is a focused playoff-only PBP sync that doesn't pollute regular-season aggregates; ran end-to-end against 2025-26 (now 36 games covered). Cron installed on Vivek's laptop with documented schedule. Backlog entry added for moving the cron off-laptop to a server.
- Quick wins from the design audit: 56px logo mark + new `courtvue-mark.svg`, favicon (`icon.svg`) replacing legacy `.ico`, `bip-display tabular-nums` on StatCard values, momentum gradient on WinProbabilityChart, animated Ticker on MVP composite scores, ported brand primitives (Kicker/Pill/Button/Stat/Icon/Hardwood/Reveal/Ticker) and chart components (WinProbability/StandingsLadder/BoxScoreTable) into reusable directories.
- Verified with **360 backend tests** (no count change — same suite as Sprint 77, with the storyline test patched to mock the live CDN), `npx tsc --noEmit` clean, `npm run lint` shows the 7 pre-existing warnings unchanged. Closeout: `specs/sprint-77c-closeout.md`.

---

### Sprint 77 — Broadsheet Playoff Home + Game Detail Deep-Dive
**Branches:** `feature/sprint-77a-game-data-foundation` + `feature/sprint-77b-broadsheet-screens` (Claude, two-team parallel, Architect → 8 Engineers → Reviewer → Optimizer)

- Shipped a fresh broadsheet/newsprint visual direction for `/` (replaces Sprint 73's home during the playoff window) and a deep Game Detail page with 12 new modules above the existing box-score sections. Driven by a new design tarball that introduced the broadsheet feel + a user-facing Mode toggle (Playoff / Regular / Offseason) on top of Sprint 73's auto-detect.
- Stream A built per-game data primitives: WP trajectory + lead-tracker (closed-form logistic over PBP), possession diary (top 24 lead-impact possessions tagged shot/defense/turnover/transition/clutch), per-quarter player +/- via PBP substitution walk, series odds history (post-game WP snapshots via Sprint 75 simulator overrides), and a single resilient `game_detail_assembler`. Plus `useViewMode` hook (auto-detect + localStorage override), storyline copy on `/api/playoffs/today`, and `/api/playoffs/leaders` with trend symbols + 5-game grades.
- Stream B built 26 new components under `frontend/src/components/broadsheet/` (11 home + 15 game-detail). Auto-pick scoreboard chrome for live/halftime games, broadsheet for finals + pre-game; manual toggle persists in localStorage. Existing `/games/[gameId]` box-score / PBP feed / 3D-visualizer / score timeline preserved below the new modules under `#legacy-game-explorer` anchor.
- All broadsheet UI gated by `useViewMode` so toggle-back to `regular_season` or `offseason` renders Sprint 73's home cleanly under the same masthead chrome.
- Reviewer no-blockers; Optimizer addressed 3 concerns (tightened live-state inference, memoized LeadTracker + PossessionDiary geometry, WCAG AA contrast fix on possession-diary impact tags).
- Verified with **360 backend tests** (was 346, +14 new), `npm run build` + `npm run lint` clean.

---

### Sprint 76 — Methodology Rigor Pass
**Branch:** `claude/improve-evaluation-methods-ZAo94` (Claude, single-stream)

- Promoted every previously-deferred methodology upgrade from "planned" in the registry to either a working end-to-end implementation or a focused design memo with explicit data prerequisites. Pure backend sprint by design.
- Added eight new reliability primitives in `backend/services/reliability_service.py`: `_z_for_level` table (correctly-calibrated Wilson and normal intervals at 0.80 / 0.90 / 0.95 / 0.99), `pearson_correlation`, `collinearity_warnings`, `covariance_matrix`, `shrunk_covariance`, `invert_matrix`, `mahalanobis_distance`, `weight_sensitivity_analysis`, `principal_components`, `project_to_components`, `bayesian_change_score`, and `softmax`. Hardened `empirical_bayes_rate` with input validation and posterior clamping.
- Bumped seven methodology versions end-to-end with structured response evidence: `similarity_v3` (shrunk Mahalanobis distance method on `find_similar_players_with_archetype` with auto-fallback to weighted Euclidean below `3 × n_features` candidate rows; resolved method per-comp), `custom_metric_v2` (collinearity warnings at `|r| ≥ 0.85` plus top-5 ranking sensitivity under ±10% weight perturbations), `scouting_brief_v2` (cross-card contradiction detection across role/trajectory, role/usage, and strengths/shot-profile rule families), `mvp_case_v4` (Basketball Value weight-perturbation sensitivity over `REFINED_VALUE_WEIGHTS`), `style_xray_v2` (top-2 PCA latent axes with explained-variance ratios + feature loadings; pool gate `2 × n_features`), `trend_intelligence_v2` (Bayesian two-sample change probability per metric with `MIN_BASELINE_GAMES = 4`), `archetype_rules_v2` (soft-membership distribution over the 13 archetype rules anchored to the hard label via a pre-softmax bonus).
- Expanded the validation harness from 6 fixtures (team_fit + shot_lab) to 17 fixtures covering every registered methodology domain. A coverage assertion in the test suite blocks future registry additions from shipping without a fixture.
- Authored `specs/methodology-future-modeling.md` (~200 lines) for the two remaining open items (`mvp_case_v5` Award Case voter calibration, `opportunity_v2` uplift modeling). Both are blocked on data prerequisites, not engineering — the memo captures full data shape, math sketch, service wiring, and acceptance criteria so the work can pick up cleanly when the data lands. Backlog entries call out the data prerequisite explicitly.
- No frontend code changed; every new response field is `Optional` so existing consumers keep working unchanged. Frontend follow-on work (rendering the new methodology evidence in existing drawers) is captured in the closeout under "Frontend follow-ons".
- Verified with **346 backend tests** (was 293 at Sprint 75 close; +53 net new), `npm run lint` clean (7 pre-existing warnings), `npm run build` clean. Closeout: `specs/sprint-76-closeout.md`.

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

---

### Sprint 82 — Public Platform + Player Depth + Scraper Hardening
**Branches:** `feature/sprint-82a-player-depth`, `feature/sprint-82b-hosting`, `feature/sprint-82c-scrapers`, `feature/sprint-82d-public-mode` (Claude, four-stream)

- Stream A — Player splits + play-type UI: `frontend/src/components/PlayerSplitsPanel.tsx` (Location/Win-Loss/Days-Rest/Month/Pre-Post-All-Star families) and `PlayTypePanel.tsx` (Synergy archetypes). Closed Sprint 81 deferred frontend work.
- Stream B — Public hosting infra: `infra/bip-api.service` (gunicorn + 2 uvicorn workers), `infra/Caddyfile` (auto-HTTPS via Let's Encrypt), `infra/caddy-install.sh`, `infra/deploy.sh`, `infra/playwright-install.sh`, full `infra/README.md` runbook.
- Stream C — Scraper hardening: new `PlaywrightScraper` base class with viewport spoofing + `wait_until="networkidle"` for Cloudflare JS challenges. PST scraper switched to Playwright. Sports Reference URL fixed + parser rewritten.
- Stream D — Public mode pivot: dropped Caddy basicauth, `api.courtvue.app` reads `CF-Connecting-IP`. New `NBA_API_USER_FETCH_DISABLED` env flag; 3 user-facing methods cache-first + guarded. Centralized `frontend/src/lib/external-metrics.ts` source of truth + `<ExternalMetricsAttribution>` component.
- Verified with 479 backend tests (was 464, +15 new), `npx tsc --noEmit` clean.

---

### Sprint 84 — Production Deploy + Workflow Reset
**Branch:** `master` (doc-only updates after the Suspense fix on `43b7a4a`) (Claude, single-session)

- **Site went live.** `https://courtvue.app` (Vercel) + `https://api.courtvue.app` (Hetzner CPX11 `ubuntu@5.78.114.15` running Caddy + gunicorn + 2 uvicorn workers + PostgreSQL 16). Cloudflare orange-cloud proxies both with 5 cache rules (TTLs 2hr-12hr) + WAF rule blocking empty user-agent + zgrab + masscan.
- **SSH access recovered via Hetzner rescue mode** — required mounting `/dev/sda1`, bind-mounting `/proc`, `/sys`, `/dev`, and chrooting to create the missing `ubuntu` user (UID 1000, GID 1000, sudo group, NOPASSWD), enable the SSH service symlink, and fix `/home/ubuntu` ownership. First attempt failed because we wrote to `/mnt` without first mounting the disk — wrote to the rescue tmpfs which vanished on reboot.
- **Bug fix shipped during deploy** (`43b7a4a`): wrap `useSearchParams` in `<Suspense>` for `/bracket`, `/games/[gameId]`, `/teams/[abbr]` — Next.js 14+ production builds reject `useSearchParams` outside a Suspense boundary. Other 5 pages already had Suspense wrappers.
- **Postgres bootstrap:** `bip` user existed but had no password and no `DATABASE_URL` was set in `/etc/bip/env`. Set password and added connection string.
- **New 8-phase Sprint Workflow** documented in `AGENTS.md`: Plan → Implement → QA → Pre-merge Verification → Merge → Deploy → Production Smoke Test → Closeout. New Pre-merge Verification Checklist gating master pushes (now equivalent to deploying to production within ~2 min via Vercel auto-deploy). New Production Deploy Procedure (frontend automatic; backend manual `infra/deploy.sh`). New Rollback Procedures (Vercel one-click promote, git checkout + deploy.sh, alembic downgrade -1, Cloudflare purge). Session Start Checklist now requires a 5-second production health check.
- **CLAUDE.md** updated: new **Production** section (URLs, VM, edge layer, secrets), new **Production Deploy** subsection in Commands, new **Production Safety** section (7 rules around auto-deploy, API contracts, schema migrations, cache TTLs, CORS, secrets, rollback).
- Verified end-to-end: frontend 200 (~145ms), API health 200 (~52ms), leaderboards 200 (~191ms cold cache). Closeout: `specs/sprint-84-closeout.md`.

---

### Sprint 83 — MVP Launch Readiness
**Branches:** `feature/sprint-83a-blockers`, `feature/sprint-83b-launch-polish`, `feature/sprint-83c-playoff-polish` (Claude, three-stream + follow-on)

- Stream A: 9 critical UX production blockers (leaderboards skeleton fix, mobile hamburger nav `MobileNav.tsx`, team-detail tabs as native `<select>` on mobile, standings 4-col mobile table, `app/not-found.tsx` + `app/error.tsx`, localStorage hardening for private browsing, search dropdown `60vh` cap, onboarding `bip-kicker` labels).
- Stream B: First-impression polish + SEO + analytics (home hero rewrite, root-layout `Metadata` with OG/Twitter blocks, `@vercel/analytics`, `app/robots.ts` + `app/sitemap.ts`, offseason empty state on HomeLeagueLeaders, LiveTicker context label).
- Sprint 83-followup: Dynamic OG image (`app/og/route.tsx` — `next/og` ImageResponse using inline `courtvue-mark.svg` geometry).
- Stream C — Playoff surface polish: Shot Diet Pressure copy, Lineup Chess empty-state, From the Desk → series-aware CTA, Four Factor Edge regular-season fallback (panel always renders 8 metrics), Story Rail tile deep-links → `/bracket?series_id={sid}`, SeriesCard per-game G1–G7 chip strip.
- Verified: 472 → 480 backend tests, `npm run build` + `npm run lint` clean. Closeout: `specs/sprint-83-closeout.md`.

---

### Sprint 85 — Bracket Auto-Advance + Per-Series Detail + Tracking/Hustle + Lint Cleanup
**Branches:** `feature/sprint-85a-bracket-advance`, `feature/sprint-85b-per-series-detail`, `feature/sprint-85c-tracking-hustle`, `feature/sprint-85d-lint-cleanup` (Claude, 4-stream parallel via subagents)

- **First sprint executed end-to-end under the new 8-phase workflow** from Sprint 84. 480 → 490 backend tests (+10), `npm run lint` 4 errors + 8 warnings → 0/0.
- Stream A: Alembic 0021 adds `parent_top_series_id` + `parent_bottom_series_id` (nullable, indexed) to `playoff_series` + relaxes NOT NULL on seed columns; `_compute_next_round_slot` + `_auto_advance_closed_series` in `playoff_bracket_service.py` encode standard NBA pairing (1v8 → R2 vs 4v5 winner; through CF and Finals); `SeriesCard.tsx` renders TBD pill ("Awaiting winner of R{n}") when either team is null.
- Stream B: NEW route `/playoff-series/[seriesId]` + NEW service `playoff_series_player_logs_service.py` joining series → games → `PlayerGameLog` rows + NEW endpoint `GET /api/playoffs/series/{id}/player-logs` + NEW `<SeriesPlayerLogTable>` component (grouped by player, per-game stat rows, totals row, each game-row links to `/games/{game_id}`).
- Stream C: NEW services `player_tracking_service.py` + `player_hustle_service.py` (cache-first, sync-on-miss) + endpoints `/api/players/{id}/tracking` (3 families: Shot Creation / Passing / Shot Defense) + `/api/players/{id}/hustle` + components `PlayerTrackingPanel` + `PlayerHustlePanel` mounted in `PlayerDashboard` after the existing splits/play-types panels.
- Stream D: 4 lint errors → 0 (state pattern for setState-in-effect; HTML-entity escaping); 8 warnings → 0; **Monte Carlo flake fix** — `playoff_simulator_service.py:436` was `rng.seed(hash(series_id))` and Python's `hash(str)` is per-process randomized; fix `rng.seed(series_id)` directly. 10/10 stable post-fix.
- **Phase 6 surfaced 2 latent infra bugs from Sprint 82+84:** `infra/deploy.sh` `source /etc/bip/env` didn't auto-export to subprocesses (fixed with `set -a/+a`); raw `python -m alembic` ignored `DATABASE_URL` because `alembic.ini` hardcoded a passwordless URL (fixed by invoking `python -m db.migrations` instead). The `--migrate` deploy flow is now actually production-ready.
- Production smoke test passed all 4 surfaces. Closeout: `specs/sprint-85-closeout.md`.
