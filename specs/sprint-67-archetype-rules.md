# Sprint 67 — Archetype & Shot Diagnosis Taxonomy

**Status:** A1 (player archetypes) — 15 archetypes, three tune passes complete, locked for B1 implementation. A2 (shot diagnosis tags) pending Codex.
**Consumed by:** `backend/services/player_archetype_service.py` (A1) and `backend/services/shot_diagnosis_service.py` (A2).
**Discipline:** deterministic rules only, mirroring `backend/routers/styles.py::classify_archetype` (Sprint 60). No ML, no embeddings.

---

## Part 1 — Player Archetype Taxonomy (Stream A / Claude)

### 1.1 Feature extraction

All features are computed from `SeasonStat` (and `Player` for size/age). No new upstream data this sprint. Features are normalized to **per-season z-scores** against a peer pool of qualifying players so era-independence is preserved (same discipline as `similarity_service.find_similar_players`).

**Subject-row selection.** `season_stats` has a row per `(player_id, season, team_abbreviation, is_playoff)`. For a mid-season trade the NBA produces a `"TOT"` aggregate row. Classifier resolution order, per player+season:
1. Prefer `is_playoff == False AND team_abbreviation == "TOT"` when present.
2. Else use the single `is_playoff == False` row for that player+season.
3. If multiple non-`TOT` regular-season rows exist and no `TOT` is present, fall through to `developmental` with a `reason` note "split-season without TOT aggregate — sample ambiguous".

Playoff rows (`is_playoff == True`) are never used by the classifier — archetype is a regular-season identity.

**Peer pool for z-score computation.** All players in the same `season` whose subject-row selection yielded a single well-defined row AND `gp >= 20` AND `min_pg >= 15` AND all of the following non-null: `usg_pct, ast_pg, par3, ftr, ts_pct, stl_pg, blk_pg, oreb_pct, dbpm, obpm, min_pg`. Rationale: keep the pool to rotation players so the distribution isn't dragged by 5-minute cameos. A player who fails pool entry is not classified at all — returns `developmental` with `reason` = "below minute/game threshold for archetype classification".

**Feature dictionary.**

