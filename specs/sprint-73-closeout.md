# Sprint 73 Closeout — Playoffs Platform

**Date:** 2026-04-28
**Branches:** `feature/sprint-73a-playoffs-data` (Stream A, merged to master), `feature/sprint-73b-playoffs-features` (Stream B, ready for merge)
**Status:** Stream A merged + pushed; Stream B ready for merge

---

## Goal

Center the platform on the 2026 NBA first-round playoffs while keeping the regular-season scope intact. Three pillars: (1) close the data-model gaps so playoff data is first-class, (2) extend the daily sync cadence to keep playoff data fresh, (3) ship playoff features for casual fans, coaching staff, and advanced analytics. Every playoff surface is gated by a new auto-detected `useSeasonPhase()` hook so the platform reverts cleanly outside the playoff window.

---

## Sprint shape

Two-team parallel — Stream A (data) merged first, Stream B (features) branched off A's merged tip. Architect → 4 parallel Engineers per stream → Reviewer → Optimizer.

---

## Shipped — Stream A (data foundation)

### EA1 · Schema migration `0012_playoffs_data_layer`
- New `playoff_series` table: `season, round, series_id, top/bottom_seed_team_id, top/bottom_seed, top/bottom_wins, status, winner_team_id, created_at, updated_at` with `(season, series_id)` unique constraint and indexes on `season`/`round`/`status`.
- `is_playoff` Boolean added to `lineup_stats`; unique constraint reworked to include the new flag.
- `season_type`, `series_id`, `series_game_num`, `playoff_seed` added to `game_logs` and `warehouse games` with series-id indexes.
- ORM models in `backend/db/models.py` mirror the migration. `routers/stats.py:career_stats` now sorts the existing `playoff_seasons` Pydantic list descending so it surfaces meaningfully. **7 new tests** (4 playoff_series + 3 career_playoff_seasons).

### EA2 · Sync extensions + daily/post-game cadence
- `nba_client` adds `season_type` pass-through to `get_league_dash_player_stats`, `get_team_stats`, `get_team_general_splits`, `get_team_shooting_splits`, `get_player_game_ids`, `get_team_game_log`, `get_standings_data`. Splits payloads now flag `is_playoff=True` when `season_type="Playoffs"`.
- `_cache_ttl_for_season` returns the new `PLAYOFF_CACHE_TTL=2h` during the playoff window via a 5-minute LRU phase cache that lazy-imports the season-phase service. Matches all five playoff phases (play-in, R1, R2, conference finals, finals).
- `sync_service.sync_official_*` functions accept `is_playoff` and route end-to-end. New `services/playoff_bracket_service.build_or_refresh_bracket()` derives `PlayoffSeries` rows from playoff GameLogs and back-references `series_id`/`series_game_num`/`playoff_seed`.
- `daily_sync.sh` adds `--post-game` and `--dry-run` subcommands plus a playoff-phase block at the end of the morning cron and an INFO summary line. **4 new tests**.

### EA3 · Service unblocks
- Removed hardcoded `is_playoff == False` filters from `player_archetype_service`, `team_fit_service`, `lineup_context_service`, `similarity_service`. All five services accept `season_type` (default `"Regular Season"`).
- Confidence note degrades one tier on archetype responses for playoff samples; team-fit emits a `low_sample_warning` when playoff games < 8.
- Routers `standings`, `advanced`, `similarity`, `teams`, `team_fit` accept `season_type` and pass through. **3 new tests**.

### EA4 · Season-phase service + playoff API surface
- New `services/season_phase_service.get_current_phase()` auto-detects via date window (Apr–Jun → playoffs, Jul–Sep → offseason) AND `is_playoff=True` GameLog rows in last 7 days. Round inferred from highest active/scheduled `PlayoffSeries.round`. Cached 5 minutes.
- New `services/playoff_simulator_service.simulate_series()` runs 1000 deterministic Monte-Carlo trials (seeded from `hash(series_id)`) using a sigmoid of weighted z-scores (net rating + top-5 BPM + pace-adjusted TS%) plus a 0.06 home-court bump.
- New routes: `GET /api/season-phase`, `GET /api/playoffs/bracket`, `GET /api/playoffs/series/{id}`, `GET /api/playoffs/today`, `GET /api/playoffs/series-simulation/{id}`. **6 new tests**.

