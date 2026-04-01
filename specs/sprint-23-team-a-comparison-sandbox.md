# Sprint 23 Team A: Comparison Sandbox

## Goal

Extend `/compare` from player-only into a coach-friendly comparison workspace with `Players` and `Teams` modes.

## Public Interface Changes

- Add `GET /api/compare/teams?team_a=...&team_b=...&season=...`
- Add frontend team-comparison types:
  - `TeamComparisonSnapshot`
  - `TeamComparisonRow`
  - `TeamComparisonStory`
  - `TeamComparisonResponse`
- Add a Teams mode to `/compare`

## Behavior Rules

- Preserve the current player compare flow exactly
- Teams mode should compare two teams on:
  - shooting efficiency
  - turnovers
  - rebounding
  - pace
  - true shooting
  - net rating / recent form
- Generate 3-5 simple story labels from explicit stat differences
- Use existing team analytics/intelligence data only

## Testing Scenarios

- Player compare still works unchanged
- Team mode loads valid team-vs-team comparison rows
- Story labels update when team selections change
- Empty and loading states remain readable

## Assumptions / Defaults

- Season default can match the current compare surface default
- No new warehouse dependency is added
- Team comparison can degrade gracefully if one or both teams lack some advanced fields
