# PBP Accuracy Fix: Real Possession Counting + Actual Stint Duration

## Context

The play-by-play pipeline's on/off and lineup stats have two accuracy bugs that make the numbers unreliable for serious analysis:

1. **Possession counting misses free-throw-ending possessions.** Only FGA + TOV are counted. Any possession that ends with a missed last free throw (the most common non-FGA possession terminator) is silently skipped. This underreports total possessions and inflates ORTG/DRTG for high-foul-drawing players.

2. **Minutes on court are estimated, not measured.** The formula `minutes = possessions / 2.0` assumes a fixed ~2 possessions per minute — which varies meaningfully by pace (1.5–2.5). The raw clock timestamps are already stored in the `PlayByPlay` table as `clock` fields (`"PT05M30.00S"`), and the `_parse_clock_seconds()` helper (pbp_service.py line 16) already converts them. The `Stint` dataclass (pbp_service.py line 48) already has `seconds: float = 0.0` and `PlayerOnOffAccumulator` (pbp_service.py lines 228–229) already has `on_seconds`/`off_seconds` fields — both are literally unused stubs waiting to be wired up.

**No DB schema changes needed.** The existing `on_minutes`/`off_minutes` (PlayerOnOff) and `minutes` (LineupStats) columns keep their names — the values will just be accurate instead of approximated. No frontend changes needed.

---

## Fix 1: Free-Throw Possession Counting

**Where:** `build_stints()` in `backend/services/pbp_service.py` (lines 67–211), specifically the possession accumulator block (lines 170–180).

**How it works today:**
```python
if action_type in ("2pt", "3pt"):
    home_poss_acc += 1  # or away
elif action_type == "turnover":
    home_poss_acc += 1  # or away
```

