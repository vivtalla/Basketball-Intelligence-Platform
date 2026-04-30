"""Salary ingestion service (Sprint 78 FO1 Trade Machine).

The full Spotrac/HoopsHype scrape is out-of-scope for the Sprint 78 deliverable
— it's brittle and changes every off-season. This service ships a clean
``sync_salary_data`` interface backed today by a hand-curated seed CSV
(``backend/data/seed/contracts_2025_26.csv``) so downstream features
(Trade Machine, Free Agency Workspace, Multi-Year Trajectory) have real
contract rows to wire against. A future ``source="spotrac"`` branch can
slot in with no caller changes.

Idempotent: re-running upserts on (player_id, season). Skips rows whose
``nba_player_id`` is not present in the ``Player`` table — no new players
are inserted from the salary feed.
"""
from __future__ import annotations

import csv
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from db.models import Player, PlayerContract, Team

logger = logging.getLogger(__name__)

DEFAULT_SEED_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "seed",
    "contracts_2025_26.csv",
)


def _coerce_bool(raw: Any) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return False
    return str(raw).strip().lower() in ("1", "true", "t", "yes", "y")


def _coerce_int(raw: Any, default: Optional[int] = None) -> Optional[int]:
    if raw is None or raw == "":
        return default
    try:
        return int(str(raw).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return default


def _read_seed_rows(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            rows.append({
                "nba_player_id": _coerce_int(raw.get("nba_player_id")),
                "team_abbr": (raw.get("team_abbr") or "").strip().upper() or None,
                "season": (raw.get("season") or "").strip() or None,
                "salary": _coerce_int(raw.get("salary"), 0) or 0,
                "years_remaining": _coerce_int(raw.get("years_remaining"), 1),
                "is_player_option": _coerce_bool(raw.get("is_player_option")),
                "is_team_option": _coerce_bool(raw.get("is_team_option")),
                "contract_type": (raw.get("contract_type") or "").strip() or None,
                "source": (raw.get("source") or "estimated").strip() or "estimated",
            })
    return rows


def sync_salary_data(
    db: Session,
    source: str = "seed_csv",
    seed_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Upsert ``PlayerContract`` rows from the chosen source.

    Returns a small summary dict the CLI/cron can log:
    ``{rows_upserted, rows_skipped, source, last_synced_at}``.
    """
    if source != "seed_csv":
        # Reserved for future Spotrac / HoopsHype scraper branches.
        raise NotImplementedError("Unsupported salary source: %s" % source)

    path = seed_path or DEFAULT_SEED_PATH
    if not os.path.exists(path):
        logger.warning("Seed CSV missing at %s — no contracts ingested.", path)
        return {
            "rows_upserted": 0,
            "rows_skipped": 0,
            "source": source,
            "last_synced_at": datetime.utcnow().isoformat(),
        }

    seed_rows = _read_seed_rows(path)
    teams_by_abbr = dict(
        (team.abbreviation, team)
        for team in db.query(Team).all()
    )

    rows_upserted = 0
    rows_skipped = 0
    now = datetime.utcnow()

    for entry in seed_rows:
        player_id = entry.get("nba_player_id")
        season = entry.get("season")
        if not player_id or not season:
            rows_skipped += 1
            continue
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            # Don't invent players from a salary feed — log + skip.
            logger.debug("Skipping contract row for unknown player_id=%s", player_id)
            rows_skipped += 1
            continue

        team = teams_by_abbr.get(entry.get("team_abbr") or "")
        team_id = team.id if team else None

        existing = (
            db.query(PlayerContract)
            .filter(
                PlayerContract.player_id == player_id,
                PlayerContract.season == season,
            )
            .first()
        )

        row_source = entry.get("source") or source

        if existing is None:
            row = PlayerContract(
                player_id=player_id,
                team_id=team_id,
                season=season,
                salary=entry.get("salary") or 0,
                years_remaining=entry.get("years_remaining") or 1,
                is_player_option=bool(entry.get("is_player_option")),
                is_team_option=bool(entry.get("is_team_option")),
                contract_type=entry.get("contract_type"),
                source=row_source,
                last_synced_at=now,
            )
            db.add(row)
        else:
            existing.team_id = team_id if team_id is not None else existing.team_id
            existing.salary = entry.get("salary") or 0
            existing.years_remaining = entry.get("years_remaining") or 1
            existing.is_player_option = bool(entry.get("is_player_option"))
            existing.is_team_option = bool(entry.get("is_team_option"))
            existing.contract_type = entry.get("contract_type")
            existing.source = row_source
            existing.last_synced_at = now

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
