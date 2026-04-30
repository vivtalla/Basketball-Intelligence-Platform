# Sprint 81 Closeout — Data Foundation Closeout

**Completed:** 2026-04-30
**Type:** Two-stream parallel sprint (Stream A scrapers, Stream B architecture+methodology+domains)
**Test count:** 415 → 464 backend tests (+49 new)

---

## What Shipped

### Stream A — Real Data Scrapers (replace seed CSV stubs)

All three scrapers follow the same pattern: rate-limited HTTP module → idempotent upsert into existing Sprint 78 tables → silent fallback to seed CSV on any failure (network, anti-bot, parse error). New shared base in `backend/data/scrapers/_base.py` (`HttpScraper` + `ScraperError`) handles user-agent rotation, retry/backoff, and the 2s rate-limit ceiling.

#### A1 — Spotrac Salary Scraper
- New: `backend/data/scrapers/spotrac.py` (~30 team cap pages, content-based table parser)
- Modified: `backend/services/salary_ingestion_service.py` — `--source spotrac` branch + name → player_id resolution + transparent fallback to seed CSV
- Modified: `backend/data/sync_salaries.py` — default source flipped to `spotrac` (with seed_csv fallback)
- 7 new tests in `backend/tests/test_spotrac_scraper.py` (parser fixtures, anti-bot detection, fallback behavior, idempotency)
- `salary_source` field flips from `"estimated"` to `"spotrac"` for resolved rows; UI badge updates automatically

#### A2 — ProSportsTransactions Injury History Scraper
- New: `backend/data/scrapers/prosportstransactions.py` — paginated injury archive scraper, regex-based body-part classification (17 body parts), severity classifier (4 tiers), per-player FIFO pairing of relinquished → acquired events
- Modified: `backend/data/sync_injury_history.py` — `--source prosportstransactions` mode with player-name → player_id resolution; default backfill window 2020-onward
- 10 new tests in `backend/tests/test_pst_scraper.py` (body-part classification, season boundary, FIFO pairing, fallback)

#### A3 — Sports Reference Draft Prospects Scraper
- New: `backend/data/scrapers/sportsreference_cbb.py` — fetches per-game stats page for the season, sorts by PPG, filters to ≥10 PPG, caps at top-N (default 100)
- Tolerates Sports Reference's HTML-comment-wrapped table anti-scrape pattern
- Modified: `backend/data/sync_draft_prospects.py` — `--source sportsreference` branch with seed CSV fallback
- 8 new tests in `backend/tests/test_sportsreference_scraper.py` (parser, comment-wrapped tables, low-PPG filter, fallback, idempotency)

### Stream B — Architecture, Methodology, New Data Domains

#### B1 — Legacy `play_by_play` Retirement
Frees ~677 MB / 30% of DB size. Migration completed in three steps:

1. **Reader migrations (9 files):**
   - `routers/advanced.py` — distinct game count → `PlayByPlayEvent`
   - `services/team_intelligence_service.py` — distinct game count → `PlayByPlayEvent`
   - `services/possession_diary_service.py` — order_by → `PlayByPlayEvent.order_index`
   - `services/game_detail_assembler.py` — drop legacy fallback (only one branch needed now)
   - `services/shot_lab_service.py` — distinct game IDs → `PlayByPlayEvent`
   - `services/pbp_service.py` — `legacy_event_count` always returns 0; legacy branch deleted from `describe_event_stream_for_game`; `load_pbp_events_for_game` simplified
   - `services/game_trajectory_service.py` — order_by → `PlayByPlayEvent.order_index`
   - `services/warehouse_service.py` — dropped delete-before-insert + dual-write to `PlayByPlay`; coverage report no longer surfaces a "legacy" bucket
   - `services/pbp_sync_service.py` — full migration: `_store_pbp_events`, `_replace_pbp_events`, `_load_stored_pbp_events`, `existing_raw` check all switched to `PlayByPlayEvent`. New `season` parameter threaded through the helpers since `PlayByPlayEvent.season` is non-null.

2. **Sync script migrations (2 files):**
   - `data/sync_playoff_pbp.py` and `data/sync_today_playoff_finals.py` — existence checks switched to `PlayByPlayEvent`

3. **Model + migration:**
   - Removed `PlayByPlay` ORM class and `GameLog.play_by_play` relationship from `db/models.py`
   - New migration `0018_sprint81_drop_legacy_pbp.py` — `DROP TABLE play_by_play` with `_has_table()` idempotent guard
   - New CI guard test `tests/test_no_legacy_pbp_imports.py` — fails if any service file imports `PlayByPlay` again
   - Three legacy-fallback tests in `test_shotchart_db_first.py` deleted (tested behavior that no longer exists)

