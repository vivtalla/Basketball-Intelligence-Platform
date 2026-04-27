# CourtVue Labs

CourtVue Labs is a full-stack NBA analytics platform for player evaluation, team analysis, advanced metrics, and play-by-play insights. It is built for analysts and basketball enthusiasts who need rigorous, data-driven basketball context.

---

## Tech Stack

- **Frontend**: Next.js 16, React 19, TypeScript, Tailwind CSS 4, Recharts, SWR
- **Backend**: FastAPI (Python), async endpoints, Pydantic v2 for validation
- **Database**: PostgreSQL (primary via SQLAlchemy 2.0), SQLite (`cache.db` — NBA API response cache only)
- **Data Sources**: `nba_api` (NBA.com Stats API), CSV imports for external metrics (LEBRON, RAPTOR, PIPM, EPM, RAPM)
- **Schema Management**: Alembic migrations (`backend/alembic/`) with `db/ensure_schema.py` retained only as a compatibility wrapper

---

## Architecture

```
backend/
  main.py                   → FastAPI app entry, CORS, router registration
  config.py                 → Env config (DB URL, cache TTLs, NBA API settings)
  routers/                  → Route handlers (players, stats, shotchart, leaderboards, teams, advanced, gamelogs)
  services/                 → Business logic (sync, PBP processing, advanced metrics)
  models/                   → Pydantic response schemas
  db/
    database.py             → SQLAlchemy engine & session factory (get_db dependency)
    models.py               → ORM models — see table below
    ensure_schema.py        → Compatibility wrapper for the Alembic migration path
    migrations.py           → Programmatic migration entry point (`python -m db.migrations`)
  data/
    nba_client.py           → NBA API wrapper (rate limiting, CacheManager, _cache_ttl_for_season)
    cache.py                → SQLite CacheManager (get/set/delete)
    pbp_import.py           → CLI: play-by-play data import
    epm_rapm_import.py      → CLI: external metric CSV import
    bulk_import.py          → CLI: bulk player/season data import

frontend/
  src/
    app/                    → Next.js pages (home, players/[id], leaderboards, compare, learn, teams, standings)
    components/             → React components (see component inventory below)
    hooks/                  → usePlayerStats, usePlayerSearch
    lib/
      api.ts                → All backend API calls (single source of truth)
      types.ts              → TypeScript interfaces mirroring backend Pydantic schemas
```

### ORM Models (`backend/db/models.py`)

| Model | Table | Purpose |
|-------|-------|---------|
| `Team` | `teams` | NBA team metadata |
| `Player` | `players` | Player profiles (NBA person_id as PK) |
| `SeasonStat` | `season_stats` | Season averages + advanced metrics per player/season/team |
| `TeamSeasonStat` | `team_season_stats` | Canonical official team dashboard season stats |
| `TeamSplitStat` | `team_split_stats` | Canonical official team general split stats |
| `PlayerGameLog` | `player_game_logs` | Per-game stats, persisted to avoid repeat API calls |
| `GameLog` | `game_logs` | Game metadata (date, teams, score) — PBP parent |
| `PlayByPlay` | `play_by_play` | Individual PBP events |
| `PlayerOnOff` | `player_on_off` | On/off splits derived from PBP stints |
| `LineupStats` | `lineup_stats` | 5-man lineup ratings derived from PBP |

---

## Commands

### Development

```bash
# Backend — run from backend/
uvicorn main:app --reload                    # FastAPI dev server :8000

# Frontend — run from frontend/
npm run dev                                  # Next.js dev server :3000
npm run build                                # Production build
npm run lint                                 # ESLint
```

### Schema Updates

```bash
# Run from backend/ — canonical schema upgrade path
python -m db.migrations
```

> **Note:** Schema evolution is migration-driven. `python -m db.ensure_schema` still works as a compatibility alias, but new schema work should land as Alembic revisions.

### Data Import

```bash
# Play-by-play sync — run from backend/
python data/pbp_import.py --season 2024-25
python data/pbp_import.py --season 2024-25 --player-id 123456 --force-refresh

# External metrics CSV import — run from backend/
python data/epm_rapm_import.py data.csv --metrics epm,rapm
python data/epm_rapm_import.py data.csv --metrics lebron,raptor,pipm

# Bulk import — run from backend/
python data/bulk_import.py --season 2024-25
```

