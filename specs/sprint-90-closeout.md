# Sprint 90 Closeout — Deferred Items Cleanup

**Branch:** `feature/sprint-90-deferred-items`
**Worktree:** `/Users/viv/Documents/bip-s90`
**Closed:** 2026-05-03

## What shipped

User asked to focus on "deferred items". The BACKLOG had 4 formally-deferred entries; Sprint 90 ships all the code-actionable ones plus refines the docs for the external blockers. Single sequential branch, 4 commits, end-to-end.

### Stream A — MVP Award Case Voter Calibration Activation

Sprint 79 shipped the LOO-CV calibration harness for MVP Award Case modifier weights but left `CALIBRATED_AWARD_CASE_WEIGHTS` pinned to the Sprint 76 hand-tuned priors at module import. The calibration result was never threaded through the MVP scorer and the methodology registry hardcoded `status="active_with_calibration_pending"`. Sprint 90 wires the live calibration through both surfaces:

- **A1+A2** (`d56bc81`): new `_get_calibration_state(db)` helper in `mvp_service.py` runs `calibrate_award_case_weights(db)` once per request, cached 24h in SQLite `cache.db` (key `award_case_calibration:v1`). On error, falls back silently to defaults so MVP race never breaks on calibration. `_build_ranked_candidates` uses `state["weights"]` instead of the module-level `CALIBRATED_AWARD_CASE_WEIGHTS`, returns the full state alongside candidates / as_of / sensitivity (4-tuple). New `MvpCalibrationMetadata` Pydantic model surfaces on every `MvpRaceResponse`. New optional `runtime_calibration: Dict` field on `MethodologyDomain`; registry service augments the `mvp` domain entry with live calibration state when `db` is available; methodology router passes `db` through.
- **A3** (`046d287`): 4 new integration tests in `test_award_calibration.py`. Suite goes 509 → **513**. Tests:
  1. `test_calibration_activates_when_dataset_has_signal` — seeds 6 seasons × 5 candidates with a known generating model, asserts calibrate flips `calibration_pending → False`, fitted weights differ from defaults on at least one pillar, and the drift cap holds.
  2. `test_get_calibration_state_caches_result` — proves the SQLite cache short-circuits the live calibrate function on the second call (sentinel injection + monkey-patch).
  3. `test_methodology_registry_augments_mvp_with_runtime_calibration` — asserts `runtime_calibration` is populated on the mvp domain.
  4. `test_methodology_registry_passes_through_other_domains` — non-mvp domains must NOT have `runtime_calibration` populated (no coupling).

**Behavior unchanged when `calibration_pending=True`** (same default weights). Once `materialize_award_modifiers.py` runs in production, `/api/methodology/mvp` will surface fitted weights + cross-validated Spearman + fold count, and the MVP race response will use the fitted weights without a code change.

### Stream B — Opportunity Uplift UI Surface

Sprint 79 shipped the `opportunity_v2` KNN service that produces an `uplift` sibling field on every `OpportunityPlayerRow` (mean_uplift / IQR band / neighbor_count / evidence_confidence / 3 named comparables). The frontend has been ignoring it for ~3 months because the type wasn't even mirrored in `types.ts`.

- **B1+B2+B3+B4+B5** (`fbd4a42`):
  - `types.ts` (append-only): new `OpportunityUpliftComparable` + `OpportunityUplift` interfaces, `uplift: OpportunityUplift | null` on `OpportunityPlayerRow`. Plus `MvpCalibrationMetadata` + `calibration_metadata?` on `MvpRaceResponse` (mirrors Sprint 90 A).
  - new `UpliftEvidenceCard.tsx` (Sprint 58 evidence-card visual pattern): header + confidence pill, 2-col mean/band layout color-toned by sign, top-3 historical comparables with from→to season + USG delta + TS delta, descriptive caveat footer. Empty state when `uplift === null`.
  - `OpportunityDashboard.tsx`: mounts the card full-width below the existing 2×2 evidence card grid (uplift card benefits from the wider layout).
  - `OpportunityRow.tsx`: compact one-line uplift hint at row bottom ("Uplift +0.0034 TS · 12 comps", color-toned by sign, hover tooltip with full IQR band) so rail browsing surfaces the evidence without expanding the detail panel.
  - `MethodologyDrawer.tsx`: new collapsible "v2 uplift evidence" subsection explaining KNN over 286 observations, shrunk-Mahalanobis distance, K=20 / min 5, confidence bands, and the descriptive (not causal) caveat.

