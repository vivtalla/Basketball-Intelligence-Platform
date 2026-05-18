"""Sprint 102 (Stream B) — team-fit for draft prospects.

Bridge between the draft data layer and the existing team-fit algorithm
(`team_fit_service.py`, v3). The v3 service was built around NBA-player
inputs; this adapter takes a ``DraftProspect`` and a translated NBA stat
profile, builds a synthetic ``SeasonStat`` row, and feeds it through the
same scoring pipeline against all 30 NBA team rosters.

Public function: ``compute_team_fit_for_prospect(db, prospect, limit=5,
season=None)`` → ``List[ProspectTeamFit]``.

Calibration note (v1 of the adapter):
We use NBA-player norms when computing the prospect's z-vector — the same
norms the player-side team-fit uses. This means a young/raw prospect
typically projects below NBA-average across the board and lands as
"different_fit" against teams that already have strong production at his
position. That's *correct* but pessimistic; the prospect is being compared
against established NBA producers, not other prospects. A future sprint
should switch to a prospect-pool norm for the value-supply scoring step
specifically. Documented in the Sprint 102 closeout under deferred.

NCAA-only features (par3 = 3PA/FGA, ftr = FTA/FGA) are filled with
position-aware defaults when missing from the prospect record. The
team-fit v3 z-scorer would otherwise return None and skip the prospect
entirely.
"""
from __future__ import annotations

import logging
from typing import List, Optional
from types import SimpleNamespace

from sqlalchemy.orm import Session

from db.models import DraftProspect, DraftProspectStat, Player, Team
from models.draft import (
    FitDriverLite,
    OverlapFlagLite,
    ProspectTeamFit,
)
from services.team_fit_service import (
    MIN_TEAM_PLAYERS,
    _score_team_fit,
    _team_rows,
)
from services.similarity_service import (
    _qualified_rows_v2,
    _season_norms_v2,
)

logger = logging.getLogger(__name__)


METHODOLOGY_VERSION = "team_fit_v3_draft_adapter"

# Position-aware fallback values for NCAA features not captured on
# DraftProspectStat. These approximate NBA distributions so the prospect
# isn't penalized by missing features in z-scoring.
_PAR3_BY_POSITION = {
    "PG": 0.42, "SG": 0.50, "G": 0.46,
    "SF": 0.42, "PF": 0.32, "F": 0.38,
    "C": 0.18,
}
_FTR_BY_POSITION = {
    "PG": 0.28, "SG": 0.22, "G": 0.25,
    "SF": 0.24, "PF": 0.28, "F": 0.26,
    "C": 0.34,
}

# Fit-label thresholds, calibrated against team_fit_v3 score distributions.
FIT_LABEL_BETTER = 70.0
FIT_LABEL_SIMILAR = 50.0


def _latest_stat(prospect: DraftProspect) -> Optional[DraftProspectStat]:
    rows = list(prospect.stats or [])
    if not rows:
        return None
    rows.sort(key=lambda r: (r.season or "", (r.gp or 0)), reverse=True)
    return rows[0]


def _fit_label(score: float) -> str:
    if score >= FIT_LABEL_BETTER:
        return "better_fit"
    if score >= FIT_LABEL_SIMILAR:
        return "similar_fit"
    return "different_fit"


def _summary(team_abbr: str, score: float, value_drivers, overlap_flags) -> str:
    """One-line synthesis for a prospect-team fit card."""
    label = _fit_label(score)
    if label == "better_fit" and value_drivers:
        return "{0} would unlock the prospect's {1}; fit score {2:.1f}.".format(
            team_abbr, value_drivers[0].label.lower(), score,
        )
    if label == "different_fit" and overlap_flags:
        return "{0} is already strong at {1}; limited value-add at fit {2:.1f}.".format(
            team_abbr, overlap_flags[0].feature_key.replace("_", " "), score,
        )
    if value_drivers:
        return "{0} could leverage the prospect's {1} (fit {2:.1f}).".format(
            team_abbr, value_drivers[0].label.lower(), score,
        )
    return "{0} fit projects to {1:.1f}.".format(team_abbr, score)


def _build_synthetic_season_stat(
    prospect: DraftProspect,
    stat: DraftProspectStat,
    season: str,
) -> object:
    """Construct a SeasonStat-like SimpleNamespace from prospect data.

    The team-fit pipeline reads attributes off the object via getattr; we
    need to populate every key in SIMILARITY_STATS_V2 plus a few SeasonStat
    metadata fields the pipeline expects.

    Falls back to position-aware defaults for par3 + ftr when missing.
    """
    position = (prospect.primary_position or "F").upper()
    par3 = _PAR3_BY_POSITION.get(position, 0.36)
    ftr = _FTR_BY_POSITION.get(position, 0.26)

    return SimpleNamespace(
        # Identity — use a synthetic negative ID so it can't collide with
        # any real Player.id in the pipeline's player_lookup.
        player_id=-1 * (prospect.id or 1),
        season=season,
        team_abbreviation="__PROSPECT__",  # never matches a real team
        is_playoff=False,
        min_pg=float(stat.min_pg or 0.0),
        gp=int(stat.gp or 0),
        # SIMILARITY_STATS_V2 features
        pts_pg=float(stat.pts_pg or 0.0),
        reb_pg=float(stat.reb_pg or 0.0),
        ast_pg=float(stat.ast_pg or 0.0),
        stl_pg=float(stat.stl_pg or 0.0),
        blk_pg=float(stat.blk_pg or 0.0),
        tov_pg=float(stat.tov_pg or 0.0),
        ts_pct=float(stat.ts_pct or 0.0),
        usg_pct=float(stat.usg_pct or 0.0),
        par3=par3,
        ftr=ftr,
        # Misc fields some helpers read
        primary_position=position,
    )


