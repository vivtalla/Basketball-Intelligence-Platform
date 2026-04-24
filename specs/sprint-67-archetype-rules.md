# Sprint 67 — Archetype & Shot Diagnosis Taxonomy

**Status:** A1 (player archetypes) complete by Claude. A2 (shot diagnosis tags) pending Codex.
**Consumed by:** `backend/services/player_archetype_service.py` (A1) and `backend/services/shot_diagnosis_service.py` (A2).
**Discipline:** deterministic rules only, mirroring `backend/routers/styles.py::classify_archetype` (Sprint 60). No ML, no embeddings.

---

## Part 1 — Player Archetype Taxonomy (Stream A / Claude)

### 1.1 Feature extraction

All features are computed from `SeasonStat` (and `Player` for size). No new upstream data this sprint. Features are normalized to **per-season z-scores** against a peer pool of qualifying players so era-independence is preserved (same discipline as `similarity_service.find_similar_players`).

**Peer pool for z-score computation.** All players in the same `season` with `gp >= 20` AND `min_pg >= 15` AND `is_playoff == False` AND all required features non-null. Rationale: keep the pool to rotation players so the distribution isn't dragged by 5-minute cameos.

**Feature dictionary.**

| Feature key | Source | Formula | Role signal |
|---|---|---|---|
| `usg_z` | `season_stats.usg_pct` | raw value | creation burden |
| `ast_rate_z` | `season_stats.ast_pg / min_pg * 36` (AST/36) | per-36 assists | playmaking |
| `ast_tov_z` | `season_stats.ast_tov` | raw | playmaking quality |
| `par3_z` | `season_stats.par3` | FG3A / FGA | perimeter diet |
| `ftr_z` | `season_stats.ftr` | FTA / FGA | rim pressure / foul drawing |
| `ts_z` | `season_stats.ts_pct` | raw | shooting efficiency |
| `stl_rate_z` | `season_stats.stl_pg / min_pg * 36` | per-36 steals | perimeter defense |
| `blk_rate_z` | `season_stats.blk_pg / min_pg * 36` | per-36 blocks | rim protection |
| `oreb_z` | `season_stats.oreb_pct` | raw | interior activity |
| `dreb_rate_z` | `season_stats.dreb / (dreb + opp_dreb)` fallback to `dreb / min_total * 36` if opp unavailable | defensive rebound share | defensive anchor signal |
| `dbpm_z` | `season_stats.dbpm` | raw | all-round defense |
| `obpm_z` | `season_stats.obpm` | raw | all-round offense |
| `fg3_pct_z` | `season_stats.fg3_pct` (gated on `fg3a >= 50`) | raw | shooting talent |
| `size_inches` | `players.height` | raw inches (not z-scored) | archetype gating |

**Missing-feature policy.** If a required feature for a rule is null, the rule **does not fire** (does not contribute a magnitude). A player with all required features null falls through to `Developmental` or `Rotational`.

**Rim rate fallback.** The plan notes rim rate as a target feature but `SeasonStat` has no rim-zone column. For this sprint, use `ftr_z` as a rim-pressure proxy. If Shot Lab zone aggregation is cheap per-player (it already powers `build_shot_quality_response`), a follow-on can swap in true rim rate; for now `ftr_z` is the documented proxy.

### 1.2 Archetype catalog

14 archetypes total, ordered most-specific → least-specific in the classifier (first match wins, like `classify_archetype`). Every archetype has (a) trigger rule, (b) reason phrase template, and (c) trigger-magnitude list feeding `_archetype_confidence`.

**Ordering policy.** Offensive-identity rules first (heliocentric → ball-handler → iso scorer → secondary playmaker), then shooter/wing profiles (movement shooter → 3-and-D → rim pressure guard → connective forward), then interior offense (interior finisher), then defensive-primary rules (defensive anchor → stretch big → switchable stopper), then low-usage fallback (rotational energy), then the developmental catch-all. Defensive Anchor is intentionally placed **before** Stretch Big so that Wembanyama / Holmgren-type players whose defense defines them don't get re-labeled by incidental perimeter volume.

