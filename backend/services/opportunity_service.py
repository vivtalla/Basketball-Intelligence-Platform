"""Opportunity Score service — Sprint 58.

Multi-axis workspace that identifies *why* a qualifying player has the
strongest untapped role opportunity on their team / in the league.

Signals (each capped at ±2.0 per-bucket z-score before weighting):
  * efficiency_load_gap   — (ts_pct z) − (usg_pct z)
  * team_impact_swing     — PlayerOnOff.on_off_net z
  * lineup_synergy_lift   — top teammate net_rating_with − baseline lineup net rating
  * role_fit_gap          — cohort-relative 3PA rate + eFG% + FTr shortfall
  * cohort_percentile     — per-bucket net-rating + scoring composite

Weights are exposed in the API and the UI methodology drawer.
"""
from __future__ import annotations

import math
import statistics
import time
from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import LineupStats, Player, PlayerOnOff, SeasonStat
from models.insights import (
    OpportunityCompareHandoff,
    OpportunityDriverContribution,
    OpportunityMethodology,
    OpportunityPlayerRow,
    OpportunityResponse,
    OpportunityRoleFit,
    OpportunityTeammate,
    OpportunityTeamRollup,
)


METHODOLOGY_VERSION = "opportunity_v1"

# Sprint 65: in-process TTL cache. The `team=ALL` whole-league traversal is the hot path
# (scouting boards iterating every team) and it re-does ~30 lineup+on/off queries per call.
# Short TTL for the live season, longer for historical (which never changes intra-day).
_CURRENT_SEASON_CACHE_TTL = 600         # 10 min
_HISTORICAL_SEASON_CACHE_TTL = 24 * 3600

_OPPORTUNITY_CACHE: Dict[Tuple[Any, ...], Tuple[float, OpportunityResponse]] = {}


def _active_nba_season() -> str:
    """Current NBA season in 'YYYY-YY' form. Duplicated from nba_client to avoid the import cycle."""
    now = time.localtime()
    start_year = now.tm_year if now.tm_mon >= 8 else now.tm_year - 1
    return f"{start_year}-{str((start_year + 1) % 100).zfill(2)}"


def _opportunity_cache_ttl(season: str) -> int:
    return _CURRENT_SEASON_CACHE_TTL if season == _active_nba_season() else _HISTORICAL_SEASON_CACHE_TTL


def _opportunity_cache_key(
    season: str, team: Optional[str], min_minutes: float, position: Optional[str]
) -> Tuple[Any, ...]:
    # date-bucket keeps the cache honest across the nightly sync; historical seasons
    # do not change day-over-day but the date bucket costs nothing and prevents drift.
    return (
        season,
        (team or "ALL").upper(),
        round(float(min_minutes), 1),
        (position or "NONE").upper(),
        date.today().isoformat(),
    )


def clear_opportunity_cache() -> None:
    """Test + ops hook."""
    _OPPORTUNITY_CACHE.clear()

WEIGHTS: Dict[str, float] = {
    "efficiency_load_gap": 0.30,
    "team_impact_swing": 0.25,
    "lineup_synergy_lift": 0.20,
    "role_fit_gap": 0.15,
    "cohort_percentile": 0.10,
}

Z_CAP = 2.0
MIN_LINEUP_POSSESSIONS = 100

# Confidence thresholds
CONFIDENCE_THRESHOLDS = {
    "minutes_pg": {"high": 28.0, "medium": 18.0, "low": 10.0},
    "on_minutes": {"high": 500.0, "medium": 200.0, "low": 50.0},
}

# Position buckets reused from trajectory_service; duplicated here to avoid
# cross-service coupling and keep the opportunity rules explicit.
_POSITION_BUCKET_MAP: Dict[str, str] = {
    "pg": "G", "sg": "G", "g": "G", "guard": "G",
    "sf": "F", "pf": "F", "f": "F", "forward": "F",
    "c": "C", "center": "C",
}


def _position_bucket(position: Optional[str]) -> str:
    """Map a player's NBA position string to {G, F, C, other}.

    NBA positions often come back as compound strings like 'Guard-Forward',
    'Forward-Guard', 'Center-Forward', or 'SG/SF'. Sprint 65 fix: split on
    '-' / '/' and take the first token so compound positions bucket correctly
    (e.g. 'Guard-Forward' → 'G', not 'other').
    """
    if not position:
        return "other"
    cleaned = position.lower().strip().replace("/", "-")
    primary = cleaned.split("-", 1)[0].strip()
    return _POSITION_BUCKET_MAP.get(primary, "other")


