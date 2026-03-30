# Sprint 17 Closeout

**Sprint:** 17  
**Date:** 2026-03-30  
**Owner:** Codex  
**Status:** Final

---

## Shipped

- Added team rotation intelligence as a new analyst workflow on team pages
- Added `GET /api/teams/{abbr}/rotation-report?season=...` backed by existing warehouse tables only
- Added the `Rotation Intelligence` team-page section with starter stability, risers/fallers, impact anchors, and recommended game links
- Added Sprint 17 workflow artifacts:
  - `specs/sprint-17-team-rotation-intelligence.md`
  - `specs/sprint-17-review-note.md`
  - `specs/sprint-17-optimizer-note.md`
- Fixed a pre-existing React hook-order lint blocker in `frontend/src/components/SeasonSplits.tsx`
- Merged Sprint 17 to `master`

## Deferred / Not Finished

- No platform-wide visual refresh shipped in Sprint 17
- `2025-26` warehouse completion remains an operational follow-through lane rather than Sprint 17 feature work

## Coordination Lessons

- The four-role workflow worked cleanly once the architect artifact and gate notes were recorded in `specs/`
- Using a clean merge worktree avoided conflicts with older dirty local checkouts during final merge and push

## Technical Lessons

- Local test launches on alternate ports need matching `CORS_ORIGINS` or the frontend can look empty despite healthy backend responses
- Running reviewer verification through both `npm run lint` and `npm run build` surfaced one real pre-existing UI bug and one environment-only font-fetch issue

## Next Sprint Seeds

- Choose and implement a platform color refresh with a deliberate palette direction rather than incremental color tweaks
- Candidate palette directions:
  - Hardwood editorial: cream, charcoal, deep forest, brass
  - Arena night: graphite, steel, electric blue, ember
  - Data lab: warm white, ink, teal, signal orange
  - Broadcast classic: off-black, cool gray, crimson, gold
- Decide whether the color refresh is platform-wide or starts with the home, team, and player surfaces only
- Continue `2025-26` warehouse catch-up operationally while the next feature sprint proceeds
