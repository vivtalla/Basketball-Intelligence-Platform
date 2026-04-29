# Sprint 77c Closeout — Broadsheet Live Data + Sync Hooks

**Date:** 2026-04-28
**Branch:** `feature/sprint-77c-broadsheet-live-data` (this closeout merges to master)
**Status:** Ready for merge

---

## Theme

Sprint 77 (a + b) shipped the broadsheet/newsprint Playoff Home and Game Detail surfaces as a faithful translation of the design tarball, with most copy and stats hardcoded against the prototype edition. Sprint 77c replaces every prototype placeholder with live data, fixes a class of small-sample distortions in the analytics, wires the home-page surfaces to the live NBA scoreboard, and adds a daily/post-game sync hook so the bracket stays current without manual intervention.

User intent (paraphrased from session): _the Sprint 77 broadsheet looks right, but the headlines, leaders, slate, and bracket are out of date or wrong. Make them live, and add a hook so they stay live without me re-running the sync._

---

## Sprint shape

Single-stream conversational sprint. No parallel teams. Driven by iterative user feedback against the live deployment — every change in this closeout was triggered by a specific observation on the running app.

Master tip moves from `67c4d59` (Sprint 77b merge) to the merge commit produced by this closeout.

---

## Shipped

### Live data wiring across the playoff broadsheet

**`/api/playoffs/today` now merges the live CDN scoreboard.** New `get_todays_scoreboard()` helper in `backend/data/nba_client.py` hits `cdn.nba.com/.../todaysScoreboard_00.json`. The endpoint pulls the DB rows for the target date, then for today's date overlays scoreboard data — completed games stay authoritative from the DB; upcoming/in-progress games come from the scoreboard with `tipoff_utc` and `broadcaster` fields. New `_build_scheduled_game_from_scoreboard()` looks up series context (round, top/bottom seeds, current series record) by team-pair when a game isn't yet in the DB.

**Schema additions:** `PlayoffSeriesGameWithMatchup` gained `tipoff_utc` (ISO-8601 string) and `broadcaster` fields. Both Optional. `BroadsheetGameCard` consumes `tipoff_utc` for the kicker line instead of a hardcoded `19:00:00Z` fallback, and tags the kicker with the real broadcaster ("8:00 PM ET · Game 5 · TNT") when the scoreboard provides one.

**Hermetic test fix:** `tests/test_playoff_today_storyline.py` now patches `_scoreboard_games_for_today` to return `{}` so the test stays deterministic when the fixture date matches the system date.

### Story Rail — auto-generated from platform stats, internal links only

**New `backend/services/story_rail_service.py`** computes three tiles from current playoff data:
- **Heat Check** — biggest positive scoring delta over last 3 playoff games vs season pts_pg (12 PPG floor for relevance).
- **Efficiency Desk** — highest TS% among scorers averaging ≥15 PPG with ≥4 GP.
- **X-Factor** — best impact composite among PPG ∈ [8, 22) — surfaces secondary scorers / playmakers as hidden drivers.

**New endpoint `GET /api/playoffs/story-rail?season=YYYY-YY`** returns up to 3 `PlayoffStoryTile` rows. Each tile carries `kicker`, `headline`, `subhead`, `byline` ("CourtVue Numbers Desk"), `href` (always internal), and `read_time`. Tiles refresh every 5 minutes via SWR. Replaces the hardcoded prototype copy in `StoryRail.tsx`.

**No external content.** Headlines link to `/players/{id}` only. No paywalled article links, no scraped excerpts — every tile is computed, not curated.

### Narrative Leaders — composite ranking + smart stat lines + methodology popover

**Composite impact score** in `backend/services/playoff_leaders_service.py`:
```
impact = pts_pg * 0.35
       + ast_pg * 0.20
       + reb_pg * 0.10
       + min(ts_pct, 0.65) * 100 * 0.20
       + net_rating * 0.15
```
TS% clamped at 65% to neutralize small-sample shooting inflation (a 1-min cameo at 1/1 FG no longer outranks a 30 PPG star). Qualifying thresholds: `GP ≥ 4`, `MIN_PG ≥ 22`, `PPG ≥ 12` — filters out cup-of-coffee bench cameos. Falls back to the loose filter (any non-null PPG) when zero players qualify, so the rail is never empty early in the postseason.

