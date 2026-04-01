# Sprint 23 Team D: Game-Day Pre-Read Deck

## Goal

Create a short, printable coach workflow for pregame briefing at `/pre-read`.

## Public Interface Changes

- Add `GET /api/pre-read?team=...&opponent=...&season=...`
- Add route `/pre-read`
- Add shared types:
  - `PreReadSlide`
  - `PreReadAdjustment`
  - `PreReadDeckResponse`

## Behavior Rules

- Inputs:
  - team
  - opponent
  - season
- Output should be a 3-5 slide web deck that prints cleanly
- Include:
  - tonight's 3 focus levers
  - top 2 matchup advantages
  - one-line tactical adjustments
- Reuse Team B focus-lever logic where possible
- No hard dependency on PDF generation

## Testing Scenarios

- Valid team/opponent input loads a complete deck
- Deck is readable in browser and print layout
- Empty or sparse-data states are still actionable

## Assumptions / Defaults

- V1 is a printable HTML deck, not a document export system
- Matchup advantages can be built from existing team analytics/intelligence fields
