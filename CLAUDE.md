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

## Production

CourtVue Labs is publicly live as of Sprint 84.

| Surface | URL | Hosted On |
|---------|-----|-----------|
| Frontend | https://courtvue.app | Vercel (hobby tier, auto-deploys on push to master) |
| Backend API | https://api.courtvue.app | Hetzner CPX11 (`ubuntu@5.78.114.15`) |
| Database | localhost on the VM | PostgreSQL 16, co-located with FastAPI |

**Edge layer:** Cloudflare proxies all traffic for `courtvue.app` and `api.courtvue.app` (orange-cloud), provides DNS, WAF, rate limiting (100 req/10 min per IP), and edge caching with TTLs ranging from 5 min (catch-all) to 12 hr (player splits).

**Backend service stack:** Caddy (reverse proxy, auto-HTTPS via Let's Encrypt) → gunicorn + 2 uvicorn workers on `127.0.0.1:8000` → FastAPI. Service unit at `/etc/systemd/system/bip-api.service`. Caddyfile at `/etc/caddy/Caddyfile`. Production env at `/etc/bip/env` (`DATABASE_URL` with password, `NBA_API_USER_FETCH_DISABLED=true`, `CORS_ORIGINS`).

**Frontend env:** `NEXT_PUBLIC_API_URL=https://api.courtvue.app` set in Vercel project settings (Production, Preview, Development).

**Where secrets live:** Production `DATABASE_URL` is on the VM only at `/etc/bip/env`. Never commit to repo. Vercel env vars are managed via the Vercel dashboard, not the repo.

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

### Production Deploy

**Frontend (automatic):** push to `master` → Vercel detects the change and deploys within ~2 min. Verify at https://vercel.com → CourtVue project → Deployments. No manual step required.

**Backend (manual):**
```bash
ssh ubuntu@5.78.114.15
cd /home/ubuntu/bip && git pull origin master
sudo bash infra/deploy.sh                # restart services + health check
sudo bash infra/deploy.sh --migrate      # also runs alembic upgrade head
```

`infra/deploy.sh` validates the Caddyfile, reloads Caddy, restarts `bip-api`, and exits non-zero if `/api/health` doesn't return 200.

**Inspecting the live backend:**
```bash
sudo systemctl status bip-api caddy
sudo journalctl -u bip-api -n 100 --no-pager
sudo journalctl -u caddy -n 50 --no-pager
```

**Cache invalidation (when caches are masking a fix):** Cloudflare dashboard → courtvue.app zone → Caching → Configuration → **Purge Everything**. Use sparingly — purges all 5 cache rules at once.

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

## Production Safety

The site is live and serves real traffic. Read this before merging anything that could break production.

- **Pushes to `master` auto-deploy the frontend via Vercel within ~2 min.** A merged build error or runtime crash goes live immediately. Always run `npm run build` locally before merging.
- **API contract changes need coordinated frontend updates in the same sprint.** Removing or renaming an endpoint, field, or query param without updating the frontend that consumes it will break production the moment master deploys.
- **Schema changes require Alembic migrations.** Never rely on startup DDL. The deploy script runs `alembic upgrade head` only when invoked with `--migrate`.
- **Cache TTLs delay user-visible changes.** A new endpoint's first response is cached at the Cloudflare edge for the matching rule's TTL. If a fix needs to land immediately, purge cache after deploying.
- **CORS is restricted to `courtvue.app` and `www.courtvue.app`.** Frontend deploys at preview URLs (vercel.app subdomains) won't be able to call the production API.
- **`DATABASE_URL` is on the VM only.** Never commit it. If you need to test against production data, ssh in and use `psql` directly.
- **Rollback is fast for both layers.** Frontend: Vercel dashboard → previous deployment → "Promote to Production" (one click). Backend: ssh in, `git checkout <prev-sha>`, `bash infra/deploy.sh`. Migrations roll back with `alembic downgrade -1`.

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
- **Platform methodology lives in `specs/platform-methodology.md`.** Update it when adding or materially changing analytical formulas, scoring models, confidence thresholds, proxy labels, or methodology versions.
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

CourtVue Labs uses a hybrid sprint model: major feature sprints typically run as two parallel teams, while small or tightly coupled sprints use one sequential `Architect → Engineer → Reviewer → Optimizer` stream. **Worktree cleanup is a required closeout step** — every sprint worktree under `~/Documents/` must be removed once its branch is confirmed merged to master (see Sprint Closeout Checklist in `AGENTS.md`, step 14). Stale worktrees clutter the filesystem and can be large (hundreds of MB due to node_modules).

**Sprints are self-contained.** Every sprint ships its features in their final state — no "phase 1" with a tail of follow-on polish in the next sprint. If a feature has obvious next-step work (sortable columns on a new table, richer labels on a new component, backfill scripts for a new migration), that work belongs in the same sprint. Lengthen the sprint if scope grows; never ship the 60% solution and defer the rest.

**Deferral is the exception, not the default.** Acceptable reasons: blocked on data we don't have, blocked on infrastructure we don't have, blocked on a user decision, or genuinely a different domain (sister features, not follow-on polish). Anything else is incomplete work — finish it before closeout. See `AGENTS.md` → **Deferral Policy** for the full bar.

---

## Recent Sprints

> Full history → `specs/sprint-history.md`

### Sprint 96 — Cleanup, Performance Pass, /beta Reorg

- **Three parallel streams in one release.** Single branch (`feature/sprint-96-cleanup-and-perf`) + 1 hotfix on master, 11 commits, 90+ files changed. 588 backend tests (was 581, +4 new for `last_night_pulse_service`), `npm run build` clean, `npm run lint` 0/0. Deployed end-to-end to courtvue.app + api.courtvue.app.
- **Stream A — Playoff freshness:** `SeriesTrackerStrip.pickTrackedSeries()` now filters to `status==="active"` only and sorts round desc + combined wins desc (no backfill from closed/scheduled). New `LastNightPulse` component replaces `StoryRail` on `/` and `/playoffs` — three game-driven tiles (Tonight's Headliner / Last Night's Hero / Series Momentum) computed from `PlayerGameLog` last-36h + `PlayoffSeries.updated_at`. New service + endpoint + 4 tests. `StoryRail.tsx`, `getPlayoffStoryRail`, `PlayoffStoryTile`/`Response` types, `story_rail_service.py`, and `GET /api/playoffs/story-rail` deleted end-to-end. Cloudflare cache rule 1 expanded to bypass `/today`, `/bracket`, `/last-night-pulse` via free-tier compound OR. VM crontab tightened from `*/30` to `*/15`. Hotfix `b26f28a`: `_series_to_response` and `/today` post-pass derive `status="active"` when stored `"scheduled"` but observed wins > 0 (production R2 series rows persist as scheduled because flip-to-active only fires when *parent* clinches).
- **Stream B — Performance pass:** Two N+1 fixes in `routers/teams.py` — `list_teams` collapsed from 1+30 queries to a grouped LEFT-OUTER-JOIN; `team_roster` from 1+N to 1+1 batched `IN (...)`. Image optimization on 5 components — dropped `unoptimized` and added explicit `sizes` (FavoritesList 36px, PlayerHeader 160px, MvpRacePanel 48/80px, HomeMvpTeaser 48px). Recharts code-split via `next/dynamic({ ssr: false })` on three tab-conditional charts (`LineupScatterPanel`, `StandingsBumpChart`, `ImpactScatterChart`). `@next/bundle-analyzer` wired behind `ANALYZE=1`.
- **Stream C — `/beta` reorganization:** 19 directories moved under `frontend/src/app/beta/` via `git mv`. Kept at root: `/`, `/playoffs`, `/bracket`, `/player-stats`, `/standings`, `/og`, `/admin/*`. `next.config.ts` returns 308 redirects from every old path with `:path*`. One-shot codemod rewrote ~90 internal href / router / object-property path literals (then deleted). `NavLinks.tsx` restructured: primary tabs + "Beta" dropdown listing all 19 routes alphabetized. New `frontend/src/app/beta/layout.tsx` adds a one-line beta banner.
- **Workflow note:** First codemod pass missed bare path literals in object properties (`{href: "/teams"}`), template-literal builders (`return_to: \`/teams/...\``), and string-array entries in `sitemap.ts` — added `(?<!/api)(?<!\w)["\`]/<route>` patterns with negative lookbehind on second pass. Free-tier Cloudflare Cache Rules don't have `matches regex` — use `Edit expression` with `starts_with` OR-compounds instead.
- **Deferred:** B5 keep-list ISR refactor (`/player-stats`, `/standings`, `/playoffs` server-component conversion). **Why:** different domain — same kind of work as the per-page `/beta` graduation pattern; deserves its own focused sprint per page. Closeout: `specs/sprint-96-closeout.md`.

### Sprint 95 — Lineup Lab

- **New `/lineups` page with league-wide leaderboard and interactive What-If Studio.** Single branch (`feature/sprint-95-lineup-lab`), 1 commit, 23 files changed. 581 backend tests (was 549, +32 new), `npm run build` clean, `npm run lint` 0/0.
- **Stream A — Backend models** (`backend/models/lineups.py` NEW): 6 Pydantic models — `LineupLeaderboardEntry`, `LineupLeaderboardResult`, `LineupBuilderRequest`, `PlayerRemovalImpact`, `LineupBuilderResult`, `SublineupsResult`. `LineupArchetype` + `LineupConfidence` literal types.
- **Stream B — Leaderboard service** (`backend/services/lineup_leaderboard_service.py` NEW): `_lineup_confidence` (poss ≥200 → high/≥80 → medium/else → low), `_classify_lineup` (Elite/Offensive Wall/Defensive Wall/Negative/Balanced/Unclassified), `_shrink` (Bayesian formula with prior=150), `build_lineup_leaderboard` (3 batch queries, zero N+1).
- **Stream C — Builder service** (`backend/services/lineup_builder_service.py` NEW): exact match by sorted player_ids key, partial match by overlap score (top 3), WOWY player-removal impacts (LIKE + post-parse false-positive defense reused from Sprint 94), small-sample warnings (<80 poss).
- **Stream D — Sub-lineup service** (`backend/services/lineup_sublineup_service.py` NEW): `itertools.combinations(sorted(ids), size)` over 5-man data; possession-weighted net_rating; 2-man/3-man aggregated combos per team.
- **Stream E — Router** (`backend/routers/lineups.py` NEW): `GET /api/lineups/leaderboard`, `POST /api/lineups/builder`, `GET /api/lineups/sublineups`. Registered in `backend/main.py`. Backward compatible: `/api/advanced/lineups` untouched.
- **Stream F — Frontend types/api/hooks**: 8 new types in `types.ts`, 3 new API functions (including `postLineupBuilder` as direct POST), 2 new SWR hooks.
- **Stream G — Frontend UI**: `/lineups` page with Leaderboard tab (ORTG×DRTG Recharts scatter with reversed Y-axis, 12-column sortable table, team+min-poss filters) and What-If Studio tab (5 pre-allocated player slots, match quality banner, player removal impact grid). 7 new components in `components/lineups/`. NavLinks More dropdown updated. Teams page gains 2-man + 3-man sub-lineup `<details>` sections using compact `LineupLeaderboardTable`.
- **Stream H — Tests**: 32 new tests — 18 leaderboard (confidence, shrunk formula, all 5 archetypes + unclassified, filters, sort), 8 builder (exact/partial/none, order-independent key, removal impact, delta sign, small-sample warning, false-positive filter), 6 sublineup (C(5,2)=10, C(5,3)=10, poss gate, aggregation, weighted nr, sorted output).
- **Post-merge:** "Top Lineups" tab removed from `/player-stats` (112 lines deleted) — superseded by Lineup Lab's richer leaderboard.
- **Deferred:** none. Closeout: `specs/sprint-95-closeout.md`.

*Sprint 94 and earlier moved to `specs/sprint-history.md`.*

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
| `codex-sprint-71-methodology-rigor` | Codex | Merged to master |
| `feature/sprint-72-design-system-closeout` | Claude | Merged to master |
| `feature/sprint-73a-playoffs-data` | Claude | Merged to master |
| `feature/sprint-73b-playoffs-features` | Claude | Merged to master |
| `codex-sprint-74-methodology-upgrades` | Codex | Merged to master |
| `codex-sprint-75-playoff-command-center` | Codex | Merged to master |
| `claude/improve-evaluation-methods-ZAo94` | Claude | Merged to master |
| `feature/sprint-77a-game-data-foundation` | Claude | Merged to master |
| `feature/sprint-77b-broadsheet-screens` | Claude | Merged to master |
| `feature/sprint-77c-broadsheet-live-data` | Claude | Merged to master |
| `feature/sprint-78-phase0-schemas` | Claude | Merged to master |
| `feature/sprint-78-fo1-trade-machine` | Claude | Merged to master |
| `feature/sprint-78-fo2-free-agency` | Claude | Merged to master |
| `feature/sprint-78-fo3-draft-prospects` | Claude | Merged to master |
| `feature/sprint-78-fo4-team-arc` | Claude | Merged to master |
| `feature/sprint-78-fo5-injury-impact` | Claude | Merged to master |
| `feature/sprint-78-cf1-share-cards` | Claude | Merged to master |
| `feature/sprint-78-cf2-bracket-pickem` | Claude | Merged to master |
| `feature/sprint-78-cf3-career-hof-view` | Claude | Merged to master |
| `feature/sprint-78-cf4-game-story-mode` | Claude | Merged to master |
| `feature/sprint-78-cf5-streaks-milestones` | Claude | Merged to master |
| `feature/sprint-82a-player-depth` | Claude | Merged to master |
| `feature/sprint-82b-hosting` | Claude | Merged to master |
| `feature/sprint-82c-scrapers` | Claude | Merged to master |
| `feature/sprint-82d-public-mode` | Claude | Merged to master |
| `feature/sprint-83a-blockers` | Claude | Merged to master |
| `feature/sprint-83b-launch-polish` | Claude | Merged to master |
| `feature/sprint-83c-playoff-polish` | Claude | Merged to master |
| `feature/sprint-94-on-off-impact-revamp` | Claude | Merged to master |
| `feature/sprint-95-lineup-lab` | Claude | Merged to master |
| `feature/sprint-96-cleanup-and-perf` | Claude | Merged to master |

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
| `Sparkline` | `components/` | Pure SVG polyline with min/max scaling, optional baseline reference, delta-driven stroke color, em-dash fallback for <2 values (Sprint 72) |
| `SeriesCard` | `components/playoffs/` | Compact playoff series card with seed pills, W-L state, status pill; deep-links to /pre-read?series_id=... (Sprint 73) |
| `PlayoffBracketView` | `components/playoffs/` | East/West two-column bracket tree grouping series by round (Sprint 73) |
| `CoachingAdjustmentsTimeline` | `components/playoffs/` | Horizontal numbered timeline rendering PreReadDeckResponse.adjustments with forest dots for prior games and gold for the current game (Sprint 73) |
| `SeriesWPChart` | `components/playoffs/` | Wraps Sprint 70 WinProbabilityChart for cumulative series-level WP across games 1-7 (Sprint 73) |
| `DailyPlayoffSlate` | `components/playoffs/` | Today's playoff slate with tipoff times, away @ home rows, optional WP percent (Sprint 73) |
| `SeriesNarrative` | `components/playoffs/` | Auto-rotating series storyline carousel; honors prefers-reduced-motion by stacking (Sprint 73) |
| `PlayoffsHomeSections` | `components/playoffs/` | Tiny client wrapper that gates DailyPlayoffSlate behind useSeasonPhase().isPlayoffs so the server-component home page stays a server component (Sprint 73) |
| `SeriesWPSimulator` | `components/playoffs/` | Bracket-driven series picker + Monte-Carlo projection chart with memoized SVG geometry; Sprint 75 added real non-mutating hypothetical W/L overrides |
| `PlayoffCommandCenter` | `components/playoffs/` | Coach/analyst `/bracket` command surface with selected-series rail, pulse, tactical edges, star burden, shot diet, lineup chess, simulator, and reliability card (Sprint 75) |
| `PostseasonHeatmap` | `components/playoffs/` | USG% × TS%-delta scatter computed client-side from Regular vs Playoffs leaderboards; rotation-player filter with WCAG AA quadrant labels (Sprint 73) |
| `OpponentLineupMatchupMatrix` | `components/playoffs/` | 5×5 net-rating delta matrix between a team's and opponent's top-5 playoff lineups; 100+ possessions per cell threshold (Sprint 73) |
| `NavLinks` | `components/` | Client-only nav link group extracted from layout.tsx so the conditional Bracket nav item can read useSeasonPhase (Sprint 73) |
| `PlayerSplitsPanel` | `components/` | Official NBA situational splits with family toggle (Location, Win/Loss, Days Rest, Month, Pre/Post All-Star) and 18-column stat table with W%/+/- color coding (Sprint 82) |
| `PlayTypePanel` | `components/` | Synergy play-type breakdown: hybrid table with inline possession-share bars + PPP/percentile coloring; min 10 possessions filter (Sprint 82) |
| `ExternalMetricsAttribution` | `components/` | Reusable source-attribution UI with `footer` (subtle) + `banner` (prominent amber) variants for LEBRON/RAPTOR/EPM/PIPM/RAPM disclosure (Sprint 82) |
| `ImpactScatterChart` | `components/on-off/` | ORTG Δ × DRTG Δ scatter; bubble size ∝ on-court minutes; color by impact_classification; reference lines at 0 and ±3 (Sprint 94) |
| `OnOffImpactPanel` | `components/on-off/` | Main coaching panel for player profile: badge + confidence callout, hero chips, decomposition bars, lineup context, external validation, methodology drawer (Sprint 94) |
| `OnOffImpactBadge` | `components/on-off/` | Classification pill; border style mirrors confidence tier — solid/dashed/dotted (Sprint 94) |
| `OnOffConfidenceCallout` | `components/on-off/` | Single-line confidence tier chip with on-court minutes label (Sprint 94) |
| `OnOffDecompositionBar` | `components/on-off/` | Recharts BarChart for ORTG Δ / DRTG Δ; zero + ±3 reference lines; marginal_net annotation (Sprint 94) |
| `OnOffLineupPanel` | `components/on-off/` | Two-column top/worst lineup grid; player name chips + net_rating + possessions (Sprint 94) |
| `OnOffExternalValidationPanel` | `components/on-off/` | RAPM/EPM/PIPM chips + agreement note + public-dataset attribution disclaimer (Sprint 94) |
| `OnOffMethodologyDrawer` | `components/on-off/` | Collapsible `<details>` — formulas, classification thresholds, confidence tiers, caveats (Sprint 94) |
| `LineupLeaderboardTable` | `components/lineups/` | 12-column sortable table (Players/Team/MIN/POSS/ORTG/DRTG/Net Rtg/Shrunk/vs Team/Archetype/Conf); `compact` prop for sub-lineup sections (Sprint 95) |
| `LineupScatterPanel` | `components/lineups/` | ORTG×DRTG Recharts scatter; Y-axis reversed (lower DRTG = better = top); bubble radius ∝ sqrt(minutes); color by archetype; reference lines at avg ORTG/DRTG (Sprint 95) |
| `LineupArchetypePill` | `components/lineups/` | Archetype label pill: Elite=teal, Offensive Wall=amber, Defensive Wall=indigo, Balanced=gray, Negative=red, Unclassified=faded (Sprint 95) |
| `LineupConfidenceBadge` | `components/lineups/` | Confidence badge (High/Med/Low) with possessions count inline; colors green/yellow/gray (Sprint 95) |
| `LineupBuilderPanel` | `components/lineups/` | 5 pre-allocated searchable player slots; Build/Reset buttons; disabled until ≥2 slots filled (Sprint 95) |
| `LineupBuilderResults` | `components/lineups/` | Match quality banner (green/yellow/red) + exact/closest lineup cards + player removal impact grid (Sprint 95) |
| `LineupMethodologyDrawer` | `components/lineups/` | Collapsible `<details>`: shrinkage formula, archetype rules, confidence thresholds, What-If mechanics, sub-lineup aggregation, caveats (Sprint 95) |
| `LastNightPulse` | `components/broadsheet/` | Three game-driven tiles for the playoffs surface: Tonight's Headliner / Last Night's Hero / Series Momentum. Powered by `useLastNightPulse` SWR hook (5 min refresh) (Sprint 96) |