**Dynamic stat line** picks the most narratively distinctive 3-stat triple per player:
- Slot 1 — always PPG (the rail is a "leaders" hero).
- Slot 2 — AST if ≥5 and elite vs RPG; otherwise RPG; falls back to whichever is bigger when neither is elite.
- Slot 3 — TS% if ≥58, else NET if ≥+5, else USG% if ≥28, else fallback to TS% / NET. Result: a playmaker reads "29.1 PPG · 8.4 AST · 62.1 TS%", a stretch big reads "24.6 PPG · 11.2 RPG · +9.4 NET".

**Front-end:** `NarrativeLeaders.tsx` now renders an Impact pill on the right of each row showing the composite score in accent green. A new `<MethodologyTooltip>` (CSS group-hover, no React state) anchors to the **ⓘ** glyph next to the section header and reveals the formula, TS% cap, qualifying thresholds, and trend/grade definitions on hover/focus. Anchored `left-0` (not `right-0`) so the popover extends rightward into the panel rather than off-page.

### Performer Heatmap — fixed plotting math + hover tooltip

**Bug 1 (plot math):** `backend/data/leaderboards` returns `usg_pct` as a 0..1 fraction (`0.378`), but the chart axis is 10..40 in percentage points. Every dot was getting clamped to `usg_min=10`. Fixed via a defensive `pctToScale()` helper that scales ≤1.5 inputs by 100.

**Bug 2 (small samples):** `gp ≥ 2 / min_pg ≥ 8` was letting Embiid-on-1-game distort the chart. Bumped to `gp ≥ 4 / min_pg ≥ 18` to match Narrative Leaders. Header chip + empty-state copy updated to match.

**Bug 3 (link):** "All leaders →" from `NarrativeLeaders` now passes `?seasonType=Playoffs` so the leaderboards toggle is pre-set when arriving from the playoff broadsheet.

**Hover tooltip:** new HTML-positioned tooltip on each dot showing player name (display serif), team · GP · MPG (mono uppercase), a 3-stat grid (Playoff USG%, Playoff TS%, TS% Δ color-coded by sign), and the regular-season TS% baseline. Auto-anchors left or right depending on where the dot sits so the tooltip never spills off-panel. Hovered dot grows from r=4 to r=6 with a darker stroke; non-hovered dots fade to 0.4 opacity.

### `/leaderboards` — TopLeadersTable that responds to the toggle

**New `frontend/src/components/leaderboards/TopLeadersTable.tsx`.** Top-10 leaderboard table that re-fetches from `/api/leaderboards` whenever the seasonType toggle flips. Stat-picker chips (PPG · AST · RPG · TS% · USG% · NET) drive the sort and the highlighted column. Heading copy adapts: "The current playoff workload" vs "The full-season scoreboard".

**Heatmap gated to Playoffs.** `PostseasonHeatmap` is inherently a playoff-vs-regular comparison; it now only renders when the toggle is on Playoffs.

### Series Tracker Strip — game-level deep links

