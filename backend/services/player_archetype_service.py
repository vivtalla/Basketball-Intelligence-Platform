"""Player archetype classifier — Sprint 67 / Stream A.

Deterministic z-score rule engine. No ML, no embeddings. Mirrors the
`classify_archetype` pattern from `backend/routers/styles.py` (Sprint 60).

Full taxonomy, thresholds, subject-row selection rules, and load-bearing
threshold rationale live in `specs/sprint-67-archetype-rules.md`.
"""
from __future__ import annotations

import math
import re
import statistics
import time
from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import Player, SeasonStat
from models.archetype import (
    ArchetypeContributor,
    ArchetypeSample,
    PlayerArchetype,
)


METHODOLOGY_VERSION = "player_archetype_v1"

# --- Peer pool gates --------------------------------------------------------

MIN_GP = 20
MIN_MIN_PG = 15.0
DEVELOPMENTAL_GP_FLOOR = 30
DEVELOPMENTAL_MIN_PG_FLOOR = 20.0
FG3_ATTEMPT_GATE = 50  # fg3_pct_z masked out below this many attempts

# Features required on every pool entrant (see spec §1.1).
REQUIRED_FEATURES = (
    "usg_pct",
    "ast_pg",
    "par3",
    "ftr",
    "ts_pct",
    "stl_pg",
    "blk_pg",
    "oreb_pct",
    "dbpm",
    "obpm",
    "min_pg",
)

# --- Feature display labels (for ArchetypeContributor.label) ----------------

FEATURE_LABELS: Dict[str, str] = {
    "usg_z": "Usage rate",
    "ast_rate_z": "Assists per 36",
    "ast_tov_z": "Assist/turnover ratio",
    "par3_z": "3-point attempt rate",
    "ftr_z": "Free-throw rate",
    "ts_z": "True shooting %",
    "stl_rate_z": "Steals per 36",
    "blk_rate_z": "Blocks per 36",
    "oreb_z": "Offensive rebound %",
    "dbpm_z": "Defensive BPM",
    "obpm_z": "Offensive BPM",
    "fg3_pct_z": "3-point %",
}

# Features eligible to appear as user-facing contributors. Gating features
# (ast_tov, size_inches) live inside triggers only.
ARCHETYPE_CONTRIBUTOR_KEYS = frozenset(FEATURE_LABELS.keys())

# --- TTL cache --------------------------------------------------------------

_CURRENT_SEASON_CACHE_TTL = 600          # 10 min
_HISTORICAL_SEASON_CACHE_TTL = 24 * 3600

# Maps season -> (expires_at, _SeasonFrame)
_SEASON_FRAME_CACHE: Dict[str, Tuple[float, "_SeasonFrame"]] = {}


def clear_archetype_cache() -> None:
    """Test + ops hook."""
    _SEASON_FRAME_CACHE.clear()


def _active_nba_season() -> str:
    """Duplicated from nba_client to avoid the import cycle (same as opportunity_service)."""
    now = time.localtime()
    start_year = now.tm_year if now.tm_mon >= 8 else now.tm_year - 1
    return f"{start_year}-{str((start_year + 1) % 100).zfill(2)}"


def _cache_ttl(season: str) -> int:
    return _CURRENT_SEASON_CACHE_TTL if season == _active_nba_season() else _HISTORICAL_SEASON_CACHE_TTL


# --- Height parser ----------------------------------------------------------

_HEIGHT_RE = re.compile(r"^\s*(\d+)\s*[-'’]\s*(\d+)")


def parse_height_to_inches(value: Optional[str]) -> Optional[int]:
    """Parse 'players.height' (string) into inches.

    Accepts '6-7', "6'7", "6'7\"", '6’7' — returns None for blank/unparseable.
    """
    if not value:
        return None
    match = _HEIGHT_RE.match(str(value))
    if not match:
        return None
    feet = int(match.group(1))
    inches = int(match.group(2))
    total = feet * 12 + inches
    # Sanity: NBA players span ~66"–90". Reject obvious garbage.
    if total < 60 or total > 96:
        return None
    return total


# --- Subject-row selection --------------------------------------------------

def _select_subject_row(rows: List[SeasonStat]) -> Optional[SeasonStat]:
    """Spec §1.1: prefer TOT for regular-season; else the single non-TOT rs row."""
    rs_rows = [r for r in rows if not r.is_playoff]
    if not rs_rows:
        return None
    tot_rows = [r for r in rs_rows if (r.team_abbreviation or "").upper() == "TOT"]
    if tot_rows:
        return tot_rows[0]
    if len(rs_rows) == 1:
        return rs_rows[0]
    return None  # split-season without TOT — ambiguous