Run `VACUUM FULL` on the Hetzner VM after deploy to reclaim the bytes.

#### B2 — Historical Modifier Materialization → Activates `mvp_case_v5`
- New table `award_case_candidates` (migration `0019_sprint81_award_case_candidates.py`) — Basketball Value + 5-pillar modifier vector per (player, season, award_type)
- New ORM model `AwardCaseCandidate` in `db/models.py`
- New script `data/materialize_award_modifiers.py`:
  - `_basketball_value()` — composite of per-game production + TS%-above-league-average + GP reliability factor (~50 = generational MVP, ~30 = strong candidate, ~15 = All-NBA contender)
  - `_team_framing()` — joined through `TeamSeasonStat × Team` to read team `(w, l)` for the season; centered so 41-41 = 0, 60-22 ≈ +0.5
  - `_eligibility_pressure()` — penalizes <65 GP / <30 mpg per the new NBA eligibility rule
  - `_clutch_proxy()` — uses `season_stats.clutch_*` columns when present, else 0
  - `_momentum_proxy()`, `_signature_games_proxy()` — return 0 for historical seasons (no per-game WPA available offline); calibrator naturally weighs these lower on historical folds
- Modified `services/award_calibration_service.py` — new `_load_calibration_dataset()` helper joins `award_voting × award_case_candidates`; `calibrate_award_case_weights()` runs LOO-CV when ≥5 seasons available, applies ±0.04 drift cap, returns `calibration_pending=False` only when LOO-CV Spearman ≥ 0.7
- Acceptance gate: if Spearman < 0.7, surface the failure in `notes` and keep priors (don't ship calibrated weights worse than hand-tuned defaults)
- 9 new tests in `backend/tests/test_award_modifier_materialization.py`

#### B3 — Missing Official Data Domains
Closes the two highest-priority gaps from `specs/official-data-source-matrix.md`:

**Player split dashboards** (`LeagueDashPlayerStats` family):
- New table `player_split_stats` — mirror of `team_split_stats` per-player
- New ORM model `PlayerSplitStat` in `db/models.py`
- New nba_client wrapper `get_player_general_splits()` + 5 dataset families (Location, W/L, Days Rest, Month, Pre/Post All-Star)
- New service `sync_official_player_general_splits()` in `sync_service.py`
- New endpoint `/api/players/{player_id}/splits` — returns rows grouped by family

**Play type stats** (Synergy `PlayTypeStats` family):
- New table `play_type_stats` — per-player by archetype with possession + efficiency triplet (poss, ppp, percentile)
- New ORM model `PlayTypeStat` in `db/models.py`
- New service `sync_official_play_type_stats()` iterating 11 Synergy families (Isolation, Transition, PRBallHandler, PRRollMan, Postup, Spotup, Handoff, Cut, OffScreen, Putbacks, Misc); reuses existing `get_synergy_player_play_types()` wrapper
- New endpoint `/api/players/{player_id}/play-types` — sorted by possession volume

Migration `0020_sprint81_player_splits_play_types.py` creates both tables idempotently. Frontend rendering deferred to Sprint 82.

6 new tests in `backend/tests/test_player_splits_play_types.py` (sync upsert + idempotency + endpoint shape + 404 behavior).

---

## Files Changed — Summary

### New
- `backend/data/scrapers/__init__.py`
- `backend/data/scrapers/_base.py`
- `backend/data/scrapers/spotrac.py`
- `backend/data/scrapers/prosportstransactions.py`
- `backend/data/scrapers/sportsreference_cbb.py`
- `backend/data/materialize_award_modifiers.py`
- `backend/alembic/versions/0018_sprint81_drop_legacy_pbp.py`
- `backend/alembic/versions/0019_sprint81_award_case_candidates.py`
- `backend/alembic/versions/0020_sprint81_player_splits_play_types.py`
- `backend/tests/test_spotrac_scraper.py`
- `backend/tests/test_pst_scraper.py`
- `backend/tests/test_sportsreference_scraper.py`
- `backend/tests/test_award_modifier_materialization.py`
- `backend/tests/test_no_legacy_pbp_imports.py`
- `backend/tests/test_player_splits_play_types.py`
- `specs/sprint-81-closeout.md`

### Modified
- `backend/services/salary_ingestion_service.py` — Spotrac branch + fallback
- `backend/services/award_calibration_service.py` — query materialized table; LOO-CV gate; drift cap
- `backend/services/pbp_service.py`, `pbp_sync_service.py`, `warehouse_service.py`, `team_intelligence_service.py`, `possession_diary_service.py`, `game_detail_assembler.py`, `game_trajectory_service.py`, `shot_lab_service.py` — `PlayByPlay` → `PlayByPlayEvent` migration
- `backend/services/sync_service.py` — `sync_official_player_general_splits`, `sync_official_play_type_stats`
- `backend/routers/advanced.py` — distinct game count
- `backend/routers/players.py` — `/splits` and `/play-types` endpoints
- `backend/db/models.py` — drop `PlayByPlay`, add `PlayerSplitStat`, `PlayTypeStat`, `AwardCaseCandidate`
- `backend/data/sync_salaries.py`, `sync_injury_history.py`, `sync_draft_prospects.py` — new `--source <scraper>` choices with fallback
- `backend/data/sync_playoff_pbp.py`, `sync_today_playoff_finals.py` — existence checks → `PlayByPlayEvent`
- `backend/data/nba_client.py` — `get_player_general_splits()` + `playerdashboardbygeneralsplits` import
- `backend/data/daily_sync.sh` — wired three new scrapers + materializer + two new domain syncs
- `backend/tests/test_schema_migrations.py` — head revision → `0020_sprint81_player_splits_play_types`
- `backend/tests/test_game_detail_assembler.py`, `test_game_trajectory.py`, `test_possession_diary.py`, `test_series_odds_history.py`, `test_shotchart_db_first.py`, `test_sprint32_team_prep_core.py` — `PlayByPlay` → `PlayByPlayEvent` fixtures (seed `WarehouseGame` + add `season`/`order_index`)

---

## Verification

| Check | Result |
|-------|--------|
| Backend test suite | **464 passed** (was 415, +49 net new) |
| Frontend `npx tsc --noEmit` | Clean |
| `daily_sync.sh --dry-run` | Lists all new sync targets in correct order |
| Alembic head revision | `0020_sprint81_player_splits_play_types` |
| CI guard `test_no_legacy_pbp_imports.py` | Passes — no service file imports retired `PlayByPlay` |
| Scraper fallback tests | All three scrapers tested for ScraperError → seed CSV fallback path |

---

## Pending — Production Rollout

Once the Hetzner VM picks up these changes (next git pull on `5.78.114.15`):

1. **Run migrations:** `python -m alembic upgrade head` (creates 3 new tables, drops `play_by_play`)
2. **VACUUM FULL** to reclaim 677 MB after `play_by_play` drop
3. **First nightly run** at 6am UTC will exercise all three scrapers + new domain syncs. Monitor `/var/log/bip-sync.log` for `fallback_used=true` markers.
4. **First materialization run** will populate `award_case_candidates` from the existing 57 `award_voting` rows. Calibration will run on next `mvp_case` request.
5. **R2 backups** continue automatically — the new tables are included in the pg_dump stream.

---

## Out of Scope (deferred to Sprint 82+)

- **Frontend rendering** of `/api/players/{id}/splits` and `/api/players/{id}/play-types` (endpoints ship in this sprint, UI in next)
- **Tracking / hustle / passing dashboards** — flagged in data architecture but deferred to keep scope sane
- **Cloudscraper / Playwright fallback for Spotrac** — only if basic scraper fails repeatedly
- **`game_logs` legacy table retirement** — separate effort; `play_by_play` was the high-bytes target
- **`player_game_logs` → `game_player_stats` migration** — not blocking
- **DPOY / MIP / 6MOY award calibration** — same code path as MVP, but separate seed CSV; deferred
- **FastAPI public deploy** — Sprint 82 candidate

---

## Lessons

- Default arguments in Python bind at function-definition time. `_load_calibration_dataset(db, csv_path=SEED_CSV_PATH)` doesn't honor a runtime `patch("module.SEED_CSV_PATH", ...)` unless the call site explicitly forwards the patched value.
- `PlayByPlayEvent.action_number` is nullable; `order_index` is the safe ordering column when migrating reader code from `PlayByPlay`.
- Sports Reference wraps tables in HTML comments as anti-scrape; `BeautifulSoup.find_all(string=Comment)` + nested `BeautifulSoup(str(comment))` handles both cases.
- Tests using `from db.models import X` break at collection time when `X` is removed — running the full suite after retiring a model surfaces fixture cleanup work that grep wouldn't catch.
- httpx isn't a pinned dev dep; FastAPI `TestClient` won't import. Existing convention is to call route handlers directly with an in-memory SQLite session and dependency injection bypassed.
