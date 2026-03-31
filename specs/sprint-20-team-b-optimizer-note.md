# Sprint 20 — Team B Optimizer Note

Status: Final

## Scope Reviewed

- Trajectory score computation pipeline
- Insights page query behavior and render flow

## Findings

- No blocking optimizer findings.

## Notes

- The service groups game rows in-memory once, computes split aggregates per player, then applies one pool-wide z-score pass for the final trajectory score.
- The frontend uses a single query keyed by the active controls, keeping the page responsive without redundant fetch patterns.
