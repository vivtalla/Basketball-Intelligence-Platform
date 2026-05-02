# Sprint 82 Closeout — Public Platform + Player Depth + Scraper Hardening

**Sprint:** 82
**Date:** 2026-04-30
**Owner:** Claude
**Status:** Final

---

## Shipped

Four-stream sprint (A → B → C in parallel + a follow-on D for public mode). 479 backend tests (was 464, +15 net new). `npx tsc --noEmit` clean.

### Stream A — Player splits + play-type UI (commit `f8c6b89`, merge `b0ca6be`)
- `frontend/src/components/PlayerSplitsPanel.tsx` (new) — official NBA split stats with family toggle (Location, Win/Loss, Days Rest, Month, Pre/Post All-Star) and 18-column stat table with W%/+/- color coding.
- `frontend/src/components/PlayTypePanel.tsx` (new) — Synergy play-type breakdown with inline possession share bars, PPP and league percentile coloring.
- Wired into `PlayerDashboard` between `<SeasonSplits />` and `<PerformanceCalendar />`, regular-season only.
- Types + API + hooks added to `lib/types.ts`, `lib/api.ts`, `hooks/usePlayerStats.ts`. Closes the Sprint 81 deferred frontend work for `/api/players/{id}/splits` and `/api/players/{id}/play-types`.

### Stream B — Public hosting infra (commit `2a3b964`, merge `f86d69e`)
- `infra/bip-api.service` — systemd unit running gunicorn + 2 uvicorn workers on `127.0.0.1:8000` (loopback only).
- `infra/Caddyfile` — reverse proxy with auto-HTTPS via Let's Encrypt + security headers + JSON access logs.
- `infra/caddy-install.sh` — one-time bootstrap (apt repo, Caddyfile copy, service enable).
- `infra/deploy.sh` — idempotent post-git-pull script (pip install, alembic upgrade, caddy reload, health check).
- `infra/playwright-install.sh` — one-time Chromium install for the PST scraper.
- `infra/README.md` — full deployment runbook.
- `gunicorn==23.0.0` added to `backend/requirements.txt`.

### Stream C — Scraper hardening (commit `453e62b`, merge `82f677a`)
- `backend/data/scrapers/_base.py` — new `PlaywrightScraper` base class with ImportError guard, user-agent rotation, viewport spoofing, `wait_until="networkidle"` for Cloudflare JS challenges, ScraperError wrapping on timeout/crash.
- `backend/data/scrapers/prosportstransactions.py` — switched from `HttpScraper` to `PlaywrightScraper` (2-line change). All parsing logic unchanged.
- `backend/data/scrapers/sportsreference_cbb.py` — fixed URL from `-per-game.html` (404) to `-leaders.html`. Rewrote parser to target `div#leaders_pts_per_g` blocks with `<span class="who">` + `<span class="value">` structure. Added BeautifulSoup Comment fallback for SR's HTML-comment anti-scrape wrapping. New `_fetch_player_profile_stats()` follows individual player profile links to get full stat lines (RPG, APG, FG%, etc.) for each top-N prospect.
- `playwright>=1.40.0` added to `backend/requirements.txt`.
- 3 new tests in `test_pst_scraper.py` (success, timeout, generic exception). 3 new tests in `test_sportsreference_scraper.py` (leaders parser, comment-wrapping, low-PPG filter). All 24 scraper tests pass.

### Stream D — Public mode follow-on (commits `aa3ab85`, `6cd3a51`, `b16012c`, merge `3664f56`)
Vivek pivoted mid-sprint from "FO-only basicauth" to "fully public read-only." Sprint 82d implements the three changes that pivot requires:

**D1 — Infra (`aa3ab85`).** Dropped Caddy `basicauth` block. `api.courtvue.app` now reads real client IP from `CF-Connecting-IP` (Cloudflare proxy header). Updated `infra/README.md` with public-mode runbook including Cloudflare WAF rate-limit rule (100 req/10min per IP → managed challenge), bot blocks, and cache rules tuned to nightly cron cadence (5min default, 30min playoffs, 1h standings, 6h leaderboards, 12h splits).

**D2 — Backend NBA API isolation (`b16012c`).** New env flag `NBA_API_USER_FETCH_DISABLED` (defaults false). When true, `nba_client` raises `LiveFetchBlockedError` on cache miss instead of calling `stats.nba.com`. Wrapped the 3 uncached user-facing methods (`get_career_stats`, `get_team_game_log`, `get_player_info`) with cache-first + guarded-fetch. `stats_service` and `team_net_rating_service` catch the error and return graceful empty responses. `daily_sync.sh` explicitly exports the flag to false at the top so cron always fetches normally regardless of `/etc/bip/env`. 7 new tests in `test_user_fetch_guard.py`.

