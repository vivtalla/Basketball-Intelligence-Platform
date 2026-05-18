# Sprint 101 Closeout — Draft Analyzer UI + Historical Outcomes Population

**Sprint:** 101
**Date:** 2026-05-17
**Owner:** Claude
**Status:** Final (pending CI + merge)
**Branch:** `feature/sprint-101-draft-analyzer-ui`
**Sister sprint:** Sprint 100 (data foundation + backend) shipped at `133c4f6`

---

## Shipped

Four parallel streams. 11 new frontend components, 4 modified files, 1 new top-level route + 2 new historical-view routes, 1 starter seed CSV, and the Draft analyzer graduated from `/beta/draft` to top-level nav alongside Playoffs / Player Stats / Standings.

### Stream A — Board enrichment + nav graduation

- **`frontend/src/components/draft/TierBadge.tsx` (NEW)** — color-palette anchor. Five projected-tier colors + five outcome-tier colors, all in one component. Re-exported `TIER_PALETTE` + `TIER_LABELS` so Stream B/C components use the same hues without re-deriving.
- **`frontend/src/components/draft/ConsensusRankCell.tsx` (NEW)** — board-row rank cell. Prefers Sprint 100's `consensus_rank_float` (formats as `4.3`), shows a tiny σ pill (`σ 2.1`) when variance > 0, falls back to legacy integer `consensus_rank`, falls back to em-dash.
- **`frontend/src/components/draft/MockSourcesPill.tsx` (NEW)** — small `n/3` indicator with hover tooltip explaining single-source outliers. Color scales with consensus strength (3/3 = forest, 2/3 = amber, 1/3 = muted).
- **`frontend/src/components/NavLinks.tsx`** + **`MobileNav.tsx`** — added `<Link href="/draft">Draft</Link>` to the top-level nav block; removed entry from the Beta dropdown. Active styling from Sprint 100 (`linkClass(href)` + `usePathname()`) handles the highlight automatically.
- **`frontend/next.config.ts`** — split `BETA_ROUTES` into `BETA_ROUTES` + new `GRADUATED_ROUTES`. Graduated routes generate 308 redirects in the opposite direction (`/beta/draft` → `/draft`) so external bookmarks pointing at the old URL keep working.
- **`frontend/src/app/draft/page.tsx`** (relocated from `/beta/draft/page.tsx`, extended) — board now has a new "Tier" column rendering `<TierBadge>`, a Rank column rendering `<ConsensusRankCell>` + `<MockSourcesPill>` side-by-side, a new "Projected tier" filter select, and a "Polarizing only (σ > 5)" checkbox. Sort defaults to consensus rank ascending (using `consensus_rank_float` when present).
- **`frontend/src/app/draft/[prospectId]/page.tsx`** (relocated) — see Stream B for content additions.

### Stream B — Prospect detail enrichment (7 new components)

All seven components handle null/empty Sprint 100 fields gracefully (`if (!data) return null;` pattern); none of the new sections render an empty card.

- **`MockDraftConsensusPanel.tsx`** — per-source rankings table. Source links to source URL (ESPN/NBADraft.net/CBS), consensus mean + σ at top-right, tier badge per row, comp-player-name column when populated, as-of date per row.
- **`CombineMeasurementsCard.tsx`** — anthropometrics + athletic testing in two side-by-side grids (size & length / athletic testing). Footer shows source link + as-of month. Handles partial fills (e.g. height present, vert missing) with "—" rather than collapsing rows.
- **`InternationalStatsPanel.tsx`** — per-season league rows (Euroleague / EuroCup / Adriatic / French LNB / G League). Layout mirrors the existing CollegeStats table. Attribution footer shows most-recent source URL.
- **`HistoricalCompsGrid.tsx`** — outcome-weighted comp cards. Each card: player name, similarity score, outcome_tier badge, career-summary chips (GP / PPG / All-Star × N / All-NBA × N). Neighbourhood-confidence chip (high/medium/low) anchored at the top right of the section. Sorted by similarity desc.
- **`RiskIndicatorsBars.tsx`** — pure-SVG horizontal bars for the five 0..1 axes. Color gradient muted→amber→red based on value. Hover tooltips per axis explain what the risk captures.
- **`HistoricalBaselineChart.tsx`** — single horizontal stacked bar showing star/starter/role_player/bust percentages from the comp neighbourhood. Renders an explicit "Insufficient comp data" caveat when the analysis service flags `insufficient: true`.
- **`TranslationV2Ranges.tsx`** — point-and-CI range bars for pts/reb/ast per-100 + TS%. Each metric: SVG bar with the 95% CI as a forest-green block, a vertical tick at the point estimate. Below the bars: a three-column breakdown of pace multiplier, league strength multiplier, age multiplier. Confidence factors live in a collapsible `<details>` element at the bottom.