**The fix:** When a `freethrow` event is the *last* free throw in its sequence (description matches `r'\b(\d) of \1\b'` — e.g. "2 of 2", "1 of 1", "3 of 3") AND the possession did not already have a FGA (i.e., it wasn't an and-one), count it as a possession.

Track with a per-stint boolean `_poss_had_fga: bool = False`:
- Set to `True` when a `2pt`/`3pt` event is processed
- Reset to `False` when the stint closes (on substitution/period boundary)
- On `freethrow` event:
  - If description matches last-FT regex **and** `_poss_had_fga is False` → increment possession counter
  - When description matches last-FT regex → reset `_poss_had_fga = False` (possession chain resets)

This correctly handles:
- Regular FGA → possession counted (no FT double-count since `_poss_had_fga=True`)
- And-1 (made FGA + 1 FT) → only FGA counts; `_poss_had_fga` flag prevents FT re-count
- Shooting foul (2 or 3 FTs, no prior FGA) → last FT counts as possession
- Technical FTs → these happen mid-possession and typically have "Technical" in description; can be excluded by checking for absence of "Technical" in the description

**Regex for last-FT detection:**
```python
import re
_LAST_FT_RE = re.compile(r'\b(\d) of \1\b')  # matches "1 of 1", "2 of 2", "3 of 3"
```

---

## Fix 2: Actual Stint Duration from Clock

**Where:** `build_stints()` in `backend/services/pbp_service.py`, plus downstream aggregation.

**How it works today:** `stint.seconds` is always `0.0` (stub). Minutes are computed later as `possessions / 2.0`.

**The fix:**

**Step A — Track clock in `build_stints()`:**

The `_parse_clock_seconds()` helper (pbp_service.py line 16) already converts `"PT05M30.00S"` → float seconds remaining in period. NBA clock counts DOWN (e.g., starts at 720.0 for a 12-minute quarter), so:

```
stint_duration = clock_at_stint_start − clock_at_stint_end
```

Track two variables:
- `_stint_start_clock: float | None = None` — set when a new stint opens
- `_last_clock: float | None = None` — updated on every event with a parseable clock

When closing a stint (on substitution or period boundary):
```python
if _stint_start_clock is not None and _last_clock is not None:
    stint.seconds = max(0.0, _stint_start_clock - _last_clock)
```

After closing, reset: `_stint_start_clock = _last_clock` (new stint starts where old one ended).

Edge case — period boundary: when a `period` event fires, the clock resets to the full period length in the next period. Handle by resetting `_stint_start_clock = None` after a period boundary, then set it from the first event of the new period.

**Step B — Accumulate seconds in `compute_on_off()`** (pbp_service.py lines 233–270):

`PlayerOnOffAccumulator` already has `on_seconds` and `off_seconds` fields (lines 228–229) — just populate them:
```python
if pid in team_players_on:
    acc.on_seconds += stint.seconds   # ← add this line
    ...
else:
    acc.off_seconds += stint.seconds  # ← add this line
    ...
```

**Step C — Accumulate seconds in `LineupAccumulator`** (pbp_service.py line 411):

Add `seconds: float = 0.0` to `LineupAccumulator`. In `compute_lineup_stats()` (lines 419–440):
```python
acc.seconds += stint.seconds  # for both home and away
```

**Step D — Use actual seconds in `_upsert_on_off()`** (pbp_sync_service.py lines 276–295):

Wherever the `data` dict is built before calling `_upsert_on_off()` (pbp_sync_service.py ~lines 490–523), replace:
```python
# Old
"on_minutes": acc.on_possessions / 2.0,
"off_minutes": acc.off_possessions / 2.0,
```
With:
```python
# New — use real seconds if available, fallback to possession estimate
"on_minutes": acc.on_seconds / 60.0 if acc.on_seconds > 0 else acc.on_possessions / 2.0,
"off_minutes": acc.off_seconds / 60.0 if acc.off_seconds > 0 else acc.off_possessions / 2.0,
```

**Step E — Use actual seconds in `_upsert_lineup()`** (pbp_sync_service.py lines 297–314):

```python
# Old
row.minutes = round(possessions / 2.0, 1) if possessions else None
# New
row.minutes = round(acc.seconds / 60.0, 1) if acc.seconds > 0 else (round(possessions / 2.0, 1) if possessions else None)
```

---

## Critical Files

| File | Lines | Change |
|------|-------|--------|
| `backend/services/pbp_service.py` | 67–211 (`build_stints`) | Add FT possession counting + clock tracking for seconds |
| `backend/services/pbp_service.py` | 233–270 (`compute_on_off`) | Accumulate `on_seconds`/`off_seconds` |
| `backend/services/pbp_service.py` | 411–416 (`LineupAccumulator`) | Add `seconds: float = 0.0` field |
| `backend/services/pbp_service.py` | 419–440 (`compute_lineup_stats`) | Accumulate `acc.seconds` |
| `backend/services/pbp_sync_service.py` | ~490–523 | Pass `on_seconds`/`off_seconds` in data dict |
| `backend/services/pbp_sync_service.py` | 276–295 (`_upsert_on_off`) | Use seconds for minutes if > 0 |
| `backend/services/pbp_sync_service.py` | 297–314 (`_upsert_lineup`) | Use seconds for minutes if > 0 |

**Reuse existing:**
- `_parse_clock_seconds()` — pbp_service.py line 16 — already converts `"PT05M30.00S"` to float seconds
- `Stint.seconds` — pbp_service.py line 48 — field exists, always `0.0`, just needs to be set
- `PlayerOnOffAccumulator.on_seconds` / `off_seconds` — pbp_service.py lines 228–229 — fields exist, always `0.0`, just needs to be accumulated

---

## Build Order

```
1. Fix FT possession counting in build_stints()     — isolated, testable
2. Wire clock tracking → Stint.seconds              — same function, builds on step 1
3. Accumulate seconds in compute_on_off()           — 2 lines
4. Add seconds to LineupAccumulator + compute_lineup_stats()  — 2 lines
5. Update _upsert_on_off() and _upsert_lineup() to use seconds  — 2 lines each
```

---

## Verification

- Run the backend: `uvicorn main:app --reload` from `backend/`
- Trigger a full season re-sync: `POST /api/advanced/sync-season` with `{"season": "2024-25"}`
- Check a player's on/off: `GET /api/advanced/{player_id}/on-off?season=2024-25` — `on_minutes` and `off_minutes` should now be real values (not multiples of 0.5 from the possessions/2 formula)
- Verify possessions increased: total possessions for a game should be closer to 90–100 (NBA average) vs. previously undercounting
- Check lineup minutes: `GET /api/advanced/lineups?season=2024-25` — `minutes` values should reflect real court time
- No frontend changes needed — UI renders `on_minutes`/`off_minutes`/`minutes` as-is