# --- Feature extraction -----------------------------------------------------

def _per_36(numerator_pg: Optional[float], min_pg: Optional[float]) -> Optional[float]:
    if numerator_pg is None or min_pg is None or min_pg <= 0:
        return None
    return (float(numerator_pg) * 36.0) / float(min_pg)


def _extract_raw_features(row: SeasonStat) -> Optional[Dict[str, float]]:
    """Return the raw (pre-z) feature dict, or None if any required feature missing."""
    for attr in REQUIRED_FEATURES:
        if getattr(row, attr, None) is None:
            return None
    min_pg = float(row.min_pg)
    ast_rate = _per_36(row.ast_pg, min_pg)
    stl_rate = _per_36(row.stl_pg, min_pg)
    blk_rate = _per_36(row.blk_pg, min_pg)
    if ast_rate is None or stl_rate is None or blk_rate is None:
        return None

    feats: Dict[str, float] = {
        "usg": float(row.usg_pct),
        "ast_rate": ast_rate,
        "par3": float(row.par3),
        "ftr": float(row.ftr),
        "ts": float(row.ts_pct),
        "stl_rate": stl_rate,
        "blk_rate": blk_rate,
        "oreb": float(row.oreb_pct),
        "dbpm": float(row.dbpm),
        "obpm": float(row.obpm),
    }
    # ast_tov is optional in triggers; include it when present for secondary_playmaker.
    if row.ast_tov is not None:
        feats["ast_tov"] = float(row.ast_tov)
    # fg3_pct is sample-gated: only include when the player has enough volume.
    if row.fg3_pct is not None and (row.fg3a or 0) >= FG3_ATTEMPT_GATE:
        feats["fg3_pct"] = float(row.fg3_pct)
    return feats


# --- Season-frame build -----------------------------------------------------

class _SeasonFrame:
    """Cached per-season pool: raw features, means/stds, and player_id -> z-scores."""

    def __init__(
        self,
        season: str,
        zscores_by_player: Dict[int, Dict[str, float]],
        raw_by_player: Dict[int, Dict[str, float]],
        size_by_player: Dict[int, int],
        gp_by_player: Dict[int, int],
        min_pg_by_player: Dict[int, float],
        row_by_player: Dict[int, SeasonStat],
    ) -> None:
        self.season = season
        self.zscores_by_player = zscores_by_player
        self.raw_by_player = raw_by_player
        self.size_by_player = size_by_player
        self.gp_by_player = gp_by_player
        self.min_pg_by_player = min_pg_by_player
        self.row_by_player = row_by_player
        self.peer_pool_size = len(zscores_by_player)


def _build_season_frame(db: Session, season: str) -> _SeasonFrame:
    rows: List[SeasonStat] = (
        db.query(SeasonStat)
        .filter(SeasonStat.season == season, SeasonStat.is_playoff == False)  # noqa: E712
        .all()
    )
    # Group by player_id then resolve subject row (prefer TOT).
    by_player: Dict[int, List[SeasonStat]] = defaultdict(list)
    for row in rows:
        by_player[row.player_id].append(row)

    # Player metadata for height gating.
    player_ids = list(by_player.keys())
    players: Dict[int, Player] = (
        {p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()}
        if player_ids
        else {}
    )

    raw_by_player: Dict[int, Dict[str, float]] = {}
    size_by_player: Dict[int, int] = {}
    gp_by_player: Dict[int, int] = {}
    min_pg_by_player: Dict[int, float] = {}
    row_by_player: Dict[int, SeasonStat] = {}

    for player_id, p_rows in by_player.items():
        subject = _select_subject_row(p_rows)
        if subject is None:
            continue
        if (subject.gp or 0) < MIN_GP or (subject.min_pg or 0) < MIN_MIN_PG:
            continue
        player = players.get(player_id)
        size = parse_height_to_inches(player.height) if player else None
        if size is None:
            continue
        feats = _extract_raw_features(subject)
        if feats is None:
            continue
        raw_by_player[player_id] = feats
        size_by_player[player_id] = size
        gp_by_player[player_id] = int(subject.gp)
        min_pg_by_player[player_id] = float(subject.min_pg)
        row_by_player[player_id] = subject

    # Compute per-feature mean/std across the peer pool.
    feature_keys = set()
    for feats in raw_by_player.values():
        feature_keys.update(feats.keys())

    stats: Dict[str, Tuple[float, float]] = {}
    for key in feature_keys:
        values = [f[key] for f in raw_by_player.values() if key in f]
        if len(values) < 2:
            stats[key] = (0.0, 1.0)
            continue
        mean = statistics.fmean(values)
        variance = statistics.pvariance(values, mu=mean)
        std = math.sqrt(variance) if variance > 0 else 1.0
        stats[key] = (mean, std)

    zscores_by_player: Dict[int, Dict[str, float]] = {}
    for player_id, feats in raw_by_player.items():
        z: Dict[str, float] = {}
        for key, raw_val in feats.items():
            mean, std = stats[key]
            z[f"{key}_z"] = (raw_val - mean) / std if std != 0 else 0.0
        zscores_by_player[player_id] = z

    return _SeasonFrame(
        season=season,
        zscores_by_player=zscores_by_player,
        raw_by_player=raw_by_player,
        size_by_player=size_by_player,
        gp_by_player=gp_by_player,
        min_pg_by_player=min_pg_by_player,
        row_by_player=row_by_player,
    )