**D3 — Frontend attribution (`6cd3a51`).** New `frontend/src/lib/external-metrics.ts` is the single source of truth for LEBRON, RAPTOR, EPM, PIPM, RAPM full names, sources, and URLs. New `<ExternalMetricsAttribution>` component with `footer` and `banner` variants. Fixed three under-attributed surfaces:
  - `StatTable.tsx` Advanced view: `°` superscript + hover tooltips on external metric column headers, footer legend with clickable source links.
  - `CustomMetricBuilder.tsx`: dropdown options now read `EPM · Dunks & Threes`; prominent amber banner appears above the formula whenever an external metric is referenced.
  - `ComparisonView.tsx`: replaced buried single-line disclaimer with the centralized component; advanced rows get column tooltips.

---

## Deferred / Not Finished

- **VM deploy execution** — all infra files are merged but Vivek hit a Hetzner Cloud Console password issue and parked the VM steps for later. The runbook in `infra/README.md` walks through Caddy install, env config, service start, Vercel import, and Cloudflare DNS+WAF setup. Recommended path for SSH recovery is Hetzner rescue mode (boot rescue OS with SSH key injected via Cloud UI, then mount `/mnt/` and append the key to `/mnt/home/ubuntu/.ssh/authorized_keys`) — sidesteps the VNC password fight entirely.
- **Cloud domain registration** — `courtvue.app` not yet purchased.
- **Vercel project import** — not yet created.
- **Spotrac retry-on-empty** (Sprint 82c stretch) — not implemented; the existing 65% scrape coverage was acceptable. Worth revisiting only if production runs show repeated LAL/CHI empties.

---

## Coordination Lessons

- **Worktree path whitelisting matters.** Two of three implementation agents (82a, 82c, 82d both backend and frontend) reported sandbox denials when running `git` against `/Users/viv/Documents/bip-s82*`. The agent did the file work correctly but couldn't commit. The main session had to commit on its behalf. For future parallel-stream sprints, either pre-allow the worktree paths in the agent context or have agents return staged-but-uncommitted state by design.
- **Mid-sprint pivot worked cleanly.** Sprint 82's plan landed FO-gated hosting, then Vivek changed to public read-only. Sprint 82d as a follow-on (rather than amending the merged 82b commit) kept history clean and made the pivot reviewable.

## Workflow Lessons

- **Plan-then-execute parallelism scaled well.** Three Plan agents in parallel produced execution-ready specs that engineer agents could implement without re-research. Token cost was about 4x a single-stream sprint but wall-clock was about 0.7x.
- **Test infrastructure assumed pre-installed dependencies.** Sprint 82c added `playwright` to `requirements.txt` but the local backend venv hadn't installed it. Required a manual `pip install` in the venv before running the scraper test suite. CI would have hit the same gap. Future sprints that add new pip deps should auto-install before running tests, OR include a setup step in the implementation prompt.

## Technical Lessons

- **Late-import for env-flag guards.** `nba_client._block_live_fetch_if_user_mode()` uses `import config; getattr(config, "NBA_API_USER_FETCH_DISABLED", False)` rather than `from config import ...`. The module-attribute lookup is required for `monkeypatch.setattr("config.NBA_API_USER_FETCH_DISABLED", True)` to take effect — a bound name from `from config import ...` would have been frozen at first import.
- **Playwright sync API plays well with cron.** No asyncio coordination needed; the context manager opens/closes a fresh Chromium per call, ~0.5s overhead per page. For ~40 paginated PST pages with 2.5s rate-limit delays, the per-call browser cycle cost is negligible.
- **Sports Reference's anti-scrape wrapping is consistent.** Both the leaders page (`div#leaders_pts_per_g`) and individual player profile pages (`table#players_per_game`) wrap their target elements in HTML comments. The same `BeautifulSoup.find_all(string=Comment)` + nested re-parse pattern handles both.
- **One pre-existing flaky test:** `test_series_odds_monotonic_toward_winning_side` (Monte Carlo simulation, no fixed seed). Passes in isolation, occasionally fails in the full suite due to RNG variance. Not a Sprint 82 regression. Worth fixing the seed in a future sprint.

## Next Sprint Seeds

1. **Execute the Sprint 82b VM deploy** when Vivek is ready. Rescue-mode SSH recovery is the recommended path (avoids VNC password issues entirely).
2. **Tracking / hustle / passing dashboards** — the third-and-fourth official data domains from `specs/official-data-source-matrix.md`. Mirror the Sprint 81 B3 pattern (new tables + sync + endpoints + frontend in a follow-up sprint).
3. **Spotrac retry-on-empty** — only worth doing if production logs show repeated LAL/CHI empties after Sprint 82b deploys.
4. **Award calibration cohort expansion** — extend `award_voting_seed.csv` backward to 2008-09 if LOO-CV Spearman fails to clear 0.7 in production. Add DPOY/MIP/6MOY ballot rows for parallel calibration.
5. **Fix the flaky `test_series_odds_monotonic_toward_winning_side`** — pin the RNG seed.

## Backlog Refresh

- `specs/BACKLOG.md` updated: Sprint 82 candidates section rewritten — public hosting, player splits/play-types frontend, and PST/SR scraper fixes all moved out of the candidate list. Public-mode infra noted as merged-but-not-deployed; tracking dashboards and Spotrac retry remain open. New entry: "Execute pending VM deploy" with the rescue-mode escape hatch documented.
