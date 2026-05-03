#!/usr/bin/env python3
"""Sprint 86 Stream A2 — backfill ``parent_top_series_id`` /
``parent_bottom_series_id`` on existing closed playoff series.

Sprint 85's auto-advance only fires on the close-transition of a series. Any
series that closed BEFORE the migration landed (e.g. 2025-26 OKC-PHX,
SAS-POR) has NULL parent pointers on its child Round-2 row, so the frontend
TBD label cannot deep-link "winner of 1v8 (OKC/PHX)".

This one-shot script walks every series for a given season, computes the
child slot each closed series feeds (via ``compute_next_round_slot``), and
fills in the child's ``parent_{top|bottom}_series_id`` only when it is
currently NULL. Idempotent — safe to re-run.

Usage (from ``backend/``)::

    python data/backfill_playoff_parent_pointers.py --season 2025-26

Production runbook (after merging Stream A)::

    cd /home/ubuntu/bip/backend
    set -a && source /etc/bip/env && set +a
    ./venv/bin/python data/backfill_playoff_parent_pointers.py --season 2025-26
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any, Dict, Optional

# Allow direct ``python data/backfill_playoff_parent_pointers.py`` invocation
# from the ``backend/`` working directory without setting PYTHONPATH.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session  # noqa: E402

from db.database import SessionLocal  # noqa: E402
from db.models import PlayoffSeries, Team  # noqa: E402
from services.playoff_bracket_service import compute_next_round_slot  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("backfill_playoff_parent_pointers")


# Static EAST/WEST abbreviation map mirrors routers/playoffs.py — used as a
# fallback when ``Team.conference`` is empty for the parent's top-seed team.
_EAST_ABBRS = {
    "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DET", "IND", "MIA",
    "MIL", "NYK", "ORL", "PHI", "TOR", "WAS",
}
_WEST_ABBRS = {
    "DAL", "DEN", "GSW", "HOU", "LAC", "LAL", "MEM", "MIN", "NOP",
    "OKC", "PHX", "POR", "SAC", "SAS", "UTA",
}


def _conference_token(db: Session, team_id: Optional[int]) -> str:
    """Return ``"E"`` / ``"W"`` for the given team, falling back to the
    static abbr map. Returns ``"X"`` when the conference cannot be derived
    — ``compute_next_round_slot`` then refuses to route the winner.
    """
    if team_id is None:
        return "X"
    team = db.query(Team).filter(Team.id == team_id).first()
    if team is None:
        return "X"
    conf = (getattr(team, "conference", "") or "").strip().upper()
    if conf.startswith("E"):
        return "E"
    if conf.startswith("W"):
        return "W"
    abbr = (team.abbreviation or "").upper()
    if abbr in _EAST_ABBRS:
        return "E"
    if abbr in _WEST_ABBRS:
        return "W"
    return "X"


def backfill_parent_pointers(db: Session, season: str) -> Dict[str, Any]:
    """Walk all playoff series for ``season`` and fill child rows' parent
    pointers from each closed parent. Returns a summary dict with counts.

    Idempotent rules:
      - Closed parents are processed in round order (round 1 → 3).
      - For each closed parent we compute its child slot.
      - The child's ``parent_{top|bottom}_series_id`` is set ONLY when it is
        currently NULL. A non-null pointer is left untouched.
    """
    series_rows = (
        db.query(PlayoffSeries)
        .filter(PlayoffSeries.season == season)
        .order_by(PlayoffSeries.round.asc(), PlayoffSeries.series_id.asc())
        .all()
    )

    closed_seen = 0
    skipped_no_winner = 0
    skipped_no_slot_info = 0
    skipped_finals = 0
    skipped_child_missing = 0
    updated_top = 0
    updated_bottom = 0
    already_set = 0

    by_series_id = {row.series_id: row for row in series_rows}

    for parent in series_rows:
        if parent.status != "closed":
            continue
        closed_seen += 1
        if parent.winner_team_id is None:
            skipped_no_winner += 1
            continue
        if parent.round is None or parent.round >= 4:
            skipped_finals += 1
            continue

        conf_token = _conference_token(db, parent.top_seed_team_id)

        slot_info = compute_next_round_slot(
            season=season,
            conference_token=conf_token,
            round_number=int(parent.round),
            top_seed=parent.top_seed,
            bottom_seed=parent.bottom_seed,
        )
        if slot_info is None:
            skipped_no_slot_info += 1
            log.warning(
                "no slot info for closed series %s (round=%s top_seed=%s conf=%s)",
                parent.series_id,
                parent.round,
                parent.top_seed,
                conf_token,
            )
            continue

        child_slot = str(slot_info["child_slot"])
        slot_id = str(slot_info["slot_id"])

        # Find the child row. Prefer the synthetic slot_id (auto-advance
        # placeholder); otherwise search the next round for a row whose
        # matching seat already lists this winner. This mirrors the
        # fallback path in ``_auto_advance_closed_series``.
        child = by_series_id.get(slot_id)
        if child is None:
            next_round = int(slot_info["round"])
            for candidate in series_rows:
                if candidate.round != next_round:
                    continue
                if (
                    child_slot == "TOP"
                    and candidate.top_seed_team_id == parent.winner_team_id
                ):
                    child = candidate
                    break
                if (
                    child_slot == "BOT"
                    and candidate.bottom_seed_team_id == parent.winner_team_id
                ):
                    child = candidate
                    break

        if child is None:
            skipped_child_missing += 1
            log.warning(
                "no child row found for closed parent %s → slot %s",
                parent.series_id,
                slot_id,
            )
            continue

        if child_slot == "TOP":
            if child.parent_top_series_id:
                already_set += 1
            else:
                child.parent_top_series_id = parent.series_id
                updated_top += 1
                log.info(
                    "set parent_top_series_id=%s on child %s",
                    parent.series_id,
                    child.series_id,
                )
        else:  # BOT
            if child.parent_bottom_series_id:
                already_set += 1
            else:
                child.parent_bottom_series_id = parent.series_id
                updated_bottom += 1
                log.info(
                    "set parent_bottom_series_id=%s on child %s",
                    parent.series_id,
                    child.series_id,
                )

    db.commit()

    summary = {
        "season": season,
        "series_total": len(series_rows),
        "closed_seen": closed_seen,
        "updated_top": updated_top,
        "updated_bottom": updated_bottom,
        "already_set": already_set,
        "skipped_no_winner": skipped_no_winner,
        "skipped_no_slot_info": skipped_no_slot_info,
        "skipped_finals": skipped_finals,
        "skipped_child_missing": skipped_child_missing,
    }
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill parent_*_series_id on existing playoff series rows."
    )
    parser.add_argument(
        "--season",
        required=True,
        help='Season string, e.g. "2025-26".',
    )
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        summary = backfill_parent_pointers(db, season=args.season)
        log.info("backfill_playoff_parent_pointers complete: %s", summary)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
