# Sprint 71 Closeout

**Sprint:** 71
**Date:** 2026-04-28
**Owner:** Codex
**Status:** Final

---

## Shipped

- Added backend methodology registry contracts and `GET /api/methodology` / `GET /api/methodology/{domain}`.
- Added shared reliability math: empirical Bayes shrinkage, reliability score, confidence labels, Wilson/normal uncertainty bands, robust z-scores, and winsorized z-scores.
- Added optional `analysis_metadata` to Shot Lab, Team-Fit, and Opportunity responses without changing existing frontend contracts.
- Updated platform methodology docs and added `specs/methodology-validation.md` for golden fixtures and calibration targets.
- Added Sprint 71 reliability/registry tests; full backend suite is 263 passing.

## Deferred / Not Finished

- No full ML/model replacement shipped this sprint; hierarchical shot quality, Mahalanobis similarity, uplift Opportunity, and Bayesian trend detection remain follow-ons.
- Frontend rendering of new methodology metadata was intentionally deferred because Claude is running an independent frontend sprint.

## Coordination Lessons

- Backend/docs-only sprinting worked well alongside a parallel frontend sprint when `AGENTS.md` explicitly marked frontend shared files out of scope.

## Workflow Lessons

- Keep methodology rigor increments honest: ship registry, metadata, tests, and docs before claiming advanced calibrated models exist.

## Technical Lessons

- Additive `analysis_metadata` is a safe way to introduce reliability and validation without breaking current response consumers.

## Next Sprint Seeds

- Render methodology registry and response-level `analysis_metadata` in UI drawers once frontend ownership is clear.
- Build Team-Fit golden fixture pressure tests and calibrate better-fit thresholds beyond the deterministic `+5` rule.
- Upgrade Shot Lab expected-shot modeling with hierarchical baselines and EB shot-making stabilization.
- Add Bayesian change detection for Trend/Trajectory with schedule, role, and injury context.

## Backlog Refresh

- Added a methodology reliability/calibration follow-on and reframed existing Team-Fit, Opportunity, and probabilistic-model backlog items around the new registry foundation.

