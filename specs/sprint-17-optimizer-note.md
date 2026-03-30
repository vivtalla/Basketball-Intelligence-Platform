## Sprint 17 Optimizer Note

Status: Ready to Merge

### Scope reviewed

- new rotation-report query path in `backend/services/team_rotation_service.py`
- new frontend fetch path and team-page rendering flow

### Findings

No optimization changes required beyond the current implementation.

### Rationale

- Backend work is bounded to four main reads for the report: recent games, recent game-player rows, season rows, and on/off rows, plus a single player lookup.
- The service avoids per-player or per-game database round trips and computes recommendation notes in memory from already-fetched rows.
- Frontend data fetching is scoped to the intelligence tab and uses a dedicated SWR key, so it does not add broad over-fetching elsewhere on the team page.
- The rotation panel reuses the existing team page flow rather than duplicating the larger intelligence payload.
