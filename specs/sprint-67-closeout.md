# Sprint 67 Closeout

**Sprint:** 67 — Decision Intelligence (Player Archetypes + Shot Diagnosis + Scouting Brief)
**Date:** 2026-04-24
**Owner:** Claude (single-stream sprint; both stream A and stream B executed on one branch)
**Branch:** `feature/sprint-67-decision-intelligence`
**Status:** Final

---

## Theme

Make the CourtVue player page answer a basketball question — *"Who is this player, how do they create value, and what should I do with that?"* — in under a minute, rather than just displaying stats. The three features shipped this sprint compound: archetype labels and shot diagnosis tags are the raw material the scouting brief consumes.

---

## Shipped

### Stream A — Player Archetype + Similarity Engine

- **A1** — Deterministic 15-archetype taxonomy locked in `specs/sprint-67-archetype-rules.md` after three tune passes. Every load-bearing threshold has an inline rationale note; every fixture has a dual-eligibility note where it can route to more than one archetype. Explicit `balanced_role` (rotation player with no rule firing) vs `developmental` (thin sample) keys rather than a reason_variant flag.
- **B1** — `backend/services/player_archetype_service.py`: z-score feature extraction over `season_stats` + `Player.height` (string-parsed), per-season TTL-cached peer-pool frame (10 min current / 24 h historical), 15-rule first-match-wins classifier matching the Sprint-60 team Style-X-Ray pattern, confidence bands (`_archetype_confidence`), top-4 contributor fingerprint, TOT-preferred subject-row selection for mid-season trades.
- **B2** — `backend/services/similarity_service.py` extended with a `mode` parameter (`season | age | team_fit`) and a 13-feature V2 distance (9 legacy + `par3`, `ftr`, `stl_pg`, `blk_pg`). Every V2 comp carries archetype label + key + confidence via batch-classify. Legacy `find_similar_players(cross_era=...)` signature preserved untouched for backwards compatibility. `team_fit` mode returns `NotImplementedError` in the service and a `501` from the router (deferred to follow-up task B10).
- **B3/B4** — `GET /api/archetype/{player_id}` and `mode=...` extension on `GET /api/similarity/{player_id}` (route-level).
- **C1/C2** — Archetype and similarity-v2 types + API client functions appended to `frontend/src/lib/types.ts` and `frontend/src/lib/api.ts` under the AGENTS.md append-only lock policy.
- **C3** — `PlayerArchetypeProfile.tsx` + `ArchetypeContributors.tsx` + `ArchetypeMethodologyDrawer.tsx` ported from `components/xray/` patterns. Hero card hides the fingerprint for developmental/balanced-role so we don't show a zero-signal bar chart when the rules intentionally said "no dominant signal."
- **C4** — `PlayerSimilarity.tsx` rewritten with a Season / Age / Team-Fit tab header. Team-Fit shows a deferred-state card rather than pretending to work. Each comp card carries a confidence-tinted archetype pill.
- **C7a** — `usePlayerArchetype.ts` SWR hooks (archetype + similarity-with-archetype) with null-playerId / empty-season short-circuits.
- Wired `<PlayerArchetypeProfile>` directly above `<PlayerSimilarity>` on `PlayerDashboard` so the archetype label contextualizes the comps.

### Stream B — Shot Diagnosis + Scouting Brief

