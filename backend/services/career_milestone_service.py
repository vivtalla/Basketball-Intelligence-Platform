"""Career milestone detection for the CF3 Legacy view.

Reuses the Phase 0 ``MilestoneSnapshot`` table when CF5's nightly
populator has run (rows present for the player). When the table is
empty we compute milestones live by aggregating the player's
``SeasonStat`` rows.

This is a deliberately small, deterministic milestone catalog — career
points, threes, rebounds, assists, steals, blocks, games played. Award
milestones (championships, All-Star nods, MVPs) live in
``career_legacy_service.compute_hof_projection`` because they require
an awards table not yet in the schema.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import MilestoneSnapshot, SeasonStat
from models.career_legacy import MilestoneAchievement, MilestoneApproach


# Catalog: (key, label, threshold, stat_attr_in_seasonstat).
# Single source of truth for both achieved + approaching milestones so
# the live-computation path and the DB path agree on labels.
MILESTONE_CATALOG: List[Tuple[str, str, int, str]] = [
    ("10k_pts", "10,000 career points", 10_000, "pts"),
    ("15k_pts", "15,000 career points", 15_000, "pts"),
    ("20k_pts", "20,000 career points", 20_000, "pts"),
    ("25k_pts", "25,000 career points", 25_000, "pts"),
    ("30k_pts", "30,000 career points", 30_000, "pts"),
    ("1k_3pm", "1,000 career threes", 1_000, "fg3m"),
    ("2k_3pm", "2,000 career threes", 2_000, "fg3m"),
    ("3k_3pm", "3,000 career threes", 3_000, "fg3m"),
    ("5k_ast", "5,000 career assists", 5_000, "ast"),
    ("10k_ast", "10,000 career assists", 10_000, "ast"),
    ("5k_reb", "5,000 career rebounds", 5_000, "reb"),
    ("10k_reb", "10,000 career rebounds", 10_000, "reb"),
    ("1k_stl", "1,000 career steals", 1_000, "stl"),
    ("1k_blk", "1,000 career blocks", 1_000, "blk"),
    ("500_gp", "500 career games", 500, "gp"),
    ("1000_gp", "1,000 career games", 1_000, "gp"),
]


def _career_totals(db: Session, player_id: int) -> Dict[str, float]:
    """Sum non-playoff totals for the milestone-relevant stat attrs."""
    rows: List[SeasonStat] = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id == player_id,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    # De-dupe attrs from the catalog — multiple thresholds share an attr
    # (e.g. 10k_pts and 20k_pts both read SeasonStat.pts).
    attrs = sorted({attr for _, _, _, attr in MILESTONE_CATALOG})
    totals: Dict[str, float] = defaultdict(float)
    distinct_seasons: set = set()
    pts_pg_total = 0.0
    pts_pg_w = 0.0
    for r in rows:
        for attr in attrs:
            v = getattr(r, attr, None)
            if v is not None:
                try:
                    totals[attr] += float(v)
                except (TypeError, ValueError):
                    continue
        gp = int(r.gp or 0)
        if gp > 0 and r.pts_pg is not None:
            pts_pg_total += float(r.pts_pg) * gp
            pts_pg_w += gp
        distinct_seasons.add(r.season)

    totals["seasons"] = float(len(distinct_seasons))
    if pts_pg_w > 0:
        totals["_career_ppg"] = pts_pg_total / pts_pg_w
    return totals


def _games_to_milestone(
    threshold: int,
    current: float,
    pace_per_game: Optional[float],
) -> Optional[int]:
    if current >= threshold:
        return None
    if not pace_per_game or pace_per_game <= 0:
        return None
    remaining = threshold - current
    return max(1, int(round(remaining / pace_per_game)))


def _stat_pace_per_game(
    db: Session,
    player_id: int,
    attr: str,
    pts_pg_career: Optional[float],
) -> Optional[float]:
    """Return the player's per-game rate for the given stat attr.

    Uses the most recent regular-season row when available, otherwise
    falls back to a career average. ``pts`` resolves directly to
    pts_pg; other counting stats are derived as total/gp from the most
    recent season.
    """
    if attr == "pts":
        return pts_pg_career
    if attr == "gp":
        return 1.0
    rows: List[SeasonStat] = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id == player_id,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .order_by(SeasonStat.season.desc())
        .limit(3)
        .all()
    )
    if not rows:
        return None
    total = 0.0
    gp = 0
    for r in rows:
        v = getattr(r, attr, None)
        g = int(r.gp or 0)
        if v is None or g <= 0:
            continue
        try:
            total += float(v)
            gp += g
        except (TypeError, ValueError):
            continue
    if gp == 0:
        return None
    return total / gp


def _read_snapshot_rows(db: Session, player_id: int) -> List[MilestoneSnapshot]:
    return (
        db.query(MilestoneSnapshot)
        .filter(MilestoneSnapshot.player_id == player_id)
        .all()
    )


def compute_career_milestones(
    db: Session,
    player_id: int,
) -> Tuple[List[MilestoneAchievement], Optional[MilestoneApproach]]:
    """Return (achieved, next_approach) for a player.

    Tries the nightly snapshot table first; falls back to live
    computation when no snapshot rows exist for the player. The live
    path is what the test suite exercises today.
    """
    snapshot_rows = _read_snapshot_rows(db, player_id)
    if snapshot_rows:
        achieved: List[MilestoneAchievement] = []
        approaches: List[Tuple[int, MilestoneApproach]] = []
        for row in snapshot_rows:
            label = next(
                (lbl for k, lbl, _, _ in MILESTONE_CATALOG if k == row.milestone_key),
                row.milestone_key,
            )
            if row.achieved_on is not None:
                achieved.append(
                    MilestoneAchievement(
                        milestone_key=row.milestone_key,
                        milestone_label=label,
                        threshold=int(row.threshold),
                        achieved_on=row.achieved_on,
                        achieved_in_season=row.season,
                        current_value=float(row.current_value or 0.0),
                    )
                )
            else:
                points_remaining = max(
                    0.0,
                    float(row.threshold) - float(row.current_value or 0.0),
                )
                approaches.append((
                    row.games_to_milestone or 10**9,
                    MilestoneApproach(
                        milestone_key=row.milestone_key,
                        milestone_label=label,
                        threshold=int(row.threshold),
                        current_value=float(row.current_value or 0.0),
                        points_remaining=round(points_remaining, 1),
                        games_to_milestone=row.games_to_milestone,
                    ),
                ))
        approaches.sort(key=lambda x: x[0])
        next_approach = approaches[0][1] if approaches else None
        return achieved, next_approach

    # Live-compute path
    totals = _career_totals(db, player_id)
    if not totals:
        return [], None
    achieved_live: List[MilestoneAchievement] = []
    approach_candidates: List[MilestoneApproach] = []
    pts_pg_career = totals.get("_career_ppg")

    for key, label, threshold, attr in MILESTONE_CATALOG:
        cur = totals.get(attr, 0.0)
        if cur >= threshold:
            # Detect season-of-achievement by walking forward.
            achieved_in = _detect_achieved_season(db, player_id, attr, threshold)
            achieved_live.append(
                MilestoneAchievement(
                    milestone_key=key,
                    milestone_label=label,
                    threshold=threshold,
                    achieved_in_season=achieved_in,
                    current_value=round(float(cur), 1),
                )
            )
        else:
            pace = _stat_pace_per_game(db, player_id, attr, pts_pg_career)
            games_left = _games_to_milestone(threshold, cur, pace)
            approach_candidates.append(
                MilestoneApproach(
                    milestone_key=key,
                    milestone_label=label,
                    threshold=threshold,
                    current_value=round(float(cur), 1),
                    points_remaining=round(float(threshold - cur), 1),
                    games_to_milestone=games_left,
                )
            )

    approach_candidates.sort(
        key=lambda x: (
            x.games_to_milestone if x.games_to_milestone is not None else 10**9
        )
    )
    next_approach = approach_candidates[0] if approach_candidates else None
    return achieved_live, next_approach


def _detect_achieved_season(
    db: Session,
    player_id: int,
    attr: str,
    threshold: int,
) -> Optional[str]:
    rows: List[SeasonStat] = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id == player_id,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .order_by(SeasonStat.season.asc())
        .all()
    )
    running = 0.0
    for r in rows:
        v = getattr(r, attr, None)
        if v is None:
            continue
        try:
            running += float(v)
        except (TypeError, ValueError):
            continue
        if running >= threshold:
            return r.season
    return None
