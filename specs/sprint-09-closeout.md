# Sprint 09 Closeout

**Sprint:** 09
**Date:** 2026-03-28
**Status:** Final

---

## Shipped

### Claude — Leaderboard enhancements + historical data
- **Career Leaders tab** — career averages ranked across all seasons; backed by `GET /api/leaderboards/career`
- **Team filter** — dropdown on Player Stats mode; backed by `GET /api/leaderboards/teams`
- **Multi-column table** — primary stat + Pts/Reb/Ast/TS%/PER/BPM context columns always visible
- **Stat tooltips** — `title` attribute on all column headers
- **URL state persistence** — deep-linkable via `useSearchParams`/`useRouter`; Suspense wrapper for Next.js App Router
- **Historical data pipeline** — `_historical_schedule_game_ids()` in `nba_client.py` using `data.nba.com` mobile schedule (avoids blocked `stats.nba.com`). Synced 2021-22 (633 players), 2022-23 (595), 2023-24 (595) — 1230 games each, ~12 min per season
- New Pydantic models: `CareerLeaderboardEntry`, `CareerLeaderboardResponse`; `LeaderboardEntry` enriched with context columns

### Codex — Team/PBP sync operations dashboard
- Coverage page season sync actions and team detail handoff from coverage to team page
- `TeamIntelligencePanel` improvements and lineup visibility enhancements

### Workflow hardening (Codex)
- Sprint-dependent work allocation table replaces permanent file ownership
- Explicit branch isolation rule — sprint work stays on sprint branch, never directly on `master`
- Sprint closeout checklist + `specs/CLOSEOUT_TEMPLATE.md`

---

## Deferred

- Historical PBP sync (2023-24, 2022-23 on/off + clutch stats) — `--pbp-only` not run; ~2-3h per season. Candidate for Sprint 10.
- Career tab `min_gp` slider — currently hardcoded to 15 GP per season minimum

---

## Coordination Lessons

- Sprint-dependent ownership is better than permanent file territories — enables each sprint to assign areas to whoever is doing that work
- Branch isolation rule needs to be explicit in AGENTS.md; agents should never commit sprint work directly to `master`
- Codex self-defining scope works well when Claude's scope is clearly bounded and shared files are claimed up front

## Technical Lessons

- `stats.nba.com` is completely blocked from this machine (even raw curl). All new data fetching must use CDN endpoints
- `data.nba.com/data/10s/v2015/json/mobile_teams/nba/{year}/league/00_full_schedule.json` is the reliable historical game ID source
- CDN box score (`liveData/boxscore/boxscore_{game_id}.json`) works for both current and historical seasons
- `useSearchParams()` in Next.js App Router requires a Suspense boundary — wrap the page content component

---

## Next Sprint Seeds

- Historical PBP sync for 2022-23 and 2023-24 (on/off, clutch, lineup stats)
- Player profile enhancements: contract/salary data, draft info display
- Leaderboard career tab: min_gp slider, seasons filter
- Compare page: add career arc tab using multi-season historical data now available
