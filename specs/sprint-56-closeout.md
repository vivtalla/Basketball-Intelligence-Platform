# Sprint 56 Closeout — Player Impact + Profile Clarity

## Summary

Sprint 56 added a clearer Team Impact layer to the MVP tracker and cleaned up the player profile so Shot Lab owns shot analysis without burying the page in repeated panels.

Branch: `codex/sprint-56-player-impact-profile-clarity`

## Shipped

- Added additive MVP `team_impact` contracts with team net rating, candidate game W-L, on/off net swing, on/off ORTG/DRTG, minutes, confidence, and explanatory notes.
- Added Team Impact methodology language that frames on/off as team performance per 100 possessions with lineup/sample caveats.
- Added a dedicated Team Impact lens to `/mvp` candidate detail and surfaced team-impact evidence in Voter Room comparisons.
- Reworked player-page play-by-play context into **Team Impact & Clutch** with clearer on/off explanations.
- Cleaned the player profile hierarchy by removing the default `ShotSeasonEvolution` and standalone `ZoneProfilePanel`.
- Kept Shot Lab as the canonical shot-analysis home while preserving important unique workflows:
  - `Diet`: action-type fingerprint and distance profile.
  - `Quality`: expected shot value.
  - `Making`: actual-minus-expected shot making.
  - `Creation`: creation proxies plus recent filtered shot context and Game Explorer links.
  - `Scout Summary`: shooting identity cards.
- Added “why this matters” notes to Shot Lab intelligence views.
- Updated Sprint 56 coordination state and logged a UI-cleanup lesson in `tasks/lessons.md`.

## Deferred / Follow-Ons

- Add lineup-with/without teammate context to Team Impact so on/off can be explained beyond a single player split.
- Add team-impact trend lines over time once dated on/off or lineup snapshots are persisted.
- Add “example possessions” links directly from Shot Lab quality/making bins, not only recent filtered shots.
- Revisit `ShotSeasonEvolution` later as a compact career-change story if it can answer a distinct question from current Shot Lab intelligence.
- Add profile-section navigation or collapsible deep-dive controls if the player page grows again.

## Verification

- `backend/venv/bin/python -m py_compile backend/models/mvp.py backend/services/mvp_service.py`
- `backend/venv/bin/python -m pytest backend/tests/test_mvp_service.py -q`
  - `15 passed`
- `npm run lint`
- `npm run build`
- `git diff --check`

## Workflow Notes

- Team Impact used existing `PlayerOnOff`, `TeamSeasonStat`, and `PlayerGameLog` rows; no migration was needed.
- On/off confidence now considers both on-court and off-court minutes so large starter samples do not overstate confidence when bench/off samples are thin.
- UI cleanup should move unique workflows into the right tab instead of deleting them. The action fingerprint, distance profile, and Game Explorer shot links survived by moving into Diet/Creation.

## Next Sprint Seeds

- Build a player profile navigation layer if the profile continues to gain high-value sections.
- Add lineup-aware explanations to MVP Team Impact and player-page Team Impact & Clutch.
- Add richer replay handoffs from Shot Lab Quality/Making/Creation bins into Game Explorer.
- Add Shot Intelligence Ops to `/coverage` for freshness, partial linkage, and baseline readiness.
