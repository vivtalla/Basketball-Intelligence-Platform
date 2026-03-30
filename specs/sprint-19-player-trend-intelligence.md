# Sprint 19: Player Trend Intelligence

Status: Final

## Goal

Add a flagship player-page decision workflow that explains how a player's role changed recently, whether trust is rising or falling, and which games to inspect next.

## Product shape

- New backend contract: `GET /api/players/{player_id}/trend-report?season=...`
- New player-page section placed below `PlayerHeader` and above the chart/splits stack
- Regular-season only in v1
- Keep the current Hardwood Editorial visual system

## Backend requirements

- Build the report primarily from:
  - `player_game_logs`
  - `season_stats`
  - `player_on_off`
  - `players`
  - `teams`
- Use `game_player_stats` opportunistically for `starts_last_10` and recommended-game `is_starter`, because `player_game_logs` does not store starter flags
- No schema changes
- No new mandatory warehouse dependency for the whole report
- `status = "ready"` when the player has at least 5 stored regular-season game logs in that season
- `status = "limited"` otherwise, while still returning a valid response shape

## Response shape

- `player_id`
- `player_name`
- `team_abbreviation`
- `season`
- `status`
- `window_games`
- `role_status`
- `recent_form`
- `season_baseline`
- `trust_signals`
- `impact_snapshot`
- `recommended_games`

Recommended supporting models:
- `PlayerTrendForm`
- `PlayerTrendSignals`
- `PlayerTrendGame`
- `PlayerTrendImpactSnapshot`
- `PlayerTrendReport`

## Derived rules

- Default recent window: last 10 regular-season games
- `minutes_delta = recent_form.avg_minutes - season_baseline.avg_minutes`
- `points_delta = recent_form.avg_points - season_baseline.avg_points`
- `efficiency_delta = recent_form.avg_fg_pct - season_baseline.avg_fg_pct`
- `starts_last_10`
- `bench_games_last_10`
- `games_30_plus_last_10`
- `games_under_20_last_10`
- `minute_volatility` = population standard deviation of recent minutes, rounded to 1 decimal

`role_status` thresholds:
- `entrenched_starter`: `starts_last_10 >= 8` and `minutes_delta >= -1.0`
- `rising_rotation`: `minutes_delta >= 4.0` or `games_30_plus_last_10 >= 5`
- `losing_trust`: `minutes_delta <= -4.0` or `games_under_20_last_10 >= 5`
- `volatile_role`: `minute_volatility >= 8.0`
- else `stable_rotation`

`recent_form` and `season_baseline` both include:
- `games`
- `avg_minutes`
- `avg_points`
- `avg_rebounds`
- `avg_assists`
- `avg_fg_pct`
- `avg_fg3_pct`
- `avg_plus_minus`

`impact_snapshot` includes:
- `pbp_coverage_status`
- `on_off_net`
- `on_minutes`
- `bpm`
- `per`
- `pts_pg`
- `ts_pct`

`pbp_coverage_status` logic:
- `ready` when on/off exists and season scoring-split fields exist
- `partial` when either on/off or season scoring-split fields exist
- `none` otherwise

## Recommended games

Return 3–5 recent games with:
- `game_id`
- `game_date`
- `matchup`
- `result`
- `minutes`
- `points`
- `plus_minus`
- `is_starter`
- `trend_note`

Priority order:
- largest absolute minutes deviation from season average
- then start/bench role flips
- then largest absolute scoring deviation
- then largest absolute plus-minus

`trend_note` should use deterministic rule text:
- `heavy workload spike`
- `starter look after bench stretch`
- `minutes dip despite normal scoring`
- `big scoring outlier`
- `strong plus-minus swing`
- fallback: `recent role check`

## Frontend requirements

- Add matching frontend types and API function
- Add SWR hook for the new report
- Add `PlayerTrendIntelligencePanel`
- Render it only in regular-season mode
- In playoff mode show a precise message that the workflow is regular-season only
- In limited mode show a clean early-data message, not an error
- Include:
  - summary strip
  - recent vs season comparison
  - trust signals
  - impact snapshot
  - games to review next
- Link recommended games to `/games/{game_id}`

## Supporting hardening

- Remove `next/font/google` dependency from the app shell
- Use deterministic local font stacks via CSS variables so `next build` does not rely on external font fetches

## Verification

- Backend compile check for new backend files
- `npm run lint`
- `npm run build`
- DB-backed spot checks:
  - one player with 10+ regular-season logs returns `ready`
  - one player with fewer than 5 logs returns `limited`
  - missing `player_on_off` does not break the response
