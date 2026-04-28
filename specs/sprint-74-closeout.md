# Sprint 74 Closeout — Methodology Reliability Rollout + Team-Fit/Shot Lab vNext

## Summary

Sprint 74 promoted methodology reliability from backend-only metadata into a product-wide pattern. The sprint shipped shared methodology registry/validation contracts, analyst-facing methodology evidence UI, `shot_quality_v2`, and `team_fit_v3` while preserving existing response compatibility and raw descriptive values.

## Shipped

- Upgraded the methodology registry to `methodology_registry_v2` with model stage, season-type support, validation notes, and implementation references.
- Added methodology validation fixtures and `GET /api/methodology/validation` for golden-case pass/fail reporting.
- Added shared frontend methodology types, API helpers, SWR hooks, and `<MethodologyEvidenceCard>` for version, reliability, samples, uncertainty, drivers, limitations, and validation notes.
- Wired shared methodology evidence into Team-Fit, Shot Intelligence, Opportunity, Archetype/Similarity, Trend/Trajectory, Style X-Ray, MVP/Gravity, Scouting Brief, and Custom Metrics surfaces.
- Upgraded Shot Lab to `shot_quality_v2` with hierarchical expected-shot baseline blending, empirical Bayes stabilized shot-making, uncertainty bands, and sustainability labels.
- Upgraded Team-Fit to `team_fit_v3` with current fit vs theoretical best usage, fit-gap interpretation, reliability-gated better-fit labels, analysis-context warnings, and playoff low-sample notes.
- Updated `specs/platform-methodology.md` and `specs/methodology-validation.md` with the new methodology versions, formulas, reliability gates, and validation fixtures.

## Verification

- `backend/venv/bin/python -m pytest backend/tests` — 290 passed, 2 FastAPI deprecation warnings.
- `npm run lint` — passed with 7 pre-existing `usePlayerStats.ts` unused-import warnings.
- `npm run build` — passed.
- `git diff --check` — passed.

## Deferred / Follow-Ons

- Calibrate Team-Fit better-fit thresholds with historical roster examples instead of current deterministic reliability tiers.
- Add second-wave model upgrades for Similarity, Trend/Trajectory, Opportunity, Style X-Ray, MVP/Award Case, Gravity, and Custom Metrics now that the shared metadata surface exists.
- Expand validation fixtures from qualitative golden cases into historical calibration reports with drift alerts.
- Validate Shot Lab stabilized shot-making against larger held-out samples and tune prior weights by shot family if needed.

## Workflow Notes

- The canonical checkout was actively changed by a parallel branch during closeout, so Sprint 74 was recovered and committed from a clean temporary worktree to avoid trampling unrelated playoff/MVP/gravity edits.
- Shared frontend contracts stayed append-only in `frontend/src/lib/types.ts` and `frontend/src/lib/api.ts`.
- No database migration was required.
- Closeout found repo-local backend/frontend dev servers already running on ports 8000/3000; both were stopped and the ports were confirmed clear before merge.
