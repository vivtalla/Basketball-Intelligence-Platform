# Sprint 62 Closeout

**Sprint:** 62  
**Date:** 2026-04-21  
**Owner:** Codex  
**Branch:** `feature/sprint-62-style-intelligence-and-team-shooting-splits`  
**Status:** Closeout prepared on branch; pending merge to `master`

---

## Shipped

- Added canonical persisted official team shooting splits with new `team_shooting_split_stats` storage, Alembic revision `0009_team_shooting_split_stats`, and ORM coverage in `backend/db/models.py`.
- Added official `TeamDashboardByShootingSplits` parsing and sync flow: `nba_client.get_team_shooting_splits(season, team_id)` plus `sync_official_team_shooting_splits(db, season, team_ids=None)`.
- Updated `backend/data/daily_sync.sh` so official team shooting splits refresh immediately after team general splits in the daily sync path.
- Added DB-first `GET /api/teams/{abbr}/shooting-splits?season=...` and additive contracts for `TeamShootingSplitRow` and `TeamShootingSplitsResponse`.
- Extended Style X-Ray with additive `shot_profile_drivers` and `StyleShotProfileDriver`, built from persisted team shooting splits instead of live official calls.
- Reworked X-Ray scenario generation to use live shot-profile drivers, and enriched label reason plus neighbor summaries with shot-profile evidence.
- Upgraded the team `Splits` tab into a dual workspace:
  - `Situational` keeps the existing general splits workflow
  - `Shooting` introduces the new `TeamShootingSplitsPanel`
- Added the full-width `Shot Profile Drivers` card to the X-Ray surface and kept existing Compare, Prep, and What-If handoffs intact.
- Fixed a follow-up UI bug where the team-page split-mode toggle could override the user’s selection when both datasets were present.
- Added targeted backend coverage for shooting-splits parsing, sync/API/schema paths, and Style X-Ray shot-profile driver behavior.

## Deferred / Follow-Ons

- Standalone compare/prep/team-defense shooting-splits workflows remain out of scope; Sprint 62 kept the first rollout focused on team page + Style X-Ray.
- The live `AssitedShotTeamDashboard` payload looked suspicious during QA and should be sanity-checked against upstream semantics before any heavier product use of that family.
- Backfill/ops affordances for team shooting splits still rely on existing daily sync and targeted job entry points rather than a dedicated new ops panel.
- Style X-Ray now has stronger shot-profile grounding, but longer-horizon archetype movement/history and richer matchup bridges remain future work.

## Verification

- `backend/venv/bin/python -m pytest backend/tests/test_team_dashboard_parsing.py backend/tests/test_official_team_stats.py backend/tests/test_schema_migrations.py backend/tests/test_style_xray_shot_profile.py -q`
- `backend/venv/bin/python -m py_compile backend/data/nba_client.py backend/models/styles.py backend/models/team.py backend/routers/styles.py backend/routers/teams.py backend/services/sync_service.py`
- `npm run lint`
- `npm run build`
- `git diff --check`
- Local QA:
  - `GET /api/teams/OKC/splits?season=2025-26`
  - `GET /api/teams/OKC/shooting-splits?season=2025-26`
  - `http://localhost:3000/teams/OKC?tab=splits&season=2025-26`
  - `http://localhost:3000/insights?tab=xray&team=OKC&season=2025-26`

## Workflow Lessons

- Sprint closeout is a repo artifact set, not just code + tests. Implementation work is not complete until the `AGENTS.md` checklist artifacts are updated or explicitly marked pending if merge-dependent.
- Dual-mode UI surfaces should not auto-correct the selected mode after data arrives. Respect the user’s explicit tab/toggle choice once the page is interactive.
- New official split families should get a quick semantic QA pass against live payloads during rollout, especially when labels or percentage fields are easy to misread upstream.

## Next Sprint Seeds

1. **Shot-profile workflow expansion:** carry canonical team shooting splits into Compare, Prep, and team-defense workflows now that the storage shape is stable.
2. **Assisted-shot validation:** audit `AssitedShotTeamDashboard` semantics and normalize any misleading fields before relying on that family for stronger product messaging.
3. **Style Intelligence follow-ons:** deepen X-Ray archetype movement history, neighbor context, and matchup/action bridges on top of the new shot-profile driver layer.
4. **Shooting-split ops/backfill visibility:** decide whether the new split family needs dedicated coverage health or job controls beyond the existing daily sync path.