| # | Key | Label | Trigger | Reason template |
|---|---|---|---|---|
| 1 | `heliocentric_creator` | Heliocentric Creator | `usg_z >= 1.2 AND ast_rate_z >= 1.0 AND obpm_z >= 1.0` | "High usage, elite playmaking, and above-average efficiency — possessions orbit this player." |
| 2 | `lead_ball_handler` | Lead Ball-Handler | `usg_z >= 0.7 AND ast_rate_z >= 0.8` | "High usage with heavy on-ball creation — defined by volume and playmaking regardless of shot diet." |
| 3 | `iso_scorer` | Iso Scorer | `usg_z >= 0.7 AND ast_rate_z <= 0.5 AND par3_z <= 0.0 AND ftr_z >= 0.2` | "High-usage mid-range and rim scorer without a heavy passing burden — a bucket-getter." |
| 4 | `secondary_playmaker` | Secondary Playmaker | `ast_rate_z >= 0.6 AND usg_z <= 0.5 AND ast_tov_z >= 0.3` | "Connective passing with controlled usage and low turnover risk." |
| 5 | `movement_shooter` | Movement Shooter | `par3_z >= 0.8 AND fg3_pct_z >= 0.3 AND usg_z <= 0.5` | "High perimeter volume at reliable accuracy in a low-to-moderate usage role." |
| 6 | `three_and_d_wing` | 3-and-D Wing | `par3_z >= 0.5 AND fg3_pct_z >= 0.3 AND dbpm_z >= 0.5 AND 77 <= size_inches <= 82` | "Spot-up perimeter threat at wing size paired with above-average defense." |
| 7 | `rim_pressure_guard` | Rim Pressure Guard | `ftr_z >= 0.6 AND par3_z <= 0.0 AND usg_z >= 0.0 AND size_inches <= 77` | "Downhill guard with above-average foul drawing, a paint-first diet, and meaningful on-ball usage." |
| 8 | `connective_forward` | Connective Forward | `ast_rate_z >= 0.4 AND par3_z >= 0.2 AND size_inches >= 78 AND usg_z <= 0.5` | "Positional playmaking from the wing/forward with modern spacing." |
| 9 | `interior_finisher` | Interior Finisher | `ts_z >= 0.7 AND par3_z <= -0.4 AND oreb_z >= 0.4` | "Paint-bound scorer finishing efficiently at high volume inside, with rebound activity." |
| 10 | `defensive_anchor` | Defensive Anchor | `blk_rate_z >= 1.0 AND dbpm_z >= 0.8 AND size_inches >= 80` | "Rim protection and team-defense impact anchor the back line." |
| 11 | `stretch_big` | Stretch Big | `par3_z >= 0.5 AND size_inches >= 80 AND blk_rate_z >= -0.2` | "Frontcourt size with a perimeter shot the opponent must respect." |
| 12 | `switchable_stopper` | Switchable Stopper | `stl_rate_z >= 0.7 AND dbpm_z >= 0.6 AND 76 <= size_inches <= 82` | "On-ball disruption at wing size — switches across multiple positions." |
| 13 | `rotational_energy` | Rotational Energy | `oreb_z >= 0.5 AND ftr_z >= 0.3 AND usg_z <= 0.0` | "Low-usage energy role — second chances, fouls drawn, hustle impact." |
| 14 | `developmental` | Developmental / Balanced | Fallback: no rule above fired | If `gp < 30 OR min_pg < 20`: "Sample too thin to commit to an archetype yet." Otherwise emit `reason_variant="balanced"`: "Role profile sits near league average across the archetype-defining features." Label flips to **"Balanced Role"** for the balanced variant. |

