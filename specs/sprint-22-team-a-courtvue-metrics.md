# Sprint 22 — Team A CourtVue Metrics

## Goal

Ship the CourtVue rebrand across shared user-facing surfaces and turn `/metrics` into the flagship custom-metric workspace.

## Scope

- Rename visible product branding from Basketball Intelligence Platform / BIP to CourtVue
- Add `POST /api/metrics/custom`
- Keep the existing metrics math, but align the public contract and frontend wiring to the new route
- Upgrade `/metrics` to support:
  - built-in presets
  - URL-shareable metric state
  - validation and anomaly callouts
  - direct links to player pages and compare

## Required files

- `frontend/src/app/layout.tsx`
- `frontend/src/app/page.tsx`
- `frontend/src/app/metrics/page.tsx`
- `frontend/src/components/CustomMetricBuilder.tsx`
- `frontend/src/hooks/useCustomMetric.ts`
- `backend/routers/metrics.py`
- `backend/services/custom_metric_service.py`
- shared append-only updates in `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`, and `backend/main.py`

## Acceptance

- CourtVue branding appears in app metadata, nav, hero, footer, Learn page, and API title
- `/metrics` loads from a shareable URL and restores config state
- metric submission uses `POST /api/metrics/custom`
- result rows link to player pages and Compare
- invalid weights, mixed-stat warnings, insufficient pools, and anomalies all surface cleanly
