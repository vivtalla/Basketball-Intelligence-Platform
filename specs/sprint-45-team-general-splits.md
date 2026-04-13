# Sprint 45 — Canonical Team General Splits

## Goal

Add canonical persisted official team general splits from `TeamDashboardByGeneralSplits` so prep, compare, and opponent-context workflows can rely on DB-first split data.

## Scope

- Add `team_split_stats` via Alembic revision `0004_team_split_stats`
- Persist regular-season general split families:
  - `LocationTeamDashboard`
  - `WinsLossesTeamDashboard`
  - `DaysRestTeamDashboard`
  - `MonthTeamDashboard`
  - `PrePostAllStarTeamDashboard`
- Add `nba_client.get_team_general_splits(season, team_id)`
- Add `sync_official_team_general_splits(db, season, team_ids=None)`
- Add thin persisted read API: `GET /api/teams/{abbr}/splits?season=2025-26`
- Add daily sync refresh after official team season stats

## Out of Scope

- No major UI surface
- No shooting split dashboards in Sprint 45
- No request-time official API repair in user-facing routes
- No play-type persistence in Sprint 45

## Verification

- Client parsing tests for mocked `TeamDashboardByGeneralSplits`
- Sync tests for insert/update/filter/delete behavior
- Team splits route tests for persisted reads and missing-data 404s
- Migration/schema tests for `0004_team_split_stats`
