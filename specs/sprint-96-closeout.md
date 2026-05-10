# Sprint 96 Closeout — Cleanup, Performance Pass, /beta Reorg

**Branch:** `feature/sprint-96-cleanup-and-perf` + 1 hotfix commit on `master` (`b26f28a`)
**Merged:** 2026-05-10
**Date:** 2026-05-09 – 2026-05-10
**Owner:** Claude

---

## Summary

Three parallel streams in one release: kill home-page playoff staleness, take the top performance wins, and move 19 routes under `/beta/` so the platform's surface stays focused while pages get reworked one at a time. Solo sprint, no Codex involvement.

---

## Shipped (in `master`)

### Stream A — Playoff home freshness

- **Round-aware tracker:** `SeriesTrackerStrip.pickTrackedSeries()` now filters to `status === "active"` only and sorts by round desc + combined wins desc. Closed/eliminated and scheduled series never appear; backfill across rounds is gone.
- **`LastNightPulse` replaces `StoryRail`** on `/` and `/playoffs`. Three game-driven tiles (Tonight's Headliner / Last Night's Hero / Series Momentum) computed from `PlayerGameLog` (last ~36h) + `PlayoffSeries.updated_at`. New service + endpoint + 4 tests. The old `StoryRail.tsx`, `getPlayoffStoryRail`, `PlayoffStoryTile`/`Response` types, `story_rail_service.py`, and `GET /api/playoffs/story-rail` are deleted end-to-end.
- **Cloudflare cache rule 1** expanded from `/api/playoffs/today` to a free-tier-friendly compound OR matching `/today`, `/bracket`, and `/last-night-pulse`. All three now bypass the edge so the home page reflects game completion within minutes (was up to 2 hours).
- **VM crontab** post-game cadence tightened from `*/30` to `*/15` during 21:00–05:30 UTC.
- **Hotfix `b26f28a`:** `_series_to_response` and `/today` post-pass now derive `status="active"` when the stored series is `"scheduled"` but observed wins > 0. Production R2 series rows persist as `"scheduled"` because the auto-advance flip-to-active logic only fires when a *parent* clinches; deriving in the response layer makes R2 series visible to the tracker without DB mutation. Caught during production smoke when the new active-only filter showed an empty tracker on a clearly-mid-progression bracket.

### Stream B — Performance pass

- **N+1 fixes in `routers/teams.py`:** `list_teams` is now one grouped LEFT-OUTER-JOIN + `GROUP BY` (was 1 + 30 queries). `team_roster` batches latest-`SeasonStat` lookups into one `IN (...)` query (was 1 + N).
- **Image optimization** on 5 components (`FavoritesList`, `PlayerHeader`, `MvpRacePanel` ×2, `HomeMvpTeaser`): dropped `unoptimized`, added explicit `sizes` attributes matching CSS containers. Headshot bytes drop from ~100KB to ~15-25KB per image.
- **Code-split Recharts** via `next/dynamic({ ssr: false })` on three tab-conditional charts: `LineupScatterPanel`, `StandingsBumpChart`, `ImpactScatterChart`. Recharts (~200KB gzipped) no longer ships with the initial route bundle on `/beta/lineups`, `/standings`, `/player-stats`.
- **`@next/bundle-analyzer`** wired behind `ANALYZE=1` for future audits.

### Stream C — `/beta` reorganization

- **19 directories moved** under `frontend/src/app/beta/` via `git mv` (history preserved): `ask`, `compare`, `coverage`, `draft`, `free-agency`, `games`, `insights`, `leaderboards`, `learn`, `lineups`, `metrics`, `milestones`, `mvp`, `picks`, `players`, `playoff-series`, `pre-read`, `teams`, `trade-machine`.
- **Kept at root:** `/`, `/playoffs`, `/bracket`, `/player-stats`, `/standings`, `/og`, `/admin/*`.
- **One-shot codemod** rewrote ~90 internal href / router / object-property path literals (then deleted). `frontend/next.config.ts` returns 308 redirects from every old path → `/beta/<path>` with `:path*` so dynamic sub-routes follow.
- **`NavLinks.tsx`** restructured: primary nav is Playoffs / (Bracket if playoffs) / Player Stats / Standings; the dropdown was renamed from "More" to "Beta" and lists all 19 moved routes alphabetized.
- **`frontend/src/app/beta/layout.tsx`** adds a one-line beta banner above moved surfaces.

### Verification