- **A2** — 12-tag shot diagnosis taxonomy appended to the sprint spec. Triggers keyed on already-computed quality/creation/identity deltas (not raw values) so era/rule changes don't require re-tuning. Explicit sustainability derivation (zone-delta stdev × coverage), creation-burden thresholds, and headline template.
- **B5** — `backend/services/shot_diagnosis_service.py`: pure layer over `shot_intelligence_service` outputs. 12 tag rules + minimum-sample gate (50 shots) + sustainability/creation-burden derivation + headline composer. Tag ranking caps at 4 and drops red-low-confidence noise. Archetype-derived gating features (size, `ftr_z`, `par3_z`) attached best-effort.
- **B6** — `GET /api/shotchart/{player_id}/diagnosis` route in `backend/routers/shotchart.py`. Reuses the existing `_player_shot_context` loader and `build_shot_quality_response` / `build_shot_creation_response` so shot-loading code stays in one place.
- **B7** — `backend/services/scouting_brief_service.py`: composes five cards (Role, Strengths/Weaknesses, Usage & Efficiency, Shot Profile, Trajectory) from archetype + opportunity + shot diagnosis + trajectory services. Each card is best-effort; a failing source service skips its card with a warning rather than propagating. Composition is fully server-side so confidence language stays consistent.
- **B8** — `GET /api/players/{player_id}/scouting-brief` route.
- **C1/C2** — Diagnosis + scouting brief contracts appended to `types.ts` and `api.ts`.
- **C5** — `ShotDiagnosisPanel.tsx` rendered beneath `<ShotIntelligencePanel>` in `ShotChart` for intelligence views (quality/making/creation/summary). Grade+sentiment drive the chip palette (green strength, red risk, yellow otherwise).
- **C6** — `ScoutingBrief.tsx` 5-card strip inserted directly below `<PlayerHeader>` on `PlayerDashboard`. Server-ordered cards with defensive re-sort, confidence pill per card, deep-link header. Fails silent when the brief returns zero cards so the page doesn't render a stub strip.
- **C7b** — `usePlayerShotDiagnosis.ts` SWR hooks (diagnosis + scouting brief).

### Cruft sweep

Four untracked stale files from the Sprint 65 closeout's incomplete cleanup were blocking `npm run build`:
- `frontend/src/components/UsageBurdenMatrix.tsx`
- `frontend/src/components/UsageLoadBoard.tsx`
- `frontend/src/components/UsageEfficiencyDashboard.tsx` (pre-rename duplicate of the shipped `OpportunityDashboard.tsx`)
- `backend/services/usage_efficiency_service.py` (pre-rename duplicate)

All four referenced the `UsageEfficiencyPlayerRow` type that Sprint 65 intentionally removed. None were in git history (hence still untracked). Deleted.

---

## Deferred / Not Finished

- **B10 — Team-Fit similarity mode.** Service raises `NotImplementedError`; router returns 501; frontend tab shows deferred state. Backend scaffolding (`_build_candidate_pool` mode branch) is in place to plug in.
- **A3 — Hand-label tuning.** Didn't run the 30-player hand-label validation against the archetype rules. Live 2024-25 sanity trace against the spec's expectations table passed 9/10 (only mismatch was Lu Dort → `movement_shooter` instead of `switchable_stopper`, which is the honest numerical label for his 2024-25 profile with `ftr_z = -1.50`).
- **C9 — Inbound deep-link banners** (e.g., scouting brief card → Shot Lab with preselected diagnosis tag) were not implemented. Deep links work as simple anchors today.
- **C8 — Copy polish pass** on tag/card labels was skipped. Language is accurate but not yet tuned for coaching ergonomics.

---

## Verification

- **Backend pytest:** **243 passed** (was 196 before Sprint 67) — 47 new tests total: 14 archetype, 8 similarity modes, 20 shot diagnosis, 5 scouting brief. No regressions.
- **Frontend `npm run build`:** clean. Required the Sprint-65-cruft sweep to pass, which also fixes a latent build-breaker the previous sprint had missed.
- **Frontend `npm run lint`:** 0 errors, 7 pre-existing warnings in `usePlayerStats.ts` (unused imports Sprint 59 left behind).
- **Frontend `tsc --noEmit`:** clean.
- **Live-DB smoke:** ran `build_scouting_brief` against Jokić, SGA, and Tatum on 2024-25. All three surface real role/strengths/usage-efficiency/shot-profile cards. Jokić routes to `Elite rim pressure — Sustainable`. SGA routes to `Foul-drawing creator · Dead corners — Sustainable`. Tatum's Shot Profile correctly skips (shot-chart cache thin). Trajectory card skips for all three (service is 2025-26 only — known constraint).

---

## Coordination Lessons

