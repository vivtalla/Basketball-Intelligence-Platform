# Sprint 21 Closeout

Status: Final

## Shipped work

- Split the old `Leaderboards` experience into two dedicated top-level workspaces:
  - `/metrics`
  - `/player-stats`
- Moved `Build Your Own Metric` to the new `Metrics` page
- Added built-in starter presets for the metric builder:
  - `Scoring Engine`
  - `Playmaking Load`
  - `Two-Way Impact`
  - `Efficiency Big`
- Added browser-local saved presets with save, load, and delete actions
- Removed the custom metric builder from the stats workspace so `Player Stats` is focused on ranking and exploration
- Replaced `/leaderboards` with a compatibility redirect to `/player-stats`
- Updated the app shell and home page to feature `Player Stats` and `Metrics` as first-class navigation targets
- Cleaned up visible player-name shortening, including the compare-page legend labels
- Recorded Team A and Team B reviewer/optimizer artifacts for the sprint

## Verification

- `npm install`
- `npm run lint`
- `npm run build`
- Live QA on a local Sprint 21 frontend:
  - `HEAD /leaderboards` returned `307` to `/player-stats`
  - `/metrics` rendered the new metric workspace content
  - `/player-stats` rendered the split stats workspace content
- Code search confirmed the `full_name.split(" ")[1]` compare-page shortcut was removed

## Deferred work

- Saved metric presets are still local-only; there is no share or account-sync path yet
- The renamed `Player Stats` workspace still reuses the legacy leaderboard UI structure and can be visually modernized later
- No end-to-end browser automation yet for the new route split and redirect behavior

## Coordination lessons

- The dual-team sprint structure still works well even for lighter frontend-only sprints when the work is partitioned by route ownership
- Using a dedicated integration branch after team branches merge kept the lint/build/live-QA fixes isolated from the feature branches
- Compatibility redirects are easy to underestimate; they need live route checks, not just build success

## Technical lessons

- The current warehouse worker script is batch-oriented now, so operational restarts need a shell loop wrapper rather than the old built-in `--loop` flags
- Next.js 16 route `searchParams` behavior needs explicit async handling on compatibility routes
- For local-presets UI, a lazy state initializer is the cleanest way to satisfy the repo’s React lint rules

## Next-sprint seeds

- Add shareable or account-backed metric presets
- Modernize the `Player Stats` workspace styling to match the newer Hardwood Editorial surfaces more closely
- Connect `Metrics` results directly into player and compare workflows with one-click follow-through
