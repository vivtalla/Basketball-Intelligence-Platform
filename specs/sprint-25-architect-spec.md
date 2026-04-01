# Sprint 25 Architect Spec

## Goal
Ship the first platform-intelligence layer for CourtVue Labs by adding coach-facing decision tools, guided game follow-through, pace/style identity, and trend cards, while shipping beta foundations for what-if, scouting, and compare follow-ons.

## Public interface changes
- New backend endpoints:
  - `GET /api/decision/lineup-impact`
  - `GET /api/decision/play-type-ev`
  - `GET /api/decision/matchup-flags`
  - `POST /api/follow-through/games`
  - `GET /api/styles/teams/{abbr}`
  - `GET /api/styles/xray`
  - `POST /api/scenarios/what-if`
  - `GET /api/trends/cards`
  - `GET /api/scouting/play-types`
  - `GET /api/compare/lineups`
  - `GET /api/compare/styles`
- New frontend workflows:
  - team-page `Decision Tools`
  - `/insights` tabs for `Trend Cards` and `What-If`
  - `/compare` modes for `lineups` and `styles`
  - `/pre-read` scouting/report mode
  - Game Explorer context banner and return path

## Behavior rules
- Play-type work is explicitly inferred/proxy-based in v1.
- Every recommendation or flag must include evidence and a drill-down path.
- All drill-downs preserve source context through URL params.
- Low-support outputs degrade to directional/limited states instead of returning fake precision.
- Shared type and API additions remain append-only.

## Testing scenarios
- Team decision tools load with evidence, confidence, and follow-through links.
- Trend cards show meaningful weekly changes and empty states when no shift clears thresholds.
- What-if scenarios return bounded outputs with unsupported-case warnings.
- Compare launches preserve context and shareable URLs.
- Scouting and pre-read output remain print-friendly.

## Defaults and assumptions
- Sprint is core-first: full decision tools, follow-through, style profiles, and trend cards; beta/foundation for what-if, scouting, play-style x-ray, and compare follow-ons.
- No schema changes unless performance forces them.
- Use existing `GameTeamStat`, `LineupStats`, `PlayByPlayEvent`, and `WarehouseGame` inputs.
