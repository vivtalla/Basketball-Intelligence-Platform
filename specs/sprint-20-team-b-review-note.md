# Sprint 20 — Team B Review Note

Status: Final

## Scope Reviewed

- `GET /api/insights/trajectory`
- `backend/services/trajectory_service.py`
- `Insights` trajectory tracker UI

## Findings

- No blocking review findings.

## Checks Run

- `python -m py_compile backend/models/insights.py backend/services/trajectory_service.py backend/routers/insights.py backend/tests/test_trajectory_service.py`
- `pytest backend/tests/test_trajectory_service.py`
- `npm run lint`

## Notes

- The old year-over-year `Breakout Tracker` framing no longer drives the page; the new workflow is centered on recent-window deltas against an out-of-window baseline.
- The route stays constrained to `2025-26` and excludes undersampled players rather than manufacturing rankings.