### Stream A verification
- **286 backend tests passing** (was 266, +20 new).
- Frontend untouched in Stream A; build/lint stayed clean.

---

## Shipped — Stream B (frontend playoff features)

### EB1 · Bracket page + season-phase frontend wiring
- New `/bracket` route with East/West two-column tree; renders an off-season empty state when `!isPlayoffs` so the route is safe outside the playoff window.
- New `<SeriesCard>` (forest brand stripe + seed pills + W-L state + status pill) reusable across bracket and home-page surfaces; deep-links to `/pre-read?series_id=...`.
- New `<PlayoffBracketView>` lays out series by round with kicker headers; supports rounds 1–4 plus optional finals.
- New `useSeasonPhase` SWR hook with long-lived caching gates every Sprint 73 playoff UI.
- New `<NavLinks>` client component extracted from the server-component layout so the conditional Bracket nav item can read `useSeasonPhase` without forcing the entire layout client-side.

### EB2 · Series-mode Pre-Read + Coaching Adjustments Timeline
- When `/pre-read?series_id=...` AND `useSeasonPhase().isPlayoffs`, the page additionally renders a series-state header card, a `<SeriesWPChart>` cumulative win-probability curve (wraps Sprint 70 `<WinProbabilityChart>`), and a `<CoachingAdjustmentsTimeline>` that finally surfaces the `PreReadDeckResponse.adjustments` field returned by `/api/pre-read` since Sprint 70 but never rendered.
- Series-mode UI is double-gated on URL param AND playoff phase. Existing single-game prep workflow byte-identical in regular season.

### EB3 · Home shift + leaderboards toggle
- `<HomeMvpTeaser>` early-returns null in playoffs.
- New `<SeriesNarrative>` carousel rotates active series every 3s with pause-on-hover; honors `prefers-reduced-motion` by stacking. `safeIndex` derived from state — no setState-in-effect.
- New `<DailyPlayoffSlate>` (wrapped by `<PlayoffsHomeSections>` so the server-component `page.tsx` stays server) lists tonight's games via `getPlayoffsToday()`.
- `<HomeLeagueLeaders>` gains a Regular/Playoffs pill toggle; in playoff mode the trend sparkline column hides (regular-season only) and a sample-size caveat appears when the top scorer has fewer than 3 games.
- `/leaderboards` converts from a server redirect to a client page wrapped in `<Suspense>`; in regular season it `router.replace`s to `/player-stats` preserving search params, in playoffs it renders the same Regular/Playoffs toggle at the top.

### EB4 · WP simulator + postseason heatmap + opponent lineup matrix
- `<SeriesWPSimulator>` mounts below the MVP race grid in playoffs. Bracket-driven series picker, SWR-backed simulation fetch, inline SVG projection chart with memoized geometry, top/bottom-seed cumulative WP pills, hypothetical W/L stub buttons (no-op v1, documented).
- MVP page header reframes to `{round_label} MVP Race` in playoffs.
- `<PostseasonHeatmap>` mounts at the bottom of `/leaderboards` in playoffs only. Fetches both Regular and Playoffs leaderboards and computes USG% × TS%-delta per player; filters to rotation players (`min_pg ≥ 8`, `gp ≥ 2`); quadrant labels in `var(--foreground)` for WCAG AA contrast.
- `<OpponentLineupMatchupMatrix>` powers a new `opponent_matchup` tab on `/teams/[abbr]` that renders only when the team is in an active series. 5×5 net-rating delta matrix (forest for team advantage, terracotta for opponent), 100+ possessions per cell threshold.

### Stream B verification
- Frontend `npm run build`: clean (`/bracket` route registered).
- Frontend `npm run lint`: 0 errors, only the 7 pre-existing `usePlayerStats.ts` warnings.
- Backend `pytest`: still **286 passing**.

---

## Architecture: Architect → Engineers → Reviewer → Optimizer

1. **Architect** — plan file at `~/.claude/plans/fizzy-churning-ullman.md`.
2. **Engineers** — 8 parallel subagents (4 per stream). Stream A merged first; Stream B branched off the merged tip.
3. **Reviewer** — single subagent. Signed off with no blocking issues; flagged 4 non-blocking concerns.
4. **Optimizer** — single subagent. Addressed 2 of 4 concerns in one defensive-fixes commit (`e875287`):
   - Replaced fixed UTC-7 `_PACIFIC_OFFSET` in `routers/playoffs.py` with `pytz.timezone("US/Pacific")` so `/api/playoffs/today` returns the correct day in winter.
   - Memoized `<SeriesWPSimulator>` projection-chart geometry so SWR-driven parent re-renders don't recompute the SVG path on every cycle.
