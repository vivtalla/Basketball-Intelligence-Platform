"""Sprint 79 Stream A1 — historical award voting CSV loader.

Backs the ``mvp_case_v5`` calibration. The CSV is committed to the repo at
``backend/data/seed/award_voting_seed.csv`` (12+ seasons of MVP outcomes).
A future ``source="basketball_reference"`` branch will scrape the live
``awards_share`` table and slot in here without caller changes.

Idempotent: per-row upsert on (player_id, season, award_type, ballot_position).
Comments and blank rows in the CSV are skipped.
"""

from __future__ import annotations

import csv
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from db.models import AwardVote, Player

logger = logging.getLogger(__name__)

DEFAULT_SEED_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "seed",
    "award_voting_seed.csv",
)


def _coerce_int(raw: Any, default: Optional[int] = None) -> Optional[int]:
    if raw is None or raw == "":
        return default
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default


def _coerce_float(raw: Any, default: Optional[float] = None) -> Optional[float]:
    if raw is None or raw == "":
        return default
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return default


def _read_seed_csv(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        # Strip comment lines (start with '#') before passing to DictReader.
        cleaned = [line for line in fh if not line.lstrip().startswith("#")]
    reader = csv.DictReader(cleaned)
    for entry in reader:
        if not entry.get("player_id"):
            continue
        rows.append(
            {
                "player_id": _coerce_int(entry.get("player_id")),
                "season": (entry.get("season") or "").strip(),
                "award_type": (entry.get("award_type") or "MVP").strip(),
                "ballot_position": _coerce_int(entry.get("ballot_position")),
                "voter_count": _coerce_int(entry.get("voter_count"), default=0) or 0,
                "total_award_points": _coerce_float(entry.get("total_award_points"), default=0.0) or 0.0,
            }
        )
    return rows


def sync_award_voting(
    db: Session,
    *,
    source: str = "seed_csv",
    seed_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Idempotent loader for the award_voting table.

    Returns: {rows_upserted, rows_skipped, source, last_synced_at}.
    """
    if source != "seed_csv":
        raise NotImplementedError("Unsupported award voting source: {0}".format(source))

    path = seed_path or DEFAULT_SEED_PATH
    if not os.path.exists(path):
        logger.warning("award voting seed CSV not found: %s", path)
        return {
            "rows_upserted": 0,
            "rows_skipped": 0,
            "source": source,
            "last_synced_at": datetime.utcnow().isoformat(),
        }

    seed_rows = _read_seed_csv(path)
    logger.info("award voting seed: %d rows from %s", len(seed_rows), path)

    rows_upserted = 0
    rows_skipped = 0
    now = datetime.utcnow()

    for entry in seed_rows:
        player_id = entry["player_id"]
        season = entry["season"]
        award_type = entry["award_type"]
        if not player_id or not season or not award_type:
            rows_skipped += 1
            continue

        # Don't invent players — skip rows whose player_id isn't in the roster.
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            logger.debug(
                "Skipping award_voting row for unknown player_id=%s season=%s",
                player_id, season,
            )
            rows_skipped += 1
            continue

        existing = (
            db.query(AwardVote)
            .filter(
                AwardVote.player_id == player_id,
                AwardVote.season == season,
                AwardVote.award_type == award_type,
                AwardVote.ballot_position == entry["ballot_position"],
            )
            .first()
        )

        if existing is None:
            row = AwardVote(
                player_id=player_id,
                season=season,
                award_type=award_type,
                ballot_position=entry["ballot_position"],
                voter_count=entry["voter_count"],
                total_award_points=entry["total_award_points"],
                source=source,
            )
            db.add(row)
        else:
            existing.voter_count = entry["voter_count"]
            existing.total_award_points = entry["total_award_points"]
            existing.source = source

        try:
            db.flush()
            rows_upserted += 1
        except Exception:
            db.rollback()
            rows_skipped += 1
            continue

    db.commit()
    return {
        "rows_upserted": rows_upserted,
        "rows_skipped": rows_skipped,
        "source": source,
        "last_synced_at": now.isoformat(),
    }
