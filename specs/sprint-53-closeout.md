# Sprint 53 Closeout — MVP Race Timeline And Refined Methodology

Date: 2026-04-18  
Branch: `codex/sprint-53-mvp-race-timeline`  
Base: `master`

## Shipped

- Added Alembic revision `0007_mvp_race_timeline` for DB-first MVP race timeline storage:
  - `mvp_race_snapshots`
  - `mvp_race_snapshot_candidates`
- Added MVP snapshot materialization:
  - `backend/services/mvp_timeline_service.py`
  - `backend/data/mvp_timeline_snapshots.py`
  - `materialize_mvp_snapshot` warehouse job dispatch
  - idempotent same-season/date/profile/min-GP replacement behavior
- Added `GET /api/mvp/timeline` with weekly reconstructed voter timeline output:
  - methodology labels
  - horizon start/end
  - weekly rank/score/stat series
  - risers/fallers/steady leaders
  - compact movement reasons
- Replaced the first thin movement strip with a larger `/mvp` Voter Timeline:
  - rank-path chart
  - hoverable candidate paths
  - candidate inclusion controls
  - non-overlapping right-edge labels
  - methodology and limitation copy
- Implemented refined MVP methodology v3:
  - `mvp_case_v3_refined`
  - Basketball Value Score
  - Award Case Score
  - Basketball Value Rank, Award Case Rank, Ballot-Eligible Rank
  - additive candidate confidence objects
  - award modifiers for team framing, eligibility pressure, clutch, momentum, and signature games
  - structured qualitative lenses for role difficulty, scalability, game control, two-way pressure, and playoff translation
- Demoted legacy `box_first`, `balanced`, and `impact_consensus` profiles into sensitivity comparison while keeping backward-compatible API support.
- Updated `/mvp` methodology explanations throughout the page so a standalone viewer can understand score purpose, confidence, context-only signals, and timeline limits.
- Added canonical methodology doc at `specs/mvp-tracker-methodology-brief.md`.
- Fixed game-log-derived MVP rates so zero-minute/DNP rows do not dilute timeline and split PPG.

## Deferred

- True historical reconstruction for impact, Gravity, clutch, opponent-adjusted context, and signature-game leverage once dated source rows exist.
- Production scheduling for daily MVP snapshot jobs after deployment cadence is finalized.
- MVP voter-room compare mode for two or three candidates.
- Player-page MVP case embeds once the v3 candidate contract settles.
- Coverage-ops dashboard for official tracking/play-type/hustle/Gravity source health.
- Calibration pass for Award Case modifier caps after more live-user review.

## Verification

- `backend/venv/bin/python -m py_compile backend/services/mvp_service.py backend/services/mvp_timeline_service.py`
- `backend/venv/bin/python -m pytest backend/tests/test_mvp_service.py -q`
- `backend/venv/bin/python -m pytest backend/tests/test_schema_migrations.py -q`
- `npm run lint` from `frontend/`
- `npm run build` from `frontend/`
- `git diff --check`
- Local API smoke against `http://127.0.0.1:8000`:
  - `/api/mvp/race?season=2025-26&top=10&min_gp=20&profile=balanced`
  - `/api/mvp/timeline?season=2025-26&profile=balanced&days=210&top=8&min_gp=20`

## Notes

- The current `/mvp` default is now Award Case Rank, with Basketball Value kept visible as the analytical base.
- Weekly timeline scoring intentionally uses only historical game-log inputs that exist at each cutoff. Current impact, Gravity, clutch, and opponent-adjusted context remain current-case annotations until dated rows are persisted.
- The DNP/zero-minute fix matters because NBA game-log feeds can include rows that are real schedule entries but not played games. Timeline PPG and case splits now use played-game denominators.
