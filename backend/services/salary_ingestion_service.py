"""Salary ingestion service (Sprint 78 FO1, Sprint 81 Spotrac integration).

``sync_salary_data`` ingests contracts into ``player_contracts``. As of
Sprint 81 the ``"spotrac"`` source pulls live data from
``https://www.spotrac.com/nba/{team-slug}/cap``; ``"seed_csv"`` reads
``backend/data/seed/contracts_2025_26.csv`` as the fallback path.

Failure policy: when ``source="spotrac"`` errors (anti-bot, parse, network),
we log + transparently fall back to the seed CSV so Trade Machine never goes
dark. Callers can pass ``source="seed_csv"`` to skip the scrape entirely.

Idempotent: re-running upserts on (player_id, season). Skips rows whose
``nba_player_id`` (or resolved-name lookup) is not present in the ``Player``
table — no new players are inserted from the salary feed.
"""
from __future__ import annotations

import csv
import logging
import os
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session


def _ascii_fold(name: str) -> str:
    """Lowercase + strip diacritics so 'Nikola Jokić' matches Spotrac's 'Nikola Jokic'."""
    if not name:
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).strip().lower()

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


def _build_name_index(db: Session) -> Dict[str, int]:
    """ASCII-folded lowercase full-name → player_id lookup for Spotrac name resolution.

    Spotrac doesn't expose ``nba_player_id`` directly; the table column we
    parse is the player's display name. Our DB stores Unicode names
    (e.g. 'Nikola Jokić') while Spotrac strips diacritics ('Nikola Jokic'),
    so we ascii-fold both sides before matching. Multi-name collisions
    (e.g., Marcus Morris Sr./Jr.) resolve to whichever row sorts later —
    acceptable as a best-effort, and unresolved names just get skipped.
    """
    index: Dict[str, int] = {}
    for player in db.query(Player).all():
        folded = _ascii_fold(player.full_name or "")
        if folded:
            index[folded] = player.id
    return index


def _fetch_spotrac_rows(season: str) -> List[Dict[str, Any]]:
    """Live scrape; raises ``ScraperError`` on failure (caught upstream)."""
    # Imported lazily so unit tests that don't exercise the network path
    # don't pay the requests/bs4 import cost.
    from data.scrapers.spotrac import SpotracScraper

    return SpotracScraper().fetch_contracts(season=season)


def _resolve_spotrac_rows(
    raw_rows: List[Dict[str, Any]],
    name_index: Dict[str, int],
) -> List[Dict[str, Any]]:
    """Convert Spotrac rows (player_name) → ingestion rows (nba_player_id).

    Rows whose ``player_name`` doesn't resolve are dropped with a debug log;
    they show up in ``rows_skipped`` at the end.
    """
    resolved: List[Dict[str, Any]] = []
    for row in raw_rows:
        name = _ascii_fold(row.get("player_name") or "")
        nba_player_id = name_index.get(name)
        if nba_player_id is None:
            logger.debug("spotrac: no player_id for name=%s", name)
            continue
        resolved.append({
            "nba_player_id": nba_player_id,
            "team_abbr": row.get("team_abbr"),
            "season": row.get("season"),
            "salary": int(row.get("salary") or 0),
            "years_remaining": int(row.get("years_remaining") or 1),
            "is_player_option": bool(row.get("is_player_option")),
            "is_team_option": bool(row.get("is_team_option")),
            "contract_type": row.get("contract_type"),
            "source": "spotrac",
        })
    return resolved


def sync_salary_data(
    db: Session,
    source: str = "seed_csv",
    seed_path: Optional[str] = None,
    season: str = "2025-26",
) -> Dict[str, Any]:
    """Upsert ``PlayerContract`` rows from the chosen source.

    Args:
        db: SQLAlchemy session.
        source: ``"spotrac"`` (live) or ``"seed_csv"`` (fallback).
        seed_path: optional override for the seed CSV path.
        season: only consulted when ``source="spotrac"``.

    Returns: ``{rows_upserted, rows_skipped, source, last_synced_at, fallback_used}``.
    """
    fallback_used = False
    rows: List[Dict[str, Any]]
    effective_source = source

    if source == "spotrac":
        try:
            raw_rows = _fetch_spotrac_rows(season=season)
            name_index = _build_name_index(db)
            rows = _resolve_spotrac_rows(raw_rows, name_index)
            if not rows:
                raise RuntimeError("spotrac returned 0 resolvable rows")
        except Exception as exc:  # noqa: BLE001 — fall back on any failure
            logger.warning(
                "spotrac scrape failed (%s) — falling back to seed CSV", exc
            )
            fallback_used = True
            effective_source = "seed_csv"
            rows = _read_seed_rows(seed_path or DEFAULT_SEED_PATH)
    elif source == "seed_csv":
        path = seed_path or DEFAULT_SEED_PATH
        if not os.path.exists(path):
            logger.warning("Seed CSV missing at %s — no contracts ingested.", path)
            return {
                "rows_upserted": 0,
                "rows_skipped": 0,
                "source": effective_source,
                "last_synced_at": datetime.utcnow().isoformat(),
                "fallback_used": fallback_used,
            }
        rows = _read_seed_rows(path)
    else:
        raise ValueError("Unsupported salary source: {0}".format(source))

    teams_by_abbr = dict(
        (team.abbreviation, team)
        for team in db.query(Team).all()
    )

    rows_upserted = 0
    rows_skipped = 0
    now = datetime.utcnow()

    for entry in rows:
        player_id = entry.get("nba_player_id")
        season_str = entry.get("season")
        if not player_id or not season_str:
            rows_skipped += 1
            continue
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            logger.debug("Skipping contract row for unknown player_id=%s", player_id)
            rows_skipped += 1
            continue

        team = teams_by_abbr.get(entry.get("team_abbr") or "")
        team_id = team.id if team else None

        existing = (
            db.query(PlayerContract)
            .filter(
                PlayerContract.player_id == player_id,
                PlayerContract.season == season_str,
            )
            .first()
        )

        row_source = entry.get("source") or effective_source

        if existing is None:
            new_row = PlayerContract(
                player_id=player_id,
                team_id=team_id,
                season=season_str,
                salary=entry.get("salary") or 0,
                years_remaining=entry.get("years_remaining") or 1,
                is_player_option=bool(entry.get("is_player_option")),
                is_team_option=bool(entry.get("is_team_option")),
                contract_type=entry.get("contract_type"),
                source=row_source,
                last_synced_at=now,
            )
            db.add(new_row)
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
        "source": effective_source,
        "last_synced_at": now.isoformat(),
        "fallback_used": fallback_used,
    }
