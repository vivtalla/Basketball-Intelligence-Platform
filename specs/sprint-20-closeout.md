# Sprint 20 Closeout

Status: Final

## Shipped work

- Rewrote `AGENTS.md` from a single-pipeline workflow into a dual-team sprint model with:
  - Team A `Metric Builder Team`
  - Team B `Trajectory Team`
  - explicit `Architect -> Engineer -> Reviewer -> Optimizer` gates for each team
- Added `POST /api/leaderboards/custom-metric` for user-defined composite metrics
- Added the `Build Your Own Metric` workflow to `Leaderboards`, including:
  - stat and weight selection
  - player-pool and season controls
  - validation and warning messaging
  - ranked results
  - metric profile interpretation
  - anomaly surfacing
- Added `GET /api/insights/trajectory` for recent-window player trajectory tracking
- Replaced the old YoY `Breakout Tracker` framing on `Insights` with a 2025-26 `Trajectory Tracker`, including:
  - last-N-games controls
  - pool and minutes filters
  - breakout leaders
  - decline watch
  - excluded-player list
  - warning/context flag messaging
- Appended shared frontend contracts for both workflows in `frontend/src/lib/types.ts` and `frontend/src/lib/api.ts`
- Added team-specific Reviewer and Optimizer artifacts for both Team A and Team B

## Verification

- `python -m py_compile backend/models/leaderboard.py backend/services/custom_metric_service.py backend/routers/leaderboards.py backend/tests/test_custom_metric_service.py backend/models/insights.py backend/services/trajectory_service.py backend/routers/insights.py backend/tests/test_trajectory_service.py`
- `pytest backend/tests/test_custom_metric_service.py backend/tests/test_trajectory_service.py`
- `npm run lint`
- `npm run build`
- Live QA on Sprint 20 servers:
  - backend `GET /api/health`
  - backend `POST /api/leaderboards/custom-metric`
  - backend `GET /api/insights/trajectory`
  - frontend `/leaderboards`
  - frontend `/insights`

## Deferred work

- No end-to-end browser automation yet for the two new analyst workflows
- No save/share layer yet for custom metric configurations
- No deep linking from trajectory results into a pre-filtered player or game-investigation flow

## Coordination lessons

- The dual-team `AGENTS.md` structure made a two-feature sprint much easier to reason about than the old single-branch workflow
- Team-local hooks and components reduced cross-team merge pressure; only the shared frontend contract files needed coordinated append-only integration
- Reviewer and Optimizer artifacts work better as first-class sprint outputs, especially when two parallel teams land in one sprint

## Technical lessons

- The custom metric backend is most stable when it excludes missing-stat players rather than attempting per-player partial scoring
- For trajectory tracking, the baseline must be out-of-window or the recent change signal gets diluted immediately
- Local live QA in this environment needs occasional elevated execution because sandbox networking and Turbopack process restrictions can look like app failures even when the branch is healthy

## Next-sprint seeds

- Add saved or shareable metric presets so analysts can reuse custom composites
- Connect trajectory results to player and game investigation flows with one-click follow-through
- Expand the dual-team operating model into a reusable sprint template now that the first pass is proven