def _clamp(value: float, cap: float = Z_CAP) -> float:
    if value > cap:
        return cap
    if value < -cap:
        return -cap
    return value


def _zscore(value: Optional[float], mean: float, std: float) -> float:
    if value is None or std <= 0:
        return 0.0
    return _clamp((float(value) - mean) / std)


def _cohort_stats(values: List[float]) -> Tuple[float, float]:
    if len(values) < 2:
        return (sum(values) / len(values) if values else 0.0, 1.0)
    return (statistics.mean(values), statistics.stdev(values) or 1.0)


def _dedupe_player_rows(rows):
    """Keep one season row per player (prefer TOT row for traded players)."""
    best: Dict[int, Tuple[SeasonStat, Player]] = {}
    for stat, player in rows:
        current = best.get(player.id)
        if current is None:
            best[player.id] = (stat, player)
            continue
        current_stat, _ = current
        cand_rank = (
            1 if (stat.team_abbreviation or "").upper() == "TOT" else 0,
            int(stat.gp or 0),
            float(stat.min_pg or 0.0),
        )
        cur_rank = (
            1 if (current_stat.team_abbreviation or "").upper() == "TOT" else 0,
            int(current_stat.gp or 0),
            float(current_stat.min_pg or 0.0),
        )
        if cand_rank > cur_rank:
            best[player.id] = (stat, player)
    return list(best.values())


def _confidence(minutes_pg: Optional[float], on_minutes: Optional[float]) -> str:
    mp = float(minutes_pg or 0.0)
    om = float(on_minutes or 0.0)
    thresh_m = CONFIDENCE_THRESHOLDS["minutes_pg"]
    thresh_o = CONFIDENCE_THRESHOLDS["on_minutes"]
    if mp >= thresh_m["high"] and om >= thresh_o["high"]:
        return "high"
    if mp >= thresh_m["medium"] and om >= thresh_o["medium"]:
        return "medium"
    return "low"


def _bulk_lineup_synergy(
    db: Session,
    season: str,
    player_ids: List[int],
) -> Dict[int, Tuple[Optional[OpportunityTeammate], Optional[float]]]:
    """For each focal player, return (top teammate, synergy lift) in one pass.

    Synergy lift = max qualifying lineup net_rating_with − average net_rating
    across qualifying lineups the player appears in.
    """
    if not player_ids:
        return {}

    id_set = set(player_ids)
    # Fetch all LineupStats rows for the season in one query; partition in Python.
    rows = (
        db.query(LineupStats)
        .filter(LineupStats.season == season)
        .all()
    )

    # teammate_accum[player_id][teammate_id] -> list[(net_rating, possessions)]
    teammate_accum: Dict[int, Dict[int, List[Tuple[float, int]]]] = defaultdict(lambda: defaultdict(list))
    # player_lineup_nrs[player_id] -> list of (net_rating, possessions) for baseline
    player_lineup_nrs: Dict[int, List[Tuple[float, int]]] = defaultdict(list)

    for lineup in rows:
        poss = lineup.possessions or 0
        if poss < MIN_LINEUP_POSSESSIONS or lineup.net_rating is None:
            continue
        try:
            ids = [int(x.strip()) for x in (lineup.lineup_key or "").split("-") if x.strip()]
        except ValueError:
            continue
        focal_ids = id_set.intersection(ids)
        if not focal_ids:
            continue
        for focal in focal_ids:
            player_lineup_nrs[focal].append((lineup.net_rating, poss))
            for tid in ids:
                if tid == focal:
                    continue
                teammate_accum[focal][tid].append((lineup.net_rating, poss))

    # Resolve teammate names for the top teammate of each focal player.
    teammate_name_ids: set = set()
    for focal in teammate_accum:
        # Find top teammate by total shared possessions.
        best_tid = None
        best_poss = 0
        for tid, entries in teammate_accum[focal].items():
            total = sum(p for _, p in entries)
            if total > best_poss:
                best_poss = total
                best_tid = tid
        if best_tid is not None:
            teammate_name_ids.add(best_tid)

    name_lookup: Dict[int, str] = {}
    if teammate_name_ids:
        for p in db.query(Player).filter(Player.id.in_(list(teammate_name_ids))).all():
            name_lookup[p.id] = p.full_name

    out: Dict[int, Tuple[Optional[OpportunityTeammate], Optional[float]]] = {}
    for focal in player_ids:
        teammates = teammate_accum.get(focal, {})
        baseline_entries = player_lineup_nrs.get(focal, [])
        if not teammates or not baseline_entries:
            out[focal] = (None, None)
            continue

        total_poss = sum(p for _, p in baseline_entries)
        baseline_nr = (
            sum(nr * p for nr, p in baseline_entries) / total_poss if total_poss else 0.0
        )

        # Evaluate each teammate: possession-weighted net rating with them.
        best_top: Optional[OpportunityTeammate] = None
        best_lift: Optional[float] = None
        best_top_poss = 0
        for tid, entries in teammates.items():
            t_poss = sum(p for _, p in entries)
            if t_poss < MIN_LINEUP_POSSESSIONS:
                continue
            nr_with = sum(nr * p for nr, p in entries) / t_poss
            lift = nr_with - baseline_nr
            if best_lift is None or lift > best_lift:
                best_lift = lift
            if t_poss > best_top_poss:
                best_top_poss = t_poss
                best_top = OpportunityTeammate(
                    teammate_id=tid,
                    teammate_name=name_lookup.get(tid, str(tid)),
                    shared_possessions=t_poss,
                    net_rating_with=round(nr_with, 1),
                )
        out[focal] = (best_top, round(best_lift, 2) if best_lift is not None else None)
    return out