**Each cell of the win bar** is now a `Link` to `/games/{gameId}` for played games (uses the bracket's `series.games[i].game_id`). Hover grows the cell from h-2 to h-3 with a subtle lift so the click target is discoverable. Outer card is no longer a single Link — that was sending every click to the same `/pre-read?series_id=...` URL which then defaulted to OKC vs BOS (the page falls back to `team="OKC", opponent="BOS"` when those query params are missing).

**`BroadsheetGameCard`** now links each card directly to `/games/{gameId}` instead of `/pre-read?series_id=...`. Same prefill bug, same fix.

### Game Detail — graceful base response when PBP is missing

**`backend/services/game_detail_assembler.py`** previously hard-404'd when `play_by_play` was empty for a game, even though the base game info (score, teams, date, series context) was available. Now returns a base `GameDetailResponse` with `events: []`, `timeline: []`, `top_players: []` and lets the EA1/EA2/EA3 derived fields stay None (their try/except wrappers were already in place). Frontend renders the broadsheet shell with PBP-derived sections empty rather than the "Game detail unavailable" 404 page.

### `/playoffs` Hero + By-the-Numbers — fully data-driven

**`PlayoffHero`** + **`ByTheNumbers`** now use a shared `useEditionSnapshot()` hook that composes `/bracket` and `/today`. Computes:
- **Round label** — `ROUND_LABELS[max(active_round)]` over the bracket; "First Round" / "Conference Semifinals" / "Conference Finals" / "NBA Finals".
- **Headline** — templated by tonight's game count (0 / 1 / N games).
- **Subhead** — prose list of tonight's actual matchups (`PHI at BOS · ATL at NYK`) or a "presses rest" line.
- **Pills** — real game count, real total games played, real broadcasters from the scoreboard.
- **From-the-desk column** — list of tonight's matchups each tagged Live / Final / Scheduled instead of the prototype editor's quote.
- **By the numbers** — playoff games count, avg margin, games tonight, longest series ("OKC-MIN · 5"). "Through {today}" instead of the stale "Through May 12".

### PBP backfill for the postseason — 36 games (was 0)

**New `backend/data/sync_playoff_pbp.py`** is a focused sync that hits the per-game PBP fetch + store loop without running the regular-season aggregate computation in `_sync_games` (which would corrupt clutch / on-off / lineup tables with `is_playoff=False` flags). Walks every `season_type="Playoffs"` row in `GameLog`, fetches box score + PBP via the existing nba_client wrappers, stores events in `play_by_play`. Idempotent.

Ran end-to-end against 2025-26: synced PBP for all 33 first-round games (avg ~600 events / game). Combined with the today-finals ingest below, the postseason now has full PBP coverage for all 36 games played to date.

### Daily / post-game sync hook

**New `backend/data/sync_today_playoff_finals.py`.** Bridges the gap between the live CDN scoreboard and the DB:
1. Fetches `todaysScoreboard_00.json`.
2. Filters to `gameStatus=3` (Final) playoff games (`gameId.startswith("004")`).
3. For any game_id not in `GameLog`, fetches box score and inserts a row with `season_type="Playoffs"` + the calendar date from `gameCode`.
4. Calls `build_or_refresh_bracket()` so `PlayoffSeries.top_wins/bottom_wins/status` reflect the freshly-ingested games.
5. PBP-syncs the new games inline.

**`backend/data/daily_sync.sh`** wires this into both paths:
- `--post-game` mode runs the ingest as Step 0, before the existing bracket recompute. The bracket now sees today's finals.
- Default daily run (Step 6, in playoffs only) runs the ingest before the existing `sync_playoff_full.py` orchestration so the morning sync also catches yesterday's late finals.

**Cron lines** documented at the top of `daily_sync.sh`:
```
0 6 * * *     /path/to/repo/backend/data/daily_sync.sh             # full daily, 6am UTC
*/30 * * * *  /path/to/repo/backend/data/daily_sync.sh --post-game  # every 30 min, self-gates
```
Installed on Vivek's laptop with `MAILTO=""` to suppress mail. Smoke-tested end-to-end — bracket refreshed (8 series), 3 finals ingested, hustle/splits/injuries refreshed, all steps `status: ok`.

**Backlog entry** added: _Sync Hosting — move daily / post-game cron off the laptop_, captures the laptop-asleep-skips-runs limitation and proposes server hosting + a launchd interim if needed.

### Mode toggle bug fix

`useViewMode` rewritten to use `useSyncExternalStore` over a module-level shared store. The previous per-component `useState` meant `ModeToggle` and `HomePage` had separate override state — clicking REGULAR updated the toggle's view but not the home page. Now every consumer subscribes to the same store and re-renders together. Also adds cross-tab sync via the `storage` event.

### Quick wins from the design audit

- **Favicon** — new `frontend/src/app/icon.svg` (96×96 lens + Erlenmeyer flask on parchment ground); deleted legacy `favicon.ico`.
- **`<StatCard>`** — value gets `bip-display tabular-nums` so numerals don't dance.
- **`<WinProbabilityChart>`** — momentum gradient shading: forest above 50%, gold below. Two `linearGradient` defs per chart.
- **`<MvpRacePanel>`** — `<Ticker>` integration via new `rawValue` prop on `MetricBlock`; Award Case + Basketball Value composites count up on mount.
- **Brand primitives** — new `frontend/src/components/brand/`: `Kicker`, `Pill`, `Button`, `Stat`, `Icon` (19-icon line set), `Hardwood` re-export, `Reveal` re-export, `Ticker` (rAF count-up with decimal-aware `useCountUp`).
- **Charts** — new `frontend/src/components/charts/`: `WinProbability`, `StandingsLadder`, `BoxScoreTable`. Pure-SVG, match the design system handoff.
- **`/playoffs` route** — new dedicated page that translates `PlayoffHomeScreen.jsx` from the handoff. The home `/` page redirects here in playoff months (`new Date().getMonth() ∈ [3,5]`) when the user has no localStorage override.
- **Nav** — 56px logo mark + new `frontend/public/courtvue-mark.svg` (ink lens + court lines breaking around the flask + gold meniscus). `NavLinks` tightened to `gap-3` + `whitespace-nowrap` + `text-xs` on secondary items so 13 items sit in one row.

---

## Verification

- **Backend tests:** `360 passed, 2 warnings in ~19s` (full suite, no new test count change — same 360 from Sprint 77 close, with the storyline test patched to mock the live CDN).
- **Frontend type check:** `npx tsc --noEmit` clean.
- **Frontend lint:** `npm run lint` shows the same 7 pre-existing `usePlayerStats.ts` warnings, no new violations.
- **Live smoke tests:**
  - `/api/playoffs/today` returns 3 games today with `tipoff_utc` + scoreboard scores.
  - `/api/playoffs/story-rail?season=2025-26` returns 3 tiles (Holiday heat check, Dosunmu efficiency, KAT x-factor).
  - `/api/playoffs/leaders?season=2025-26&limit=5` returns Tatum / KAT / Brown / Cunningham / Barnes ranked by impact.
  - `/api/games/0042500101` returns 200 with full PBP-derived sections (567 events, 48 lead points, 24 possession-diary entries).
  - Bracket reflects today's BOS-PHI Game 5 (now 3-2, was stale at 3-1).
- **Cron:** `crontab -l` shows the two installed entries; `daily_sync.sh --post-game --dry-run` reports both code paths intact.

---

## Open follow-ons

- **Sync hosting** — captured in `specs/BACKLOG.md` under Later. Move the cron off Vivek's laptop to a server so missed runs aren't lost when the Mac sleeps.
- **PBP for older playoff seasons** — `sync_playoff_pbp.py` is season-scoped; running it for 2024-25 would unlock historical broadsheet game-detail rendering.
- **Story Rail richness** — current 3 templates are scoring/efficiency/x-factor. Could add tiles for "biggest playoff-vs-regular usage swing" or "team defensive rating leader of the round" without much work.
- **Headline impact-score weights** — chosen by inspection. A grid-search calibration over historical playoff voting / award shares would let us defend each weight quantitatively.
- **`/leaderboards` page UX** — once `season_type` switching is wired, an obvious next step is letting users pick more than the chip-row stats (e.g., career averages, role-relative percentiles).

---

## Files

**Modified (24):**
```
backend/data/daily_sync.sh
backend/data/nba_client.py
backend/models/playoffs.py
backend/routers/playoffs.py
backend/services/game_detail_assembler.py
backend/services/playoff_leaders_service.py
backend/tests/test_playoff_today_storyline.py
frontend/src/app/layout.tsx
frontend/src/app/leaderboards/page.tsx
frontend/src/app/page.tsx
frontend/src/components/MvpRacePanel.tsx
frontend/src/components/NavLinks.tsx
frontend/src/components/StatCard.tsx
frontend/src/components/WinProbabilityChart.tsx
frontend/src/components/broadsheet/BroadsheetGameCard.tsx
frontend/src/components/broadsheet/NarrativeLeaders.tsx
frontend/src/components/broadsheet/SeriesTrackerStrip.tsx
frontend/src/components/broadsheet/StoryRail.tsx
frontend/src/components/playoffs/PostseasonHeatmap.tsx
frontend/src/hooks/useViewMode.ts
frontend/src/lib/api.ts
frontend/src/lib/types.ts
specs/BACKLOG.md
.gitignore
```

**Deleted:**
```
frontend/src/app/favicon.ico
```

**New:**
```
backend/data/sync_playoff_pbp.py
backend/data/sync_today_playoff_finals.py
backend/services/story_rail_service.py
frontend/public/courtvue-mark.svg
frontend/src/app/icon.svg
frontend/src/app/playoffs/page.tsx
frontend/src/components/brand/{Kicker,Pill,Button,Stat,Icon,Hardwood,Reveal,Ticker}.tsx + index.ts
frontend/src/components/charts/{WinProbability,StandingsLadder,BoxScoreTable}.tsx + index.ts
frontend/src/components/leaderboards/TopLeadersTable.tsx
specs/sprint-77c-closeout.md
```