Cron: `0 6 * * * /path/to/backend/data/daily_sync.sh`

### Re-Sync PBP Stats

```bash
POST /api/advanced/sync-season   body: {"season": "2024-25"}
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql://localhost/bip` | PostgreSQL connection |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend URL for frontend |

---

## Data Conventions

- Stats stored as per-100-possessions or per-36-minute rates with raw totals alongside. Never raw totals without context.
- Player IDs: NBA.com `person_id` as canonical identifier. Names are NOT unique.
- Season format: always `"2024-25"` string — never `2024` or `2025` alone.
- Game dates: ISO 8601 (`YYYY-MM-DD`), stored as `date` type.
- All timestamps UTC. Convert to local only at display layer.
- Always surface sample size with any rate stat. Flag stats with <200 possessions or <20 games.

---

## Analytics Domain Rules

- Cross-era player comparisons must adjust for pace and league-average efficiency of that season.
- Lineup data requires ≥100 possessions together to be reportable.
- Offensive and defensive ratings use opponent-adjusted values for cross-team comparison.
- Clutch = last 5 minutes, score within 5 points.
- On/off splits come from PBP stint data, not box scores. Stint minutes measured from clock timestamps.
- External metrics (LEBRON, RAPTOR, EPM, PIPM, RAPM) are imported. Never present as platform-original. Always attribute source.
- Possession counting: FGA + TOV + last-FT-in-sequence (excluding and-ones and technical FTs).

---

## Code Style

- Python: type hints on all function signatures. Use `Annotated` types for FastAPI dependencies.
- Python version is **3.8** — use `Optional[X]` / `List[X]` from `typing`, not `X | None` / `list[X]`.
- TypeScript: strict mode, no `any`. Prefer `unknown` + type narrowing.
- API responses always use Pydantic schemas — never return raw dicts or ORM objects.
- Database queries go through the service layer, never directly in route handlers.
- Frontend data fetching uses SWR hooks — never raw `fetch` in components.
- React hooks must be pre-allocated at the top level (no conditional hooks). For compound filters with dynamic slot counts, allocate a fixed maximum number of hook slots.

---

## Caching Strategy

| Data | Storage | TTL |
|------|---------|-----|
| Game logs (per player/season) | PostgreSQL `player_game_logs` | Historical: never re-fetch. Current season: 24h. |
| Shot chart data | SQLite `cache.db` | Historical: 30 days. Current season: 6h. |
| Season/team game IDs | SQLite `cache.db` | Same TTL rules via `_cache_ttl_for_season()` |
| PBP events | PostgreSQL `play_by_play` | Fetched once per game, never re-fetched |

`_cache_ttl_for_season(season)` in `nba_client.py` returns `CURRENT_SEASON_CACHE_TTL` if `season == _active_nba_season()`, else `HISTORICAL_SEASON_CACHE_TTL`.

---

## Gotchas

- **Read `AGENTS.md` at session start before touching any code.** It contains the current sprint scope, your branch, this sprint's work allocation, the shared file Lock Table, and the Handoff Queue.
- **nba_api rate limits aggressively** — `nba_client.py` enforces 0.6s delays. Never call `nba_api` directly outside this wrapper.
- **Player names are not unique.** Multiple players share names (e.g., Marcus Morris Sr./Jr.). Always resolve to `person_id`.
- **The salary cap changes every season.** Never hardcode cap numbers.
- **External metrics are proprietary.** RAPTOR, EPM, LEBRON, etc. are imported. Always attribute source.
- **SQLite `cache.db` is for NBA API response caching only** — PostgreSQL is the primary datastore.
- **Schema changes are migration-driven.** Use Alembic revisions and `python -m db.migrations`; do not rely on app-startup DDL.
- **Python 3.8.** No union type syntax (`X | Y`), no `list[X]` subscripting at runtime in type hints.
- **Do not add a `Co-Authored-By: Claude` trailer to git commits.** Commits must not credit Claude. Omit the `🤖 Generated with Claude Code` footer on PRs as well.

---

## Core Principles

