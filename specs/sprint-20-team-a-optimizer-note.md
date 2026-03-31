# Sprint 20 — Team A Optimizer Note

Status: Final

## Scope Reviewed

- Custom metric normalization and ranking path
- Leaderboards metric-builder render flow

## Findings

- No blocking optimizer findings.

## Notes

- The metric service computes z-scores once per component across the eligible pool, then reuses those values while ranking.
- The frontend only runs the custom metric evaluation on explicit submit, avoiding background recomputation while weights are being edited.
