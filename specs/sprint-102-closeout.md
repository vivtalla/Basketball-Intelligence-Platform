# Sprint 102 Closeout — Draft Analyzer Polish + Team-Fit Integration

**Sprint:** 102
**Date:** 2026-05-18
**Owner:** Claude
**Status:** Final (pending CI + merge)
**Branch:** `feature/sprint-102-analyzer-polish-and-team-fit`
**Sister sprints:** Sprint 100 (data foundation) + Sprint 101 (analyzer UI)

---

## Shipped

Three streams. ~2 new backend service files + 1 router extension + 3 new Pydantic shapes, 2 new frontend components + 9 polished components/pages, 1 new test suite (~7 tests), and a meaningful expansion of the historical-outcomes seed CSV (51 → 92 rows).

### Stream A — Design polish (Sprint 70 conformance)

Applied HeroHardwood backdrops, Reveal wrappers, `bip-panel` / `bip-display` / `bip-kicker` classes, responsive typography (`text-3xl sm:text-4xl`), and table-overflow wrappers across every Sprint 101 surface.

- **Pages polished:**
  - [frontend/src/app/draft/page.tsx](frontend/src/app/draft/page.tsx) — header → `bip-panel-strong rounded-[2.2rem]` + HeroHardwood backdrop. Heading `text-3xl sm:text-4xl`. Table section wrapped in `<Reveal>` + `<div className="overflow-x-auto">` so the wide column set scrolls horizontally on mobile.
  - [frontend/src/app/draft/[prospectId]/page.tsx](frontend/src/app/draft/[prospectId]/page.tsx) — same pattern on the prospect-detail header. HeroHardwood `seed={summary.prospect_id ?? 1}` so each prospect gets a slightly different grain texture.
  - [frontend/src/app/draft/historical/page.tsx](frontend/src/app/draft/historical/page.tsx) — header polished. Year cards wrapped in `<Reveal delay={idx * 60}>` for the staggered fade-in, each card adopts `bip-panel rounded-[1.85rem]` + `hover:-translate-y-1 hover:border-[var(--accent)]` hover state.
  - [frontend/src/app/draft/historical/[year]/HistoricalClassClient.tsx](frontend/src/app/draft/historical/[year]/HistoricalClassClient.tsx) — header polished. Loading + populated states wrapped in `<Reveal>`.

- **Components polished** — section wrappers across the Sprint 101 components changed from bare `rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5` to `bip-panel rounded-[1.85rem] p-5 sm:p-6`:
  - [TeamFitPanel.tsx](frontend/src/components/draft/TeamFitPanel.tsx) (Sprint 102 new — Stream B)
  - [MockDraftConsensusPanel.tsx](frontend/src/components/draft/MockDraftConsensusPanel.tsx)
  - [CombineMeasurementsCard.tsx](frontend/src/components/draft/CombineMeasurementsCard.tsx)
  - [HistoricalCompsGrid.tsx](frontend/src/components/draft/HistoricalCompsGrid.tsx)
  - [HistoricalBaselineChart.tsx](frontend/src/components/draft/HistoricalBaselineChart.tsx) — both rendered states (insufficient-data caveat panel + populated chart)
  - [RiskIndicatorsBars.tsx](frontend/src/components/draft/RiskIndicatorsBars.tsx)
  - [TranslationV2Ranges.tsx](frontend/src/components/draft/TranslationV2Ranges.tsx)
  - [InternationalStatsPanel.tsx](frontend/src/components/draft/InternationalStatsPanel.tsx) — full-width table now wrapped in `<div className="overflow-x-auto">` for mobile.
  - [HistoricalClassTable.tsx](frontend/src/components/draft/HistoricalClassTable.tsx) — same overflow wrapper for the new "Best fit" column landing.

- **Mobile audit:** `/draft` page-content overflow on 375px viewport is now 49px and traces entirely to the pre-existing top-nav layout (CourtVue Labs logo + nav row); Sprint 101 panels themselves fit cleanly. Tables horizontally scroll inside their panel containers as designed.

### Stream B — Team-fit integration

