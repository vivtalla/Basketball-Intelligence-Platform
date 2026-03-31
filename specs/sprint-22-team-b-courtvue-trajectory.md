# Sprint 22 — Team B CourtVue Trajectory

## Goal

Turn `/insights` into a CourtVue recent-window trajectory workflow that highlights breakouts, declines, and the reasons behind them.

## Scope

- Keep `/insights` as the route
- Use `GET /api/insights/trajectory` as the primary contract
- Ensure the report:
  - excludes the recent window from the baseline
  - enforces sample and minutes thresholds
  - z-score normalizes final trajectory scores
  - returns breakout leaders, decline watch, excluded players, warnings, narratives, and context flags
- Update page copy to CourtVue where Team B surfaces touch branding

## Required files

- `frontend/src/app/insights/page.tsx`
- `frontend/src/components/TrajectoryTracker.tsx`
- `frontend/src/hooks/useTrajectory.ts`
- `backend/routers/insights.py`
- `backend/services/trajectory_service.py`
- shared append-only updates in `frontend/src/lib/types.ts` and `frontend/src/lib/api.ts` if needed

## Acceptance

- `/insights` renders the recency-first trajectory workflow
- changing the window or pool updates the rankings
- exclusion and warning rules behave correctly
- labels and context flags map to the documented thresholds
- UI remains readable on mobile and desktop