- **Data integrity over speed**: Never ship a pipeline without output schema validation.
- **Context is everything**: A stat without context (sample size, opponent adjustment, era normalization) is misleading.
- **Simplicity first**: Make every change as simple as possible and minimize code impact.
- **Only touch what's necessary**: Don't refactor adjacent code while fixing a bug. Scope changes tightly.
- **No laziness**: Find root causes. Avoid temporary fixes. Maintain senior-level engineering standards.

---

## Agent Behaviors

### Plan Mode Default
- Enter plan mode for any task with 3+ steps or an architectural decision.
- If something goes wrong mid-execution, stop and re-plan immediately — don't keep pushing.
- Use plan mode for verification steps, not just building.
- Write a detailed spec upfront to reduce ambiguity before any code is written.

### Subagent Strategy
- Use subagents frequently to keep the main context window clean.
- Offload research, exploration, and parallel analysis to subagents.
- For complex problems, throw more compute via subagents rather than reasoning linearly.
- One task per subagent — focused execution, not omnibus prompts.

### Self-Improvement Loop
- After any correction from the user, update `tasks/lessons.md` with the pattern as a rule.
- Write the lesson as a rule, not a narrative, to prevent repeating the same mistake.
- Review `tasks/lessons.md` at the start of each session.
- Iterate ruthlessly until the mistake rate drops.

### Verification Before Done
- Never mark a task complete without proving it works.
- Diff behavior between `master` and your changes when relevant.
- Ask: "Would a staff engineer approve this?"
- Run tests, check logs, and demonstrate correctness before declaring done.

### Demand Elegance (Balanced)
- For non-trivial changes, ask: "Is there a more elegant solution?"
- If a fix feels hacky, ask: "Knowing everything I know now, implement the elegant solution."
- Skip this for simple fixes — don't over-engineer straightforward changes.
- Challenge your own work before presenting it to the user.

### Autonomous Bug Fixing
- When given a bug report, fix it — don't ask for re-explanation of what's broken.
- Use logs, error messages, and failing tests to diagnose root cause.
- Require zero context-switching from the user.
- Fix failing CI/lint tests automatically when encountered.

---

## Task Management

Convention:
```
tasks/
  todo.md      → per-session work plan (transient — create at session start when needed)
  lessons.md   → self-improvement log (persistent — never reset)
```

Workflow:
1. **Plan First** — write the plan in `tasks/todo.md` with checkable items.
2. **Verify Plan** — confirm the plan before any implementation begins.
3. **Track Progress** — mark items complete as you go; don't batch-check at the end.
4. **Explain Changes** — provide a high-level summary at each step.
5. **Document Results** — add a review section to `tasks/todo.md` when done.
6. **Capture Lessons** — update `tasks/lessons.md` after any correction.

---

## Sprint Process

CourtVue Labs uses a hybrid sprint model: major feature sprints typically run as two parallel teams, while small or tightly coupled sprints use one sequential `Architect → Engineer → Reviewer → Optimizer` stream. Branch/worktree cleanup is part of the default operating model.

---

## Recent Sprints

> Full history → `specs/sprint-history.md`

### Sprint 70 — Design System Integration

