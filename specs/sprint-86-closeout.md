# Sprint 86 Closeout — Complete Sprint 85 Follow-Ons + Team-Level Tracking/Hustle + OG Polish

**Sprint:** 86
**Date:** 2026-05-02
**Owner:** Claude (5 parallel streams; B + E via main session, A + C + D via subagents)
**Status:** Final

---

## Post-closeout hotfix (`1de57c5`, 2026-05-03)

Production users reported player profiles loading slowly. Root cause: 4 nba_client wrappers added in Sprint 85+86 (`get_player_tracking_dashboard`, `get_league_team_tracking_dashboard`, `get_league_hustle_player_stats`, `get_league_team_hustle_stats`) skipped the `_block_live_fetch_if_user_mode()` guard that Sprint 82d added to other methods. On production with `NBA_API_USER_FETCH_DISABLED=true`, user requests were triggering live `stats.nba.com` calls that took 6+ seconds (single player) or 30+ seconds (team — 12 calls per sync). The team-tracking hang OOM'd a worker; systemd auto-restarted but the gunicorn worker pool got saturated and `/api/players/*` requests queued up too.

**Fix:** added `_block_live_fetch_if_user_mode()` after the cache-miss check in all 4 wrappers (`backend/data/nba_client.py`). On user requests, sync attempts now raise `LiveFetchBlockedError` immediately → service catches → returns empty in <100ms. Verified post-deploy: tracking dropped 6.2s → 92ms (67× faster).

**QA gap that allowed this:** Phase 3 manual smoke walkthrough hit endpoints locally where the guard isn't active (`NBA_API_USER_FETCH_DISABLED` defaults to false in dev). They returned data. Production was the only place that triggered the bug.

**Workflow fix applied:** Pre-merge Verification Checklist (`AGENTS.md`) now includes "any new `nba_client` wrapper has `_block_live_fetch_if_user_mode()` after cache-miss check" so this class of regression can't recur.

---

## Shipped

First sprint operating under the new **Deferral Policy** (added at end of Sprint 85). Goal was to honor the policy by completing every Sprint 85 follow-on + team-level tracking/hustle (sister-feature) + OG polish (Sprint 83 carry) in one self-contained sprint, rather than letting them stack as a tail of half-baked work.

490 → 500 backend tests (+10 net new). `npm run build` clean. `npm run lint` 0 errors / 0 warnings (Sprint 85 baseline maintained).

### Stream A — Bracket auto-advance polish (`feature/sprint-86a-bracket-polish`)
Two related Sprint 85 follow-ons bundled because they share `playoff_series` data.

