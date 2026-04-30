"""Sprint 78 / FO3 — Draft Prospect Workspace API.

Routes:

- ``GET /api/draft/board?year=2026&limit=60`` — sortable, filterable
  prospect board (one row per prospect).
- ``GET /api/draft/prospects/{prospect_id}`` — full prospect detail with
  per-game stats, NBA-translated per-100 line, NBA comps, and combine
  measurements.

Both routes are read-only and live entirely in the prospect tables; the
upstream sync responsibility belongs to ``data/sync_draft_prospects.py``.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import DraftProspect, DraftProspectMeasurement, DraftProspectStat
from models.draft import (
    CollegeStatLine,
    DraftProspectSummary,
    MeasurementPanel,
    ProspectBoardResponse,
    ProspectDetail,
)
from services.draft_prospect_comp_service import find_nba_comps
from services.draft_translation_service import translate_prospect_to_nba

logger = logging.getLogger(__name__)

router = APIRouter()


def _latest_stat(prospect: DraftProspect) -> Optional[DraftProspectStat]:
    rows = list(prospect.stats or [])
    if not rows:
        return None
    rows.sort(key=lambda r: (r.season or "", (r.gp or 0)), reverse=True)
    return rows[0]


def _summary_from_prospect(prospect: DraftProspect) -> DraftProspectSummary:
    latest = _latest_stat(prospect)
    return DraftProspectSummary(
        prospect_id=prospect.id,
        external_id=prospect.external_id,
        full_name=prospect.full_name,
        draft_year=prospect.draft_year,
        age_on_draft_day=prospect.age_on_draft_day,
        height_inches=prospect.height_inches,
        weight_lbs=prospect.weight_lbs,
        primary_position=prospect.primary_position,
        school=prospect.school,
        school_type=prospect.school_type,
        consensus_rank=prospect.consensus_rank,
        headshot_url=prospect.headshot_url,
        archetype_label=None,  # archetype only resolved on detail (cheaper board)
        pts_pg=getattr(latest, "pts_pg", None),
        reb_pg=getattr(latest, "reb_pg", None),
        ast_pg=getattr(latest, "ast_pg", None),
        ts_pct=getattr(latest, "ts_pct", None),
        usg_pct=getattr(latest, "usg_pct", None),
    )


@router.get("/board", response_model=ProspectBoardResponse)
def get_board(
    year: int = Query(2026, description="Draft year (e.g. 2026)."),
    limit: int = Query(60, ge=1, le=200),
    position: Optional[str] = Query(None, description="Filter to PG/SG/SF/PF/C/G/F."),
    school_type: Optional[str] = Query(None, description="ncaa | g_league | international | high_school"),
    db: Session = Depends(get_db),
) -> ProspectBoardResponse:
    """Return the prospect board for a given draft year.

    Sorted by ``consensus_rank`` ascending (NULLs trail). The board is meant
    to be cheap — no archetype classification or comp computation here; that
    happens on the detail route.
    """
    query = db.query(DraftProspect).filter(DraftProspect.draft_year == year)
    if position:
        query = query.filter(DraftProspect.primary_position == position)
    if school_type:
        query = query.filter(DraftProspect.school_type == school_type)
    prospects = query.all()

    # Sort with NULL consensus ranks pushed to the end, then alpha by name as
    # a deterministic tiebreaker.
    prospects.sort(key=lambda p: (
        p.consensus_rank if p.consensus_rank is not None else 9999,
        p.full_name or "",
    ))
    prospects = prospects[:limit]

    return ProspectBoardResponse(
        draft_year=year,
        count=len(prospects),
        prospects=[_summary_from_prospect(p) for p in prospects],
    )


@router.get("/prospects/{prospect_id}", response_model=ProspectDetail)
def get_prospect_detail(
    prospect_id: int,
    db: Session = Depends(get_db),
) -> ProspectDetail:
    prospect: Optional[DraftProspect] = db.query(DraftProspect).filter(
        DraftProspect.id == prospect_id
    ).one_or_none()
    if prospect is None:
        raise HTTPException(status_code=404, detail=f"prospect {prospect_id} not found")

    summary = _summary_from_prospect(prospect)

    college_stats: List[CollegeStatLine] = [
        CollegeStatLine(
            season=s.season,
            league=s.league,
            team_name=s.team_name,
            gp=s.gp,
            min_pg=s.min_pg,
            pts_pg=s.pts_pg,
            reb_pg=s.reb_pg,
            ast_pg=s.ast_pg,
            stl_pg=s.stl_pg,
            blk_pg=s.blk_pg,
            tov_pg=s.tov_pg,
            fg_pct=s.fg_pct,
            fg3_pct=s.fg3_pct,
            ft_pct=s.ft_pct,
            ts_pct=s.ts_pct,
            usg_pct=s.usg_pct,
            pace=s.pace,
        )
        for s in (prospect.stats or [])
    ]
    college_stats.sort(key=lambda r: r.season, reverse=True)

    translation = None
    try:
        translation = translate_prospect_to_nba(db, prospect_id)
    except Exception as exc:  # noqa: BLE001 — defensive for the assembler
        logger.warning("translate_prospect_to_nba failed for prospect=%s: %s", prospect_id, exc)

    comps = []
    try:
        comps = find_nba_comps(db, prospect_id, k=5)
    except Exception as exc:  # noqa: BLE001
        logger.warning("find_nba_comps failed for prospect=%s: %s", prospect_id, exc)

    measurement_row: Optional[DraftProspectMeasurement] = (
        db.query(DraftProspectMeasurement)
        .filter(DraftProspectMeasurement.prospect_id == prospect_id)
        .order_by(DraftProspectMeasurement.id.desc())
        .first()
    )
    measurement: Optional[MeasurementPanel] = None
    if measurement_row is not None:
        measurement = MeasurementPanel(
            height_no_shoes=measurement_row.height_no_shoes,
            height_with_shoes=measurement_row.height_with_shoes,
            weight=measurement_row.weight,
            wingspan=measurement_row.wingspan,
            standing_reach=measurement_row.standing_reach,
            standing_vert=measurement_row.standing_vert,
            max_vert=measurement_row.max_vert,
            lane_agility_seconds=measurement_row.lane_agility_seconds,
            three_quarter_sprint_seconds=measurement_row.three_quarter_sprint_seconds,
            source=measurement_row.source,
        )

    return ProspectDetail(
        summary=summary,
        bio=prospect.bio,
        college_stats=college_stats,
        translation=translation,
        measurement=measurement,
        nba_comps=comps,
    )
