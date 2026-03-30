## Sprint 17: Team Rotation Intelligence

Status: Ready for Engineer

### Goal

Add a decision-oriented rotation workflow to team pages so analysts can quickly identify who is driving the team now, who is gaining or losing trust, how recent usage differs from the season baseline, and which games to inspect next in Game Explorer.

### Backend contract

Add `GET /api/teams/{abbr}/rotation-report?season=...`.

Top-level response:

- `team_id`
- `abbreviation`
- `season`
- `status` (`ready` | `limited`)
- `window_games`
- `starter_stability` (`stable` | `mixed` | `volatile`)
- `recent_starters`
- `minute_load_leaders`
- `rotation_risers`
- `rotation_fallers`
- `on_off_anchors`
- `recommended_games`

Behavior:

- Use only existing tables: `game_player_stats`, `player_on_off`, `season_stats`, `games`, `teams`, `players`.
- Default recent window is the last 10 completed team games.
- For `2024-25` and `2025-26`, compute the full report when `game_player_stats` exists.
- For seasons without warehouse-backed `game_player_stats`, return `status = "limited"` and empty arrays.
- Do not add or modify database schema.

### Derived rules

- `minutes_delta = avg_minutes_last_10 - avg_minutes_season`
- `primary_starter = true` when a player started at least half of the window games
- `starter_stability`
  - `stable` when 5 or fewer unique starters appeared across the window
  - `mixed` when 6 or 7 unique starters appeared across the window
  - `volatile` when 8 or more unique starters appeared across the window
- `recommended_games`
  - choose 3-5 recent completed games
  - rank by a combination of result margin and unusual minutes redistribution vs season norms
  - include a `rotation_note` based on the largest minute shifts or unusual starter combinations

### Frontend workflow

Add a major `Rotation Intelligence` section on the team page that complements, but does not replace, the current intelligence panel.

Required UI:

- summary strip with `rotation status`, `recent starter stability`, `largest riser`, `largest faller`
- `Recent Starters`
- `Who’s Gaining Minutes`
- `Who’s Losing Minutes`
- `Impact Anchors`
- `Games To Review Next`

Rules:

- Place it prominently in the team intelligence flow, above lineup context.
- Keep mobile and desktop layouts readable.
- Link player names to player pages and games to `/games/{game_id}`.
- For historical or non-warehouse seasons, show a precise limited-support message:
  - `This rotation report is available for warehouse-backed modern seasons only.`

### Validation targets

- Modern season team returns populated sections with correct sorting.
- Historical team returns `limited` with empty arrays and clear messaging.
- Team page renders without breaking the existing intelligence surface.
