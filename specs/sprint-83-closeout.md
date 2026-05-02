# Sprint 83 Closeout — MVP Launch Readiness

**Sprint:** 83
**Date:** 2026-05-02
**Owner:** Claude
**Status:** Final

---

## Shipped

Three streams plus follow-ons. 472 → 480 backend tests (+1 net new). `npx tsc --noEmit` clean. `npm run build` succeeds.

### Stream A — Critical UX production blockers (`ec1e3ac`)
9 fixes across the highest-traffic surfaces, each as its own commit.

- **A1 — Leaderboards loading skeleton.** `app/leaderboards/page.tsx` returned `null` during SWR fetch → blank page. Replaced with an animated skeleton matching the page layout.
- **A2 + B5 — Mobile hamburger nav + secondary "More ▾" dropdown.** New `components/MobileNav.tsx` for `<sm`. At `sm+`, top-5 nav inline (Playoffs, Player Stats, Standings, Compare, Learn) plus "More" dropdown for the rest. `useSeasonPhase`-gated Bracket link preserved.
- **A3 — Team detail tab responsiveness.** 9 tabs become a native `<select>` on `<md`; pill row stays at `md+`.
- **A4 — Standings mobile.** Table no longer forces 600px column widths on phones. Mobile shows Rank/Team/W-L/Diff/Net/TS%/NET-Rk; rest hidden via `hidden md:table-cell`. "Tap a team for the full stat sheet" hint.
- **A5 — `app/not-found.tsx`.** Friendly 404 with browse-back links.
- **A6 — `app/error.tsx`.** Route-segment error boundary with `reset` action.
- **A7 — localStorage hardening.** Wrapped remaining `setItem`/`getItem` calls in `useFavorites`, `CustomMetricBuilder`, RegularHome in try/catch. Prevents crash in private/incognito mode.
- **A8 — Search dropdowns.** `max-h-[60vh] overflow-y-auto` on PlayerSearchBar, NavSearch, compare PlayerSlot. No more bottom-of-viewport overflow.
- **A9 — Onboarding kickers.** 1-line `bip-kicker` labels above Gravity, Archetype, Team Fit panels on PlayerDashboard so casual visitors aren't lost in jargon.
- **A10 — Audited only.** Team detail hooks already use tab-conditional null SWR keys. No deferral changes needed.

### Stream B — First-impression polish + SEO + analytics (`60059ec`)
7 fixes (B5 bundled into A2).

- **B1 + B8 — Home hero rewrite + mobile platform-card density.** Subtitle replaced with concrete affordances ("Search any NBA player, compare careers, track team rotations, build your own metrics. Built for front offices and serious fans."). 3-bullet kicker row added. `hidden sm:block` on platform-card descriptions so phones see icon + title only.
- **B2 + B4 — Home OG/Twitter metadata + Vercel Analytics.** Root layout `Metadata` export expanded with `title`, `description`, `metadataBase`, full `openGraph` and `twitter` blocks. `@vercel/analytics` mounted in root layout.
- **B3 — `app/robots.ts` + `app/sitemap.ts`.** Next.js dynamic helpers; robots allows everything except `/api/` and `/admin/`; sitemap enumerates 20 static routes.
- **B6 — Offseason empty-state on HomeLeagueLeaders.** When the season has no games, the empty 4-column grid is replaced with a "Between seasons" panel linking to `/milestones` and `/draft`.
- **B7 — Live ticker context label.** Sticky leftmost gold kicker over the marquee with fade-out gradient. Dynamic label: "Today's slate" when real games map; "Demo · Live scores" when falling back to demo data.

