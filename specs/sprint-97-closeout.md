# Sprint 97 Closeout — Sync Gap Hardening

**Branch:** `feature/sprint-97-sync-hardening`
**Merged:** 2026-05-10 → 2026-05-11
**Date:** 2026-05-10 – 2026-05-11
**Owner:** Claude

---

## Summary

Production review on Sprint-96 closeout night surfaced all 4 R2 G1s missing from `game_logs` — NYK swept PHI 4-0 in real life but the home page rendered 0-3. Manual backfill executed during the incident (commit `9e65df4`); Sprint 97 follows up with three layers of permanent defense + two latent bugs that the incident uncovered.

---

## Shipped (in `master`)

### New: `services/playoff_series_backfill.py`
Walks every active/closed `PlayoffSeries`, parses the series-slot prefix from existing game IDs (`0042500SSG` format), and probes positions 1..max+1 against NBA's `boxscoresummaryv2`. Missing-and-final games get inserted with correct `series_id` + `series_game_num`. After any insert, `series_game_num` is renumbered so date order is canonical. Idempotent and rate-limited (0.6s between fetches). 6 unit tests cover parser, missing-G1 insert, renumber, idempotency, NBA-returns-None break, and skip-empty-series.

### `daily_sync.sh` hook
Backfill runs before `build_or_refresh_bracket` in `--post-game` mode so the bracket builder sees recovered games immediately. Non-fatal — a backfill failure logs and continues.

### New: `GET /api/health/sync-status` + `CacheManager.peek()`
Backfill events write a 24h-TTL marker into cache.db. The endpoint surfaces the last event (`count`, `ran_at`, `backfilled_ids`, `season`) without polluting cache hit/miss stats. Empty payload = healthy steady state.

### Hotfix: cron env self-source (`b26f28a` lineage in daily_sync.sh)
Production review showed every `*/15` cron tick was hitting the Sprint-91 `DATABASE_URL not set` guard despite the crontab using the correct `set -a && . /etc/bip/env && set +a` wrapper. Whatever was eating env propagation between cron's shell and the script's bash invocation, the symptom was identical: every tick exited before doing any work — for **at least 5 days**. This is the underlying reason the 4 R2 G1s went missing. Self-source fallback added: if `DATABASE_URL` isn't set and `/etc/bip/env` exists, the script sources it itself.

### Bracket-builder duplicate-row fix
When the cron started running again post-fix, `build_or_refresh_bracket` exposed a latent issue: when both a placeholder R2 row (`series_id = 'YYYY-CONF-R2-TOP|BOT'`) and a games-derived team-pair row (e.g. `'YYYY-CONF-R2-NYK-PHI'`) exist for the same logical slot, `_auto_advance_closed_series`'s fallback only matched candidates whose child-slot seat held the winner. Seat assignment for placeholder vs team-pair rows can disagree when conference arms aren't seed-symmetric, so the fallback missed valid sibling rows and recreated a placeholder every cron tick. Patched the fallback with a second pass: if no child-slot-matched sibling exists, accept any R2 row in the same round that already has the winner in either seat.

---

## Production Incident Mitigation (Sprint 96 closeout night)

- Manual backfill via inline SQL inserted 4 missing R2 G1s (NYK 137-98 PHI on 5/4, MIN 104-102 SAS on 5/4, DET 111-101 CLE on 5/5, OKC 108-90 LAL on 5/5).
- After Sprint 97 deploy: 4 orphan placeholder rows (`E-R2-TOP|BOT`, `W-R2-TOP|BOT`) deleted from `playoff_series` — they had zero `game_logs` references after the bracket builder re-tagged games to team-pair IDs.

---

## Verification

- **Backend tests:** 594 passing (was 588 + 6 new for `playoff_series_backfill`). Pre-existing `test_daily_sync_post_game_dry_run` still fails (DATABASE_URL guard in test env — orthogonal to this sprint; Sprint 97's self-source uses `/etc/bip/env` which doesn't exist in test env, so the guard still fires).
- **`npm run build`** + **`npm run lint`:** untouched by this sprint — no frontend changes.
- **Production smoke (post-deploy):** `/api/playoffs/bracket` shows exactly 4 R2 series with correct counts (NYK 4-0 PHI, DET 2-1 CLE, OKC 3-0 LAL, SAS 2-2 MIN). `/api/health/sync-status` returns the expected empty-state payload. Cron now executes successfully end-to-end (`backfill: no gaps found` → `bracket refreshed: 12` → `daily_sync post-game complete`). Subsequent runs do not regenerate placeholder rows.