- Skipped: `nba_client` lowercase-generic annotations (`from __future__ import annotations` makes them safe; backlog), Series WP hypothetical buttons (deliberate v1; backlog), PostseasonHeatmap position bucket coloring (needs `position` on `LeaderboardEntry`; backlog), `prefers-reduced-motion` site-wide (already covered by `globals.css:429` global wildcard rule from Sprint 72 optimizer pass — verified, no edits).

---

## Verification (final)

- Backend: `pytest -q` → **286 passed**, 2 pre-existing deprecation warnings.
- Frontend build: `npm run build` → clean. `/bracket` route generated; bundle has tree-shaken `playoffs/` chunk.
- Frontend lint: `npm run lint` → 0 errors, 7 pre-existing `usePlayerStats.ts` warnings (unchanged).
- `git diff --check` clean.
- Toggle-back guarantee verified by Reviewer: every playoff surface (home, MVP, leaderboards, teams, pre-read, bracket, NavLinks) self-gates via `useSeasonPhase()`.

---

## Workflow lessons

- **8-engineer two-stream split worked as designed.** Stream A's data foundation merged into master cleanly before Stream B branched, so Stream B engineers could write against real backend types and routes from day one. No mid-sprint backend-contract drift.
- **Subagent sandbox denials again forced central verification.** All 8 engineers reported "code complete + manual review" without running `pytest`/`npm` themselves. The orchestrator ran build/lint/pytest centrally before each merge — the same pattern Sprint 72 settled into. Worth codifying in future engineer prompts: "do not assume sandbox can run npm/pytest; report code-complete and let the orchestrator verify."
- **Reviewer + Optimizer split kept scope tight.** Reviewer found 4 non-blocking concerns; Optimizer triaged and acted on 2 (the cheapest), deferred 2 explicitly to backlog. This kept the closeout at a stable 286 tests + clean build/lint without ballooning into a Sprint 73 v1.1.
- **`Query("...")` defaults break direct unit tests.** EA3 used `season_type: SeasonType = Query("Regular Season")` in `routers/standings.py` which made `season_type == "Regular Season"` evaluate False when the test called the route handler as a plain function. Fixed by dropping the `Query()` wrapper for plain string defaults — FastAPI still picks them up as query params. Worth flagging as a pattern: when adding new route query params, prefer plain-typed defaults so tests work both via FastAPI and direct call.
- **Toggle-back guarantee held without much code.** Adding `useSeasonPhase()` once and gating every playoff component on `isPlayoffs` was sufficient; no feature flags needed. Auto-detection from data + date window means the platform reverts to regular season the moment the playoff window closes — no manual flip required.

---

## Backlog disposition

Removed from `specs/BACKLOG.md`:
- "Untapped API Payload — second-tier wins" → `PreReadDeckResponse.adjustments` shipped via EB2; the rest carry forward in a renamed entry.

Added to `specs/BACKLOG.md`:
- **Series WP Simulator hypothetical state**: backend `/api/playoffs/series-simulation/{id}` accepts `?override_top_wins=&override_bottom_wins=` so the W/L stub buttons in the frontend can drive real hypothetical re-simulation.
- **PostseasonHeatmap position bucket coloring**: requires `position` field on `LeaderboardEntry`; small backend change.
- **Opponent lineup head-to-head net delta**: replace the standalone net rating delta in `<OpponentLineupMatchupMatrix>` with a true shared-possession net delta once a `lineup-matchups` endpoint exists.
- **`nba_client.py` lowercase-generic annotations cleanup**: file uses `from __future__ import annotations` so they're safe, but worth normalizing to typing `Dict[]`/`List[]` in a sweep.
- **Print stylesheet for `/insights/trajectory` and `/insights/x-ray`**: Sprint 72 added Pre-Read print rules; carry the pattern across.

Carry-over (still in backlog):
- Untapped API payload second-tier wins (MVP `impact_consensus`, `signature_games` carousel, Trajectory `key_stat_deltas`, prep_context `best_edge_label`).
- Frontend component-logic test infrastructure (Vitest setup).

---

## Files changed