def _prospect_player_stub(prospect: DraftProspect) -> Player:
    """Build a non-persisted Player object so team-fit helpers that branch
    on Player attributes (position bucket, full_name) work uniformly.
    """
    return Player(
        id=-1 * (prospect.id or 1),
        full_name=prospect.full_name,
        position=prospect.primary_position,
    )


def compute_team_fit_for_prospect(
    db: Session,
    prospect: DraftProspect,
    *,
    limit: int = 5,
    season: Optional[str] = None,
) -> List[ProspectTeamFit]:
    """Return the top-N best-fit NBA teams for a draft prospect.

    Args:
        db: SQLAlchemy Session.
        prospect: DraftProspect ORM instance (loaded with stats relationship).
        limit: max number of teams to return (sorted by fit_score desc).
        season: NBA season to score rosters from. Defaults to the prospect's
            draft year season (e.g. ``"2025-26"`` for ``draft_year=2026``).
            Historical prospects pass their own draft season so we score
            against era-appropriate rosters.

    Returns ``[]`` if the prospect has no usable stat row or if no team has
    the MIN_TEAM_PLAYERS qualified roster rows.
    """
    stat = _latest_stat(prospect)
    if stat is None:
        return []

    # Default to the prospect's draft season minus one (the prospect was
    # scouted during ``draft_year - 1`` to ``draft_year`` NBA season).
    if season is None:
        draft_year = prospect.draft_year or 2026
        season = "{0}-{1}".format(draft_year - 1, str(draft_year)[-2:])

    # Pull qualified NBA rows + season norms (same as the player-side path).
    all_rows = _qualified_rows_v2(db, is_playoff=False)
    if not all_rows:
        logger.warning(
            "draft_team_fit: no qualified NBA rows in pool; cannot score prospect=%s",
            prospect.id,
        )
        return []
    norms = _season_norms_v2(all_rows)

    subject_row = _build_synthetic_season_stat(prospect, stat, season)
    subject_player = _prospect_player_stub(prospect)

    # Player lookup for overlap-flag teammate name resolution.
    player_ids = list({row.player_id for row in all_rows})
    player_lookup = {
        p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()
    } if player_ids else {}

    by_team = _team_rows(all_rows, season)
    teams_by_abbr = {
        (t.abbreviation or "").upper(): t for t in db.query(Team).all()
    }

    results: List[ProspectTeamFit] = []
    for team_abbr, roster in by_team.items():
        if len(roster) < MIN_TEAM_PLAYERS:
            continue
        try:
            (
                fit_score,
                _value_score,
                _overlap_score,
                _role_score,
                value_drivers,
                role_drivers,
                overlap_flags,
            ) = _score_team_fit(
                db, subject_player, subject_row, roster, norms, player_lookup,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "draft_team_fit: scoring failed for prospect=%s team=%s",
                prospect.id, team_abbr,
            )
            continue

        team = teams_by_abbr.get(team_abbr)
        results.append(ProspectTeamFit(
            team_abbreviation=team_abbr,
            team_id=getattr(team, "id", None) if team is not None else None,
            fit_score=fit_score,
            fit_label=_fit_label(fit_score),
            summary=_summary(team_abbr, fit_score, value_drivers, overlap_flags),
            value_drivers=[
                FitDriverLite(
                    feature_key=d.feature_key,
                    label=d.label,
                    prospect_z=round(d.player_z, 2),
                    team_need_z=round(d.team_need_z, 2),
                    contribution=round(d.contribution, 2),
                )
                for d in value_drivers[:3]
            ],
            overlap_flags=[
                OverlapFlagLite(
                    feature_key=f.feature_key,
                    teammate_name=f.teammate_name,
                    teammate_id=f.teammate_id,
                    gap=round(f.gap, 2),
                )
                for f in overlap_flags[:3]
            ],
            role_runway_note=(
                "Role runway favors the prospect at {0}.".format(role_drivers[0].label.lower())
                if role_drivers else None
            ),
            methodology_version=METHODOLOGY_VERSION,
        ))

    results.sort(key=lambda r: r.fit_score, reverse=True)
    return results[:limit]


def compute_best_team_fit_for_prospect(
    db: Session,
    prospect: DraftProspect,
    *,
    season: Optional[str] = None,
) -> Optional[ProspectTeamFit]:
    """Convenience: top-1 team-fit for a prospect.

    Used by the historical-class endpoint to denormalize ``best_team_fit_*``
    onto each ``HistoricalProspectEntry`` row.
    """
    top = compute_team_fit_for_prospect(db, prospect, limit=1, season=season)
    return top[0] if top else None
