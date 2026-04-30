"""Sprint 81 — materialize Basketball Value + modifier vectors for every
(player, season) referenced by ``award_voting``.

Activates ``mvp_case_v5`` calibrated weights. Without this materialization
``award_calibration_service.calibrate_award_case_weights()`` returns the
hand-tuned defaults with ``calibration_pending=True``.

Why approximations:
``mvp_service.py``'s production scoring uses live game logs + clutch splits
+ opponent context + signature-game windows that don't exist as derived
data for old seasons. We compute Basketball Value from season-level stats
(per-100 production + efficiency + GP-weighted reliability) and modifier
proxies from team-context columns. The output is good enough to fit
calibration weights against historical voting outcomes, which is what we
need for ``mvp_case_v5`` to flip from ``calibration_pending=True`` to
``False``.

Idempotent: re-running upserts on (player_id, season, award_type).

Usage:
    python data/materialize_award_modifiers.py
    python data/materialize_award_modifiers.py --season 2023-24  # single season
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session  # noqa: E402

from db.database import SessionLocal  # noqa: E402
from db.models import (  # noqa: E402
    AwardCaseCandidate,
    AwardVote,
    SeasonStat,
    Team,
    TeamSeasonStat,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Basketball Value from season_stats — composite of production, efficiency,
# and reliability. Centered around ~25 for elite MVP candidates so the math
# scale matches what mvp_service.py's live scoring produces.
# ---------------------------------------------------------------------------

def _basketball_value(stat: SeasonStat) -> float:
    """Composite ranking score for a player-season.

    ~50 = generational MVP year (Curry 2015-16, Jokic 2022-23)
    ~30 = strong MVP candidate
    ~15 = All-NBA contender
    ~0  = league average
    """
    pts = float(stat.pts or 0)              # per-game points
    ast = float(stat.ast or 0)
    reb = float(stat.reb or 0)
    ts = float(stat.ts_pct or 0.55)         # league-average fallback
    gp = float(stat.gp or 0)

    # Per-game production (points heaviest, then assists/rebounds at 0.6 weight)
    production = pts + 0.6 * ast + 0.4 * reb

    # Efficiency lift: TS% above 0.55 league average, scaled to ±15.
    efficiency_bonus = (ts - 0.55) * 100.0

    # GP reliability: <50 GP discounts; 70+ = full credit.
    gp_factor = max(0.5, min(1.0, gp / 70.0))

    return (production + efficiency_bonus) * gp_factor


# ---------------------------------------------------------------------------
# Modifier vector proxies. The five dimensions match
# ``award_calibration_service.MODIFIER_KEYS`` order exactly.
# ---------------------------------------------------------------------------

def _team_framing(
    stat: SeasonStat,
    team_record_by_abbr_season: Dict[Tuple[str, str], Tuple[int, int]],
) -> float:
    """Team success modifier: above-average wins help the candidate's case.

    Centered so a 41-41 team contributes 0; a 60-22 team contributes ~+0.5.
    Capped at ±1.0.
    """
    record = team_record_by_abbr_season.get(((stat.team_abbreviation or "").upper(), stat.season))
    if not record:
        return 0.0
    wins, losses = record
    total = wins + losses
    if total <= 0:
        return 0.0
    win_pct = wins / total
    return max(-1.0, min(1.0, (win_pct - 0.500) * 4.0))


def _eligibility_pressure(stat: SeasonStat) -> float:
    """Negative modifier for low GP / low minutes (NBA's 65-game rule + voter bias).

    Range: 0.0 (full eligibility) → -1.0 (clearly ineligible by GP/MP).
    """
    gp = float(stat.gp or 0)
    mpg = float(stat.min_per_game or 0) if hasattr(stat, "min_per_game") else 0.0
    if mpg == 0.0:
        # Compute MPG from total minutes if min_per_game isn't a column.
        min_total = float(stat.min_total or 0)
        mpg = min_total / gp if gp > 0 else 0.0

    if gp >= 65 and mpg >= 30:
        return 0.0
    if gp < 50 or mpg < 25:
        return -1.0
    # Linear ramp between the bounds.
    gp_factor = (gp - 50) / 15.0
    mpg_factor = (mpg - 25) / 5.0
    return max(-1.0, min(0.0, -0.5 * (1 - gp_factor) - 0.5 * (1 - mpg_factor)))


def _clutch_proxy(stat: SeasonStat) -> float:
    """Clutch proxy from season clutch columns when present, else 0.

    season_stats has clutch_* columns from PBP-derived metrics. Old seasons
    pre-PBP-derivation will always read 0 here — that's fine, the calibrator
    will just learn to weigh clutch lower than other pillars on those folds.
    """
    pts_clutch = getattr(stat, "clutch_pts", None) or 0
    fga_clutch = getattr(stat, "clutch_fga", None) or 0
    if not pts_clutch or not fga_clutch:
        return 0.0
    # Points per clutch FGA — normalize so ~1.2 PPS == +0.5 modifier.
    return max(-1.0, min(1.0, ((pts_clutch / fga_clutch) - 1.0) * 2.0))


def _momentum_proxy(stat: SeasonStat) -> float:
    """Momentum is a recency-weighted in-season trend signal.

    Old seasons don't have game-log granularity available offline, so we
    return 0 for historical materialization. Live mvp_service.py computes
    the real value at request time. The calibrator will lean less on this
    pillar when historical folds are mostly 0.
    """
    return 0.0


def _signature_games_proxy(stat: SeasonStat) -> float:
    """Same caveat as momentum — proxies to 0 without per-game WPA data."""
    return 0.0


# ---------------------------------------------------------------------------
# Materialization driver
# ---------------------------------------------------------------------------


def _build_team_record_index(
    db: Session, seasons: List[str]
) -> Dict[Tuple[str, str], Tuple[int, int]]:
    """(team_abbreviation, season) → (wins, losses) from team_season_stats joined to teams.

    TeamSeasonStat carries team_id + ``w``/``l``; we resolve abbreviation via
    the ``teams`` table so the SeasonStat join key (which is abbreviation,
    not id) lines up.
    """
    index: Dict[Tuple[str, str], Tuple[int, int]] = {}
    if not seasons:
        return index
    rows = (
        db.query(TeamSeasonStat, Team)
        .join(Team, Team.id == TeamSeasonStat.team_id)
        .filter(
            TeamSeasonStat.season.in_(seasons),
            TeamSeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    for stat, team in rows:
        team_abbr = (team.abbreviation or "").upper()
        if not team_abbr:
            continue
        wins = int(getattr(stat, "w", 0) or 0)
        losses = int(getattr(stat, "l", 0) or 0)
        index[(team_abbr, stat.season)] = (wins, losses)
    return index


def materialize(
    db: Session,
    *,
    season: Optional[str] = None,
    award_type: str = "MVP",
    verbose: bool = True,
) -> Dict[str, int]:
    """Upsert AwardCaseCandidate rows for every (player, season) in award_voting.

    Args:
        season: optional single-season filter; default = all seasons present.
        award_type: which award to materialize candidates for.

    Returns: ``{inserted, updated, skipped_no_season_stat, scanned}``.
    """
    query = db.query(AwardVote).filter(AwardVote.award_type == award_type)
    if season is not None:
        query = query.filter(AwardVote.season == season)
    votes = query.all()
    if not votes:
        if verbose:
            print("materialize_award_modifiers: no award_voting rows to process")
        return {"inserted": 0, "updated": 0, "skipped_no_season_stat": 0, "scanned": 0}

    seasons_in_play = sorted({v.season for v in votes})
    team_record_index = _build_team_record_index(db, seasons_in_play)

    # Pull all relevant season_stats once. Use Regular Season slice (is_playoff=False).
    player_season_pairs = {(v.player_id, v.season) for v in votes}
    stat_rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.is_playoff == False,  # noqa: E712
            SeasonStat.season.in_(seasons_in_play),
        )
        .all()
    )
    # GP-weighted dedupe in case a player has multiple TOT rows.
    stat_index: Dict[Tuple[int, str], SeasonStat] = {}
    for row in stat_rows:
        key = (row.player_id, row.season)
        if key not in player_season_pairs:
            continue
        existing = stat_index.get(key)
        if existing is None or (row.gp or 0) > (existing.gp or 0):
            stat_index[key] = row

    inserted = updated = skipped = 0
    now = datetime.utcnow()

    for vote in votes:
        stat = stat_index.get((vote.player_id, vote.season))
        if stat is None:
            skipped += 1
            continue

        bv = _basketball_value(stat)
        modifiers = (
            _team_framing(stat, team_record_index),
            _eligibility_pressure(stat),
            _clutch_proxy(stat),
            _momentum_proxy(stat),
            _signature_games_proxy(stat),
        )

        existing = (
            db.query(AwardCaseCandidate)
            .filter(
                AwardCaseCandidate.player_id == vote.player_id,
                AwardCaseCandidate.season == vote.season,
                AwardCaseCandidate.award_type == award_type,
            )
            .one_or_none()
        )
        if existing is None:
            db.add(
                AwardCaseCandidate(
                    player_id=vote.player_id,
                    season=vote.season,
                    award_type=award_type,
                    basketball_value=bv,
                    modifier_team_framing=modifiers[0],
                    modifier_eligibility_pressure=modifiers[1],
                    modifier_clutch=modifiers[2],
                    modifier_momentum=modifiers[3],
                    modifier_signature_games=modifiers[4],
                )
            )
            inserted += 1
        else:
            existing.basketball_value = bv
            existing.modifier_team_framing = modifiers[0]
            existing.modifier_eligibility_pressure = modifiers[1]
            existing.modifier_clutch = modifiers[2]
            existing.modifier_momentum = modifiers[3]
            existing.modifier_signature_games = modifiers[4]
            existing.last_synced_at = now
            updated += 1

    db.commit()
    summary = {
        "inserted": inserted,
        "updated": updated,
        "skipped_no_season_stat": skipped,
        "scanned": len(votes),
    }
    if verbose:
        print("materialize_award_modifiers:", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", default=None, help="Limit to a single season (e.g. 2023-24).")
    parser.add_argument("--award-type", default="MVP", help="Award type filter (default MVP).")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    db = SessionLocal()
    try:
        materialize(db, season=args.season, award_type=args.award_type)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
