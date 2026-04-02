# Sprint 27 Closeout

**Sprint:** 27
**Date:** 2026-04-01
**Owner:** Codex
**Status:** Final

---

## Shipped

- Upcoming schedule API: `GET /api/schedule/upcoming` backed by warehouse `games`
- Injury-aware team surfaces: `GET /api/teams/{abbr}/availability`, roster availability card on team pages, and pre-read availability summaries
- Pre-read deck contract expansion for structured team/opponent availability and next-game context
- Official NBA injury-report fallback when the live JSON feed returns 403
- Injury identity hardening: `player_name_aliases`, `injury_sync_unresolved`, alias-backed fallback resolution, and `GET /api/injuries/unresolved`
- `/api/injuries/current` now excludes `Available` rows; live smoke test on 2026-04-01 synced `159` rows with only `5` unresolved

## Deferred / Not Finished

- Standings history / trend line still needs a snapshot-oriented standings shape before a real last-30-days curve
- Shot zone analytics remains a separate sprint-sized product slice
- Compare-level injury awareness is still a follow-on after team pages and pre-read

## Coordination Lessons

- Shared contract files stayed low-risk because the sprint stayed single-stream
- `backend/main.py` needed the schedule router and schema bootstrap touched together during integration

## Workflow Lessons

- Live browser QA plus live backend smoke tests caught more truth than static route checks alone
- Local sandboxing blocks Postgres-backed smoke tests, so final local API verification may require approved out-of-sandbox commands

## Technical Lessons

- The NBA injuries JSON feed is not reliable from local IPs; the official injury-report page/PDF needs to remain a supported fallback path
- Alias-backed player identity resolution works immediately when derived from existing player rows, not only from freshly re-synced alias tables

## Next Sprint Seeds

- Finish the remaining unresolved injury rows with targeted roster/alias cleanup
- Add compare-side availability framing now that team and pre-read surfaces are live
- Add standings trend history once snapshot semantics are nailed down
- Build shot zone efficiency and side-by-side zone profile comparisons off persisted shot data