- Pure-frontend sprint bringing the CourtVue Labs design system (cream/forest-green/gold palette, Source Serif 4 display, Source Sans 3 sans, JetBrains Mono mono) deeper into Teams, Metrics, Pre-Read, and Compare. Built from a gzipped tarball of HTML/JSX prototypes at `https://api.anthropic.com/v1/design/h/cs_JsS8pYIm1mYPQ8INqJQ`.
- **Teams directory** (`/teams`) full redesign: replaced the simple grid of team cards with a two-column layout matching `TeamsScreen.jsx`. Conference filter pills (All/East/West) backed by a static `TEAM_META` map (conference + brand color keyed by abbreviation), sort dropdown (Name/Conference/Roster size), sticky left directory with colored abbreviation badges and selection borders, and a right `TeamDetailPreview` panel with color-tinted header and four quick-access tab links.
- **Metrics page** (`/metrics`) hero leader card: `<HeroHardwood>` woodgrain texture above the leaderboard inside `CustomMetricBuilder.tsx`, only when `data.player_rankings.length > 0`. Renders the metric label kicker, #1 ranked player + team, and composite score in 72pt `bip-display` type — matching the design's `MetricsScreen.jsx` exactly.
- **Pre-Read page** (`/pre-read`) three new sections: (1) visual matchup header card with home + vs + away team boxes, (2) six bilateral `MatchupBar` comparison bars (OFF RTG, DEF RTG, PACE, EFG%, TS%, NET RTG) fed by `useTeamAnalytics(home, season)` + `useTeamAnalytics(away, season)` with winning side highlighted in forest-green, (3) "Three things to win" focus levers section that surfaces `data.focus_levers` from the existing `/api/pre-read/{team}/{opponent}` API in the design's `FocusLever` card style. Focus levers were already returned by the API but never rendered on the page.
- **Compare page** (`/compare`) two summary panels added inside `ComparisonView` for `mode !== "percentile" && mode !== "arc"`: (1) "The deltas" — 5-card grid of biggest stat differences (Scoring, True shooting, Playmaking, Rebounding, Impact BPM) with leader's last name + delta in display type, (2) "Key takeaways" — top 3 plain-language bullet differences ranked by absolute delta across PTS/TS%/AST/REB/BPM/STL/BLK.
- Backend untouched; backend test count stays at **257 passing**. Frontend `npm run build` and `npm run lint` clean (7 pre-existing `usePlayerStats.ts` warnings).
- Subagent rate-limit hit forced inline implementation — see closeout `specs/sprint-70-closeout.md` for the workflow lesson on when not to fan out.

### Sprint 69 — Team-Fit Intelligence and Injury-Aware Context

- Shipped **Team-Fit Intelligence v2**: new `GET /api/team-fit/{player_id}` endpoint, deterministic current-team fit scoring, alternate-team ranking, component breakdowns (`skill_supply`, `roster_need`, `role_competition`, `confidence`), score deltas, warnings, methodology, and frontend `<TeamFitPanel>`.
- Upgraded Team-Fit explainability across similarity and player page: teammate-covered feature chips, overlap drivers, current-team value summaries, "team needs from him" drivers, better-fit rationale, and latest-qualified-season fallback for incomplete current-season rows.
- Added the **analysis context platform**: Alembic `0011_player_analysis_contexts`, `PlayerAnalysisContext` ORM, manual context CRUD routes, automatic injury/recovery windows from `player_injuries`, and a player-page settings drawer for manual injury/recovery/availability notes.
- Made **Player Trend Intelligence injury-aware**: role drops inside injury/recovery/availability windows now surface `adjusted_role_status="injury_context"` and context-aware copy instead of blunt `losing_trust`, while raw deltas remain visible.
- Verified with **257 backend tests**, frontend `npm run build`, frontend `npm run lint` (7 pre-existing warnings), `git diff --check`, local Alembic migration, and closeout cleanup of local backend/frontend servers plus ports 8000/3000.

*Sprint 68 and older moved to `specs/sprint-history.md`.*

---

## Active Branches

| Branch | Owner | Status |
|--------|-------|--------|
| `master` | — | Stable |
| `feature/sprint-57-insights-revamp` | Claude | Merged to master |
| `feature/sprint-58-usage-opportunity-workspace` | Claude | Merged to master |
| `codex-sprint-59-insights-trend-overhaul` | Codex | Merged to master |
| `feature/sprint-60-insights-xray-explainability` | Claude | Merged to master |
| `feature/sprint-61-shot-lab-polish-and-ops` | Claude | Merged to master |
| `feature/sprint-62-style-intelligence-and-team-shooting-splits` | Codex | Merged to master |
| `feature/sprint-63-team-insights-workflow-expansion` | Codex | Merged to master |
| `feature/sprint-64-coaching-workflow-intelligence` | Claude | Merged to master |
| `feature/sprint-65-scouting-opportunity-fit` | Claude | Merged to master |
| `codex-sprint-66-staff-packet-handoff` | Codex | Merged to master |
| `feature/sprint-67-decision-intelligence` | Claude | Merged to master |
| `feature/sprint-68-decision-intelligence-followups` | Claude | Merged to master |
| `codex-sprint-69-team-fit-intelligence` | Codex | Merged to master |
| `feature/sprint-70-design-system-integration` | Claude | Merged to master |

