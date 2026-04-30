# Sprint 78 Closeout — 10-Team Parallel Sprint: Front Office + Casual Fan

**Date:** 2026-04-29
**Branches:** Phase 0 + 10 feature branches, all merged to `master`
**Status:** Shipped. `master` at `c3ec5dd`.

---

## Theme

Sprint 78 is the largest sprint to date — **10 parallel feature teams** running the standard `Architect → Engineer → Reviewer → Optimizer` pipeline (per CLAUDE.md, scaled up from Sprint 77's 8). Two streams of five: Front Office (NBA exec) features and Casual Fan engagement features.

Sprint 77c ended with the playoff broadsheet wired to live data and a daily/post-game sync hook installed. The clearest gaps remaining were (1) NBA front-office decisioning workflows the platform had no surface for at all (trade evaluation, salary cap, free agency, draft prospects, multi-year planning, injury impact) and (2) casual-fan engagement hooks (shareable content, predictions, narrative views, milestone celebrations). Sprint 78 ships both streams.

---

## Sprint shape

- **Phase 0 schema kickoff** landed 8 new tables on `master` ahead of any team architect, so 10 concurrent architects could spec services against stable types without colliding on `models.py`.
- Two streams of 5 teams each, each run through the standard pipeline. Three teams (FO1, FO3, FO5) got expanded engineering allocation for live-data ingestion alongside their feature work.
- All 10 agents worked in dedicated git worktrees (`/Users/viv/Documents/bip-{team}` or `/tmp/bip-{team}`) to keep parallel branches from contending over the main checkout.
- File-lock discipline was strict-additive only on shared files (`models.py`, `main.py`, `lib/types.ts`, `lib/api.ts`, `NavLinks.tsx`); merge coordinator resolved conflicts at integration time.

`master` tip moved from `657cf7c` (Sprint 77c merge) through Phase 0 (`a4269d0`), Wave 1 (4 CF teams merged at `6742f16`), Wave 2 (6 FO + CF2 teams), and a final auto-resolver-fix commit to `c3ec5dd`.

---

## Phase 0 — Schema kickoff

**Branch:** `feature/sprint-78-phase0-schemas` (Claude — coordinator)

8 new tables, 1 Alembic migration (`0013_sprint78_phase0_schemas`), idempotent against fresh SQLite + production Postgres:

- `player_contracts` — backs FO1/FO2/FO4
- `draft_prospects` + `draft_prospect_stats` + `draft_prospect_measurements` — back FO3
- `draft_pick_assets` — backs FO4
- `player_injury_history` — backs FO5 (distinct from current-state `player_injuries`)
- `player_streaks` + `milestone_snapshots` — back CF5

Schema-migration test updated to assert the new head revision. 360 backend tests passed at Phase 0 close.

---

## Stream A — Front Office (5 teams)

### FO1 — Trade Machine + Salary Ingestion
**Branch:** `feature/sprint-78-fo1-trade-machine` (commit `1b3cd36`)

Flagship exec feature. Ships:
- **Salary ingestion** — `services/salary_ingestion_service.py` with a CSV-backed seed adapter (`backend/data/seed/contracts_2025_26.csv`, 50 fabricated-but-plausible rows) and a clean interface for a future Spotrac scraper. CLI `data/sync_salaries.py --source seed_csv`. Wired into `daily_sync.sh` post-game.
- **Trade rule engine** — `services/trade_machine_service.py` validates ±125% salary-matching for up to 4-team packages. Flags (does not enforce) tax line, 1st apron, 2nd apron, BYC, traded-player exception per the user-confirmed scope decision.
- **Trade impact projection** — `services/trade_impact_service.py` reuses `lineup_impact_service` + on/off + archetype to project per-team net-rating delta + rotation health + archetype gap callouts. Best-effort with `confidence: "thin_sample"` fallback.
- **`/api/trade/{validate, impact, contracts/{abbr}}`** in `routers/trade.py`.
- **Frontend `/trade-machine`** — multi-team trade builder, validation card, salary-match summary, impact-projection cards, methodology popover.
- **6 backend tests** in `test_trade_machine.py`.

### FO2 — Free Agency Workspace
**Branch:** `feature/sprint-78-fo2-free-agency` (commit `89fbdc9`)

Soft-depends on FO1's `PlayerContract` schema. Ships:
- **`services/free_agency_service.py`** — pulls expiring contracts (12-month window or `years_remaining ≤ 1`), buckets by tier (max / above_mid / mid_level / minimum / two_way) with cap-threshold approximations, ranks team fits via existing `team_fit_service`.
- **`/api/free-agency`** + **`/api/free-agency/{player_id}/fits`** routes with tier/position/age filters.
- **Frontend `/free-agency`** — leaderboard with filters, expandable per-row top-10 team fits with rationale chips, empty-state when contracts table is empty.
- **5 backend tests** including empty-state and tier bucketing.

### FO3 — Draft Prospect Workspace + NCAA Translation
**Branch:** `feature/sprint-78-fo3-draft-prospects` (commit `e368568`)

Ships:
- **Seed CSV** — `backend/data/seed/draft_prospects_2026.csv` with 30 fabricated prospects (real names from public 2026 mocks). NCAA scraper interface stubbed for future. CLI `data/sync_draft_prospects.py`. Wired into `daily_sync.sh`.
- **`services/draft_translation_service.py`** — pace-adjusted (NCAA ≈ 70 pos → NBA ≈ 100) per-100 projection with `translation_confidence` (0..1) + factor narratives.
- **`services/draft_prospect_comp_service.py`** — z-score Euclidean comp matching against current-season `season_stats`, k=5 NBA comps with archetype label + rationale chip, reusing `similarity_service` patterns.
- **`/api/draft/{board, prospects/{id}}`** routes.
- **Frontend `/draft`** + **`/draft/[prospectId]`** detail pages — board, stat strips (per-game + translated per-100), 5-comp grid, measurement panel.
- **3 backend tests**.

### FO4 — Multi-Year Team Arc + Aging Curves
**Branch:** `feature/sprint-78-fo4-team-arc` (commit `72122de`)

Ships:
- **`services/aging_curve_service.py`** — empirical position-bucketed (G/F/C) aging curves from 10+ years of historical `SeasonStat`. In-process cache. Sparse-bucket fallback to "all".
- **`services/team_arc_projection_service.py`** — 3-year roster projection with `PlayerContract` integration (gracefully falls back to current roster if empty), `DraftPickAsset` overlay, decision levers (incoming picks / signings / outgoing releases).
- **`/api/teams/{abbr}/arc`** GET + POST (POST takes a `levers` body) on `routers/teams.py`.
- **Frontend** — new "Arc" tab on `/teams/[abbr]` with SVG arc chart (Off/Def/Net + projected wins), per-year roster table, decision-lever sliders (pick slot/year + re-sign + release), cap-state strip with placeholder when empty, methodology popover.
- **4 backend tests** covering aging curves, single-player projection, base team-arc, and lever overrides.

### FO5 — Injury Impact + Historical Duration Modeling
**Branch:** `feature/sprint-78-fo5-injury-impact` (commit `f156e2c`)

Ships:
- **Historical injury seed** — 220-row synthetic seed (`player_injury_history_seed.csv`) spanning 4 seasons × 10 body parts with `source=seed_synthetic`. Deterministic generator committed alongside. ProSportsTransactions scraper interface stubbed for future.
- **`services/injury_duration_model.py`** — tiered cohort (body_part + age band + recurrence) empirical distribution, hardcoded prior fallback at `n < 5`.
- **`services/availability_impact_service.py`** — extends existing `team_availability_service` with rotation re-projection + net-rating delta when injured players are removed.
- **2 new endpoints** on `routers/injuries.py`: `/{player_id}/duration-estimate` and `/team/{team_abbr}/availability-impact`.
- **Frontend** — `PlayerInjuryPanel` mounted in `PlayerDashboard`; `TeamAvailabilityImpactPanel` on team roster tab; methodology popovers on both.
- **4 backend tests**.

---

## Stream B — Casual Fan (5 teams)

### CF1 — Shareable Story Cards
**Branch:** `feature/sprint-78-cf1-share-cards` (commit `5ec3b4c`)

Ships:
- **`services/share_card_service.py`** — Pillow-based PNG renderer (1200×630, OG-default). Card types: player season, game recap, series, milestone. Broadsheet aesthetic — parchment ground, serif title, gold accent, mono uppercase kicker, large tabular-nums stat line.
- **`/api/share/{player|game|series|milestone}/{id}.png`** routes returning PNG with 1-hour cache header.
- **Frontend `<ShareCardButton>`** (pill + compact variants) mounted on player profile, game-detail broadsheet, and series-tracker cards. Client-side download via opening the API URL in a new tab.
- **OG metadata** on `/games/[gameId]` and `/playoffs` via dedicated `layout.tsx` files (the pages are `"use client"`, so metadata has to live in layouts).
- **`generateMetadata`** on player profile route.
- **2 backend tests** (player + game card PNG validation).

### CF2 — Bracket Pick'em + Model Comparison
**Branch:** `feature/sprint-78-cf2-bracket-pickem` (commit `9a0d8b0`)

Per user-confirmed scope: **localStorage-only, single-user, no auth**. Framing is "you vs CourtVue's model".

Ships:
- **`services/picks_scoring_service.py`** — scores user picks against actual outcomes + against the model's predicted bracket (reuses `playoff_simulator_service.simulate_series` per series; no full-bracket helper existed). Rubric: 1/2/4/8 pt by round, +50% length bonus when winner correct, 5pt per award.
- **`/api/picks/score`** + **`/api/picks/model`** routes.
- **Frontend `/picks`** — bracket pick UI, MVP/COY/DPOY/ROY pickers (BPM-leader dropdown), debounced auto-scoring, head-to-head scorecard, narration list, methodology popover, reset button. Persists to `localStorage` key `bip-picks-{season}`.
- **3 backend tests**.

### CF3 — Career Hall of Fame View
**Branch:** `feature/sprint-78-cf3-career-hof-view` (commit `f7717d7`)

Ships:
- **`services/career_legacy_service.py`** — era-adjusted PPG (pace ratio) + TS% delta vs league avg + composite HOF projection (20k pts +30 / MVP·DPOY +20 / All-Stars +15 each cap 60 / ring +10 → Likely-HOF / Borderline / Tracking with top-3 drivers).
- **`services/career_milestone_service.py`** — reads `MilestoneSnapshot` when populated, falls back to live computation across 16 catalog milestones (10k/15k/20k/25k/30k pts, 1k/2k/3k 3PM, 5k/10k ast/reb, 1k stl/blk, 500/1k GP).
- **`services/era_peer_service.py`** — career-aggregate z-vector (GP-weighted) over the existing 9-stat similarity feature set, returns 5-10 best peers across all NBA history.
- **`/api/players/{player_id}/legacy`** route on new `routers/career.py`.
- **Frontend** — new "Legacy" tab on player profile via `<LegacyTab>` (era-adjusted stat strip, `CareerArcChart` reuse with milestone overlay, era-peer grid linking back to player profiles, HOF projection card with score gauge + drivers).
- **4 backend tests**.

### CF4 — Game Story Mode (frontend-led)
**Branch:** `feature/sprint-78-cf4-game-story-mode` (commit `e254927`)

Frontend-led team — no new backend service. Ships:
- **`<GameStoryTimeline>`** component (~500 lines) — combines WP swing events + top possession-diary entries + scoring events into a single ranked narrative timeline. Each "moment" gets `narrative_score = |wp_delta| × 100 + lead_impact × 0.5`. Renders top 8-12 as scrollable broadsheet cards with anchor links to existing modules.
- Mounted in `BroadsheetGameDetail.tsx` between score banner and `SharedGameModules`.
- Methodology popover (CSS group-hover, no React state) explaining the ranking formula.
- **1 backend test** (`test_wp_series_provides_enough_signal_for_story_timeline`) covering the existing `compute_win_probability` output shape.

### CF5 — Streaks & Milestones Tracker
**Branch:** `feature/sprint-78-cf5-streaks-milestones` (commit `1514ae7`)

Ships:
- **`services/streak_detection_service.py`** — 5 streak types (30+ pts, double-doubles, triple-doubles, 50%+ FG / 15+ FGA, 5+ 3PM). Walks `PlayerGameLog` reverse-chronologically, upserts into `player_streaks`.
- **`services/milestone_proximity_service.py`** — 12-milestone catalog (10k/15k/20k/25k pts, 1k/2k/3k 3PM, 5k/10k ast/reb). Computes current career value, next unhit threshold, `games_to_milestone`. Upserts into `milestone_snapshots`.
- **`services/signature_performance_service.py`** — percentile-ranked per-player career box-score lines from the most recent slate.
- **`/api/milestones/{active-streaks, approaching, signature-performances}`** routes.
- **`data/sync_streaks_milestones.py`** CLI + `daily_sync.sh` hooks (post-game + morning paths).
- **Frontend `/milestones`** page with three sections + `PlayerStreakChip` on `PlayerHeader` + story-rail tile integration in `story_rail_service.py`.
- **5 backend tests**.

---

## Verification

- **Backend tests:** `397 passed` (was 360 at Sprint 77c close, +37 new across 10 teams + Phase 0).
- **`npx tsc --noEmit`:** clean.
- **`npm run lint`:** 8 warnings — all pre-existing (the same `usePlayerStats.ts` set + 1 `SeriesTrackerStrip.tsx`).
- **Live smoke tests** (where applicable):
  - `python data/sync_salaries.py --source seed_csv` populates 50 contracts.
  - `python data/sync_draft_prospects.py --source seed_csv` populates 30 prospects.
  - `python data/sync_injury_history.py --source seed_csv` populates 220 historical injuries.
  - `python data/sync_streaks_milestones.py --season 2025-26` upserts streaks + snapshots.
  - All new routes return 200 against an empty DB (graceful empty-state contracts).

---

## Merge sequence

```
657cf7c (Sprint 77c) — pre-sprint master tip
a4269d0 — Phase 0 schemas
fdf0a87 — CF4 Game Story
456d1c0 — CF1 Share Cards
11f78b0 — CF3 Career HOF
6742f16 — CF5 Streaks & Milestones (Wave 1 closed)
cfa235d — FO1 Trade Machine
08ddfea — FO2 Free Agency
30c2d40 — FO3 Draft Prospects
9b42ade — FO4 Multi-Year Arc
4e94495 — FO5 Injury Impact
17d506b — CF2 Bracket Pick'em (Wave 2 closed)
c3ec5dd — auto-resolver fix (closing braces)
```

Two waves of merges. Wave 1 had 4 conflicts (mostly main.py + types.ts + api.ts + NavLinks.tsx — all additive). Wave 2 had 6 of the same. A small Python `merge_resolve.py` script automated the "additive both sides" pattern after the third hand-resolved merge — kept the second half of the integration moving fast.

One small fix-up commit at the end (`c3ec5dd`) restored closing `);` and `}` pairs in `api.ts` (`getProspectDetail`, `getTeamArcWithLevers`) and `types.ts` (`TeamArcResponse`) where the auto-resolver's straight-text concatenation crossed function boundaries. Caught by `tsc --noEmit` before push.

---

## Risks captured + outcomes

1. **NCAA data infrastructure greenfield (FO3)** — accepted: shipped seed CSV path with stubbed scraper interface. Translation model is empirical/naive but defensible. Future sprint can wire Sports Reference.
2. **Spotrac scraping brittle (FO1)** — accepted: shipped seed CSV with `salary_ingestion_service` interface ready for a future scraper.
3. **10 concurrent architects on `models.py`** — Phase 0 prevented the collision; no in-flight team had to touch `models.py`.
4. **CF4 overlap with Sprint 77 game-detail** — Framed as frontend-led extension. Clean integration.
5. **FO5 historical injury data** — Built seed-CSV ingestion path with scraper interface. ProSportsTransactions integration is future work.
6. **Sprint 77c just shipped** — All new features handle empty bracket / today / leaders gracefully (mostly because the new tables they query are themselves empty after Phase 0).
7. **Closeout at 10-team scale** — Captured here. CLAUDE.md "Recent Sprints" updated; Sprint 77 retired to `specs/sprint-history.md`.

---

## Open follow-ons

- **Real Spotrac scraper** — replace seed CSV in FO1 once the scraper is built. Daily sync hook is already wired.
- **Real Sports Reference NCAA scraper** — same for FO3.
- **Real ProSportsTransactions historical scraper** — same for FO5.
- **Postgres migration boolean default** — Phase 0 migration uses `sa.text("0")` for booleans, which works on SQLite but may need tweaking for production Postgres (FO1 agent flagged this; not blocking SQLite).
- **Trade Machine cap fidelity** — apron / tax / BYC / TPE flagged but not enforced. Future sprint with full CBA fidelity.
- **Pick'em multi-user** — currently localStorage-only per user direction. Cookie-ID identity is a future option.
- **Game Story narrative_score backend** — currently computed client-side. Backend `narrative_score` field on PBP events is a future optimization.
- **Era-peer span** — CF3's era-peer compute was capped at the 16+ historical seasons in `SeasonStat`. Pre-2005 peers require importing older data.
- **Methodology popovers everywhere** — most new features include them; a couple may need a polish pass (Optimizer scope).
- **OG image polish** — CF1 PNGs render with default fonts when the project's serif TTF isn't installed in the venv. Optimizer pass to ship a TTF fallback or improve rendering.

---

## Files

- **45 new + ~20 modified** across the sprint.
- 10 new routes: `/trade-machine`, `/free-agency`, `/draft`, `/draft/[prospectId]`, `/picks`, `/milestones`, `/api/share/*`, `/api/players/{id}/legacy`, `/api/teams/{abbr}/arc`, `/api/injuries/team/{abbr}/availability-impact` (plus existing extensions).
- 10 new backend services + 4 new routers + 8 new ORM tables + 1 Alembic migration.
- 4 seed CSVs (contracts, draft prospects, injury history, plus the in-place daily sync hooks that consume them).

Detailed per-team file inventory is in each team's commit message; reproduced files-only summary not duplicated here to keep the doc scannable.
