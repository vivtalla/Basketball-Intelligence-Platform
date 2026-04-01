# Sprint 23 Team B: Four-Factor Focus Levers

## Goal

Add a coach-facing `Focus Levers` panel to the team page that turns the four factors into concise game-planning priorities.

## Public Interface Changes

- Add `GET /api/teams/{abbr}/focus-levers?season=...`
- Add shared types:
  - `TeamFactorRow`
  - `TeamFocusLever`
  - `TeamFocusLeversReport`

## Behavior Rules

- Build from existing team analytics, standings-ready context, recent form, and warehouse-backed team data only
- Summarize:
  - shooting
  - turnovers
  - rebounding
  - free throws
- Return 2-3 prioritized focus levers with impact framing
- Keep the panel concise and decision-oriented
- Degrade gracefully when some supporting metrics are sparse

## Testing Scenarios

- Backend returns factor rows and prioritized levers
- Team page renders focus levers without breaking existing intelligence content
- Modern and historical seasons behave sensibly when sparse

## Assumptions / Defaults

- Impact framing can be heuristic and explicit rather than model-heavy
- Use existing team analytics fields before inventing new derived models