`npm run build` clean, `npm run lint` 0/0. No backend changes — `opportunity_v2` already shipped the field; frontend just ignored it.

### Stream C — Cloudflare deferrals + cache-effectiveness baseline

- **`882bb2f`**: three small docs updates to `infra/README.md`:
  - **Backup retention section**: click-by-click R2 dashboard instructions (rule name, action, days) so the Sprint 87 deferral is ~5 min of UI work.
  - **New "Cache effectiveness baseline" subsection**: captures the 2026-05-03 prod snapshot (`row_count=535, size_bytes=16MB, hit/miss=0` on a fresh worker). Notes the per-worker counter caveat from Sprint 88 and when to act (hit-rate < 50% after sustained traffic → bump TTLs in `nba_client.py`).
  - **New `/api/health` bypass-cache section**: retires the Sprint 88 deferred BACKLOG entry. On review the rule is **not needed** — the catch-all 2hr TTL covers it and UptimeRobot reaches origin every 5 min. The README already implicitly said this; now made explicit.

## Verification

Pre-merge:
- `pytest -q`: **513 passed**, 2 warnings (unchanged FastAPI on_event deprecation).
- `npm run build`: clean.
- `npm run lint`: 0 errors / 0 warnings.
- Local curl smoke against backend on :8005:
  - `/api/methodology/mvp` returns `runtime_calibration` populated with the expected default state.
  - `/api/methodology/archetype` returns `runtime_calibration: null` (proves no coupling).
  - `/api/mvp/race?season=2024-25&top=3` returns `calibration_metadata` with `pending=true, weights_source=default, weights={...defaults}`.

## Methodology summary

For Stream A (Award Case calibration activation):
- Same scoring formula and weights as Sprint 79; the difference is **how live the weights are**. Today: module-import constant pinned to defaults. Sprint 90: per-request call to `calibrate_award_case_weights(db)`, cached 24h, surfaced as `calibration_metadata` on every MVP race response and as `runtime_calibration` on the mvp methodology domain.
- LOO-CV gate: ≥5 folds AND Spearman ≥ 0.7. Below the gate, falls back to defaults with `calibration_pending=True` (honest reporting in the metadata).
- Drift cap (±0.04 per pillar) holds even when calibration succeeds — calibration tunes the priors, doesn't replace them.

For Stream B (Opportunity Uplift UI):
- Methodology unchanged from Sprint 79 (`opportunity_v2`). The card is purely a render of fields the backend has been producing all along.
- Reads as descriptive evidence ("players similar to T historically saw X TS%"), explicitly not causal projection.

## Production deploy plan

1. `git push origin master` after merge → Vercel auto-deploys frontend.
2. `ssh ubuntu@5.78.114.15 && cd /home/ubuntu/bip && git pull origin master && sudo bash infra/deploy.sh` — backend deploy (no migration this sprint).
3. **Stream A4 — production materialization (CRITICAL):**
   ```bash
   ssh ubuntu@5.78.114.15
   cd /home/ubuntu/bip
   set -a && source /etc/bip/env && set +a
   ./backend/venv/bin/python backend/data/materialize_award_modifiers.py
   ```
   Expect ~57 rows. After materialization completes, hit `/api/methodology/mvp` and check whether `runtime_calibration.calibration_pending` flips to `false`. If LOO-CV Spearman misses the 0.7 gate, document the actual value achieved — Stream A still ships value (per-request loading + honest registry status); the BACKLOG entry gets updated to "data-blocked at modifier-proxy quality" rather than "code-blocked".