Sprint branches are created at kickoff and listed in `AGENTS.md`.

---

## Component Inventory (Frontend)

| Component | Location | Purpose |
|-----------|----------|---------|
| `PlayerDashboard` | `components/` | Main player profile shell |
| `StatTable` | `components/` | Season stats table with sorting |
| `ShotChart` | `components/` | Shot chart with heatmap mode |
| `RadarChart` | `components/` | Multi-stat radar for player comparison |
| `CareerArcChart` | `components/` | Single-player career trajectory |
| `DualCareerArcChart` | `components/` | Two-player career arc overlay (Sprint 6) |
| `ExternalMetricsPanel` | `components/` | EPM/RAPTOR/PIPM/LEBRON/RAPM per season (Sprint 6) |
| `ComparisonView` | `components/` | Side-by-side player comparison (stats + arc + radar) |
| `LineupTable` | `components/` | 5-man lineup stats |
| `OnOffTable` | `components/` | Player on/off splits |
| `WarehousePipelinePanel` | `components/` | Warehouse ingestion funnel, job stats, action buttons, auto-poll (Sprint 11–13) |
| `PlayerHeader` | `components/` | Player profile header with YoY stat delta callouts (Sprint 13) |
| `TeamIntelligencePanel` | `components/` | Team season analytics with YoY trend signals (Sprint 13) |
| `ShotValueMap` | `components/` | Zone bubbles: area ∝ frequency, color ∝ value added (Sprint 34) |
| `ShotSprawlMap` | `components/` | Gaussian density contours + convex hull court coverage map (Sprint 34) |
| `ShotDistanceProfile` | `components/` | 0–30 ft frequency ribbon with efficiency-colored gradient fill (Sprint 34) |
| `ShotSeasonEvolution` | `components/` | Career filmstrip of mini zone-heatmap courts + FG% timeline (Sprint 34) |
| `CompareShotLab` | `components/` | Shared-filter compare shot workspace with side-by-side advanced shot views (Sprint 35) |
| `ShotSnapshotButton` | `components/` | Shared snapshot save action for shot-lab surfaces |
| `TeamSplitsPanel` | `components/` | Official team general splits by family (Location, W/L, Days Rest, Month, Pre/Post All-Star) with stat table and toggle (Sprint 47) |
| `MvpRacePanel` | `components/` | MVP Award Race: ranked candidate cards with composite score bars, stat chips, delta arrows, and momentum badges (Sprint 48) |
| `TeamDefenseShotLab` | `components/` | Opponent shot lab for team-defense surfaces |
| `ProceduralHalfCourt` | `components/three/` | Procedural NBA court geometry for 3D visualizers |
| `ShotLab3DScene` | `components/three/` | React Three Fiber shot-lab 3D scene scaffold |
| `GameVisualization3D` | `components/three/` | React Three Fiber Game Explorer visualizer |
| `ThreeUnavailableState` | `components/three/` | WebGL fallback for 3D visualizers |
| `InsightsHeader` | `components/` | Shared insights page header: team/season/opponent selectors, tab bar, cross-tab handoff chips (Sprint 57) |
| `DriverBar` | `components/trajectory/` | Horizontal driver-contribution decomposition bar for Trajectory (Sprint 57) |
| `RollingSparklines` | `components/trajectory/` | Multi-signal 10-game rolling Recharts line chart with baseline reference (Sprint 57) |
| `EvidenceGames` | `components/trajectory/` | Evidence-game chips linking to Game Explorer (Sprint 57) |
| `OnOffSwingCard` | `components/trajectory/` | On/off net swing + lineup teammate context card (Sprint 57) |
| `ClutchSplitCard` | `components/trajectory/` | Clutch pts/FG% split card with sample-size caveat (Sprint 57) |
| `ShotQualityDeltaCard` | `components/trajectory/` | TS% delta (recent vs baseline) linking to Shot Lab (Sprint 57) |
| `OpportunityDriverBar` | `components/opportunity/` | Horizontal driver-contribution bar with SIGNAL_LABELS + hover descriptions (Sprint 58) |
| `OpportunityRow` | `components/opportunity/` | Left-column ranked player card with compact DriverBar + confidence pill (Sprint 58) |
| `EfficiencyLoadCard` | `components/opportunity/` | CSS scatter dot locating player on USG% vs TS% axes within cohort (Sprint 58) |
| `TeamImpactCard` | `components/opportunity/` | On/off net swing block + top lineup partners from lineup context (Sprint 58) |
| `RoleFitCard` | `components/opportunity/` | Shot diet table (3PA rate, FTr, eFG%) vs position-cohort averages with delta column (Sprint 58) |
| `CohortPositionCard` | `components/opportunity/` | 4 pills: cohort percentile, opportunity score, team opportunity score, GP (Sprint 58) |
| `DirectionalHintBanner` | `components/opportunity/` | Conditional green banner with hint text + signal basis chips (Sprint 58) |
| `MethodologyDrawer` | `components/opportunity/` | Collapsible details: weights, z-score cap, gating thresholds, confidence definitions (Sprint 58) |
| `TeamRollup` | `components/opportunity/` | Top 3 opportunity drivers across filtered roster with player counts (Sprint 58) |
| `StyleXRayWorkspace` | `components/` | Dedicated Style X-Ray Insights tab: archetype hero, fingerprint, neighbors, movement, adjacent archetypes (Sprint 60) |
| `ArchetypeFingerprint` | `components/xray/` | Top style contributors vs league with share bars (Sprint 60) |
| `NeighborQualityList` | `components/xray/` | Nearest neighbor teams with high/medium/low quality band pills (Sprint 60) |
| `MovementTimeline` | `components/xray/` | Per-feature z-score delta bars with drift narrative (Sprint 60) |
| `AdjacentArchetypes` | `components/xray/` | Nearest different archetypes the team is drifting toward (Sprint 60) |
| `XRayMethodologyDrawer` | `components/xray/` | Collapsible methodology drawer: archetype rules, confidence, neighbor bands, movement thresholds (Sprint 60) |
| `TrajectoryMethodologyDrawer` | `components/trajectory/` | Signal weights, gating rules, label bands for the trajectory score (Sprint 60) |
| `ShotHoverTooltip` | `components/` | Shared hover tooltip for ShotValueMap/Sprawl/Distance: attempts, expected FG%, Δ, sample confidence (Sprint 61) |
| `ShotExamplesChips` | `components/` | Replay deep-link chips for quality/creation bins into Game Explorer with linkage-quality pills (Sprint 61) |
| `ShotIdentityBadges` | `components/` | Compact shot-identity badges (tier + confidence + summary) for PlayerHeader and Compare (Sprint 61) |
| `ShotIntelligenceOpsPanel` | `components/` | `/coverage` ops panel: baseline status, team readiness, stale players, missing-context histogram, refresh actions (Sprint 61) |
| `LiveTicker` | `components/` | Sticky 36px dark scoreboard strip above nav with auto-scrolling demo scores and live-pulse dots (Sprint 70) |
| `FloatingBall` | `components/` | Decorative SVG basketball with `cv-ball-float` keyframe animation for hero panels (Sprint 70) |
| `Reveal` | `components/` | IntersectionObserver-driven fade-up wrapper for staggered scroll-triggered animations (Sprint 70) |
| `Parallax` | `components/` | Mouse-tracking tilt wrapper that translates child by `strength` pixels based on cursor position (Sprint 70) |
| `SpotlightCursor` | `components/` | Mouse-following radial-gradient overlay for hero panels (Sprint 70) |
| `LiveShotPulse` | `components/` | Animated half-court SVG cycling through made/missed shots with ripple keyframes (Sprint 70) |
| `StandingsLadder` | `components/` | Animated conference-race directory with team color bars, slide-in entries, playoff-cutoff coloring (Sprint 70) |
| `WinProbabilityChart` | `components/` | SVG win-probability line chart with quarter dividers, draw-in animation, and event markers (Sprint 70) |
| `HomeLiveCourt` | `components/` | Composed home-page demo section pairing LiveShotPulse + WinProbabilityChart + StandingsLadder (Sprint 70) |
| `HeroHardwood` | `components/` | Procedural woodgrain texture for hero panels and metric cards (in use since Sprint 70 design integration) |