def _get_season_frame(db: Session, season: str) -> _SeasonFrame:
    now = time.monotonic()
    cached = _SEASON_FRAME_CACHE.get(season)
    if cached is not None and cached[0] > now:
        return cached[1]
    frame = _build_season_frame(db, season)
    _SEASON_FRAME_CACHE[season] = (now + _cache_ttl(season), frame)
    return frame


# --- Rule engine ------------------------------------------------------------

def _z(zs: Dict[str, float], key: str) -> Optional[float]:
    return zs.get(key)


def _z_or_none_missing(zs: Dict[str, float], *keys: str) -> Optional[List[float]]:
    """Return list of z values in order; None if any is missing (rule does not fire)."""
    vals: List[float] = []
    for k in keys:
        v = zs.get(k)
        if v is None:
            return None
        vals.append(v)
    return vals


def _classify(
    zs: Dict[str, float],
    size_inches: int,
    gp: int,
    min_pg: float,
) -> Tuple[str, str, List[float]]:
    """Apply rules in order. Returns (archetype_key, reason, trigger_magnitudes).

    Reasons match spec §1.2 templates. A rule "does not fire" if any required
    z feature is missing from `zs`.
    """
    usg = _z(zs, "usg_z")
    ast_rate = _z(zs, "ast_rate_z")
    ast_tov = _z(zs, "ast_tov_z")
    par3 = _z(zs, "par3_z")
    ftr = _z(zs, "ftr_z")
    ts = _z(zs, "ts_z")
    stl_rate = _z(zs, "stl_rate_z")
    blk_rate = _z(zs, "blk_rate_z")
    oreb = _z(zs, "oreb_z")
    dbpm = _z(zs, "dbpm_z")
    obpm = _z(zs, "obpm_z")
    fg3_pct = _z(zs, "fg3_pct_z")

    def fires(*vals: Optional[float]) -> bool:
        return all(v is not None for v in vals)

    # 1. Heliocentric Creator
    if fires(usg, ast_rate, obpm) and usg >= 1.0 and ast_rate >= 1.0 and obpm >= 1.0:
        return (
            "heliocentric_creator",
            "High usage, elite playmaking, and above-average efficiency — possessions orbit this player.",
            [abs(usg), abs(ast_rate), abs(obpm)],
        )

    # 2. Lead Ball-Handler
    if fires(usg, ast_rate) and usg >= 0.7 and ast_rate >= 0.8:
        return (
            "lead_ball_handler",
            "High usage with heavy on-ball creation — defined by volume and playmaking regardless of shot diet.",
            [abs(usg), abs(ast_rate)],
        )

    # 3. Iso Scorer
    if (
        fires(usg, ast_rate, par3, ftr)
        and usg >= 0.7
        and ast_rate <= 0.8
        and par3 <= 0.0
        and ftr >= 0.2
    ):
        return (
            "iso_scorer",
            "High-usage mid-range and rim scorer without a heavy passing burden — a bucket-getter.",
            [abs(usg), abs(par3), abs(ftr)],
        )

    # 4. Secondary Playmaker
    if (
        fires(ast_rate, usg, ast_tov)
        and ast_rate >= 0.6
        and usg <= 0.5
        and ast_tov >= 0.3
    ):
        return (
            "secondary_playmaker",
            "Connective passing with controlled usage and low turnover risk.",
            [abs(ast_rate), abs(ast_tov)],
        )

    # 5. Movement Shooter
    if (
        fires(par3, fg3_pct, usg)
        and par3 >= 0.8
        and fg3_pct >= 0.3
        and usg <= 0.5
    ):
        return (
            "movement_shooter",
            "High perimeter volume at reliable accuracy in a low-to-moderate usage role.",
            [abs(par3), abs(fg3_pct)],
        )

    # 6. 3-and-D Wing
    if (
        fires(par3, fg3_pct, dbpm)
        and par3 >= 0.5
        and fg3_pct >= 0.3
        and dbpm >= 0.5
        and 77 <= size_inches <= 82
    ):
        return (
            "three_and_d_wing",
            "Spot-up perimeter threat at wing size paired with above-average defense.",
            [abs(par3), abs(fg3_pct), abs(dbpm)],
        )

    # 7. Rim Pressure Guard
    if (
        fires(ftr, par3, usg)
        and ftr >= 0.6
        and par3 <= 0.0
        and usg >= 0.0
        and size_inches <= 77
    ):
        return (
            "rim_pressure_guard",
            "Downhill guard with above-average foul drawing, a paint-first diet, and meaningful on-ball usage.",
            [abs(ftr), abs(par3)],
        )

    # 8. Connective Forward
    if (
        fires(ast_rate, usg)
        and ast_rate >= 0.4
        and usg <= 0.5
        and size_inches >= 78
    ):
        return (
            "connective_forward",
            "Positional playmaking from the wing/forward, regardless of shot diet.",
            [abs(ast_rate)],
        )

    # 9. Defensive Anchor
    if (
        fires(blk_rate, dbpm)
        and blk_rate >= 1.0
        and dbpm >= 0.8
        and size_inches >= 80
    ):
        return (
            "defensive_anchor",
            "Rim protection and team-defense impact anchor the back line.",
            [abs(blk_rate), abs(dbpm)],
        )

    # 10. Interior Finisher
    if (
        fires(ts, par3, oreb)
        and ts >= 0.7
        and par3 <= -0.4
        and oreb >= 0.4
    ):
        return (
            "interior_finisher",
            "Paint-bound scorer finishing efficiently at high volume inside, with rebound activity.",
            [abs(ts), abs(par3), abs(oreb)],
        )

    # 11. Stretch Big
    if fires(par3) and par3 >= 0.5 and size_inches >= 80:
        return (
            "stretch_big",
            "Frontcourt size with a perimeter shot the opponent must respect.",
            [abs(par3)],
        )

    # 12. Switchable Stopper
    if (
        fires(stl_rate, dbpm)
        and stl_rate >= 0.7
        and dbpm >= 0.6
        and 75 <= size_inches <= 82
    ):
        return (
            "switchable_stopper",
            "On-ball disruption at wing or combo-guard size — switches across multiple positions.",
            [abs(stl_rate), abs(dbpm)],
        )

    # 13. Rotational Energy
    if (
        fires(oreb, ftr, usg)
        and oreb >= 0.5
        and ftr >= 0.3
        and usg <= 0.0
    ):
        return (
            "rotational_energy",
            "Low-usage energy role — second chances, fouls drawn, hustle impact.",
            [abs(oreb), abs(ftr)],
        )

    # 14/15. Balanced Role vs Developmental fallback — decided by the caller
    # based on gp/min_pg since those aren't in `zs`.
    return ("balanced_role", "", [])


