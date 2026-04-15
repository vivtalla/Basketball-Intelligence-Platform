# Sprint 45 Closeout

## Summary

Sprint 45 extended the Sprint 44 official-data foundation into canonical persisted team general splits. The work stayed intentionally backend-first: schema, sync, parsing, thin read API, tests, and docs, with no major UI build.

This branch-level closeout was prepared on `feature/sprint-45-team-general-splits`; merge to `master` is still the final integration step.

## Shipped Work

### Canonical Team General Splits

- Added `team_split_stats` and Alembic revision `0004_team_split_stats` for official team split rows keyed by `team_id`, `season`, `is_playoff`, `split_family`, and `split_value`
- Persisted regular-season `TeamDashboardByGeneralSplits` families for location, wins/losses, days rest, month, and pre/post All-Star splits
- Stored common totals and rates for prep/opponent context: games, wins, losses, win percentage, minutes, points, rebounds, assists, turnovers, steals, blocks, shooting percentages, plus-minus, source, and sync timestamp

### Official Sync and API Surface

- Added `nba_client.get_team_general_splits(season, team_id)` with stable normalization across supported dashboard datasets
- Added `sync_official_team_general_splits(db, season, team_ids=None)` with insert/update/filter behavior and stale-row cleanup only for teams that returned fresh official data
- Updated `backend/data/daily_sync.sh` so daily official sync refreshes team general splits after official team season stats
- Added persisted-only `GET /api/teams/{abbr}/splits?season=2025-26` returning `TeamSplitsResponse` and `TeamSplitRow` models
- Kept user-facing routes DB-only: missing teams or missing persisted split data return 404 instead of request-time NBA API repair

### Docs and Backlog

- Updated `specs/official-data-source-matrix.md` so team general splits moved from gap to canonical official domain
- Added `specs/sprint-45-team-general-splits.md` as the implementation scope note
- Updated `specs/BACKLOG.md` with team shooting split dashboards as the next official split follow-on

## Verification

- `pytest backend/tests/test_team_dashboard_parsing.py backend/tests/test_official_team_stats.py backend/tests/test_schema_migrations.py`
- `pytest backend/tests/test_official_season_sync.py backend/tests/test_warehouse_materialization.py backend/tests/test_leaderboards.py backend/tests/test_team_dashboard_parsing.py backend/tests/test_official_team_stats.py backend/tests/test_schema_migrations.py`
- `pytest backend/tests`
- `python -m compileall backend/data backend/db backend/models backend/routers backend/services backend/tests`
- `git diff --check`

## Deferred / Follow-Ons

- Team shooting split dashboards remain a high-value official-data follow-on for shot-profile and style context
- Player split dashboards and play-type persistence remain open official-data domains
- Product wiring into prep, compare, and opponent-context workflows should happen after the persisted team-split contract lands
- Playoff sync is represented by `is_playoff` for schema compatibility but not implemented in this sprint

## Workflow Notes

- Sprint 45 returned to feature-branch discipline after Sprint 44's direct-to-`master` implementation
- The safest sync behavior is to avoid deleting existing rows for a team when the official endpoint returns no data; stale cleanup only runs for teams with a successful fresh payload
- Frontend lint/build was not rerun because this sprint did not touch frontend generated types, API clients, or UI code

## Next Sprint Seeds

- Consider team shooting splits next if we want to stay in the official dashboard family
- Consider player splits or play-type persistence if the next sprint should feed scouting/trend-card workflows more directly
- Start wiring persisted team general splits into prep/compare surfaces only after the Sprint 45 branch lands on `master`
