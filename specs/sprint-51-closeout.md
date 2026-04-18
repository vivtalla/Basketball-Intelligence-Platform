# Sprint 51 Closeout — MVP Gravity Foundation

Date: 2026-04-17  
Branch: `codex-sprint-51-mvp-gravity-foundation`  
Base: stacked on Sprint 50 MVP Context Map work

## Shipped

- Added Alembic revision `0005_player_gravity_context` for DB-first MVP context tables:
  - `player_play_type_stats`
  - `player_tracking_stats`
  - `player_hustle_stats`
  - `player_gravity_stats`
- Added official-data source helpers for Synergy play types, player tracking dashboard families, league hustle stats, and an NBA Inside the Game Gravity source spike.
- Added `gravity_sync_service.py` for persisted upserts and fallback proxy persistence when official Gravity is unavailable.
- Added `gravity_service.py` with CourtVue Gravity v1:
  - overall, shooting, rim, creation, roll/screen, off-ball, spacing lift, confidence, source note, and warnings
  - official NBA Gravity rows override CourtVue proxy rows when present
  - proxy rows remain labeled as derived and normalized 0-100
- Extended MVP payloads with `gravity_profile`, `context_adjusted_score`, and Gravity map coordinates.
- Added `GET /api/mvp/gravity?season=YYYY-YY&top=N` for lightweight Gravity leaderboard/context reads.
- Versioned the MVP scoring profile to `mvp_case_v2_gravity`.
- Updated `/mvp` with:
  - Gravity axis option in the case map
  - Box Score vs Gravity comparison strip
  - Gravity section in candidate case cards
  - methodology copy distinguishing official NBA Gravity from CourtVue proxy Gravity

## Deferred

- Scheduled production backfills for play-type, tracking, hustle, and gravity tables.
- Stronger parsing of the official NBA Gravity page if/when a stable structured payload is exposed.
- Calibration of CourtVue proxy Gravity against official NBA Gravity rows.
- Teammate-efficiency and lineup-with/without extensions to improve spacing-lift and off-ball components.
- Historical MVP Gravity trend snapshots.

## Verification

- `backend/venv/bin/python -m py_compile backend/data/nba_client.py backend/db/models.py backend/models/mvp.py backend/services/gravity_service.py backend/services/gravity_sync_service.py backend/services/mvp_service.py backend/routers/mvp.py`
- `backend/venv/bin/python -m pytest backend/tests/test_mvp_service.py backend/tests/test_gravity_sync_service.py backend/tests/test_schema_migrations.py -q`
- `backend/venv/bin/python -m pytest backend/tests/test_official_season_sync.py -q`
- `backend/venv/bin/python -m pytest backend/tests/test_warehouse_materialization.py -q`
- `../backend/venv/bin/python -m pytest tests/test_standings_route.py -q` from `backend/`
- `backend/venv/bin/python -m pytest backend/tests/test_shotchart_db_first.py -q`
- `npm run lint` from `frontend/`
- `npm run build` from `frontend/`
- `git diff --check`

## Notes

- The main MVP composite remains visible and unchanged in spirit. Gravity enters only through a capped `context_adjusted_score`, preventing the derived proxy from dominating.
- Official NBA Gravity is treated as optional persisted coverage. MVP reads never fetch NBA APIs directly.
- CourtVue proxy Gravity is explicitly labeled as derived and ships with confidence/warnings when source domains are missing.
