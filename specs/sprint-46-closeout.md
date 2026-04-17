# Sprint 46 Closeout - CourtVue Ask Workspace

Date prepared: 2026-04-17  
Branch: `feature/sprint-46-ask-workspace`  
Owner: Codex

## Shipped

- Added a DB-first StatMuse-inspired query layer at `POST /api/query/ask`, plus `GET /api/query/examples` and `GET /api/query/metrics`.
- Added a canonical query metric registry with labels, aliases, descriptions, formats, entity support, source metadata, and higher/lower-is-better behavior for player and team metrics.
- Added deterministic query interpretation for:
  - player leaderboards and team rankings
  - lowest/best/top/bottom sort intent
  - explicit season parsing and latest-season defaults
  - threshold filters such as `25 ppg` and `60 ts%`
  - player and team lookup fallbacks
  - player recent form from `player_game_logs`
  - team recent form from `game_team_stats` joined to `games`
  - basic player compare deep links
  - graceful low-confidence suggestions instead of dead-end errors
- Added the `/ask` frontend workspace with URL-backed `q=` state, example chips, answer cards, sortable result tables, metric hover explanations, source/readiness context, suggestions, and links into profiles, teams, games, and compare.
- Added `Ask` to the top navigation and homepage workspace grid.

## Verification

- `source backend/venv/bin/activate && pytest backend/tests`
  - 86 passed
- `npm run lint`
  - passed
- `npm run build`
  - passed, including `/ask` route generation

## Deferred

- LLM-assisted query interpretation remains intentionally out of scope; the interpreter is deterministic and structured so an optional LLM adapter can be added later behind a flag.
- All-time and full historical natural-language coverage are not yet supported beyond seasons already synced locally.
- Odds, betting, fantasy, schedules, live scores, and broad bio questions remain out of scope.
- Query history, saved searches, and account-backed personal workspaces remain future work.
- The global nav search remains player-only; `/ask` is the first full query workspace.

## Follow-On Seeds

- Add query result mini-visuals for trend/recent-form answers, especially team last-10 margin and player rolling game logs.
- Add query-powered deep links into Player Stats and Standings with the interpreted stat/filter state preloaded.
- Expand parser coverage for date windows, opponent filters, playoffs, positions, and "in a game" leaderboards.
- Add a lightweight query confidence/debug panel for development so new aliases can be tuned safely.
- Consider a guarded LLM-to-structured-query adapter only after the deterministic registry has broader coverage.