---

## Coordination Lessons

- **Production review is the catch-of-last-resort for sync correctness.** Backend tests didn't catch this — the bug lived in the timing relationship between cron, the env file, and shell process boundaries. The data drift was real, persistent, and silent for ~5 days. Without Vivek noticing "the trackers are off by one" on the home page, this would've kept compounding for weeks.

## Workflow Lessons

- **A broken cron is worse than a missing feature.** The cron started failing some unknown number of weeks ago (the bip-sync.log records of failed runs trace back at least to 5/6). No alert fired because the script exited 1 silently and the only writer to the log was the failure path itself. Sprint 97's `/api/health/sync-status` is the start of fixing this, but a real alerting story (e.g. UptimeRobot polling `sync-status` for `ran_at` > 30 min old) is still needed.
- **"Worked when I ran it via ssh" is not proof it works under cron.** I spent multiple iterations debugging by running the cron command literally via ssh — every time it worked because ssh inherits env. The actual cron environment is stripped, and reproducing it via `env -i` is the right test. Logging the cron's environment at first sight of failure (e.g. `env > /tmp/cron-env-$$.txt` at the top of `daily_sync.sh`) would have answered the question in 5 minutes.
- **Mid-sprint hotfixes during closeout are not free.** Sprint 96 closeout shipped successfully and was wrapping up when this incident hit. Treating it as Sprint 97 (with full branch/worktree/closeout discipline) instead of a hotfix-on-master was the right call — the resulting changes have proper tests, history, and a coherent narrative. But it did push the rest of the planned Sprint 97 work (the `/beta` graduation candidate) to Sprint 98.

## Technical Lessons

- **The cron env-propagation bug is still unsolved.** Self-sourcing makes the script robust to it, but I never identified *why* the cron's `set -a && . /etc/bip/env && set +a` wrapper failed to export vars to the subshell. Possible culprits: cron's parser splitting the `&&` chain across processes; `/bin/sh` (dash) vs `/bin/bash` ambiguity; some interaction with cron's PAM session setup. Worth instrumenting if it recurs after the self-source fallback is removed.
- **Two parallel R2-series-creation paths is a design smell.** `_auto_advance_closed_series` creates placeholder slots with positional IDs (`R2-TOP|BOT`); the build-from-games loop creates team-pair IDs (`R2-NYK-PHI`). They were intended to converge — the placeholder fills in seeds, the team-pair row inherits. In practice they diverge when conference arms aren't seed-symmetric. Long-term cleanup: pick one scheme. Short-term, the Sprint 97 sibling-fallback patch keeps them from creating duplicates.
- **Bypass-cache rules show as `cf-cache-status: MISS`, not `BYPASS`.** Worth noting in `infra/README.md` so the next operator doesn't think a rule is broken.

---

## Next Sprint Seeds

1. **Real alerting on sync gaps.** UptimeRobot or Cloudflare-side webhook polling `/api/health/sync-status` for `ran_at` older than 30 min OR `count > 0` in last 24h. Email/Slack on anomaly. Sprint 97's endpoint is the data source; this is the consumer.
2. **Carry-over from Sprint 96: graduate first `/beta/*` page to root.** Pick `/beta/lineups` or `/beta/teams` with Vivek and run a focused page-rework sprint.
3. **Investigate the cron env-propagation root cause.** Self-source is the safety net; understanding why `set -a && . /etc/bip/env && set +a` doesn't export under cron is still owed. Add `env > /tmp/cron-env-$$.txt` to `daily_sync.sh` for one week to capture state.
4. **Collapse the dual R2-series-creation paths.** Pick a single scheme (recommend team-pair IDs derived from game data, which is what the production state has converged to). Update `_compute_next_round_slot` to match, simplify the auto-advance flow, drop the sibling-fallback patch.
5. **Replace `PlayoffSeries.top_wins/bottom_wins` denormalized cache with a view or computed column.** Sprint 96 already filed this; Sprint 97's incident reinforces it. The denormalization is the source of every drift we've patched around.

---

## Backlog Refresh

- Removed from `specs/BACKLOG.md`: the "Harden round-transition game ingest" entry (shipped as Sprint 97's playoff_series_backfill).
- Added: alerting on sync gaps; cron env root-cause investigation; collapse dual R2-series-creation paths.
