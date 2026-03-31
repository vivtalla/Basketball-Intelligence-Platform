# Sprint 21 — Team A Metrics Workspace

Status: Ready for Engineer

## Summary

Move the custom metric workflow out of `Leaderboards` and into a dedicated `Metrics` workspace that feels like a reusable analyst tool, not an add-on panel.

## Scope

- Add `/metrics` as a new top-level route
- Make `Build Your Own Metric` the primary content on that page
- Add built-in starter presets:
  - `Scoring Engine`
  - `Playmaking Load`
  - `Two-Way Impact`
  - `Efficiency Big`
- Add local saved presets using browser storage only
- Keep backend metric scoring and endpoint behavior unchanged
- Add a contextual path back to `Player Stats`

## UX Requirements

- Desktop and mobile readable
- The page should explain what the workflow does without burying the form
- Built-in presets should load directly into the current builder state
- Saved presets should support save, load, and delete
- Saved presets are local-only in v1; no account sync wording

## Implementation Notes

- Reuse the existing `CustomMetricBuilder` and `useCustomMetric` path
- Avoid backend changes unless a frontend-only implementation proves impossible
- Prefer a small local storage helper or inline hook over shared platform state
- Keep the Hardwood Editorial visual direction

## Verification Targets

- `/metrics` renders
- A built-in preset loads and can be scored successfully
- A local preset can be saved, loaded, and deleted
- No regression in custom metric scoring behavior