**A1 — Label richness:**
- Extended `PlayoffSeriesResponse` with 4 optional fields: `parent_top_seed`, `parent_bottom_seed`, `parent_top_team_abbrs`, `parent_bottom_team_abbrs`
- New `_resolve_parent_label_fields(db, parent_series_id)` helper in `routers/playoffs.py`
- Frontend `parentLabel()` in `SeriesCard.tsx` now renders "winner of 1v8 (OKC/HOU)" when parent is R1; falls back to "winner of {abbrs}" for R2+ parents (where seed math doesn't reduce cleanly)
- 2 new tests: response shape with parent populated, absent for R1

**A2 — Parent series backfill:**
- New `backend/data/backfill_playoff_parent_pointers.py` (idempotent CLI)
- Iterates closed series in seed order, computes child slot via newly-public `compute_next_round_slot()` (Sprint 85's helper, exposed publicly), sets child's `parent_*_series_id` if NULL
- 2 new tests: correctness on R1 close, idempotency on re-run
- **Production deploy step:** ran `./venv/bin/python data/backfill_playoff_parent_pointers.py --season 2025-26` against live VM. Result: `closed_seen: 2, updated: 0, skipped_child_missing: 2`. The 2 closed series (OKC-PHX, SAS-POR) don't yet have R2 child rows in the bracket — child rows will be created on the next nightly bracket sync, at which point parent pointers populate via the auto-advance close-transition path. Backfill is correct; nothing to backfill yet.

**Result in production:** bracket response now includes all 6 parent fields per series (`parent_top_series_id`, `parent_bottom_series_id`, `parent_top_seed`, `parent_bottom_seed`, `parent_top_team_abbrs`, `parent_bottom_team_abbrs`). Frontend TBD pills will render "winner of 1v8 (OKC/PHX)" format the moment any TBD slot exists.

### Stream B — Per-series detail page sortable columns (`feature/sprint-86b-series-detail-sort`)
- New `SortableHeader` component inside `SeriesPlayerLogTable.tsx` (kept inline; no shared extraction needed)
- `useState<SortKey>` + `useState<SortDir>` + `handleSort` toggle direction; `useMemo` sort comparator on `series_totals[sortKey]`
- 8 sortable stat columns (MIN, PTS, REB, AST, STL, BLK, TOV, +/-); FG/3P/FT remain non-sortable (composite values)
- Default: MIN desc (matches Sprint 85 behavior)
- Header text updated: "click any stat to re-sort" instead of "sorted by total minutes"

### Stream C — Team-level tracking + hustle dashboards (`feature/sprint-86c-team-tracking-hustle`)
**Bigger than originally scoped** — neither ORM models nor nba_client wrappers existed. Built the full stack:

**Backend:**
- New Alembic migration `0022_sprint86_team_tracking_hustle.py`: `team_tracking_stats` + `team_hustle_stats` tables mirroring `player_*` columns with `team_id` FK. Defensive `_has_table("teams")` guard for SQLite legacy-baseline path (Sprint 85 lesson). Reversible.
- New ORM classes `TeamTrackingStat` + `TeamHustleStat`
- New nba_client wrappers — but the team-level NBA API surface differs from player-level:
  - `get_league_team_tracking_dashboard()` issues 5 `LeagueDashPtStats` calls (per `pt_measure_type`: Drives, CatchShoot, PullUpShot, PaintTouch, Possessions) for shots family + 1 call for passing + 6 `LeagueDashPtTeamDefend` calls (per defense_category bucket) for shot defense — 12 total per sync, each rate-limited
  - `get_league_team_hustle_stats()` calls `LeagueHustleStatsTeam` (matched plan)
- New sync functions `sync_team_tracking_stats` + `sync_team_hustle_stats` in `gravity_sync_service.py`
- New services `team_tracking_service.py` + `team_hustle_service.py` (cache-first, sync-on-miss)
- 2 new routes: `GET /api/teams/{abbr}/tracking` + `GET /api/teams/{abbr}/hustle`
- 6 new tests in `test_team_tracking_hustle.py` (was 2 minimum; agent over-delivered)

**Frontend:**
- New `TeamTrackingPanel.tsx` (3 family toggle: Shot Creation / Passing / Shot Defense)
- New `TeamHustlePanel.tsx` (single 8-tile grid)
- Mounted in the team detail page's analytics tab alongside `TeamAnalyticsPanel`, `TeamNetRatingChart`, etc.
- Append-only additions to `lib/api.ts` (`getTeamTracking`, `getTeamHustle`) and `lib/types.ts` (`TeamTrackingResponse`, `TeamHustleResponse`)

**Production smoke verified:** both endpoints return 200 with real data.

### Stream D — OG image polish (`feature/sprint-86d-og-image-polish`)
Carried since Sprint 83. Full rewrite:

- `frontend/src/app/og/route.tsx` rewritten 190 → ~770 LOC with 5 per-type renderers (`renderHomeCard`, `renderPlayerCard`, `renderTeamCard`, `renderSeriesCard`, `renderMvpCard`) sharing a `CardShell` (hardwood backdrop + half-court silhouette + hairline frame) and `FooterStrip`
- Custom font loading via `tryReadFontAnyExt()` helper that prefers `.woff2` and falls back to `.ttf` — Source Serif 4 Bold + Source Sans 3 Regular/Bold downloaded into `frontend/public/fonts/` (TTF files from Google Fonts CDN, ~660 KB total)
- Per-page `generateMetadata` wired up via sibling `layout.tsx` files for the 3 client-component pages (team, playoff-series, mvp); player page already a server component so metadata edited in place
- Each per-type renderer fetches data server-side from existing API endpoints
- Vercel edge-caches each OG response by URL — first request slow, subsequent instant

**Production smoke verified:** `/og` returns 200 + `image/png`; `/og?type=player&id=1628983` returns 200 + `image/png`.

### Stream E — Cache rule tuning + deferral audit (`feature/sprint-86e-cache-deferral-audit`)
Doc-only commit:
- Updated `infra/README.md` cache rule documentation: rule 4 broadened from `/api/players/*/splits` to a regex covering `(splits|play-types|tracking|hustle)` for both `/api/players/*/...` and `/api/teams/*/...`. Free tier still at 5-rule cap; explained the broadening strategy for future endpoint additions.
- Dropped Spotrac retry-on-empty from BACKLOG entirely. Production logs (7 days, 42K lines) showed 0 matches for Spotrac/empty-team errors — the conditional sketch was never needed.
- Award calibration cohort expansion: applied the new Deferral Policy explicitly. Added `Why deferred:` annotation ("Blocked on data we don't have yet — historical NBA voting data 2008-09 + DPOY/MIP/6MOY ballots"). Documented data acquisition path (basketball-reference scrape OR ~3hr manual CSV editing) and noted it's not sprint work.

**Cloudflare cache rule update:** Vivek's manual UI change (free-tier rule limit prevents automation). Documented expressions in `infra/README.md` for the next session that touches Cloudflare config.

### Phase 6 fix (`3e09de7`)
Schema migration test pinned to `0021_sprint85_bracket_advance` from Sprint 85; bumped to `0022_sprint86_team_track_hus` after Stream C's migration landed. One-line fix.

---

## Deferred / Not finished

**Per the new Deferral Policy** — the only legitimate Sprint 86 deferral:

### Award calibration cohort expansion
**Why deferred:** Blocked on data we don't have yet. Requires sourcing historical NBA voting data back to 2008-09 (~80 ballot rows + DPOY/MIP/6MOY ballots). Per the Deferral Policy section 1 ("Blocked on data we don't have yet"), this qualifies. Implementation work is ~2-3 hr but only after data is sourced.

**Acquisition path documented in `specs/BACKLOG.md`** with 2 options (basketball-reference scrape OR manual CSV editing). Recommended: manual CSV editing as a one-shot task whenever motivated; no sprint allocation needed.

**Everything else shipped.** No "polish for Sprint 87" items. No "follow-on" tail.

---

## Coordination Lessons

- **The sandbox issue is fully formalized now.** All 3 subagents (A, C, D) hit the same denial pattern — couldn't run pytest/npm/python against worktree paths. The Sprint 86 stream prompts called this out up front ("subagent stages, parent commits") and all 3 agents followed it cleanly. **The pattern is now standard operating procedure** — don't ask agents to verify in sandboxed environments.
- **5-stream sprint shape worked well.** Streams B + E (small) ran via main session in parallel with A + C + D (subagents). Total wall-clock for the parallel chunk was ~10 minutes of agent execution + ~30 minutes parent integration/verification/deploy. The "small streams in main session, big streams in subagents" split is efficient.
- **Lock table claims continue to hold up.** Streams A and C both edited `frontend/src/lib/types.ts` (append-only) — zero conflicts. Streams C and D both edited `frontend/src/app/teams/[abbr]/page.tsx` — D added a sibling `layout.tsx` and C edited `page.tsx`, so no overlap. No merge conflicts at all this sprint (Sprint 85 had 3).
- **First Deferral Policy enforcement worked.** Pre-policy, the natural Sprint 86 plan would have been "ship 60% and defer the rest." Under the policy, 5 of 7 deferred items had no good deferral reason and were scoped into the sprint upfront. The 1 legitimate deferral (Award calibration) has a clean `Why deferred:` annotation for future reference.

## Workflow Lessons

- **The Deferral Policy + Phase 1 scoping rule prevented the natural "60% MVP" trap.** When I sat down to plan Sprint 86, the easy path was: ship the 4 small Sprint 85 follow-ons + drop OG polish for "later" + scope team tracking down to "just the player-side that already exists." The policy forced the harder + better path: scope the FULL features into the sprint upfront, accept a longer sprint, ship complete work.
- **Subagent prompts referencing the plan file work well.** Each Stream A/C/D prompt pointed at `~/.claude/plans/zazzy-swimming-pebble.md` for the full spec rather than re-explaining inline. Saved tokens and kept the prompts focused on operational rules (worktree, files-to-touch, lock-table claims, no-commit rule).
- **Phase 6 still surfaces real bugs.** Sprint 85 surfaced two latent infra bugs in deploy.sh; Sprint 86 surfaced the schema test pin (one-line fix). The new workflow's Phase 3 → Phase 6 sequence catches things that would otherwise leak to production silently.
- **Production deploy of `--migrate` is now a stable path.** Sprint 86 was the second use of `infra/deploy.sh --migrate` since the Sprint 85 fixes. Worked first time, no re-deploys needed. The deploy script is mature.

## Technical Lessons

- **Team-level NBA API endpoints differ in shape from player-level.** Player-side `playerdashptshots/pass/shotdefend` return all splits in one response per family. Team-side `LeagueDashPtStats` requires one call per `pt_measure_type` (5 measures for shots) and `LeagueDashPtTeamDefend` requires one call per defense distance bucket (6 buckets) — 12 calls total to get equivalent coverage. The sync function batches them with the standard 0.6s rate limit.
- **Google Fonts CSS serves different formats based on User-Agent.** Without a browser UA, Google returns `.ttf` (smaller spec, no subsetting). With a real browser UA, returns `.woff2` (smaller files, with unicode-range subsets). For server-side OG generation, `.ttf` is fine (Satori accepts both), and the lack of subsetting is acceptable for the 100-200 chars of brand text.
- **Next.js client-component pages can't export `generateMetadata`.** Workaround: add a sibling `layout.tsx` that exports `generateMetadata`. Worked cleanly for the team / playoff-series / mvp pages.
- **`compute_next_round_slot` exposed publicly.** Sprint 85 made this a private `_compute_next_round_slot` helper inside `playoff_bracket_service.py`. Sprint 86's backfill script imported it, so it's now public (with the `_` version kept as backward-compat alias). Lesson: when writing a private helper, consider whether a follow-on script will need it.
- **Backfill scripts need the same env-loading pattern as deploy.sh.** Sprint 85's `set -a; source /etc/bip/env; set +a` pattern is now standard for any one-shot script that reads `DATABASE_URL`. Documented in the plan; worked first try in production.

## Next Sprint Seeds (Sprint 87)

There are no obvious follow-on items from Sprint 86. The deferred Award calibration is data-blocked, not code-blocked. Likely Sprint 87 candidates from the broader BACKLOG (not from Sprint 86):
- Visualization Follow-Ons (Sprint 31 seeds) — long-standing
- Methodology Calibration second-wave items
- Canonical Event Completeness backfill — still on the long-term BACKLOG

These need Vivek's prioritization. AGENTS.md is reset to "Sprint 87 — TBD awaiting kickoff" with no implicit follow-on tail.

## Backlog Refresh

Removed (shipped in Sprint 86):
- Bracket auto-advance frontend label richness
- Backfill `parent_*_series_id` on existing closed series
- Per-series detail page sortable columns
- Team-level tracking + hustle dashboards (player-side already shipped Sprint 85; team-side Sprint 86)
- Polish the home OG image (per-page parameterization shipped too)

Removed (non-issue):
- Spotrac retry-on-empty (0 production errors in 7 days; never needed)

Annotated with `Why deferred:`:
- Award calibration cohort expansion (data dependency)

Carried (long-term backlog, not Sprint 85/86 follow-ons):
- Canonical Event Completeness, Alias Backfill, Migration Adoption Discipline, Legacy Compatibility Retirement, Shot Lab Court Geometry Polish, Replay Workflow Follow-Ons, Visualization Follow-Ons, Team Prep Queue Follow-Ons, Team Shooting Split Workflow Expansion, Methodology Calibration second-wave, Archetype Peer-Pool Composition Explainer, Brief Deep-Link Banners.

The "Sprint 86 Candidates" section header in BACKLOG should be removed since all eligible items shipped or were dropped — only the data-blocked Award calibration entry remains.