```
# Stream A
backend/alembic/versions/0012_playoffs_data_layer.py     (NEW)
backend/db/models.py                                     (PlayoffSeries + LineupStats.is_playoff + GameLog.series_*)
backend/routers/stats.py                                 (career_stats sorts playoff_seasons desc)
backend/services/career_service.py                       (existing — verified)
backend/config.py                                        (PLAYOFF_CACHE_TTL=7200)
backend/data/daily_sync.sh                               (--post-game, --dry-run, playoff phase block)
backend/data/nba_client.py                               (season_type pass-through, playoff TTL)
backend/services/sync_service.py                         (is_playoff on splits/season stats)
backend/services/playoff_bracket_service.py              (NEW)
backend/services/season_phase_service.py                 (NEW)
backend/services/playoff_simulator_service.py            (NEW)
backend/services/{player_archetype,team_fit,lineup_context,similarity}_service.py  (season_type)
backend/routers/{standings,advanced,similarity,teams,team_fit}.py  (season_type query param)
backend/routers/season_phase.py                          (NEW)
backend/routers/playoffs.py                              (NEW; pytz fix)
backend/main.py                                          (register new routers)
backend/models/{archetype,team_fit,playoffs,season_phase}.py  (Pydantic + new schemas)
backend/tests/test_{playoff_series,playoff_sync,season_phase,playoff_routes,career_playoff_seasons,service_season_type}.py  (NEW)
backend/tests/test_{official_season_sync,official_team_stats,team_dashboard_parsing,schema_migrations}.py  (kwargs absorption)

# Stream B
frontend/src/app/bracket/page.tsx                        (NEW)
frontend/src/components/playoffs/                        (NEW dir: SeriesCard, PlayoffBracketView, CoachingAdjustmentsTimeline, SeriesWPChart, DailyPlayoffSlate, SeriesNarrative, PlayoffsHomeSections, SeriesWPSimulator, PostseasonHeatmap, OpponentLineupMatchupMatrix)
frontend/src/hooks/useSeasonPhase.ts                     (NEW)
frontend/src/components/NavLinks.tsx                     (NEW — extracted for client-only Bracket nav item)
frontend/src/app/{layout,page,leaderboards/page,mvp/page,pre-read/page,teams/[abbr]/page}.tsx  (gating + new sections)
frontend/src/components/{HomeMvpTeaser,HomeLeagueLeaders}.tsx  (season-phase gating + Regular/Playoffs toggle)
frontend/src/lib/{api,types}.ts                          (append-only: 5 new fetchers + matching types)
```

---

## Commits

```
e875287 chore(sprint-73): optimizer pass — defensive fixes
a8212ee feat(sprint-73): WP simulator on MVP, postseason heatmap on leaderboards, opponent matchup tab on teams (EB4)
b3661d2 feat(sprint-73): home-page playoff shift + leaderboards Regular/Playoffs toggle (EB3)
27879fd feat(sprint-73): series-mode Pre-Read with coaching adjustments timeline (EB2)
b4121f5 feat(sprint-73): playoff bracket page + season-phase frontend wiring (EB1)
2b0aed8 Merge feature/sprint-73a-playoffs-data — Sprint 73 Stream A (Playoffs Data Foundation)
dcc71bc feat(sprint-73): season-phase service + playoff API surface (EA4)
7416aaa feat(sprint-73): unblock services and routers from regular-season-only filters (EA3)
076adcc feat(sprint-73): playoff sync extensions + daily/post-game cadence (EA2)
70c5c93 feat(sprint-73): playoffs data-layer schema migration (EA1)
```

---

## Next-sprint seeds

- **Backend overrides for the WP simulator** (one of the few obvious follow-ons that completes a Sprint 73 v1).
- **Position-bucketed PostseasonHeatmap** — backend exposes `position` on leaderboards; frontend colors dots accordingly.
- **Series snapshot system** mirroring `pre_read_snapshots` from Sprint 66 for full series archives (out of scope this sprint but a natural extension).
- **Live in-game updates** — sub-minute freshness via WebSocket ingest. Out of scope this sprint; would unlock real-time bracket/WP movement during games.
- **Conference / Finals MVP-specific scoring formula tuning** — currently uses regular-season MVP score with a "Playoff" rebrand. Voter framing differs.
- **Mobile-specific playoff UX** — desktop-first this sprint; mobile responsiveness from Sprint 70 carries over but the bracket page in particular could use a mobile vertical layout.
