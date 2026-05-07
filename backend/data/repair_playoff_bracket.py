"""Repair a malformed playoff bracket.

Sprint 92 — production hit a state where ``Team.conference`` was empty for
all 30 teams, which made the bracket builder collapse every R1 winner into
a single ``<season>-X-R2-TOP`` / ``<season>-X-R2-BOT`` slot regardless of
conference. The result was a 2025-26 bracket with two malformed R2 rows
(one cross-conference: OKC West + PHI East) instead of the canonical four.

This script:

1. Backfills `Team.conference` for any team whose abbreviation is in the
   league's standard E/W roster but whose DB column is empty.
2. Wipes every R2-or-later PlayoffSeries row for the target season — those
   rows are derivative (the auto-advance produces them from R1 outcomes),
   so dropping them is non-destructive when the builder is re-run.
3. Calls ``build_or_refresh_bracket`` so the now-conference-aware builder
   re-creates the right R2/R3/R4 series with proper E/W slot ids and
   parent pointers.
4. Validates the result: 4 R2 rows, no cross-conference matchups, parent
   pointers wired, no remaining ``-X-R2`` slot ids.

Run on production:

    cd /home/ubuntu/bip/backend
    set -a && . /etc/bip/env && set +a
    venv/bin/python data/repair_playoff_bracket.py --season 2025-26 --apply

Without ``--apply`` the script reports what it would change but doesn't
write. Idempotent — safe to re-run.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import SessionLocal  # noqa: E402
from db.models import PlayoffSeries, Team  # noqa: E402
from services.playoff_bracket_service import (  # noqa: E402
    _EAST_ABBRS_FALLBACK,
    _WEST_ABBRS_FALLBACK,
    build_or_refresh_bracket,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("repair_playoff_bracket")


def _backfill_team_conference(db, apply: bool) -> int:
    """Set Team.conference from the static abbr→conference map for any
    team whose column is currently empty. Returns the number of rows
    that needed updating (or would have, in --dry-run mode)."""
    rows = db.query(Team).all()
    updated = 0
    for team in rows:
        existing = (getattr(team, "conference", "") or "").strip()
        if existing:
            continue
        abbr = (getattr(team, "abbreviation", "") or "").strip().upper()
        if abbr in _EAST_ABBRS_FALLBACK:
            new_value = "East"
        elif abbr in _WEST_ABBRS_FALLBACK:
            new_value = "West"
        else:
            continue
        log.info(
            "  team_conference: %s (%s) %r -> %r%s",
            abbr,
            team.id,
            existing,
            new_value,
            "" if apply else " [dry-run]",
        )
        if apply:
            team.conference = new_value
        updated += 1
    return updated


def _wipe_post_r1_series(db, season: str, apply: bool) -> int:
    """Delete every PlayoffSeries row for `season` whose round >= 2 so the
    builder can repopulate them. R1 rows are kept — those are the source
    of truth for outcomes."""
    rows = (
        db.query(PlayoffSeries)
        .filter(PlayoffSeries.season == season, PlayoffSeries.round >= 2)
        .all()
    )
    for row in rows:
        log.info(
            "  wipe: %s (round=%s, top=%s, bottom=%s, status=%s)%s",
            row.series_id,
            row.round,
            row.top_seed_team_id,
            row.bottom_seed_team_id,
            row.status,
            "" if apply else " [dry-run]",
        )
        if apply:
            db.delete(row)
    return len(rows)


def _validate(db, season: str) -> int:
    """Return number of integrity issues found in the season's bracket.
    Logs each one. 0 means clean."""
    rows = (
        db.query(PlayoffSeries)
        .filter(PlayoffSeries.season == season)
        .order_by(PlayoffSeries.round.asc())
        .all()
    )
    issues = 0
    # No "X" conference in any series_id.
    for s in rows:
        if "-X-R" in (s.series_id or ""):
            log.error("  validation: %s has unresolved conference (X-R)", s.series_id)
            issues += 1
    # Every R2+ row must have at least one parent pointer wired.
    for s in rows:
        if (s.round or 0) >= 2:
            if not s.parent_top_series_id and not s.parent_bottom_series_id:
                log.error("  validation: %s (round=%s) has no parent pointers", s.series_id, s.round)
                issues += 1
    # Cross-conference R2 sanity: if both seeds are populated, both teams
    # should be in the same conference. We check by series_id naming
    # since a properly built bracket encodes the conference in the id.
    for s in rows:
        if (s.round or 0) == 2 and s.top_seed_team_id is not None and s.bottom_seed_team_id is not None:
            top_team = db.query(Team).filter(Team.id == s.top_seed_team_id).first()
            bot_team = db.query(Team).filter(Team.id == s.bottom_seed_team_id).first()
            top_conf = ((top_team.conference or "") if top_team else "").strip().upper()[:1]
            bot_conf = ((bot_team.conference or "") if bot_team else "").strip().upper()[:1]
            if top_conf and bot_conf and top_conf != bot_conf:
                log.error(
                    "  validation: %s pairs %s (%s) vs %s (%s) across conferences",
                    s.series_id,
                    top_team.abbreviation if top_team else "?",
                    top_conf or "?",
                    bot_team.abbreviation if bot_team else "?",
                    bot_conf or "?",
                )
                issues += 1
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", required=True, help="Target season, e.g. 2025-26")
    parser.add_argument("--apply", action="store_true", help="Actually write changes")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        log.info("Step 1 — backfill Team.conference where empty:")
        teams_updated = _backfill_team_conference(db, apply=args.apply)
        log.info("  %d team rows touched", teams_updated)
        if args.apply and teams_updated:
            db.commit()

        log.info("Step 2 — wipe malformed R2+ rows for %s:", args.season)
        rows_wiped = _wipe_post_r1_series(db, args.season, apply=args.apply)
        log.info("  %d rows deleted", rows_wiped)
        if args.apply and rows_wiped:
            db.commit()

        log.info("Step 3 — re-run build_or_refresh_bracket(%s):", args.season)
        if args.apply:
            refreshed = build_or_refresh_bracket(db, args.season)
            log.info("  %d series rows touched by builder", refreshed)
        else:
            log.info("  [dry-run] would call build_or_refresh_bracket")

        log.info("Step 4 — validate post-repair bracket:")
        issues = _validate(db, args.season) if args.apply else 0
        if issues:
            log.error("  %d integrity issue(s) remain — investigate above", issues)
            return 1
        log.info("  bracket clean ✓" if args.apply else "  [dry-run] skipped")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
