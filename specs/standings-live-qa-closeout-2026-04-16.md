# Standings Live QA Closeout

**Date:** 2026-04-16
**Owner:** Codex
**Status:** Final
**Branch:** `master`

---

## Shipped

- Restored `2025-26` standings by extending `/api/standings` to prefer official `team_season_stats` rows while preserving snapshot fallback behavior.
- Enriched standings with game-derived `L10`, home/away, current streak, opponent PPG, and last-10 margin momentum from `game_team_stats` plus `games`.
- Expanded the standings contract with regular, shooting, advanced, ranking, and `recent_trend` fields.
- Rebuilt the standings page around grouped views: Records, Offense, Defense, Shooting, Advanced, and Rankings.
- Added compact side-by-side East/West tables, sortable metric headers, hover definitions, corrected playoff/play-in line placement, team abbreviations, and visible last-10 momentum sparklines.
- Added targeted backend coverage in `backend/tests/test_standings_route.py`.

## Verification

- `./venv/bin/python -m pytest tests/test_standings_route.py`
- `npm run lint`
- `npm run build`
- Local smoke checks for `/standings` and `/api/standings?season=2025-26`

## Deferred / Follow-Ups

- Consider a broader visual pass for the standings page once live QA settles the data density and table ergonomics.
- If daily standings history becomes important, schedule daily `team_standings` materialization so lower-page bump charts have real multi-day movement.
- Consider making standings sort state URL-backed if users want shareable views.

## Technical Notes

- `team_standings` remains useful for historical snapshots, but current-season totals and advanced metrics should come from official `team_season_stats`.
- Recent-form trend should use warehouse final-game rows, not sparse standings-history snapshots.