def build_opportunity_report(
    db: Session,
    season: str,
    team: Optional[str],
    min_minutes: float,
    position: Optional[str] = None,
    use_cache: bool = True,
) -> OpportunityResponse:
    """Build the Opportunity Workspace report.

    Results are cached in-process with a TTL keyed by
    ``(season, team, min_minutes, position, today)`` so the ``team=ALL`` scouting
    traversal does not recompute on every tab open. The date bucket invalidates
    the cache naturally at UTC midnight after the nightly sync.
    """
    cache_key = _opportunity_cache_key(season, team, min_minutes, position)
    if use_cache:
        cached = _OPPORTUNITY_CACHE.get(cache_key)
        if cached is not None:
            expires_at, response = cached
            if expires_at > time.monotonic():
                return response
            _OPPORTUNITY_CACHE.pop(cache_key, None)

    query = (
        db.query(SeasonStat, Player)
        .join(Player, Player.id == SeasonStat.player_id)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
            SeasonStat.min_pg >= min_minutes,
            SeasonStat.usg_pct.isnot(None),
            SeasonStat.ts_pct.isnot(None),
        )
    )
    team_upper = team.upper() if team else None
    if team_upper:
        query = query.filter(SeasonStat.team_abbreviation == team_upper)

    pool = _dedupe_player_rows(query.all())
    methodology = OpportunityMethodology(
        version=METHODOLOGY_VERSION,
        weights=WEIGHTS,
        z_score_cap=Z_CAP,
        min_minutes=min_minutes,
        min_lineup_possessions=MIN_LINEUP_POSSESSIONS,
        confidence_thresholds=CONFIDENCE_THRESHOLDS,
        notes=[
            "Each signal is z-scored within the player's position bucket and capped at ±2.0 so no single axis can dominate.",
            "Team-context score recomputes z-scores against the current team roster; use it as context, not ranking.",
            "Directional hints require high or medium confidence AND concurrent efficiency-load + team-impact signals.",
            "Shot-profile role fit uses 3PA rate, free-throw rate, and eFG% deltas vs the player's position bucket.",
            "Lineup synergy requires at least {0} possessions per qualifying lineup.".format(MIN_LINEUP_POSSESSIONS),
        ],
    )

    if not pool:
        return OpportunityResponse(
            season=season,
            team=team_upper,
            min_minutes=min_minutes,
            position_filter=position,
            rows=[],
            team_rollup=None,
            methodology=methodology,
            warnings=["No qualifying players matched the current season/team/minutes filters."],
        )

    # Pull on/off data and lineup synergy in bulk (scoped to the pool).
    player_ids = [p.id for _, p in pool]
    on_off_rows = (
        db.query(PlayerOnOff)
        .filter(
            PlayerOnOff.player_id.in_(player_ids),
            PlayerOnOff.season == season,
            PlayerOnOff.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    on_off_map: Dict[int, PlayerOnOff] = {row.player_id: row for row in on_off_rows}
    synergy_map = _bulk_lineup_synergy(db, season, player_ids)

    # Precompute per-bucket cohort stats. Each stat is keyed by position bucket.
    # Buckets: G, F, C, other. We also compute a "league" stat bag for fallback.
    bucket_members: Dict[str, List[Tuple[SeasonStat, Player]]] = defaultdict(list)
    for stat, player in pool:
        bucket_members[_position_bucket(player.position)].append((stat, player))

    def _collect(bucket: str, attr: str) -> List[float]:
        vals: List[float] = []
        for stat, _ in bucket_members.get(bucket, []):
            v = getattr(stat, attr, None)
            if v is not None:
                vals.append(float(v))
        return vals

    bucket_stats: Dict[str, Dict[str, Tuple[float, float]]] = defaultdict(dict)
    for bucket in bucket_members.keys():
        for attr in ("ts_pct", "usg_pct", "par3", "ftr", "efg_pct", "net_rating", "pts_pg", "ast_pg", "tov_pg"):
            bucket_stats[bucket][attr] = _cohort_stats(_collect(bucket, attr))

    # On/off net z-score is computed across the full pool (not bucket-scoped)
    # because on_off_net is less position-sensitive than shot-profile stats.
    on_off_values = [row.on_off_net for row in on_off_rows if row.on_off_net is not None]
    on_off_mean, on_off_std = _cohort_stats(on_off_values) if on_off_values else (0.0, 1.0)

    # Team-scoped means (only when team filter is active) for team_opportunity_score.
    team_stats: Dict[str, Tuple[float, float]] = {}
    if team_upper:
        for attr in ("ts_pct", "usg_pct", "par3", "ftr", "efg_pct", "net_rating", "pts_pg"):
            team_stats[attr] = _cohort_stats(
                [float(getattr(s, attr)) for s, _ in pool if getattr(s, attr) is not None]
            )

    # Synergy-lift cohort stats (pool-wide, computed once).
    synergy_raw = [v for _, v in synergy_map.values() if v is not None]
    synergy_m, synergy_s = _cohort_stats(synergy_raw) if synergy_raw else (0.0, 1.0)

    rows: List[OpportunityPlayerRow] = []
    driver_tally: Dict[str, int] = defaultdict(int)

    for stat, player in pool:
        bucket = _position_bucket(player.position)
        bs = bucket_stats[bucket]
        on_off = on_off_map.get(player.id)
        synergy_top, synergy_lift = synergy_map.get(player.id, (None, None))

        # --- Signal z-scores (capped at ±2.0) ---
        ts_m, ts_s = bs.get("ts_pct", (0.0, 1.0))
        usg_m, usg_s = bs.get("usg_pct", (0.0, 1.0))
        z_ts = _zscore(stat.ts_pct, ts_m, ts_s)
        z_usg = _zscore(stat.usg_pct, usg_m, usg_s)
        z_efficiency_load = _clamp(z_ts - z_usg)

        z_team_impact = _zscore(on_off.on_off_net if on_off else None, on_off_mean, on_off_std)

        # Lineup synergy lift: z-score using the pool-wide cohort computed above.
        z_lineup_synergy = _zscore(synergy_lift, synergy_m, synergy_s)

        # Role-fit gap: an efficient 3PA rate below bucket avg AND high eFG% signals untapped shot mix.
        par3_m, par3_s = bs.get("par3", (0.0, 1.0))
        efg_m, efg_s = bs.get("efg_pct", (0.0, 1.0))
        ftr_m, ftr_s = bs.get("ftr", (0.0, 1.0))
        z_par3 = _zscore(stat.par3, par3_m, par3_s)
        z_efg = _zscore(stat.efg_pct, efg_m, efg_s)
        z_ftr = _zscore(stat.ftr, ftr_m, ftr_s)
        # High eFG + below-bucket 3PA rate + any ftr above cohort = shot-diet opportunity.
        z_role_fit = _clamp((z_efg + z_ftr - z_par3) / 3.0)

        # Cohort percentile composite: blend net rating + scoring return vs bucket.
        nr_m, nr_s = bs.get("net_rating", (0.0, 1.0))
        pts_m, pts_s = bs.get("pts_pg", (0.0, 1.0))
        z_nr = _zscore(stat.net_rating, nr_m, nr_s)
        z_pts = _zscore(stat.pts_pg, pts_m, pts_s)
        z_cohort = _clamp((z_nr + z_pts) / 2.0)

        z_signals: Dict[str, float] = {
            "efficiency_load_gap": z_efficiency_load,
            "team_impact_swing": z_team_impact,
            "lineup_synergy_lift": z_lineup_synergy,
            "role_fit_gap": z_role_fit,
            "cohort_percentile": z_cohort,
        }

        weighted = {k: round(v * WEIGHTS[k], 4) for k, v in z_signals.items()}
        opportunity_score = round(sum(weighted.values()), 3)

        # Team-context score uses same signals but with team-scoped cohorts for
        # efficiency_load_gap, role_fit_gap, cohort_percentile. Team impact and
        # lineup synergy are intrinsically pairwise/on-off so they carry over.
        team_opportunity_score: Optional[float] = None
        if team_upper and team_stats:
            ts_m_t, ts_s_t = team_stats.get("ts_pct", (0.0, 1.0))
            usg_m_t, usg_s_t = team_stats.get("usg_pct", (0.0, 1.0))
            par3_m_t, par3_s_t = team_stats.get("par3", (0.0, 1.0))
            efg_m_t, efg_s_t = team_stats.get("efg_pct", (0.0, 1.0))
            ftr_m_t, ftr_s_t = team_stats.get("ftr", (0.0, 1.0))
            nr_m_t, nr_s_t = team_stats.get("net_rating", (0.0, 1.0))
            pts_m_t, pts_s_t = team_stats.get("pts_pg", (0.0, 1.0))
            z_el_t = _clamp(
                _zscore(stat.ts_pct, ts_m_t, ts_s_t) - _zscore(stat.usg_pct, usg_m_t, usg_s_t)
            )
            z_rf_t = _clamp(
                (
                    _zscore(stat.efg_pct, efg_m_t, efg_s_t)
                    + _zscore(stat.ftr, ftr_m_t, ftr_s_t)
                    - _zscore(stat.par3, par3_m_t, par3_s_t)
                ) / 3.0
            )
            z_co_t = _clamp(
                (_zscore(stat.net_rating, nr_m_t, nr_s_t) + _zscore(stat.pts_pg, pts_m_t, pts_s_t)) / 2.0
            )
            team_opportunity_score = round(
                z_el_t * WEIGHTS["efficiency_load_gap"]
                + z_team_impact * WEIGHTS["team_impact_swing"]
                + z_lineup_synergy * WEIGHTS["lineup_synergy_lift"]
                + z_rf_t * WEIGHTS["role_fit_gap"]
                + z_co_t * WEIGHTS["cohort_percentile"],
                3,
            )

        driver_contributions = [
            OpportunityDriverContribution(
                signal=sig,
                z_score=round(z_signals[sig], 3),
                weighted_contribution=weighted[sig],
            )
            for sig in WEIGHTS.keys()
        ]
        driver_contributions.sort(key=lambda d: abs(d.weighted_contribution), reverse=True)
        top_driver: Optional[str] = None
        for d in driver_contributions:
            if d.weighted_contribution > 0:
                top_driver = d.signal
                break
        if top_driver:
            driver_tally[top_driver] += 1

        # Cohort percentile as a 0–100 number using normal CDF on z_cohort.
        cohort_pct = round(50.0 * (1.0 + math.erf(z_cohort / math.sqrt(2.0))), 1)

        confidence = _confidence(stat.min_pg, on_off.on_minutes if on_off else None)

        # Directional hint gate — Sprint 65 calibration:
        #   1) confidence ∈ {high, medium}  (low-confidence never surfaces a banner)
        #   2) signal basis contains ≥2 concurrent positive drivers
        # Both conditions are enforced explicitly so future threshold changes can't
        # accidentally let a 1-signal hint through.
        hint: Optional[str] = None
        hint_basis: List[str] = []
        if (
            confidence in ("high", "medium")
            and z_efficiency_load > 0.8
            and z_team_impact > 0.5
        ):
            hint_basis = ["efficiency_load_gap", "team_impact_swing"]
            if z_lineup_synergy > 0.5 and synergy_top is not None:
                hint_basis.append("lineup_synergy_lift")
            if len(hint_basis) >= 2:
                hint = (
                    "Usage redistribution toward {name} is supported by an above-cohort efficiency-load gap "
                    "and a team that performs better with him on the floor."
                ).format(name=player.full_name)
            else:
                hint_basis = []

        ast_m, ast_s = bs.get("ast_pg", (0.0, 1.0))
        tov_m, tov_s = bs.get("tov_pg", (0.0, 1.0))
        role_fit = OpportunityRoleFit(
            par3=round(float(stat.par3), 3) if stat.par3 is not None else None,
            par3_bucket_avg=round(par3_m, 3),
            ftr=round(float(stat.ftr), 3) if stat.ftr is not None else None,
            ftr_bucket_avg=round(ftr_m, 3),
            efg_pct=round(float(stat.efg_pct), 3) if stat.efg_pct is not None else None,
            efg_bucket_avg=round(efg_m, 3),
            ast_pg=round(float(stat.ast_pg), 2) if stat.ast_pg is not None else None,
            ast_bucket_avg=round(ast_m, 2),
            tov_pg=round(float(stat.tov_pg), 2) if stat.tov_pg is not None else None,
            tov_bucket_avg=round(tov_m, 2),
        )

        row = OpportunityPlayerRow(
            player_id=player.id,
            player_name=player.full_name,
            team_abbreviation=stat.team_abbreviation,
            position=player.position,
            position_bucket=bucket,
            minutes_pg=round(float(stat.min_pg or 0.0), 1) if stat.min_pg is not None else None,
            gp=int(stat.gp or 0) if stat.gp is not None else None,
            # Sprint 68: bump to 3 decimal places. usg_pct is stored as a fraction
            # (0.285), so rounding at 1 dp collapsed Jokic (0.285) / SGA (0.301) /
            # Tatum (0.304) into an identical 0.3 display on the scouting brief.
            usg_pct=round(float(stat.usg_pct), 3) if stat.usg_pct is not None else None,
            ts_pct=round(float(stat.ts_pct), 3) if stat.ts_pct is not None else None,
            off_rating=round(float(stat.off_rating), 1) if stat.off_rating is not None else None,
            def_rating=round(float(stat.def_rating), 1) if stat.def_rating is not None else None,
            net_rating=round(float(stat.net_rating), 1) if stat.net_rating is not None else None,
            pts_pg=round(float(stat.pts_pg or 0.0), 1) if stat.pts_pg is not None else None,
            ast_pg=round(float(stat.ast_pg or 0.0), 1) if stat.ast_pg is not None else None,
            tov_pg=round(float(stat.tov_pg or 0.0), 1) if stat.tov_pg is not None else None,
            on_off_net=round(float(on_off.on_off_net), 1) if on_off and on_off.on_off_net is not None else None,
            on_minutes=on_off.on_minutes if on_off else None,
            off_minutes=on_off.off_minutes if on_off else None,
            top_teammate=synergy_top,
            role_fit=role_fit,
            opportunity_score=opportunity_score,
            team_opportunity_score=team_opportunity_score,
            cohort_percentile=cohort_pct,
            confidence=confidence,
            driver_contributions=driver_contributions,
            directional_hint=hint,
            hint_basis=hint_basis,
            top_driver=top_driver,
        )
        rows.append(row)

    # Apply position filter post-compute so cohort z-scores reflect the full pool.
    if position:
        pos_upper = position.upper()
        rows = [r for r in rows if r.position_bucket == pos_upper]

    rows.sort(key=lambda r: r.opportunity_score, reverse=True)

    # Sprint 65: pre-compute Compare handoff peers from the full pool (not the top-25
    # slice) so a pinned player's peers can still be loaded even when they rank
    # outside the visible leaderboard. Peers are same position_bucket, exclude self,
    # sorted by opportunity_score desc, capped at 3.
    bucket_ranked: Dict[str, List[OpportunityPlayerRow]] = defaultdict(list)
    for r in rows:
        bucket_ranked[r.position_bucket].append(r)

    top_rows = rows[:25]
    for r in top_rows:
        peers = [
            other.player_id
            for other in bucket_ranked.get(r.position_bucket, [])
            if other.player_id != r.player_id
        ][:3]
        r.compare_handoff = OpportunityCompareHandoff(
            pinned_player_id=r.player_id,
            positional_peers=peers,
            cohort_bucket=r.position_bucket,
        )

    team_rollup: Optional[OpportunityTeamRollup] = None
    if team_upper:
        team_rollup = OpportunityTeamRollup(
            team_abbreviation=team_upper,
            top_drivers=dict(driver_tally),
            sample_size=len(rows),
        )

    warnings: List[str] = []
    if not top_rows:
        warnings.append("No qualifying opportunity candidates after filters.")

    response = OpportunityResponse(
        season=season,
        team=team_upper,
        min_minutes=min_minutes,
        position_filter=position,
        rows=top_rows,
        team_rollup=team_rollup,
        methodology=methodology,
        warnings=warnings,
    )
    if use_cache:
        _OPPORTUNITY_CACHE[cache_key] = (
            time.monotonic() + _opportunity_cache_ttl(season),
            response,
        )
    return response
