# CourtVue Labs — Agent Lessons

Persistent self-improvement log. Never reset this file.
Update after any user correction. Write rules, not narratives.
Review at the start of each session.

---

## Format

Each lesson:
- **Context**: what situation triggered the mistake
- **Mistake**: what went wrong
- **Rule**: the rule to prevent recurrence

---

## Lessons

<!-- Add entries below in reverse-chronological order (newest first). -->

### 2026-04-01 — Last-name-only player full_name (recurring)

- **Context**: Player names showing as last-name-only (e.g. "Williams", "James") on Insights/TrajectoryTracker and other surfaces. Recurs across sprints.
- **Mistake**: `canonical_player_name()` exists in `sync_service.py` and correctly guards the nba_api bio sync path, but `warehouse_service._get_or_create_player()` and `bulk_sync_service.py` wrote `player.full_name` directly without the guard. New player records created via the warehouse pipeline kept landing as last-name-only.
- **Rule**: Any code path that writes `Player.full_name` MUST pass through `canonical_player_name(full_name, first_name, last_name)` from `sync_service.py`. Also use `firstName`/`familyName` fields from CDN box score payloads (not just `name`) when building the full name. 108 players still have NULL `first_name` in the DB and will need a `sync_player()` call to fully repair.
