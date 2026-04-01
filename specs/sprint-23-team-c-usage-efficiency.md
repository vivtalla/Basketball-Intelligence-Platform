# Sprint 23 Team C: Usage vs Efficiency Dashboard

## Goal

Extend `/insights` into a coach hub that keeps the existing breakout/trajectory workflow and adds a usage-vs-efficiency view.

## Public Interface Changes

- Add `GET /api/insights/usage-efficiency?season=...&team=...&min_minutes=...`
- Add shared types:
  - `UsageEfficiencyPlayerRow`
  - `UsageEfficiencySuggestion`
  - `UsageEfficiencyResponse`

## Behavior Rules

- Keep the current trajectory/breakouts workflow available
- Add a second workflow focused on offensive burden allocation
- Filter by season, team, and minimum minutes
- Show:
  - over-used inefficients
  - under-used efficient players
  - bounded redistribution suggestions
- Keep recommendations explainable and non-black-box

## Testing Scenarios

- Existing insights workflow still renders
- Usage/efficiency mode loads and categories look sensible
- Team and minute filters update results
- Empty and warning states stay readable

## Assumptions / Defaults

- Use existing `SeasonStat` fields first: `usg_pct`, `ts_pct`, `pts_pg`, `tov_pg`, `ast_pg`, `off_rating`
- Suggestions can be threshold-driven rather than predictive