### Sprint 83-followup — Dynamic OG image (`2e9c0ef`)
- **`app/og/route.tsx`** — code-generated 1200×630 OG card via `next/og` `ImageResponse`. Uses the existing `courtvue-mark.svg` geometry inlined + brand palette (#201a16 / #fff9f1 / #21483b / #b4893d). Replaces the `/og-home.png` placeholder.
- Composition: hardwood-cream gradient + faint vertical grain + hairline border + "EST. 2025 / NBA INTELLIGENCE" kicker rule + brand mark + "CourtVue / LABS" wordmark + tagline + "courtvue.app · Front offices · Serious fans" footer.
- Tested: dev server returns 200 with `image/png` Content-Type, output is 1200×630 RGBA PNG (188 KB). Vivek flagged it needs more design polish — logged to BACKLOG as a Sprint 84 candidate.

### Stream C — Playoff surface polish (`2783b56`, merge `8509c03`)
6 fixes from Vivek's pre-close review walkthrough. One cohesive commit (4 items overlap heavily on `PlayoffCommandCenter.tsx`).

- **#1 Shot Diet Pressure copy.** Replaced "Where the math is being bent." with "How playoff defense is reshaping each team's shot selection." + grey explainer paragraph (rim/paint = attacking inside, 3PAr = spacing, FTr = drawing fouls).
- **#2 Lineup Chess empty state.** "Lineup Chess activates after ~25 possessions per 5-man group. Check back after Game 2 of the series."
- **#3 From the Desk → series CTA.** Replaced the decorative parchment blockquote in `BroadsheetHero` with a series-aware `<Link>` to `/bracket?series_id=X` when an active series exists. Static blockquote remains as fallback outside the playoff window.
- **#4 Four Factor Edge regular-season fallback.** `_build_metric_edges` returns `(metrics, top_using_rs_baseline, bottom_using_rs_baseline)`; when playoff `TeamSeasonStat` is missing, uses the regular-season row with deltas left null. `build_playoff_series_intelligence` appends per-team "Showing regular-season baseline; playoff-only sample not yet synced for {team}." warnings. `FourFactorsPanel` filters those warnings and renders a small grey caveat below the metric grid. Result: panel always renders 8 metrics. New test: `test_series_intelligence_falls_back_to_regular_season_baseline`.
- **#5 Story Rail tile deep-links.** Added `_resolve_player_active_series_href(db, player_id, season, team_abbreviation?)` helper. Wired into `_heat_check`, `_efficiency_desk`, `_x_factor`, and the streak/milestone branches — tiles now resolve the player's active playoff series and link to `/bracket?series_id={sid}`. `bracket/page.tsx` reads `searchParams.series_id` and pre-selects the series in `PlayoffCommandCenter`.
- **#6 SeriesCard per-game chip strip.** Horizontal G1–G7 chip strip below the series-state header on bracket cards. W/L coloring from top seed's perspective; muted dash for unplayed; full score line on hover. Compact home bracket strip unchanged.

### Post-merge lint cleanup (`930b045`)
Fixed 3 errors my changes introduced: `<a>` → `<Link>` in error.tsx, gradient string template literal in LiveTicker, removed unused eslint-disable.

---

## Deferred / Not Finished

- **VM deploy execution** — same hangover from Sprint 82. Code is fully ready; Vivek paused the manual VM steps after the Hetzner Cloud Console password issue. Self-contained 6-phase runbook (rescue mode → firewall → DNS → caddy-install → Vercel → WAF) sits in `specs/BACKLOG.md`.
- **OG image polish** — the dynamic `/og` route ships a serviceable but not bespoke card. Vivek flagged the typography/composition. Sprint 84 candidate documented in BACKLOG: load real site fonts into Satori, consider stat callouts + half-court silhouette, mark+wordmark integration, parameterize for per-page share cards.
- **Bracket auto-advancement** — when a series concludes 4-X, advance the winner into the next-round empty slot with "TBD" opponent until the parallel arm closes. Requires `parent_series_id` + `slot_position` columns on `PlayoffSeries` (Alembic migration) OR dynamic seed-pairing slot mapping. Real feature, not polish; deferred to Sprint 84.
- **Per-series detail page** — Vivek's "fully fleshed out tracker with stats of matchup so far, with options to click through the different games and their stats." Sprint 83c routes Story Rail tiles to `/bracket?series_id=X` (Playoff Command Center) which is largely that already; a more focused per-series page with player game-by-game stat tables and click-through to `/games/[gameId]` is a Sprint 84+ feature.
- **4 pre-existing lint errors** in `draft/page.tsx`, `draft/[prospectId]/page.tsx`, `trade-machine/page.tsx` — `react-hooks/set-state-in-effect` and `react/no-unescaped-entities`. Untouched by Sprint 83. Cleanup on the BACKLOG.

---

## Coordination Lessons

- **Worktree path whitelisting still bites.** Three of three implementation agents in 83a/83b/83c hit the same sandbox denial when running `git`/`pip`/`npx`/`pytest` against `/Users/viv/Documents/bip-s83*`. They did the file work correctly but couldn't commit or verify. Main session committed and ran tests on their behalf. **Future fix**: either pre-allow worktree paths in agent permissions or accept "agent stages, parent commits" as the operating model.
- **Per-item commit discipline cracked under overlapping diffs.** Stream 83a achieved one-commit-per-fix cleanly (9 commits). Stream 83b grouped logically (5 commits — items split by file). Stream 83c collapsed to a single commit because items #1, #2, #4, #5 all touched `PlayoffCommandCenter.tsx` with interleaved hunks; per-item splits would have required `git add -p` choreography that wasn't worth the time. Lesson: scope file-overlap *into* the commit-granularity decision at planning time.

## Workflow Lessons

- **The "audit before sprint" phase paid off again.** Sprint 83's Phase 1 explore (3 agents in parallel — home/SEO audit, production-readiness audit, signature-feature feasibility) delivered file:line punch lists that the implementation agents could execute without re-research. Maybe the highest leverage step in the entire workflow.
- **Plan-mode pivots stayed clean.** Vivek's mid-stream pivots — "this should be public not gated" (Sprint 82d) and "I have notes from the review" (Sprint 83c) — were absorbed as their own scoped streams without amending merged commits. Each pivot got a fresh branch, plan-file rewrite, and merge. Keeps history reviewable.

## Technical Lessons

- **Next.js `ImageResponse` is delightful for OG.** `frontend/src/app/og/route.tsx` is 195 lines of JSX that renders a 1200×630 PNG at request time. No design files, no CDN dance. The same pattern extends to per-page share cards via query params (Sprint 78 CF1's backend share-cards already exist; the frontend equivalent is now trivially possible).
- **`next/og` (Satori) supports inline SVG with limits.** The `courtvue-mark.svg` geometry — `<circle>`, `<line>`, `<path>` — renders cleanly inside `ImageResponse` JSX. Watch out for Satori's typography limits: only Inter by default; custom fonts require explicit buffer loading.
- **Mobile-responsive tables in Tailwind: `hidden md:table-cell` per column.** The standings table fix used per-column `mobile?: boolean` flags + class application to keep the header/row schemas in sync. Cleaner than maintaining separate mobile/desktop table components.
- **Localstorage requires defensive wrappers.** Safari/Firefox private browsing throws `SecurityError` on `setItem`. Three sites in the codebase weren't wrapped (others were). Audit was a `grep -rn "localStorage\.setItem" src/` away — should be a CI lint rule eventually.
- **One pre-existing flaky test:** `test_series_odds_monotonic_toward_winning_side` (Monte Carlo, no fixed seed) still flakes occasionally. Documented in Sprint 82 closeout; not fixed in 83. BACKLOG candidate.

## Next Sprint Seeds

1. **Execute the VM deploy** (Sprint 82+83 hangover). Self-contained runbook in BACKLOG. ~30-45 min of mostly web-UI clicks.
2. **OG image polish** — load real fonts, consider stat callouts, parameterize for per-page share cards.
3. **Bracket auto-advancement** — winner-advances logic + next-round empty-slot rendering.
4. **Per-series detail page** — fully-fleshed-out tracker with player game-by-game stats and `/games/[gameId]` click-through.
5. **Lint cleanup pass** — fix the 4 pre-existing errors in draft/ and trade-machine/, the flaky Monte Carlo test, and add `localStorage.setItem` to a defensive-wrapper lint rule.
6. **Tracking / hustle / passing dashboards** — third and fourth official data domains from the matrix. Mirror Sprint 81 B3 pattern.

## Backlog Refresh

- `specs/BACKLOG.md` Sprint 83 candidates list rewritten as Sprint 84 candidates: VM deploy (still pending), OG image polish (new entry from this sprint), tracking dashboards (carried), Spotrac retry (carried), award cohort expansion (carried), flaky test (carried). New entries: bracket auto-advancement, per-series detail page, lint cleanup pass.