| Feature key | Source | Formula | Role signal |
|---|---|---|---|
| `usg_z` | `season_stats.usg_pct` | raw value | creation burden |
| `ast_rate_z` | `season_stats` | `(ast_pg * 36) / min_pg` (per-36 assists) | playmaking volume |
| `ast_tov_z` | `season_stats.ast_tov` | raw | playmaking quality |
| `par3_z` | `season_stats.par3` | `fg3a / fga` | perimeter diet |
| `ftr_z` | `season_stats.ftr` | `fta / fga` | rim pressure / foul drawing |
| `ts_z` | `season_stats.ts_pct` | raw | shooting efficiency |
| `stl_rate_z` | `season_stats` | `(stl_pg * 36) / min_pg` (per-36 steals) | perimeter defense |
| `blk_rate_z` | `season_stats` | `(blk_pg * 36) / min_pg` (per-36 blocks) | rim protection |
| `oreb_z` | `season_stats.oreb_pct` | raw | interior activity |
| `dbpm_z` | `season_stats.dbpm` | raw | all-round defense |
| `obpm_z` | `season_stats.obpm` | raw | all-round offense |
| `fg3_pct_z` | `season_stats.fg3_pct` (sample-gated: excluded from the player's feature vector if `fg3a < 50`) | raw | shooting talent |
| `size_inches` | `players.height` parsed (see below) | integer inches | archetype gating (not z-scored) |

**Height parsing.** `players.height` is stored as a string like `"6-7"` (feet-inches). Parser:
```
parse_height("6-7") -> 79   # 6 * 12 + 7
parse_height("7-0") -> 84
parse_height("")    -> None
parse_height(None)  -> None
```
A player whose height parses to `None` is **excluded from the peer pool** (not just from size-gated rules) because size is a gating feature on multiple archetypes.

**Age derivation (for similarity `mode="age"`).** `players.birth_date` is a string (format varies: `"1998-02-01"`, `"Feb 1, 1998"`, or similar — use `dateutil.parser` with fallback). Compute age as of `October 1` of the season's start year: for `season == "2023-24"`, reference date is `2023-10-01`. A player whose birth date fails to parse is excluded from the age-mode peer pool.

**Missing-feature policy inside a rule.** If any feature named in a rule's trigger is null for the subject player (after sample-gating), the rule **does not fire** and contributes nothing to `trigger_magnitudes`. The next rule in order is evaluated.

### 1.2 Archetype catalog

15 archetypes total, ordered most-specific → least-specific in the classifier (first match wins, like `classify_archetype`). Every archetype has (a) trigger rule, (b) reason phrase template, and (c) trigger-magnitude list feeding `_archetype_confidence`.

**Ordering policy.** Offensive-identity rules first (heliocentric → ball-handler → iso scorer → secondary playmaker), then shooter/wing profiles (movement shooter → 3-and-D → rim pressure guard → connective forward), then the defensive-primary big lane (defensive anchor) before the offensive-primary big lanes (interior finisher → stretch big), then perimeter defense (switchable stopper), then low-usage fallback (rotational energy), then the two `balanced_role` / `developmental` catch-alls. Defensive Anchor is intentionally placed **before** Interior Finisher and Stretch Big so that Wembanyama / Gobert / Holmgren — players whose defense defines them — don't get relabeled by their offensive profile.

| # | Key | Label | Trigger | Reason template |
|---|---|---|---|---|
| 1 | `heliocentric_creator` | Heliocentric Creator | `usg_z >= 1.0 AND ast_rate_z >= 1.0 AND obpm_z >= 1.0` | "High usage, elite playmaking, and above-average efficiency — possessions orbit this player." |
| 2 | `lead_ball_handler` | Lead Ball-Handler | `usg_z >= 0.7 AND ast_rate_z >= 0.8` | "High usage with heavy on-ball creation — defined by volume and playmaking regardless of shot diet." |
| 3 | `iso_scorer` | Iso Scorer | `usg_z >= 0.7 AND ast_rate_z <= 0.8 AND par3_z <= 0.0 AND ftr_z >= 0.2` | "High-usage mid-range and rim scorer without a heavy passing burden — a bucket-getter." |
| 4 | `secondary_playmaker` | Secondary Playmaker | `ast_rate_z >= 0.6 AND usg_z <= 0.5 AND ast_tov_z >= 0.3` | "Connective passing with controlled usage and low turnover risk." |
| 5 | `movement_shooter` | Movement Shooter | `par3_z >= 0.8 AND fg3_pct_z >= 0.3 AND usg_z <= 0.5` | "High perimeter volume at reliable accuracy in a low-to-moderate usage role." |
| 6 | `three_and_d_wing` | 3-and-D Wing | `par3_z >= 0.5 AND fg3_pct_z >= 0.3 AND dbpm_z >= 0.5 AND 77 <= size_inches <= 82` | "Spot-up perimeter threat at wing size paired with above-average defense." |
| 7 | `rim_pressure_guard` | Rim Pressure Guard | `ftr_z >= 0.6 AND par3_z <= 0.0 AND usg_z >= 0.0 AND size_inches <= 77` | "Downhill guard with above-average foul drawing, a paint-first diet, and meaningful on-ball usage." |
| 8 | `connective_forward` | Connective Forward | `ast_rate_z >= 0.4 AND size_inches >= 78 AND usg_z <= 0.5` | "Positional playmaking from the wing/forward, regardless of shot diet." |
| 9 | `defensive_anchor` | Defensive Anchor | `blk_rate_z >= 1.0 AND dbpm_z >= 0.8 AND size_inches >= 80` | "Rim protection and team-defense impact anchor the back line." |
| 10 | `interior_finisher` | Interior Finisher | `ts_z >= 0.7 AND par3_z <= -0.4 AND oreb_z >= 0.4` | "Paint-bound scorer finishing efficiently at high volume inside, with rebound activity." |
| 11 | `stretch_big` | Stretch Big | `par3_z >= 0.5 AND size_inches >= 80` | "Frontcourt size with a perimeter shot the opponent must respect." |
| 12 | `switchable_stopper` | Switchable Stopper | `stl_rate_z >= 0.7 AND dbpm_z >= 0.6 AND 75 <= size_inches <= 82` | "On-ball disruption at wing or combo-guard size — switches across multiple positions." |
| 13 | `rotational_energy` | Rotational Energy | `oreb_z >= 0.5 AND ftr_z >= 0.3 AND usg_z <= 0.0` | "Low-usage energy role — second chances, fouls drawn, hustle impact." |
| 14 | `balanced_role` | Balanced Role | No rule above fired **AND** `gp >= 30 AND min_pg >= 20` | "Role profile sits near league average across the archetype-defining features — no single style signal dominates." |
| 15 | `developmental` | Developmental | No rule above fired **AND** (`gp < 30 OR min_pg < 20`) | "Sample too thin to commit to an archetype yet." |

**Rationale notes on specific thresholds (don't "clean these up" without re-reading).**
- `heliocentric_creator`'s `usg_z >= 1.0` (not 1.2) is intentional. Top-~15% usage combined with elite playmaking and obpm is a strong enough signal; 1.2 was excluding Jokić-style centers whose usage is "only" top-15 rather than top-5.
- `lead_ball_handler` has *no* `par3_z` gate. A high-usage, high-assist guard with a mid-range diet (SGA-style) is still a lead ball-handler. Adding a par3 floor previously orphaned the mid-range-creator lane.
- `iso_scorer` (rank 3) catches the *other* side: high usage, mid-range-heavy scorers without Lead Ball-Handler-level passing (DeRozan peak, SGA-style mid-range creators). Positioned right after `lead_ball_handler`, with `ast_rate_z <= 0.8` as a hard ceiling that matches LBH's floor (no overlap, no gap). The previous `<= 0.5` threshold was too tight — it left high-usage moderate-assist mid-range creators orphaned in Balanced Role.
- `movement_shooter` (rank 5) was loosened from the original `par3_z >= 1.0 / fg3_pct_z >= 0.6` to catch high-volume veteran shooters whose accuracy dropped to league-average but whose role is still specialist spacer (late-career Klay Thompson profile).
- `three_and_d_wing` size floor raised to 77" (6'5") to exclude pure guards whose defense happens to grade well.
- `rim_pressure_guard` thresholds tuned: `ftr_z >= 0.6` (top-~30%, was top-~20% too strict); `par3_z <= 0.0` (below-average perimeter volume — archetype *requires* paint-first); `usg_z >= 0.0` floor distinguishes an on-ball creator from a bench energy guard.
- `connective_forward` drops the `par3_z` gate so old-school passing forwards (Draymond in his low-shooting years, or any non-spacing connective big) still route here. The signal is passing at size, not modern spacing.
- `defensive_anchor` placed at rank 9 (before Interior Finisher at 10 and Stretch Big at 11) so rim-protecting bigs with *any* offensive profile — shooting (Chet, Wemby) or paint-scoring (Gobert) — route to the defensive label that defines them.
- `stretch_big` dropped the `blk_rate_z >= -0.2` floor. Size-gated wings/forwards who bomb 3s (Keegan Murray, Jabari Smith Jr.) legitimately fit the archetype even without rim presence.
- `switchable_stopper` size floor lowered from 76 to 75 (6'3") to catch strong-built combo-guard stoppers like Lu Dort.
- `balanced_role` (rank 14) and `developmental` (rank 15) are distinct archetype keys, not variants of the same key. A rotation player whose feature profile is genuinely league-average is a different story from a low-sample player; the schema makes that honest.

### 1.3 Confidence band

Port `_archetype_confidence(trigger_magnitudes)` verbatim:

- `high` if `mean(|z|) >= 1.0`
- `medium` if `mean(|z|) >= 0.6`
- `low` otherwise (including `developmental` / `balanced_role`)

### 1.4 Contributors (fingerprint)

Same pattern as `_style_xray_label`: rank the full feature list by `|z|` descending and return the top 4 as `ArchetypeContributor` records. Each contributor carries `{feature_key, label, value, z, direction}` where `direction ∈ {"above", "below"}` based on sign of z.

A dedicated `ARCHETYPE_CONTRIBUTOR_KEYS` set (analog of `_STYLE_CONTRIBUTOR_KEYS`) restricts contributors to features with basketball-native labels: `usg_z`, `ast_rate_z`, `par3_z`, `ftr_z`, `ts_z`, `stl_rate_z`, `blk_rate_z`, `oreb_z`, `dbpm_z`, `obpm_z`, `fg3_pct_z`. (Skips `ast_tov_z` and `size_inches` — those are gating features used only inside triggers, not for user-facing fingerprints.)

### 1.5 Output schema

```python
# backend/models/archetype.py
class ArchetypeContributor(BaseModel):
    feature_key: str
    label: str                      # e.g. "Usage rate"
    value: Optional[float]          # raw feature value, not z
    z: float
    direction: Literal["above", "below"]

class PlayerArchetype(BaseModel):
    player_id: int
    season: str
    archetype_key: str              # e.g. "movement_shooter"
    label: str                      # e.g. "Movement Shooter"
    confidence: Literal["high", "medium", "low"]
    reason: str
    contributors: List[ArchetypeContributor]   # top 4
    sample: ArchetypeSample        # gp, min_pg, peer_pool_size
```

### 1.6 Caching

In-process TTL cache keyed on `(season, methodology_version="player_archetype_v1")` for the **full peer pool + z-scores matrix**, TTL 10 min current season / 24 h historical — same policy as Sprint 65's `opportunity_service` cache. Individual classifications are cheap once the matrix is cached.

### 1.7 Similarity upgrade (B2)

`similarity_service.find_similar_players` grows a `mode: Literal["season", "age", "team_fit"]` parameter. Default `mode="season"` preserves the current behavior (backwards-compatible with the existing `/api/similarity/{player_id}` consumers).

- `mode="season"` — existing weighted-Euclidean over the current 9 features, extended with `par3_z`, `ftr_z`, `stl_rate_z`, `blk_rate_z` (role-aware dimensions). Default `n=8`, same-season pool.
- `mode="age"` — pool = all players in any season where age is within ±1 year of the subject player's current age. Same distance function. Default `n=5`.
- `mode="team_fit"` — same-team teammate-duplicate penalty: for each feature, if `|subject_z - same_team_teammate_max_z| < 0.5`, multiply that feature's weight by 0.4 in the distance computation for comp ranking (so comps that *also* heavily duplicate an existing teammate strength drop). Default `n=5`.

Every comp payload gets `archetype_label`, `archetype_key`, `archetype_confidence` attached via batch-classify (one peer-pool matrix already cached per season).

### 1.8 Acceptance fixtures (golden tests)

One golden test per archetype using a known-plausible player / season. If the real 2024-25 data disagrees, the test records the actual archetype and the spec rules get a tuning revision before merge — not the test. Tests are aspirational-realistic, not brittle.

| Archetype | Fixture | Dual-eligibility note |
|---|---|---|
| `heliocentric_creator` | Luka Dončić 2023-24 | — |
| `lead_ball_handler` | Trae Young 2024-25 | — |
| `iso_scorer` | DeMar DeRozan 2021-22 | Must fail Lead Ball-Handler (`ast_rate_z < 0.8`) to route here. |
| `secondary_playmaker` | Tyrese Haliburton 2022-23 (pre-injury) | — |
| `movement_shooter` | Duncan Robinson 2023-24 | — |
| `three_and_d_wing` | OG Anunoby 2023-24 | Must fail Movement Shooter (`par3_z < 0.8` or `usg_z > 0.5`). |
| `rim_pressure_guard` | De'Aaron Fox 2022-23 | Must fail Lead Ball-Handler (`ast_rate_z < 0.8`) — Fox's moderate assist rate is the distinguishing feature vs. Morant-style ball-handlers. |
| `connective_forward` | Draymond Green 2022-23 | — |
| `defensive_anchor` | Victor Wembanyama 2024-25 | Fires before Interior Finisher and Stretch Big, so rim-protecting bigs with any offensive profile route here. Rudy Gobert 2020-21 also routes here (not to Interior Finisher). |
| `interior_finisher` | Ivica Zubac 2023-24 | Must fail Defensive Anchor (`dbpm_z < 0.8` or `blk_rate_z < 1.0`). Zubac's solid-but-not-elite rim protection is the distinguishing feature vs. Gobert. |
| `stretch_big` | Kristaps Porziņģis 2023-24 | Must fail Defensive Anchor (`dbpm_z < 0.8` typically). |
| `switchable_stopper` | Jrue Holiday 2022-23 | — |
| `rotational_energy` | Mitchell Robinson 2022-23 | Must fail Defensive Anchor — his blk_rate is elite but `size_inches >= 80` is close and `dbpm_z >= 0.8` may trip. If DA triggers, this routes to DA and the fixture should be moved. Fallback fixture: **Robert Williams III** in a low-minutes season. |
| `balanced_role` | Harrison Barnes 2023-24 | Rotation-starter workload (`gp >= 30 AND min_pg >= 20`) with no feature crossing any archetype threshold. |
| `developmental` | Any player with `gp < 30 OR min_pg < 20` | — |

**Rule ordering policy.** First rule whose trigger evaluates true wins. If a fixture expects a later archetype, the earlier rules must fail their own triggers on that fixture — never rely on short-circuit logic beyond the documented ordering. Fixtures are aspirational-plausible: when real 2024-25 data disagrees with a fixture, tune the thresholds in the spec *before* changing the test, but tune only if the basketball argument is stronger than the fixture itself.

**Sanity-trace expectations for B1 verification.** After B1 lands, these additional trace expectations must hold on real 2024-25 data (not part of the golden test set, but a smoke verification for D1):

| Player (2024-25) | Expected archetype | Expected *not* archetype |
|---|---|---|
| Shai Gilgeous-Alexander | `iso_scorer` (or `heliocentric_creator` if `ast_rate_z` exceeds 1.0) | `balanced_role` |
| Nikola Jokić | `heliocentric_creator` | `lead_ball_handler` |
| Rudy Gobert | `defensive_anchor` | `interior_finisher` |
| Chet Holmgren | `defensive_anchor` | `stretch_big` |
| Draymond Green | `connective_forward` | `switchable_stopper` |
| Lu Dort | `switchable_stopper` | `developmental` |
| Keegan Murray | `stretch_big` or `three_and_d_wing` | `balanced_role` |

---

## Part 2 — Shot Diagnosis Tag Taxonomy (Stream B / Codex)

*Pending — Codex to append A2 in this section.*

Expected structure:
- Tag catalog (~12 tags): key, label, sentiment (strength|risk|neutral), triggering metric + threshold, grade band (green/yellow/red cutoffs), sample confidence gating.
- Sustainability rule: zone-level delta spread + baseline coverage → {Sustainable, Hot Streak, Cold Streak, Insufficient Sample}.
- Creation burden rule: thresholds on existing `build_shot_creation_response` output → {Self-Created Heavy, Balanced, Assisted Heavy}.
- Headline template: 1-sentence composition from top-1 tag + sustainability + creation burden.
- Minimum-sample gate for emitting any tag (plan says ≥ 50 attempts).

---

## Change log

- 2026-04-23 (Claude): A1 drafted. 13 archetypes, feature dictionary, confidence bands, similarity mode extensions, golden test fixtures.
- 2026-04-23 (Claude): A1 review/tune pass. Catalog grew to 14 archetypes. Changes: (a) dropped `par3_z >= 0.2` gate from Lead Ball-Handler so mid-range creators route correctly; (b) added `iso_scorer` archetype to catch high-usage low-assist mid-range scorers (DeRozan prototype); (c) reordered Defensive Anchor before Stretch Big so rim-protecting shooters (Wemby, Chet) route defensively; (d) loosened Movement Shooter (`par3_z >= 0.8 AND fg3_pct_z >= 0.3 AND usg_z <= 0.5`); (e) raised 3-and-D Wing size floor to 77"; (f) tuned Rim Pressure Guard: `ftr_z >= 0.6`, `par3_z <= 0.0`, new `usg_z >= 0.0` floor; (g) added rationale notes for thresholds that look odd but are load-bearing; (h) updated fixture table with dual-eligibility notes; (i) split developmental into "thin sample" vs "balanced role" variants.
- 2026-04-23 (Claude): A1 second tune pass. Catalog now 15 archetypes with real schema split between `balanced_role` and `developmental`. Changes: (a) **BUG** — moved Defensive Anchor from rank 10 to rank 9 so Gobert's offensive profile can't route him to Interior Finisher first; (b) dropped `par3_z >= 0.2` gate from Connective Forward (old-school passing forwards don't need modern spacing); (c) dropped `blk_rate_z >= -0.2` floor from Stretch Big (size gate is enough; Keegan Murray / Jabari Smith types legitimately fit); (d) lowered Switchable Stopper size floor from 76 to 75 (catches Lu Dort); (e) lowered Heliocentric usg threshold from 1.2 to 1.0 (lets Jokić-volume centers route here); (f) **BUG** — swapped Rim Pressure Guard fixture from Ja Morant (fires Lead Ball-Handler) to De'Aaron Fox 22-23; (g) swapped Interior Finisher fixture to Ivica Zubac so it's clearly distinguishable from Defensive Anchor; (h) promoted `balanced_role` to a real 15th archetype key instead of a `reason_variant` flag. Confidence band thresholds unchanged.
- 2026-04-23 (Claude): A1 third (final) tune pass — spec locked. Changes: (a) **SCHEMA BUG** — `Player.height` is `String(10)` (`"6-7"` format), not an int; added explicit height-parser contract. Same for `Player.birth_date` (variable-format string) needed by similarity `mode="age"`. (b) **COVERAGE GAP** — loosened Iso Scorer's `ast_rate_z` cap from 0.5 to 0.8 so SGA-band mid-range lead creators route correctly instead of falling to Balanced Role; no-overlap-no-gap at 0.8 against Lead Ball-Handler's 0.8 floor. (c) **CRUFT** — removed `dreb_rate_z` from feature dictionary; it wasn't used by any rule and couldn't be computed cleanly (`opp_dreb` not on SeasonStat). (d) **MULTI-ROW EDGE** — documented subject-row selection policy for mid-season trades (prefer `team_abbreviation=="TOT"`, regular-season only, ambiguous split-season falls to developmental). (e) Added peer-pool explicit required-features list. (f) Added sanity-trace expectations table for D1 smoke verification beyond the golden fixture set.
