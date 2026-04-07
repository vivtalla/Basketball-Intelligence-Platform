# Sprint 43 Closeout

**Sprint:** 43
**Date:** 2026-04-06
**Owner:** Codex
**Status:** Final

---

## Shipped

- Replaced startup-time schema mutation with an Alembic-backed migration workflow and added audited baseline/drift revisions for the current schema.
- Removed normal runtime reliance on `ensure_schema.py` by moving the app onto an explicit migration path and leaving `ensure_schema.py` as a compatibility wrapper only.
- Removed the remaining request-time player bootstrap from the advanced PBP sync flow so serving behavior stays DB-first and explicit sync stays explicit.
- Collapsed the shipped decision stack behind one canonical service layer (`decision_support_service.py`) and reduced `routers/decision.py` to transport-only handlers.
- Reframed historical team/pre-read responses as explicit `legacy-compatibility` mode and added additive `runtime_policy` metadata to make warehouse-first versus compatibility mode clearer.
- Replaced the decision stack's remaining internal dependency on `routers/styles.py` with lightweight service-owned style snapshots, then tightened the live `lineup-impact` and `follow-through` paths so both endpoints stay responsive on the local dataset.
- Added an in-repo architecture audit note documenting the major findings, shipped remediations, remaining debt, and approved architectural rules.

## Deferred / Not Finished

- Sprint 43 did not remove historical legacy storage entirely; it isolated and labeled the compatibility boundary more clearly instead.
- The sprint did not complete a repo-wide router/service purity pass outside the decision stack.
- Lower-level ingestion fallback cleanup remains selective rather than exhaustive.

## Coordination Lessons

- The migration cut was safest when treated as a compatibility transition instead of a purity rewrite; keeping `ensure_schema.py` as a wrapper made the operational change much less brittle.
- The decision stack became much easier to reason about once the shipped behavior moved behind one canonical service rather than trying to “fix” multiple partially overlapping service implementations.

## Workflow Lessons

- Foundation sprints still need durable artifacts, not just code changes; the audit note is what turns a cleanup sprint into something future engineers can build on confidently.
- Warehouse-first discipline improves more when the code is forced to surface missing data honestly than when routes quietly try to fix the problem during reads.

## Technical Lessons

- `Base.metadata.create_all()` is acceptable inside a baseline migration, but not as a serving-time schema strategy.
- Additive `runtime_policy` metadata is a clean way to expose compatibility boundaries without forcing route churn.
- Query-time performance and architectural ownership are related: once the decision stack had one canonical path, it became clearer where future optimization work should actually happen.

## Next Sprint Seeds

- Continue retiring router-local business logic in other domains, especially styles and adjacent decision-support surfaces.
- Plan a narrower legacy-compatibility retirement pass for historical reads that still matter operationally.
- Continue profiling decision-tool reads opportunistically, but treat latency tuning as calibration work now that the live timeout regressions are gone.

## Verification

- `backend/venv/bin/pytest backend/tests/test_schema_migrations.py backend/tests/test_sprint25_decision_surfaces.py backend/tests/test_sprint32_team_prep_core.py`
- `backend/venv/bin/pytest`
- `python -m compileall backend`
- `frontend: npm run lint`
- `frontend: npm run build`
- Live local smoke checks on `http://127.0.0.1:8002`:
  - `GET /api/health` → `200 OK`
  - `GET /api/teams/ATL/prep-queue?season=2025-26&days=7` → `200 OK`
  - `GET /api/decision/lineup-impact?team=ATL&season=2025-26&opponent=BOS` → `200 OK`
  - `GET /api/decision/matchup-flags?team=ATL&opponent=BOS&season=2025-26` → `200 OK`
  - `GET /api/compare/teams?team_a=ATL&team_b=BOS&season=2025-26` → `200 OK`
  - `POST /api/follow-through/games` → `200 OK`

## Backlog Refresh

- Rewrote the old “Final DB-First Cleanup for Non-Core Reads” item into more specific migration/compatibility follow-ons because the broad request-time sync cleanup is now materially complete.
- Removed the temporary follow-through responsiveness follow-on after the live smoke regression was fixed inside Sprint 43.
- Reframed decision-tool performance work as ongoing calibration rather than a current blocking architecture gap.
