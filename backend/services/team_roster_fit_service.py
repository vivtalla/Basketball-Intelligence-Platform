"""Team-side player fit (Sprint 89).

Inverts ``team_fit_service`` — fix the team, score many players against it.

Two outputs:
  * ``current_roster_fits``: every qualified player on the team, scored against
    the rest of the roster (self-excluded so overlap doesn't double-count).
  * ``league_candidates``: top 25 non-roster qualified players, scored against
    the full current roster.

Reuses the Sprint 67-69 three-component model from ``team_fit_service``
(skill supply 45 / role runway 25 / teammate overlap 30 on 13 z-scored
features). Adds:
  * **Position-cohort percentile** (G/F/C) shown alongside the global
    percentile so a center isn't graded only against guard scoring rates.
    Display-only — the score formula still uses global norms so
    cross-position rankings stay coherent.
  * **Team need vector** — roster-weighted average z per feature; negative z
    surfaces as ``primary_needs`` so every fit score traces to a visible
    team-level need.
  * **Self-exclusion** — when scoring a current roster player, the comparison
    set is the rest of the roster (excluding the subject), so Role
    Competition isn't artificially inflated by the player overlapping
    themselves.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import Player, SeasonStat, Team
from models.team_fit import FitDriver, OverlapFlag
from models.team_roster_fit import (
    CohortPercentile,
    PlayerFitEntry,
    TeamNeedFeature,
    TeamNeedVector,
    TeamRosterFitMethodology,
    TeamRosterFitResponse,
)
from services.intel_math import clamp
from services.similarity_service import (
    MIN_GP,
    SIMILARITY_STATS_V2,
    STAT_KEYS_V2,
    TEAM_FIT_FEATURE_LABELS,
    _qualified_rows_v2,
    _raw_z,
    _season_norms_v2,
    _TEAM_FIT_DUPLICATE_THRESHOLD,
    _TEAM_FIT_PENALTY,
)
from services.team_fit_service import (
    METHODOLOGY_VERSION as PLAYER_SIDE_VERSION,
    MIN_TEAM_PLAYERS,
    POSITION_BUCKET_MAP,
    ROLE_FEATURES,
    WEIGHTS,
    _bucket_runway_bonus,
    _build_drivers,
    _confidence_for_team,
    _feature_team_best,
    _position_bucket,
    _team_overlap_flags,
)


SeasonType = Literal["Regular Season", "Playoffs"]

METHODOLOGY_VERSION = "team_roster_fit_v1"
LEAGUE_CANDIDATE_LIMIT = 25
LEAGUE_CANDIDATE_MIN_GP = MIN_GP  # mirrors player-side gate (20 reg / 4 playoff)
NEED_VECTOR_FEATURE_LIMIT = 5
COHORT_BUCKETS = ["G", "F", "C"]


# ---------------------------------------------------------------------------
# Position-cohort norms (Sprint 89 — display-only)
# ---------------------------------------------------------------------------

def _build_player_position_lookup(
    rows: List[SeasonStat],
    db: Session,
) -> Dict[int, str]:
    """Resolve position bucket per player_id by joining to the Player table."""
    player_ids = list({row.player_id for row in rows})
    if not player_ids:
        return {}
    players = db.query(Player).filter(Player.id.in_(player_ids)).all()
    return {p.id: _position_bucket(p.position) for p in players}


def _cohort_norms(
    rows: List[SeasonStat],
    position_lookup: Dict[int, str],
) -> Dict[str, Dict[str, Dict[str, Dict[str, float]]]]:
    """Per-(season, bucket, feature) mean/std using the same z-score recipe as
    ``_season_norms_v2``. Missing buckets fall back to the global norm at
    lookup time."""
    by_season_bucket: Dict[str, Dict[str, Dict[str, List[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    for row in rows:
        bucket = position_lookup.get(row.player_id, "other")
        if bucket == "other":
            continue
        for key in STAT_KEYS_V2:
            val = getattr(row, key, None)
            if val is not None:
                by_season_bucket[row.season][bucket][key].append(float(val))

    norms: Dict[str, Dict[str, Dict[str, Dict[str, float]]]] = {}
    for season, buckets in by_season_bucket.items():
        norms[season] = {}
        for bucket, stat_vals in buckets.items():
            norms[season][bucket] = {}
            for key, vals in stat_vals.items():
                if len(vals) < 2:
                    norms[season][bucket][key] = {
                        "mean": vals[0] if vals else 0.0,
                        "std": 1.0,
                    }
                    continue
                mean = sum(vals) / len(vals)
                variance = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
                std = math.sqrt(variance) if variance > 0 else 1.0
                norms[season][bucket][key] = {"mean": mean, "std": std}
    return norms


def _z_to_percentile(z: float) -> float:
    """Convert a z-score to a 0–100 percentile via the standard-normal CDF."""
    cdf = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return round(clamp(cdf * 100.0, 0.0, 100.0), 1)


def _cohort_percentiles_for_player(
    row: SeasonStat,
    bucket: str,
    cohort_norms: Dict[str, Dict[str, Dict[str, Dict[str, float]]]],
    feature_keys: List[str],
    limit: int = 3,
) -> List[CohortPercentile]:
    """Top-K cohort percentiles for a player, sorted by absolute z (most
    distinctive features). Falls back silently if cohort data is missing."""
    season_norms = cohort_norms.get(row.season, {})
    bucket_norms = season_norms.get(bucket, {})
    if not bucket_norms:
        return []
    scored: List[Tuple[float, CohortPercentile]] = []
    for key in feature_keys:
        stat_norm = bucket_norms.get(key)
        val = getattr(row, key, None)
        if stat_norm is None or val is None:
            continue
        std = stat_norm["std"] or 1.0
        z = (float(val) - stat_norm["mean"]) / std
        scored.append(
            (
                abs(z),
                CohortPercentile(
                    feature_key=key,
                    label=TEAM_FIT_FEATURE_LABELS.get(key, key),
                    percentile=_z_to_percentile(z),
                    bucket=bucket,
                ),
            )
        )
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


# ---------------------------------------------------------------------------
# Team need vector
# ---------------------------------------------------------------------------

def _build_team_need_vector(
    roster: List[SeasonStat],
    norms: Dict[str, Dict[str, Dict[str, float]]],
) -> TeamNeedVector:
    """Roster-weighted (by min_pg) average z per feature.
    Negative z = team is below league average on that feature ⇒ a need.
    Positive z = strength.
    """
    if not roster:
        return TeamNeedVector(features=[], primary_needs=[], primary_strengths=[])

    weighted: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    for row in roster:
        z = _raw_z(row, norms)
        if z is None:
            continue
        weight = max(float(row.min_pg or 0.0), 0.5)  # floor so deep bench still counts a little
        for key, value in z.items():
            weighted[key].append((value, weight))

    features: List[TeamNeedFeature] = []
    # dict(...).keys() dedupes — SIMILARITY_STATS_V2 lists stl_pg/blk_pg twice
    # (full weight + 0.6 weight) which would otherwise double-surface those
    # features in primary_needs / primary_strengths.
    for key in dict(SIMILARITY_STATS_V2).keys():
        samples = weighted.get(key, [])
        if not samples:
            continue
        total_weight = sum(w for _z, w in samples) or 1.0
        team_z = sum(z * w for z, w in samples) / total_weight
        features.append(
            TeamNeedFeature(
                feature_key=key,
                label=TEAM_FIT_FEATURE_LABELS.get(key, key),
                team_z=round(float(team_z), 3),
                gap=round(float(-team_z), 3),
                percentile=_z_to_percentile(team_z),
            )
        )

    needs_sorted = sorted(features, key=lambda f: f.team_z)
    strengths_sorted = sorted(features, key=lambda f: f.team_z, reverse=True)
    primary_needs = [
        f.label for f in needs_sorted[:NEED_VECTOR_FEATURE_LIMIT] if f.team_z < -0.1
    ]
    primary_strengths = [
        f.label for f in strengths_sorted[:NEED_VECTOR_FEATURE_LIMIT] if f.team_z > 0.1
    ]
    return TeamNeedVector(
        features=features,
        primary_needs=primary_needs,
        primary_strengths=primary_strengths,
    )


# ---------------------------------------------------------------------------
# Scoring + entry assembly
# ---------------------------------------------------------------------------

def _summary_for_entry(
    is_current: bool,
    full_name: str,
    score: float,
    drivers: List[FitDriver],
    overlaps: List[OverlapFlag],
) -> str:
    role = "current roster fit" if is_current else "fit"
    if drivers and overlaps:
        return "{0} {1} is {2:.1f}: clearest unlocked value is {3}, but {4} is already covered.".format(
            full_name, role, score, drivers[0].label.lower(), overlaps[0].label.lower()
        )
    if drivers:
        return "{0} {1} is {2:.1f}: clearest value add is {3}.".format(
            full_name, role, score, drivers[0].label.lower()
        )
    if overlaps:
        return "{0} {1} is {2:.1f}: overlap is the main story, led by {3}.".format(
            full_name, role, score, overlaps[0].label.lower()
        )
    return "{0} {1} is {2:.1f}: no single role feature dominates.".format(
        full_name, role, score
    )


def _score_player_against_team(
    db: Session,
    player: Player,
    subject_row: SeasonStat,
    comparison_roster: List[SeasonStat],
    norms: Dict[str, Dict[str, Dict[str, float]]],
    player_lookup: Dict[int, Player],
    cohort_norms: Dict[str, Dict[str, Dict[str, Dict[str, float]]]],
    bucket: str,
    is_current: bool,
    current_team_abbr: Optional[str],
) -> PlayerFitEntry:
    subject_z = _raw_z(subject_row, norms) or {}
    team_best = _feature_team_best(comparison_roster, norms, exclude_player_id=subject_row.player_id)
    overlaps = _team_overlap_flags(db, subject_row, comparison_roster, norms)
    overlap_keys = {flag.feature_key for flag in overlaps}

    value_drivers = _build_drivers(subject_z, team_best, list(dict(SIMILARITY_STATS_V2).keys()), 4)
    role_drivers = _build_drivers(subject_z, team_best, ROLE_FEATURES, 4)

    value_signal = sum(d.contribution for d in value_drivers) / float(len(value_drivers) or 1)
    role_signal = sum(d.contribution for d in role_drivers) / float(len(role_drivers) or 1)
    role_signal += _bucket_runway_bonus(player, subject_row, comparison_roster, player_lookup)

    unique_feature_count = len(set(key for key, _w in SIMILARITY_STATS_V2))
    overlap_ratio = len(overlap_keys) / float(unique_feature_count or 1)
    overlap_score = clamp(100.0 - (overlap_ratio * 72.0), 0.0, 100.0)
    value_score = clamp(45.0 + (value_signal * 27.5), 0.0, 100.0)
    role_score = clamp(45.0 + (role_signal * 27.5), 0.0, 100.0)

    fit_score = round(
        value_score * WEIGHTS["value_supplied"]
        + overlap_score * WEIGHTS["teammate_overlap"]
        + role_score * WEIGHTS["role_runway"],
        1,
    )

    confidence, confidence_notes = _confidence_for_team(
        comparison_roster, value_drivers or role_drivers, []
    )

    cohort_percentiles = _cohort_percentiles_for_player(
        subject_row,
        bucket,
        cohort_norms,
        list(dict(SIMILARITY_STATS_V2).keys()),
    )

    return PlayerFitEntry(
        player_id=player.id,
        full_name=player.full_name,
        position=player.position,
        position_bucket=bucket,
        headshot_url=player.headshot_url,
        current_team_abbr=current_team_abbr,
        season=subject_row.season,
        gp=int(subject_row.gp or 0),
        fit_score=fit_score,
        skill_supply_score=round(value_score, 1),
        roster_need_score=round(role_score, 1),
        role_competition_score=round(overlap_score, 1),
        confidence=confidence,
        confidence_notes=confidence_notes,
        summary=_summary_for_entry(is_current, player.full_name, fit_score, value_drivers, overlaps),
        value_drivers=value_drivers,
        role_runway_drivers=role_drivers,
        overlap_flags=overlaps,
        cohort_percentiles=cohort_percentiles,
    )


# ---------------------------------------------------------------------------
# Methodology block
# ---------------------------------------------------------------------------

def _methodology() -> TeamRosterFitMethodology:
    return TeamRosterFitMethodology(
        version=METHODOLOGY_VERSION,
        weights=WEIGHTS,
        duplicate_threshold=_TEAM_FIT_DUPLICATE_THRESHOLD,
        duplicate_penalty=_TEAM_FIT_PENALTY,
        min_team_players=MIN_TEAM_PLAYERS,
        league_candidate_min_gp=LEAGUE_CANDIDATE_MIN_GP,
        position_cohort_enabled=True,
        cohort_buckets=COHORT_BUCKETS,
        notes=[
            "Inverts player-side {0} — fix the team, score many players. Same 13 z-scored features and same three-component formula (45 / 25 / 30) so player-side and team-side reads use the same math.".format(PLAYER_SIDE_VERSION),
            "Current-roster scoring excludes the subject from the comparison roster so Role Competition isn't inflated by self-overlap.",
            "Position-cohort percentile (G / F / C) is shown alongside the global percentile so a center isn't graded only against guard rates. The score formula keeps using global norms — cohort percentile is a display-only caveat.",
            "League candidates are ranked by statistical fit only. Salary, contract length, free-agent status, age, injury history, and trade feasibility are out of scope.",
            "Same-season comparisons only. No projections.",
            "13 box-score-derived features; does not include shot location overlap, defensive scheme, or play-type fit.",
            "Position cohort is coarse (G / F / C) — does not distinguish stretch-4 vs traditional PF.",
        ],
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_team_roster_fit_report(
    db: Session,
    team_abbr: str,
    season: str = "2024-25",
    season_type: SeasonType = "Regular Season",
    league_candidate_limit: int = LEAGUE_CANDIDATE_LIMIT,
) -> TeamRosterFitResponse:
    abbr_upper = team_abbr.upper()
    team = db.query(Team).filter(Team.abbreviation == abbr_upper).first()
    if team is None:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(abbr_upper))

    is_playoff = season_type == "Playoffs"
    all_rows = _qualified_rows_v2(db, is_playoff=is_playoff)
    norms = _season_norms_v2(all_rows)

    season_rows = [r for r in all_rows if r.season == season]
    if not season_rows:
        raise HTTPException(
            status_code=404,
            detail="No qualified {0} rows found for season {1}.".format(
                "playoff" if is_playoff else "regular-season", season
            ),
        )

    # Roster = season rows whose team_abbreviation matches; skip TOT rows (those
    # are aggregates from traded players and double-count if included).
    roster: List[SeasonStat] = [
        r for r in season_rows
        if (r.team_abbreviation or "").upper() == abbr_upper
        and (r.team_abbreviation or "").upper() != "TOT"
    ]
    qualified_roster_count = len(roster)

    warnings: List[str] = []
    if qualified_roster_count < MIN_TEAM_PLAYERS:
        warnings.append(
            "{0} has only {1} qualified roster rows (min {2}); fit reads are directional only.".format(
                abbr_upper, qualified_roster_count, MIN_TEAM_PLAYERS
            )
        )

    # Pre-resolve player records for everyone in the qualified pool — used for
    # name/position/headshot in the response and for `_bucket_runway_bonus`.
    pool_player_ids = list({r.player_id for r in season_rows})
    player_lookup: Dict[int, Player] = (
        {p.id: p for p in db.query(Player).filter(Player.id.in_(pool_player_ids)).all()}
        if pool_player_ids
        else {}
    )
    position_lookup: Dict[int, str] = {
        pid: _position_bucket(p.position) for pid, p in player_lookup.items()
    }
    cohort_norms = _cohort_norms(season_rows, position_lookup)

    team_need_vector = _build_team_need_vector(roster, norms)

    # ── Current roster fits ────────────────────────────────────────────────
    current_roster_fits: List[PlayerFitEntry] = []
    if qualified_roster_count >= MIN_TEAM_PLAYERS:
        for subject_row in roster:
            player = player_lookup.get(subject_row.player_id)
            if player is None:
                continue
            comparison_roster = [r for r in roster if r.player_id != subject_row.player_id]
            entry = _score_player_against_team(
                db=db,
                player=player,
                subject_row=subject_row,
                comparison_roster=comparison_roster,
                norms=norms,
                player_lookup=player_lookup,
                cohort_norms=cohort_norms,
                bucket=position_lookup.get(subject_row.player_id, "other"),
                is_current=True,
                current_team_abbr=abbr_upper,
            )
            current_roster_fits.append(entry)
        current_roster_fits.sort(key=lambda e: e.fit_score, reverse=True)

    # ── League candidates ──────────────────────────────────────────────────
    roster_player_ids = {r.player_id for r in roster}
    candidate_rows = [
        r for r in season_rows
        if r.player_id not in roster_player_ids
        and (r.team_abbreviation or "").upper() != "TOT"
    ]

    league_candidates: List[PlayerFitEntry] = []
    if qualified_roster_count >= MIN_TEAM_PLAYERS:
        for subject_row in candidate_rows:
            player = player_lookup.get(subject_row.player_id)
            if player is None:
                continue
            entry = _score_player_against_team(
                db=db,
                player=player,
                subject_row=subject_row,
                comparison_roster=roster,
                norms=norms,
                player_lookup=player_lookup,
                cohort_norms=cohort_norms,
                bucket=position_lookup.get(subject_row.player_id, "other"),
                is_current=False,
                current_team_abbr=(subject_row.team_abbreviation or "").upper() or None,
            )
            league_candidates.append(entry)
        league_candidates.sort(key=lambda e: e.fit_score, reverse=True)
        league_candidates = league_candidates[: max(0, league_candidate_limit)]

    return TeamRosterFitResponse(
        team_abbreviation=abbr_upper,
        team_name=team.name,
        season=season,
        season_type=season_type,
        qualified_roster_count=qualified_roster_count,
        team_need_vector=team_need_vector,
        current_roster_fits=current_roster_fits,
        league_candidates=league_candidates,
        methodology=_methodology(),
        warnings=warnings,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