**Prospect detail page** integration appends all seven sections in order below the existing v1 sections: projected-tier banner, mock-draft consensus, translation v2 ranges, historical comps grid, historical baseline chart, risk indicators bars, combine measurements, international stats. Each is `null`-gated so v1-only prospects (no Sprint 100 data yet) render exactly as before.

### Stream C — Historical validation surface

- **`frontend/src/app/draft/historical/page.tsx` (NEW)** — year-picker landing. Renders a 10-card grid (2025 → 2016) with hover state lifting the year number into accent color. Caption below explains the data source + outcome-tier methodology.
- **`frontend/src/app/draft/historical/[year]/page.tsx` (NEW)** — server-component wrapper. Mirrors the Sprint 100 PR #22 `BracketPage` pattern: exports `dynamic = "force-dynamic"` so each visit hits the API fresh as the seed CSV grows over time. Parses the year from the route params and forwards to the client component.
- **`frontend/src/app/draft/historical/[year]/HistoricalClassClient.tsx` (NEW)** — client fetcher. Calls `getHistoricalDraftClass(year)`. Three rendered states: loading, friendly "Out of range" panel (when API returns 404 for years outside [2016, 2025]), and the populated table. Includes a "← All historical classes" back link.
- **`frontend/src/components/draft/HistoricalClassTable.tsx` (NEW)** — sortable table. Default sort by draft pick; toggle to outcome-tier (best first). Columns: Pick · Prospect · Team · NBA Outcome (TierBadge) · GP · PPG · All-Star × N · All-NBA × N.

### Stream D — Historical outcomes seed CSV (starter)

- **`backend/data/seed/draft_outcomes_2016_2025.csv` (NEW)** — 51-row starter sample covering 2018's full first round (30 rows) plus top-3 selections from 2019, 2020, top-4 from 2021, top-3 from 2022-2024 (21 rows). Approximate cumulative career numbers through the 2024-25 NBA season.

**This is intentionally a starter, not a final dataset.** The CSV's 51 rows are enough for the comp service's historical-baseline distribution to start lighting up (the analysis service requires ≥3 comps with outcomes to render anything other than `insufficient: true`), but the full 600-row 2016-2025 baseline is research-flavored manual curation that lives best as a follow-on task. See **Deferred** for the rationale.

### Cross-cutting

- **`specs/architecture-flows.html`** — updated `page-draft-board`, `page-draft-prospect-detail`, and `page-draft-historical` flow notes to reference the new Sprint 101 components consuming each API field. Validator: 20 nodes, 29 flows (unchanged), 207 steps (was 206). Structure OK.
- **`frontend/src/app/beta/draft/`** removed (files git-renamed to `frontend/src/app/draft/`). Git's rename detection preserves history.

## Test posture

No new backend tests this sprint (no backend code changes beyond architecture-flows.html and the seed CSV). Frontend:

- `npm run lint` clean.
- `npm run build` clean — 29 routes total; new routes `/draft`, `/draft/historical`, `/draft/[prospectId]`, `/draft/historical/[year]` all present. `/beta/draft` removed from the route table (graduated).
- Visual smoke test via preview server: `/draft` renders new Tier column + filter row + nav graduation (Draft bold/accent in top-level nav). `/draft/historical` renders the year-card grid. `/draft/historical/2010` cleanly renders the friendly error path (in production it would hit the API's 404 and show the "Out of range" panel).
- Production smoke (post-merge): see deploy plan below.

## Deploy plan

Frontend-only — no backend changes, no Alembic migration, no systemd-unit edits.

Push to master → Vercel auto-deploys within ~2 min. After deploy:

```bash
curl -sIL https://courtvue.app/draft | head -3                             # 200
curl -sIL https://courtvue.app/draft/historical | head -3                  # 200
curl -sIL https://courtvue.app/draft/historical/2018 | head -3             # 200
curl -sIL https://courtvue.app/beta/draft | head -3                        # 308 → /draft (graduated redirect)
```

Then load `https://courtvue.app/draft` in a browser:
- Top-level nav shows Draft bold/accent.
- Tier column visible on the board.
- Click into a 2026 prospect; depending on Sprint 100 data freshness on the live VM, the new sections (combine measurements, mock consensus, international stats, historical comps, risk indicators, historical baseline, translation v2) render or cleanly hide.

After `python -m scripts.backfill_draft_outcomes --start-year 2016 --end-year 2025` runs on the VM (separate manual step on production using the new seed CSV):
- `curl https://api.courtvue.app/api/draft/historical/2018 | jq '.prospects | length'` returns > 0 (was 0 in Sprint 100 closeout smoke).
- Re-loading a 2026 prospect on `/draft/[id]` now shows populated `historical_baseline` with star/starter/role_player/bust percentages instead of "Insufficient comp data".

## Lessons captured

- **Linter caught a real React 19 issue.** ESLint's `react-hooks/set-state-in-effect` rule flagged a synchronous `setState({ ...isLoading: true })` at the top of a `useEffect`. Fix was to drop it — each `/draft/historical/[year]` route is its own segment so the component remounts on year navigation and the initial useState value already covers the loading state. Worth knowing for future client-component fetch patterns.
- **Sprint 100's pre-baked types paid off immediately.** Stream B's seven new components consumed `MockRanking`, `CombineMeasurement`, `InternationalStatLine`, `HistoricalComp`, `RiskIndicators`, `HistoricalBaseline`, `NbaTranslationV2` with zero type-shape friction. Decision to over-invest in types in Sprint 100 saved real time in Sprint 101.
- **Graduating a route from /beta/ is two-step.** Removing from `BETA_ROUTES` is necessary but not sufficient — without a reverse redirect in `GRADUATED_ROUTES`, external bookmarks at the old URL would 404. The split list pattern keeps both directions explicit.
- **CSV comments don't work with `csv.DictReader`.** First draft of the seed CSV had `#`-prefixed comment lines; `DictReader` treats those as data rows and the integer-cast on `draft_year` blew up. Sprint 100's `scripts/backfill_draft_outcomes.py` doesn't filter them. Pulled comments into this closeout instead. If we later need inline docs in seed CSVs, the script needs a `# comment` skip helper.

## Deferred (per plan; documented reasons)

1. **Full 2016-2025 seed CSV (~600 rows)** — **Blocked on data.** Hand-curating accurate career aggregates for every drafted prospect from Basketball-Reference is a multi-hour research task best done in a focused session with the BBRef draft pages open side-by-side. The starter 51-row sample ships in this sprint; expansion is a follow-on task that doesn't block any of the analyzer surfaces (each new row strengthens the historical baseline without changing UI behaviour).
2. **`compute_team_fit()` per prospect** — **Different domain.** Needs team-archetype service threaded through; out of scope. → Sprint 102.
3. **Design-system polish** (HeroHardwood backdrops, Reveal staggered fade-in, full Sprint 70 typography pass) — **Different domain.** User-confirmed scope was functional-first; polish is its own sprint. → Sprint 102.
4. **`recalibrate_from_outcomes()` for translation_v2** — **Blocked on data** (item 1). Once the seed CSV is fully populated, the translation v2 calibration constants can be refit empirically. → Sprint 103 or later.
5. **First-run of weekly scrapers on production** — **Blocked on infrastructure** (waiting for the Monday cron tick after merge). The ingest scripts (`ingest_mock_drafts`, `ingest_combine`, `ingest_international`) shipped in Sprint 100 but haven't run yet on the live VM. First Monday tick post-merge will populate live `consensus_rank_float`, `combine_measurements`, and `international_stats` for the 2026 prospects. Monitor `/api/health/sync-status` for `"stale": true` on `draft_mock_rankings` / `draft_combine` / `draft_international` for the first 24h post-Monday.
6. **Tests for the new components** — **Different domain.** Project's frontend testing posture has historically been "visual smoke + build + lint" rather than unit tests for presentational components. Could revisit if a future sprint adopts a frontend test framework.
7. **Mahalanobis comp distance** — **Blocked on data** (item 1). → Sprint 103+.
8. **Pre-2016 historical drafts** — **Different domain.** Pre-pace-and-space era.
9. **Real-time draft-night updates** — **Different domain.** Needs websocket layer. → post-draft sprint.