**Rationale notes on specific thresholds (don't "clean these up" without re-reading).**
- `lead_ball_handler` has *no* `par3_z` gate. This is deliberate — a high-usage, high-assist guard with a mid-range diet (SGA-style, DeRozan-style when playmaking) is still a lead ball-handler. Adding a par3 floor previously orphaned the entire mid-range-creator lane.
- `iso_scorer` (rank 3) catches the *other* side: high usage, low assists, mid-range-heavy scorers like DeMar DeRozan's peak. Positioned right after `lead_ball_handler` so a DeRozan-year with higher-than-usual assists still routes to ball-handler.
- `movement_shooter` (rank 5) was loosened from the original `par3_z >= 1.0 / fg3_pct_z >= 0.6` to catch high-volume veteran shooters whose accuracy dropped to league-average but whose role is still specialist spacer (late-career Klay Thompson profile).
- `three_and_d_wing` size floor raised to 77" (6'5") to exclude pure guards whose defense happens to grade well.
- `rim_pressure_guard` thresholds tuned: `ftr_z >= 0.6` catches top-~30% rim pressure (was top-~20%, too strict); `par3_z <= 0.0` means below-average 3PA rate (was `<= 0.2` which paradoxically allowed above-average perimeter volume); `usg_z >= 0.0` floor distinguishes an on-ball creator from a bench energy guard.
- `stretch_big` `blk_rate_z >= -0.2` floor excludes pure stretch-4s with no rim presence, preserving the "big" framing. Defensive Anchor fires first for elite rim protectors, so Stretch Big is what's *left* — size-gated floor-spacers who aren't defensive-primary.
- `defensive_anchor` placed before `stretch_big` so Wembanyama / Chet Holmgren, who shoot threes but are *defined by* rim protection, route to the defensive label.

### 1.3 Confidence band

Port `_archetype_confidence(trigger_magnitudes)` verbatim:

- `high` if `mean(|z|) >= 1.0`
- `medium` if `mean(|z|) >= 0.6`
- `low` otherwise (including `developmental` / `balanced_role`)

### 1.4 Contributors (fingerprint)

Same pattern as `_style_xray_label`: rank the full feature list by `|z|` descending and return the top 4 as `ArchetypeContributor` records. Each contributor carries `{feature_key, label, value, z, direction}` where `direction ∈ {"above", "below"}` based on sign of z.

A dedicated `ARCHETYPE_CONTRIBUTOR_KEYS` set (analog of `_STYLE_CONTRIBUTOR_KEYS`) restricts contributors to features with basketball-native labels: `usg_z`, `ast_rate_z`, `par3_z`, `ftr_z`, `ts_z`, `stl_rate_z`, `blk_rate_z`, `oreb_z`, `dbpm_z`, `obpm_z`, `fg3_pct_z`. (Skips `ast_tov_z`, `dreb_rate_z`, `size_inches` — those are gating features used only inside triggers, not for user-facing fingerprints.)

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
| `rim_pressure_guard` | Ja Morant 2022-23 | — |
| `connective_forward` | Draymond Green 2022-23 | — |
| `interior_finisher` | Jarrett Allen 2023-24 (Gobert-type offensive profile without Defensive Anchor tripping; Gobert himself routes to Defensive Anchor first) | Gobert routes to Defensive Anchor at rank 10 before reaching this rule. |
| `defensive_anchor` | Victor Wembanyama 2024-25 | Fires before Stretch Big, so Wemby's 3PA volume doesn't relabel him. |
| `stretch_big` | Kristaps Porziņģis 2023-24 | Must fail Defensive Anchor (`dbpm_z < 0.8` typically). |
| `switchable_stopper` | Jrue Holiday 2022-23 | — |
| `rotational_energy` | Mitchell Robinson 2022-23 | — |
| `developmental` | Any player with `gp < 30 OR min_pg < 20` | — |
| `developmental` (balanced) | Any rotation player with no rule firing | `reason_variant="balanced"` — label renders as "Balanced Role". |

**Rule ordering policy.** First rule whose trigger evaluates true wins. If a fixture expects a later archetype, the earlier rules must fail their own triggers on that fixture — never rely on short-circuit logic beyond the documented ordering.

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