- **Tight spec-first discipline saved real rework.** Three A1 tune passes before a line of code surfaced two routing bugs (Gobert's offensive profile swallowing the Defensive Anchor path; Ja Morant's fixture actually firing Lead Ball-Handler, not Rim Pressure Guard) and one coverage gap (SGA-band mid-range creators falling to Balanced). If those had been found via failing tests after B1 shipped, it'd have been hours of rework.
- **The live-DB smoke at the end caught two real bugs** — an `AttributeError` on `cached.last_synced_at` (correct field is `fetched_at`) that silently routed the Shot Profile card to graceful-skip, and a `usg_pct` storage-convention error that displayed `0.3%` instead of `30%`. Both were invisible to unit tests because they depend on real warehouse field names. **Rule earned for next sprint:** any composer that touches ≥3 underlying services must have a live-DB smoke as part of done-criteria, not just pytest.
- **Cruft sweeps should be part of sprint kickoff.** The four stale Usage* files had been sitting in the working tree since Sprint 65 closed. The closeout *claimed* they were deleted, but they were actually untracked (so `git rm` never ran), sitting there silently until `npm run build` tripped on them mid-Sprint-67. Earned a lesson: **at kickoff, run `npm run build && pytest` against the baseline branch before touching code** to catch carry-over breakage early.

---

## Workflow Lessons

- **Defensive best-effort composition is worth the verbosity.** `scouting_brief_service` catches every downstream service failure individually and reports warnings per skipped card. That let the live-DB smoke render three working cards while the Shot Profile card was broken in a way that would have 500'd the whole endpoint otherwise. The UX stays honest (fewer cards, clearly marked) rather than failing the whole brief.
- **Port-don't-recreate stays the right call.** The archetype frontend components ported the Sprint-60 team Style-X-Ray patterns directly (fingerprint bar logic, methodology drawer shape, confidence pill coloring) rather than inventing a new visual language. Two benefits: the player page feels consistent with the team insights surface, and the port took a fraction of the time a from-scratch design would have.
- **Append-only discipline on shared TS files is painless once you commit to it.** Neither `types.ts` nor `api.ts` required any conflict resolution this sprint despite both growing in two distinct stream landings. The simple rule — add at the bottom, never mutate in place — is a cheap coordination tax with zero merge risk.

---

## Technical Lessons

- **Deterministic rules are the right discipline for archetypes and diagnosis tags.** Both engines are auditable, explainable in the methodology drawer, and cheap to cache. They also gave us golden tests per archetype / per tag that would be nearly impossible with an ML approach. When users want a "neural" engine, point at the drawer copy.
- **`SeasonStat`'s mid-season-trade handling matters more than expected.** Without the TOT-preferred subject-row selection, mid-season-trade players would either have been classified twice (once per team) or fallen through to developmental. The rule was a 6-line helper but invisible to the spec until I actually looked at the data model.
- **Per-season z-score pools work better than global pools.** Era independence is free; the old Sprint-60 team-X-Ray code was already using this discipline; reusing it for players kept Luka 2023-24 comparable to Tatum 2024-25 without any cross-era normalization machinery.
- **`round(x, 1)` on the OpportunityPlayerRow collapses 0.285/0.30/0.32 into an identical 0.3 display.** Discovered during the live smoke (Jokić, SGA, Tatum all showed "Usage 30.0%" despite having different actual values). Not scope for Sprint 67 but a real cosmetic bug in the Opportunity contract. Worth logging as a follow-up.

---

## Next-Sprint Seeds

### Direct follow-ons from Sprint 67

- **Team-Fit similarity mode (B10).** Teammate-duplicate penalty spec is in the A1 doc. Service has the `mode="team_fit"` branch stubbed to raise; wire it in once there's appetite.
- **Hand-label tuning pass (A3).** Pull 30 diverse players, sanity-check their classifications, retune thresholds once. Lu Dort's `movement_shooter` is the canonical edge case to look at.
- **Inbound deep-link banners (C9).** Scouting brief card → Shot Lab with preselected diagnosis tag; mirror the Sprint-65 banner pattern on Compare and Pre-Read.
- **Copy polish (C8).** Coach-readable tag labels across diagnosis and brief.
- **OpportunityPlayerRow usg_pct precision.** `round(x, 1)` collapses distinct values into identical displays; bump to `round(x, 3)` or format at the consumer.

### Natural next sprints the Sprint-67 substrate enables

- **Lineup Fit & Duo Chemistry.** Archetype labels are the natural teammate-compatibility primitive. Grade which archetype pairings outperform their expected net ratings.
- **Printable scouting report.** The on-platform brief is the content; reuse the Sprint-66 Pre-Read packet markdown export pipeline.
- **Team-vs-team archetype matchup matrix.** Team X-Ray archetypes × player archetypes → exploit/vulnerability signals.
- **Player archetype evolution timeline.** Port the team X-Ray `MovementTimeline` to players so a multi-season archetype drift becomes a user-facing surface.
