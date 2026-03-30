# Sprint 20 — Team B: Recent Trajectory Tracker

Status: Ready for Engineer

## Goal

Replace the current year-over-year `Breakout Tracker` framing with a 2025-26 recent-window trajectory workflow that compares a player's last N games against a baseline built from games outside the window.

## Product shape

- Surface: existing `Insights` page
- Primary workflow label: `Trajectory Tracker`
- Focus season: `2025-26`
- Hardwood Editorial styling remains active

## Backend contract

- Add `GET /api/insights/trajectory`
- Query params:
  - `season=2025-26`
  - `last_n_games`
  - `player_pool`
  - `min_minutes_per_game`
  - optional pool filters only if already supported cleanly in v1
- Response shape must match the sprint contract exactly:
  - `window`
  - `breakout_leaders`
  - `decline_watch`
  - `excluded_players`
  - `warnings`

## Required rules

- Baseline = season-to-date averages excluding the last N games
- Exclude players with fewer than `N + 10` total games
- Exclude players below the minimum-minutes threshold
- Exclude players when the recent window exceeds 50% of their total sample
- Compute weighted trajectory score from the specified deltas
- Z-score normalize trajectory scores before labeling
- Labels:
  - `Breaking Out`
  - `Quietly Rising`
  - `Slumping`
  - `Collapsing`
- Add context flags for:
  - injury return
  - role change via usage delta
  - schedule difficulty/ease via opponent defensive rating context

## Frontend workflow

- Rewrite `Insights` around recent-window trajectory tracking
- Include:
  - `last N games` control
  - player-pool / minutes controls
  - breakout leaders section
  - decline watch section
  - excluded players section
  - warnings section
- Keep the page clearly about recency, not year-over-year change
- Use append-only additions in shared `types.ts` and `api.ts`

## Test targets

- baseline excludes recent window correctly
- insufficient-sample exclusions work
- minimum-minutes exclusions work
- >50% window-size exclusions work
- score weighting and Z-score normalization are correct
- label bands map correctly
- context flags populate when conditions are met
- insights page no longer falls back to the old YoY breakout framing