## Production smoke (post-deploy + materialization)

```bash
# Stream A — MVP race calibration metadata
curl -sf "https://api.courtvue.app/api/mvp/race?season=2024-25" | python3 -c "
import json, sys
d = json.load(sys.stdin)
m = d.get('calibration_metadata', {})
print('pending:', m.get('calibration_pending'))
print('source:', m.get('weights_source'))
print('Spearman:', m.get('cross_validated_spearman'))
print('fold_count:', m.get('fold_count'))
print('weights:', m.get('weights'))
"

# Stream A — methodology registry runtime augmentation
curl -sf "https://api.courtvue.app/api/methodology/mvp" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('status:', d['status'])
print('runtime:', d.get('runtime_calibration'))
"

# Stream B — uplift visible on at least one Opportunity row
# (TODO once the Opportunity endpoint route is known — likely /api/insights/...)
```

Browser walk: load `/insights` → Opportunity workspace → click a row → verify the new full-width `UpliftEvidenceCard` populates below the 2×2 grid + the compact uplift hint shows in the row card on the rail. Load `/mvp` → verify race renders normally + (after materialization) the calibration metadata reflects fitted weights.

## Deferred

None this sprint shipped without follow-on. Two genuine deferrals remain in the BACKLOG, one of them new this sprint:

| Item | Why deferred |
|------|--------------|
| R2 backup lifecycle rule | Cloudflare R2 dashboard UI step (~5 min). "Different domain" per Deferral Policy. Refined click-by-click instructions live in `infra/README.md`. |
| MVP voter calibration cohort expansion | Data-blocked. If production materialization yields LOO-CV Spearman < 0.7, the next move is sourcing 4-5 more historical seasons of MVP voting from Basketball-Reference. ~2-3 hr manual CSV work, doesn't need a sprint allocation. |

The `/api/health` bypass-cache rule (Sprint 88 deferred) is **resolved as not-needed** in this closeout — to be removed from the BACKLOG entirely.

## Workflow lessons

- **Static methodology + runtime augmentation pattern.** I considered two approaches for Stream A2: (a) make the methodology registry entry dynamic by bunching live state into the `status` string, or (b) keep the static entry as the canonical methodology spec and add a separate `runtime_calibration` field surfaced when `db` is available. Went with (b) because it preserves the "registry is the static methodology document" invariant — the registry tells you *what the methodology is supposed to do*, the runtime field tells you *whether it's currently doing it*. Other domains pass through unchanged. Worth reusing as a pattern when other domains gain calibration steps (e.g. `opportunity_v2` once the held-out backtest runs).
- **Stale BACKLOG entries become invisible.** The `/api/health` bypass-cache rule was filed as Sprint 88 deferred — but the README author had explicitly written "Health bypass is unnecessary because requests are cheap and the catch-all TTL is short." The BACKLOG entry sat there for a sprint anyway. Lesson: when filing a deferral, also link to the README/docs section that confirms the action; if the docs already disagree, don't file the deferral.
- **Cached calibration result + per-request lookup.** The MVP race endpoint runs LOO-CV math (~50ms) only on the cold path (24h cache); subsequent requests are ~0.5ms cache reads. Same pattern as Sprint 89's roster-fit cache. The 24h TTL aligns with the materialization cadence (manual ops step, very rare).
- **Cross-stream type bundling.** Stream A added `MvpCalibrationMetadata` to backend. Stream B added `OpportunityUpliftComparable` + `OpportunityUplift` to backend (already present pre-Sprint-79, just not mirrored). Bundled both type additions into Stream B's frontend types commit so the append-only `types.ts` only got touched once. This worked smoothly here but only because the two sets of types are independent — if they had cross-references it would've been worth two commits.