- **Backend tests:** 588 passing, +4 new for `last_night_pulse_service`. Pre-existing `test_daily_sync_post_game_dry_run` failure unchanged from master (DATABASE_URL env guard).
- **`npm run build`:** clean.
- **`npm run lint`:** 0 errors.
- **Production smoke (post-deploy):** all 4 R2 series correctly active in `/api/playoffs/bracket`; `/today` shows correct series records (PHI 0-2 NYK, SAS 2-0 MIN); old paths 308-redirect to `/beta/`; `cf-cache-status: MISS` on every hit for the three live endpoints (bypass cache working), `MISS → HIT → HIT` on `/api/playoffs/leaders` (rule 2's 2hr cache still works).

---

## Deferred

- **B5 — ISR/SSR conversion of keep-list pages** (`/player-stats`, `/standings`, `/playoffs`). **Why deferred:** different domain — full server-component refactors of high-traffic surfaces is the same kind of work as the per-page `/beta` graduation pattern Vivek wants to run sprint-by-sprint. Doing partial server refactors cross-cutting in this sprint contradicts that intent.

---

## Coordination Lessons

- **Solo-stream lock-table discipline still pays off.** Even with no Codex involvement this sprint, claiming `types.ts`, `api.ts`, `hooks/usePlayerStats.ts`, `routers/playoffs.py`, etc. up front made it obvious which file I was about to touch in each stream and prevented the codemod from accidentally rewriting a still-being-edited path. Worth keeping the discipline even on solo sprints.

## Workflow Lessons

- **Codemod patterns must cover bare path literals, not just `href=` and `router.push(`.** First codemod pass missed object properties (`{ href: "/teams" }`), template literals in `return_to`/`route_path` builders, and array-of-strings in `sitemap.ts`. Second pass added `(?<!/api)(?<!\w)["\`]/<route>` patterns with negative lookbehind to skip `/api/...` prefixes. Total ~90 sites needed rewriting; the first pass got ~70.
- **Live deploy revealed the real bug, local DB couldn't.** The "tracker shows eliminated teams" complaint *looked* like a code bug locally, but local DB only had R1 data. The actual production bug was upstream — R2 series rows persisting as `"scheduled"` despite real games played. Caught only after production smoke. Pattern: when a UI complaint depends on data freshness, verify against production state before assuming the fix is purely frontend.
- **Free-tier Cloudflare Cache Rules don't have `matches regex`.** The `infra/README.md` instructions originally said "URI matches regex"; had to walk the operator through `Edit expression` with `starts_with` OR-compounds instead. README has been updated; future operators won't hit that wall.

## Technical Lessons

- **`PlayoffSeries.status` drift between bracket-builder insert and game-completion update.** Round-(N+1) rows are inserted with `status="scheduled"` once both seeds are populated, but the only flip-to-`"active"` path is `_maybe_advance_clinched_series`, which fires when a *parent* clinches — never re-checks existing scheduled rows when a child series's first game is played. Fixed in the response layer this sprint; the persist-side fix (a small touch in the post-game sync to flip status when wins > 0) is a Sprint 97 candidate.
- **Cloudflare reports bypass-cache as `cf-cache-status: MISS`, not `BYPASS`.** Took an extra round of header inspection to realize repeated `MISS` on `/bracket` was the desired behavior, not a misconfigured rule. Worth noting in `infra/README.md` for future cache audits.
- **Image-optimization removal is a free quick win.** 5 `<Image unoptimized />` instances were a Sprint-2-era oversight that survived ~90 sprints. Worth periodically running `grep -rn "unoptimized" frontend/src --include='*.tsx'` as a low-effort audit.

---

## Next Sprint Seeds

1. **Persist `PlayoffSeries.status = "active"` flip on first game played.** Stream A hotfix derives this in the response layer; the right home is `_maybe_advance_clinched_series` (or a new helper) called from the post-game sync. Removes the runtime derivation.
2. **Graduate `/beta/lineups` to root** (or whichever beta page Vivek wants first). The pattern is: rework page-by-page, then `git mv beta/<page>` back to `app/<page>`, drop the redirect entry from `next.config.ts`, restore the primary nav link.
3. **B5 carryover — server-component refactor of `/player-stats`.** Highest-traffic surface, biggest perceived perf win. Server-component shell + client island for the filter/sort interactivity + `export const revalidate = 300`.
4. **Bundle analyzer audit.** Run `ANALYZE=1 npm run build` and document per-route chunk sizes. Low-hanging follow-ons: more `next/dynamic` candidates (Three.js scenes, heavy compose pages).
5. **Persist scoreboard live finals into `PlayoffSeries.top_wins/bottom_wins`** (or eliminate the denormalized cache entirely in favor of always-fresh GameLog counts). The Sprint 91 fresh-count pattern in `_series_to_response` works around the stale denormalization but it's a smell — remove the source of drift.

---

## Backlog Refresh

`specs/BACKLOG.md` updated this sprint:
- Removed: "code-split Recharts" (shipped), "remove `<Image unoptimized />` instances" (shipped), "N+1 fix on /api/teams roster" (shipped).
- Added: B5 keep-list ISR refactor; per-page graduation cadence; `PlayoffSeries.status` persist-side fix; bundle analyzer audit pass.
