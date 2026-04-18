# Sprint 50 Closeout — MVP Context Map

Date: 2026-04-17  
Branch: `codex-sprint-50-mvp-context-map`

## Shipped

- Expanded the MVP case payload with award eligibility, opponent-quality splits, support-burden context, optional external impact coverage, and visual map coordinates.
- Added award eligibility derivation from game logs using 65 qualified games, 20-minute thresholds, and up to two 15-20 minute near-miss games.
- Added `GET /api/mvp/context-map` for lightweight map coordinates and quick evidence.
- Rebuilt `/mvp` around a new MVP Case Map with axis controls, bubble sizing by availability/minutes load, momentum color, and candidate quick evidence.
- Extended candidate cards, case detail sections, methodology copy, and the home MVP teaser with eligibility and context signals.

## Deferred

- Official player split dashboards, official play-type dashboards, tracking/hustle/passing dashboards, and external all-in-one metric imports remain follow-ons.
- Second-chance and fast-break scoring now has a PBP-derived fallback, but it should be replaced or calibrated if official play-type/tracking sources are persisted.
- Historical MVP rank movement and daily snapshot persistence remain future work.

## Verification

- `pytest backend/tests/test_mvp_service.py -q`
- `pytest backend/tests/test_official_season_sync.py -q`
- `pytest backend/tests/test_warehouse_materialization.py -q`
- `PYTHONPATH=backend pytest backend/tests/test_standings_route.py -q`
- `npm run lint`
- `npm run build`
- Local database smoke for `build_mvp_context_map(db, season="2025-26", top=3)` returned Nikola Jokic as the first context-map point with eligibility and quick evidence.

## Next Sprint Seeds

- Persist official player splits and/or official play-type dashboards behind DB-first read paths.
- Add an NBA gravity metric layer: start with transparent local proxies for shooting gravity, rim gravity, creation gravity, and off-ball attention, then replace or calibrate them when official tracking/play-type data is persisted.
- Add MVP movement snapshots so the case map can become a timeline race.
- Add head-to-head “voter room” comparison for two or three candidates using the new context fields.
