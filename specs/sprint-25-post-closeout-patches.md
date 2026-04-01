# Sprint 25 Post-Closeout Patches

**Date:** 2026-04-01  
**Owner:** Codex  
**Status:** Pushed to `master` in `18d9a13`

---

## Summary

This note captures the small patch pass that happened immediately after Sprint 25 closeout during live manual QA. These were not new sprint features; they were follow-up fixes needed to make the local app stable and readable for continued testing.

## Pushed Fixes

- Home-page league leaders now return canonical full player names instead of surname-only rows
- `TrajectoryTracker` now renders a safe error message string instead of a raw `Error` object
- `CustomMetricBuilder` got the same safe error-message handling
- `frontend/next.config.ts` now explicitly allows `127.0.0.1` and `localhost` in local dev

## Relevant Files

- `backend/routers/leaderboards.py`
- `frontend/src/components/TrajectoryTracker.tsx`
- `frontend/src/components/CustomMetricBuilder.tsx`
- `frontend/next.config.ts`

## Local Dev / Manual Testing Notes

- Manual testing during this patch pass used:
  - frontend: `http://127.0.0.1:3001`
  - backend: `http://127.0.0.1:8001`
- The frontend local env was corrected to point at `http://127.0.0.1:8001` through ignored `frontend/.env.local`
- If the UI appears blank in a future local session, first verify:
  1. backend is actually serving on `8001`
  2. frontend is running on `3001`
  3. local frontend env still points to `8001`, not `8000`

## What Claude Should Know

- The repo itself is clean and pushed after these patches; `master` and `origin/master` match at `18d9a13`
- The `.env.local` fix is intentionally local-only and ignored by git
- The next best move is to continue minor live patches if the user finds more UI/UX issues, then begin Sprint 26 planning from the updated `master` state