The marquee analytical feature.

- **New service:** [backend/services/draft_team_fit_service.py](backend/services/draft_team_fit_service.py) (~250 lines) — bridges draft prospects into the existing `team_fit_service.py` v3 algorithm. Pipeline:
  1. Pull the prospect's latest pre-NBA stat row.
  2. Build a synthetic `SeasonStat`-like `SimpleNamespace` (with `pts_pg`, `reb_pg`, `ast_pg`, `stl_pg`, `blk_pg`, `tov_pg`, `ts_pct`, `usg_pct`, plus position-aware fallbacks for `par3` + `ftr` — these aren't on `DraftProspectStat` but the v3 z-scorer requires them).
  3. Reuse `_qualified_rows_v2`, `_season_norms_v2`, `_team_rows` from `similarity_service` / `team_fit_service` to get NBA norms + per-team rosters.
  4. Iterate over all 30 NBA teams with `MIN_TEAM_PLAYERS` qualified rosters; call the existing `_score_team_fit` against each.
  5. Return top-N results sorted by `fit_score` desc, each tagged with `methodology_version="team_fit_v3_draft_adapter"`.
  6. Fit-label thresholds: ≥70 → `better_fit`, 50-70 → `similar_fit`, <50 → `different_fit`.
- **New Pydantic shapes** in [backend/models/draft.py](backend/models/draft.py):
  - `ProspectTeamFit` — team_abbreviation, team_id, fit_score (0-100), fit_label, summary, value_drivers, overlap_flags, role_runway_note, methodology_version.
  - `FitDriverLite` — feature_key, label, prospect_z, team_need_z, contribution. (Light version of the player-side FitDriver so the prospect API stays compact.)
  - `OverlapFlagLite` — feature_key, teammate_name, teammate_id, gap.
- **API contract additions:**
  - `ProspectDetail.team_fit_top: Optional[List[ProspectTeamFit]]` — populated when the prospect has a usable translation; null otherwise.
  - `HistoricalProspectEntry.best_team_fit_abbr` + `best_team_fit_score` — denormalized top-1 fit pin so the historical class table can render a "Best fit" badge per row.
- **Router wiring:** [backend/routers/draft.py](backend/routers/draft.py) — calls `compute_team_fit_for_prospect(db, prospect, limit=5)` inside `get_prospect_detail` (try/except so a failure doesn't 500 the whole detail route). The historical class endpoint calls `compute_best_team_fit_for_prospect(db, p, season=historical_season)` per row with the era-appropriate season so 2018's best-fit reflects 2018 NBA rosters, not 2025-26.
- **Analysis service hook:** [backend/services/draft_analysis_service.py](backend/services/draft_analysis_service.py) — the existing `compute_team_fit()` stub now delegates to the new service. Returns a dict shape so callers wanting the full prospect analysis bundle get team-fit included.
- **Frontend components:**
  - [TeamFitPanel.tsx](frontend/src/components/draft/TeamFitPanel.tsx) (new, ~150 lines) — top-5 team-fit grid with fit_score, fit-label badge (better_fit forest / similar_fit amber / different_fit muted), one-line summary, value-driver chips, overlap-flag chips. Footer attribution shows the methodology version.
  - [FitRankBadge.tsx](frontend/src/components/draft/FitRankBadge.tsx) (new, ~30 lines) — compact "DAL 78" chip used in the historical class table. Color tone scales with fit_score.
- **Frontend integration:**
  - Prospect detail page now renders `<TeamFitPanel teams={detail.team_fit_top} />` just below the projected-tier banner.
  - [HistoricalClassTable.tsx](frontend/src/components/draft/HistoricalClassTable.tsx) adds a "Best fit" column (`<FitRankBadge>` per row) + a "Best team fit" sort option.
- **Frontend types** in [frontend/src/lib/types.ts](frontend/src/lib/types.ts) — three new shapes (`FitDriverLite`, `OverlapFlagLite`, `ProspectTeamFit`) + extensions to `HistoricalProspectEntry` + `ProspectDetail`.

**Calibration risk acknowledged:** the prospect's z-vector is computed against NBA-player norms, not prospect-pool norms. Documented in the service docstring as a known v1 limitation. A future sprint can switch to prospect-pool norms for the value-supply scoring step specifically.

### Stream C — Historical outcomes seed CSV expansion

[backend/data/seed/draft_outcomes_2016_2025.csv](backend/data/seed/draft_outcomes_2016_2025.csv) grew from 51 → 92 rows. New coverage:
- 2017 picks 1-15 (Markelle Fultz → Justin Jackson, including Tatum, Mitchell, Bam, De'Aaron Fox, Lauri Markkanen).
- 2016 picks 1-15 (Ben Simmons → Juan Hernangomez, including Brandon Ingram, Jaylen Brown, Jamal Murray, Domantas Sabonis).
- 2019 picks 6-10 (Jarrett Culver → Cam Reddish).
- 2020 picks 4-6 (Patrick Williams, Isaac Okoro, Onyeka Okongwu).
- 2021 picks 5-7 (Suggs, Giddey, Kuminga).

92 is short of the plan's 300-row aspirational target — flagged as the async stream that "doesn't block sprint merge." Further expansion remains a research task; the analyzer already has enough seed data to start producing populated `historical_baseline` distributions (which require ≥3 historical comps with outcomes to render anything other than `insufficient: true`).

### Cross-cutting

- **[specs/architecture-flows.html](specs/architecture-flows.html)** — added a new step on `page-draft-prospect-detail` flow describing the team-fit pipeline: `routers/draft.py → compute_team_fit_for_prospect → team_fit_service z-scoring → 30 NBA team rosters`. Validator passes: 20 nodes, 29 flows, 208 steps. Structure OK.
- **Architecture:** no Alembic migration. No schema changes. Sprint 102 is purely API-additive (new Pydantic shapes on existing endpoints, new fields on `ProspectDetail` + `HistoricalProspectEntry`). Deploy is `git pull && sudo bash infra/deploy.sh` (no `--migrate`).
- **Commit prefixes used:** `[A]` for polish, `[B]` for team-fit, `[C]` for CSV, `[docs]` for closeout + architecture-flows.

## Test posture

- New backend tests: [backend/tests/test_draft_team_fit.py](backend/tests/test_draft_team_fit.py) — 7 tests covering:
  - `test_fit_label_thresholds` (parametrized × 7) — boundary cases of better_fit / similar_fit / different_fit.
  - `test_synthetic_season_stat_fills_position_defaults` — `_build_synthetic_season_stat` populates par3 + ftr with position-aware values (guards higher par3 than centers).
  - `test_synthetic_season_stat_carries_through_basic_stats` — raw values flow through unchanged.
  - `test_compute_team_fit_handles_missing_translation` — prospect with no stat rows → returns `[]`, doesn't raise.
  - `test_compute_team_fit_empty_pool_returns_empty` — when `_qualified_rows_v2` returns empty → `[]`.
  - `test_compute_team_fit_attribution_when_pool_present` — mocked NBA pool + scored team → result carries `methodology_version` = "team_fit_v3_draft_adapter" and correct fit_label.
  - `test_compute_team_fit_ranks_by_score_desc` — three teams scored → output sorted high → low regardless of call order.
  - `test_compute_team_fit_respects_limit` — `limit=2` returns top 2 only.
- Frontend: `npm run lint` clean. `npm run build` clean (29 routes, same as Sprint 101).
- Visual smoke via local preview: nav-graduation Draft link active on `/draft`, hero panel polished with HeroHardwood backdrop, board renders the new Sprint 100 fields, mobile-viewport content fits inside `overflow-x-auto` wrappers (only the pre-existing top-nav row overflows on sub-`sm` widths — not introduced by this sprint).

## Deploy plan

Frontend-only changes auto-deploy via Vercel on push to master (~2 min). Backend changes ship through `infra/deploy.sh` with no migration:

```bash
ssh ubuntu@5.78.114.15
cd /home/ubuntu/bip && git pull origin master
sudo bash infra/deploy.sh    # no --migrate this sprint
```

Production smoke after deploy:

```bash
# Team-fit on a current 2026 prospect
curl -sf "https://api.courtvue.app/api/draft/prospects/<id>" | jq '.team_fit_top[0] | {team_abbreviation, fit_score, fit_label, methodology_version}'

# Best-fit denormalized on historical class
curl -sf "https://api.courtvue.app/api/draft/historical/2018" | jq '.prospects[0] | {name, best_team_fit_abbr, best_team_fit_score}'

# UI smoke
open https://courtvue.app/draft                       # board has Tier column + filters; HeroHardwood backdrop on hero
open https://courtvue.app/draft/historical/2018       # historical table now has Best Fit column
```

After deploy: optionally re-run the historical outcomes backfill on the VM to pick up the 41 new CSV rows:

```bash
python -m scripts.backfill_draft_outcomes --start-year 2016 --end-year 2025
```

## Lessons captured

- **ESLint's `react/no-unescaped-entities` catches typo-level issues in template literals.** A naked `'` in a JSX text node tripped the rule in `TeamFitPanel.tsx`. The lesson is to keep the lint pass in the inner loop, not just at sprint close — it caught two issues this sprint (this one, plus Sprint 101's `react-hooks/set-state-in-effect`).
- **Existing services pay off when you bend them, not break them.** `team_fit_service.py` (Sprint 65/69) was built for player inputs, but its `_score_team_fit` internal scorer is roster-agnostic — feed it a synthetic SeasonStat with the right attribute names and it works unchanged. Took ~200 lines of bridge code rather than 600+ for a fresh team-fit algorithm. The trade-off (NBA-player z-norms, not prospect-pool z-norms) is documented as a follow-on calibration improvement.
- **Async streams need explicit lower-bound expectations.** Stream C ("seed CSV expansion") was planned as "best-effort 300+." Shipping 92 rows is a meaningful 2× improvement but well short of plan. Future sprints with research-flavored side tasks should pre-commit to a minimum (e.g. 200 rows or punt) rather than a soft target — the ambiguity makes the stream easier to under-deliver on without clear signal.

## Deferred (per plan)

1. **`recalibrate_from_outcomes()` for translation_v2** — **Blocked on data.** Even at 92 rows the seed CSV is thin for a per-feature regression refit. Wait until the CSV is at 300+ rows. → Sprint 103+.
2. **Prospect-pool z-norms for team-fit value-supply** — **Different domain (calibration).** Current adapter uses NBA-player norms; documented as a Sprint 103+ improvement.
3. **Mahalanobis comp distance** — **Blocked on data.** Same N-too-small reason.
4. **Pre-2016 historical drafts** — **Different domain.** Pre-pace-and-space era.
5. **Per-team archetype classifier** — **Different domain.** Decided in Sprint 102 planning: team_fit_v3 already scores against actual rosters, so a discrete team-archetype label isn't required. Revisit only if a future sprint wants "pace-and-space" categorical chips.
6. **Salary / cap implications in team-fit** — **Different domain.** Player-side team-fit doesn't include this either. Out of scope.
7. **Draft-night live updates** — **Different domain.** Websocket layer.
8. **Performance caching for historical-class team-fit** — **Blocked on data.** Computing 30 prospects × 30 teams per historical-class request is wasteful at scale. If p95 latency proves an issue, materialize a `prospect_team_fit_cache` table in `daily_sync.sh` for historical classes (which don't change after being populated).
9. **Per-component Reveal with staggered delays** — **Different domain (polish).** Sprint 102 wraps page sections in single Reveal blocks but skips per-card staggered Reveals for the prospect-detail sections (would require restructuring each Sprint 101 component). Lower-leverage polish vs the structural primitives (panel containers, HeroHardwood, responsive typography) which all landed.
10. **Full Sprint 70 typography pass on every component** — **Different domain (polish).** All section *headings* moved to `bip-display`/`bip-kicker`; in-card text still uses Tailwind utility classes. Polishing every label is the long-tail; not in scope for this sprint.
