# Sprint 55 Closeout — Shot Lab Intelligence

## Summary

Sprint 55 turned Shot Lab from a rich visualization suite into a scouting-ready intelligence surface. The sprint shipped a DB-first `shot_quality_v1` layer that separates shot diet, expected shot quality, actual shot making, proxy-labeled creation context, scouting identity, and coverage/trust state across player, compare, and team-defense surfaces.

Branch: `codex/sprint-55-shot-lab-intelligence`

## Shipped

- Added an on-demand Shot Lab intelligence service that computes expected FG%, expected eFG%, expected PPS, actual results, and actual-minus-expected deltas from persisted `PlayerShotChart` JSON plus enriched warehouse context.
- Added fallback smoothing from exact context bins to zone/distance/value, zone/value, shot value, and league-season baselines so sparse samples degrade honestly.
- Added player endpoints:
  - `GET /api/shotchart/{player_id}/quality`
  - `GET /api/shotchart/{player_id}/creation`
  - `GET /api/shotchart/{player_id}/identity`
  - `GET /api/shotchart/{player_id}/coverage`
- Added team-defense parity endpoints under `GET /api/shotchart/team-defense/{team_id}/...`.
- Added additive Pydantic and TypeScript contracts for quality, creation, identity, methodology, and coverage responses.
- Added SWR hooks and API helpers for player and team-defense shot intelligence.
- Added a reusable `ShotIntelligencePanel` for Quality, Making, Creation, and Scout Summary displays.
- Upgraded player Shot Lab with intelligence-first views while preserving scatter, heat, hex, value, sprawl, 3D, zone, distance, action, and context views.
- Upgraded Compare Shot Lab with side-by-side Quality, Making, Creation, and Scout Summary views using shared filters.
- Upgraded Team Defense Shot Lab with opponent shot quality allowed, opponent making allowed, allowed creation profile, and defensive shot identity.
- Extended Shot Lab snapshot metadata with intelligence view, coverage state, methodology version, and split mode.
- Added and tracked the planning inputs:
  - `specs/shot-chart-synopsis-sprint-planning.md`
  - `specs/shot-lab-intelligence-sprint-spec.md`

## Deferred / Follow-Ons

- Persisted expected-shot baseline tables or materialized jobs if on-demand baseline reads become too slow at larger coverage.
- Official tracking-grade shot quality inputs such as defender distance, touch time, dribble count, true shot clock, and contest level.
- Official assisted/self-created classification rather than proxy labels from action and linked-event context.
- Full operational coverage dashboard for shot intelligence freshness and backfill status.
- Deeper replay handoffs from selected quality/making/creation bins into example possessions.
- More precise court geometry and richer hover/tap affordances for the new intelligence views.

## Verification

- `backend/venv/bin/python -m py_compile backend/models/shotchart.py backend/services/shot_intelligence_service.py backend/routers/shotchart.py`
- `backend/venv/bin/python -m pytest backend/tests/test_shotchart_db_first.py -q`
  - `24 passed`
- `backend/venv/bin/python -m pytest backend/tests/test_schema_migrations.py -q`
  - `2 passed`
- `npm run lint`
- `npm run build`
- `git diff --check`

## Workflow Notes

- Python 3.8 remains active in the backend venv; backend/Pydantic annotations must avoid `X | Y` syntax.
- Route ordering matters in `shotchart.py`: team-defense intelligence routes and player intelligence routes must stay above the generic `/{player_id}` route.
- Reusing a single intelligence panel kept player, compare, and team-defense parity manageable.
- On-demand baselines were the right Sprint 55 default because they avoided a migration while keeping the methodology honest and testable.

## Next Sprint Seeds

- Add a Shot Intelligence Ops section to `/coverage` for baseline freshness, stale players, partial linkage, and backfill actions.
- Add “show me examples” replay handoffs from Quality/Making/Creation bins into Game Explorer.
- Materialize season-level expected-shot baselines if profiling shows repeated on-demand reads are too expensive.
- Push the shot identity framework into player cards, compare summaries, and team prep surfaces.