def _confidence(trigger_magnitudes: List[float]) -> str:
    if not trigger_magnitudes:
        return "low"
    avg = sum(trigger_magnitudes) / float(len(trigger_magnitudes))
    if avg >= 1.0:
        return "high"
    if avg >= 0.6:
        return "medium"
    return "low"


def _build_contributors(zs: Dict[str, float], raw: Dict[str, float]) -> List[ArchetypeContributor]:
    """Top 4 user-facing features by |z|, matching the team X-Ray fingerprint pattern."""
    ranked = sorted(
        ((k, zs[k]) for k in zs.keys() if k in ARCHETYPE_CONTRIBUTOR_KEYS),
        key=lambda pair: abs(pair[1]),
        reverse=True,
    )
    contributors: List[ArchetypeContributor] = []
    for key, z in ranked[:4]:
        raw_key = key[:-2] if key.endswith("_z") else key  # strip trailing _z
        contributors.append(
            ArchetypeContributor(
                feature_key=key,
                label=FEATURE_LABELS.get(key, key),
                value=raw.get(raw_key),
                z=round(z, 3),
                direction="above" if z >= 0 else "below",
            )
        )
    return contributors


# --- Public entry point -----------------------------------------------------

def classify_player_archetype(
    db: Session,
    player_id: int,
    season: str,
) -> PlayerArchetype:
    """Return the archetype classification for a single player-season.

    Always returns a `PlayerArchetype` — pool misses fall through to
    `developmental` with an explanatory reason rather than raising.
    """
    frame = _get_season_frame(db, season)

    # Pool-miss fallbacks (see spec §1.1 missing-feature / sample policy).
    if player_id not in frame.zscores_by_player:
        # Try to surface enough sample context to distinguish "no row" from
        # "thin sample" for the UI copy.
        p_rows = (
            db.query(SeasonStat)
            .filter(
                SeasonStat.player_id == player_id,
                SeasonStat.season == season,
                SeasonStat.is_playoff == False,  # noqa: E712
            )
            .all()
        )
        subject = _select_subject_row(p_rows)
        gp = int(subject.gp) if subject and subject.gp is not None else 0
        min_pg = float(subject.min_pg) if subject and subject.min_pg is not None else 0.0
        if subject is None:
            reason = "No regular-season row for this player in the requested season."
        elif gp < MIN_GP or min_pg < MIN_MIN_PG:
            reason = "Sample too thin to commit to an archetype yet."
        else:
            reason = "Missing one or more archetype-defining features for this player-season."
        return PlayerArchetype(
            player_id=player_id,
            season=season,
            archetype_key="developmental",
            label="Developmental",
            confidence="low",
            reason=reason,
            contributors=[],
            sample=ArchetypeSample(gp=gp, min_pg=min_pg, peer_pool_size=frame.peer_pool_size),
            methodology_version=METHODOLOGY_VERSION,
        )

    zs = frame.zscores_by_player[player_id]
    raw = frame.raw_by_player[player_id]
    size = frame.size_by_player[player_id]
    gp = frame.gp_by_player[player_id]
    min_pg = frame.min_pg_by_player[player_id]

    archetype_key, reason, trigger_magnitudes = _classify(zs, size, gp, min_pg)

    # Split the fallback: spec §1.2 ranks balanced_role (14) vs developmental (15).
    if archetype_key == "balanced_role":
        if gp < DEVELOPMENTAL_GP_FLOOR or min_pg < DEVELOPMENTAL_MIN_PG_FLOOR:
            archetype_key = "developmental"
            reason = "Sample too thin to commit to an archetype yet."
        else:
            reason = (
                "Role profile sits near league average across the archetype-defining "
                "features — no single style signal dominates."
            )

    label_map = {
        "heliocentric_creator": "Heliocentric Creator",
        "lead_ball_handler": "Lead Ball-Handler",
        "iso_scorer": "Iso Scorer",
        "secondary_playmaker": "Secondary Playmaker",
        "movement_shooter": "Movement Shooter",
        "three_and_d_wing": "3-and-D Wing",
        "rim_pressure_guard": "Rim Pressure Guard",
        "connective_forward": "Connective Forward",
        "defensive_anchor": "Defensive Anchor",
        "interior_finisher": "Interior Finisher",
        "stretch_big": "Stretch Big",
        "switchable_stopper": "Switchable Stopper",
        "rotational_energy": "Rotational Energy",
        "balanced_role": "Balanced Role",
        "developmental": "Developmental",
    }

    return PlayerArchetype(
        player_id=player_id,
        season=season,
        archetype_key=archetype_key,  # type: ignore[arg-type]
        label=label_map[archetype_key],
        confidence=_confidence(trigger_magnitudes),
        reason=reason,
        contributors=_build_contributors(zs, raw),
        sample=ArchetypeSample(gp=gp, min_pg=min_pg, peer_pool_size=frame.peer_pool_size),
        methodology_version=METHODOLOGY_VERSION,
    )


def classify_many(
    db: Session,
    player_ids: List[int],
    season: str,
) -> Dict[int, PlayerArchetype]:
    """Batch variant — warms the season frame once, then classifies each id.

    Used by the B2 similarity upgrade to attach archetype labels to every comp
    without re-triggering the per-call season-frame build.
    """
    # Trigger cache warm up-front; individual lookups reuse the same frame.
    _get_season_frame(db, season)
    return {pid: classify_player_archetype(db, pid, season) for pid in player_ids}
