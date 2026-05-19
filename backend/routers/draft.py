"""Sprint 78 / FO3 — Draft Prospect Workspace API.

Routes:

- ``GET /api/draft/board?year=2026&limit=60`` — sortable, filterable
  prospect board (one row per prospect).
- ``GET /api/draft/prospects/{prospect_id}`` — full prospect detail with
  per-game stats, NBA-translated per-100 line, NBA comps, and combine
  measurements.
- ``GET /api/draft/historical/{draft_year}`` — Sprint 100 new endpoint:
  past prospects with NBA career outcomes (2016-2025) for ML validation
  views.

Sprint 100 (Stream C) — the existing routes carry additive enrichment
(consensus rank + variance, projected tier, mock rankings, combine
panel, international stats, outcome-aware comps, risk indicators,
historical baseline, translation v2). All additive: existing clients
keep working.

Read-only routes; sync responsibility lives in ``data/sync_draft_prospects``.
"""
from __future__ import annotations

import logging
import os
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import (
    DraftMockRanking, DraftOutcome, DraftProspect, DraftProspectMeasurement,
    DraftProspectStat, DraftInternationalStat, Player, Team,
)
from models.draft import (
    CollegeStatLine,
    CombineMeasurement,
    DraftProspectSummary,
    HistoricalBaseline,
    HistoricalClassResponse,
    HistoricalComp,
    HistoricalProspectEntry,
    InternationalStatLine,
    MeasurementPanel,
    MockRanking,
    NbaTranslationV2,
    ProspectBoardResponse,
    ProspectDetail,
    ProspectProfile,
    ProspectTeamFit,
    RiskIndicators,
)
from services.draft_analysis_service import (
    compute_historical_baseline,
    compute_projected_tier,
    compute_risk_indicators,
)
from services.draft_prospect_comp_service import find_nba_comps
from services.draft_prospect_comp_service_v2 import find_nba_comps_v2
from services.draft_translation_service import translate_prospect_to_nba
from services.draft_translation_service_v2 import translate_prospect_v2

logger = logging.getLogger(__name__)

router = APIRouter()

DRAFT_USE_TRANSLATION_V2 = os.environ.get("DRAFT_USE_TRANSLATION_V2", "true").lower() == "true"
HISTORICAL_YEAR_MIN = 2016
HISTORICAL_YEAR_MAX = 2025


def _latest_stat(prospect: DraftProspect) -> Optional[DraftProspectStat]:
    rows = list(prospect.stats or [])
    if not rows:
        return None
    rows.sort(key=lambda r: (r.season or "", (r.gp or 0)), reverse=True)
    return rows[0]


def _summary_from_prospect(
    prospect: DraftProspect,
    db: Optional[Session] = None,
    *,
    include_projected_tier: bool = False,
) -> DraftProspectSummary:
    """Build the board-row summary.

    The board endpoint hands in ``db`` and ``include_projected_tier=True``
    because tier projection is cheap (just reads denormalized fields).
    Other call sites can skip ``db`` and tier remains None.
    """
    latest = _latest_stat(prospect)
    mock_sources_count = (
        len({m.source for m in (prospect.mock_rankings or [])}) or None
    )
    tier: Optional[str] = None
    if include_projected_tier and db is not None:
        try:
            tier = compute_projected_tier(db, prospect)
        except Exception as exc:  # noqa: BLE001 - defensive
            logger.warning("compute_projected_tier failed for prospect=%s: %s", prospect.id, exc)
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
        # Sprint 100 (Stream C) — additive enrichment.
        consensus_rank_float=prospect.consensus_rank_float,
        consensus_variance=prospect.consensus_variance,
        projected_tier=tier,
        mock_sources_count=mock_sources_count,
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
    query = (
        db.query(DraftProspect)
        .filter(DraftProspect.draft_year == year)
        # Sprint 100 (Stream C) — exclude historical backfill rows from
        # the live board. They're for training, not for display.
        .filter(DraftProspect.is_historical.is_(False))
    )
    if position:
        query = query.filter(DraftProspect.primary_position == position)
    if school_type:
        query = query.filter(DraftProspect.school_type == school_type)
    prospects = query.all()

    # Sort by mock-draft consensus rank (Sprint 100) when present, falling
    # back to the legacy integer ``consensus_rank``, then alpha by name as
    # a deterministic tiebreaker.
    def _sort_key(p: DraftProspect):
        if p.consensus_rank_float is not None:
            return (0, p.consensus_rank_float, p.full_name or "")
        if p.consensus_rank is not None:
            return (1, float(p.consensus_rank), p.full_name or "")
        return (2, 9999.0, p.full_name or "")

    prospects.sort(key=_sort_key)
    prospects = prospects[:limit]

    return ProspectBoardResponse(
        draft_year=year,
        count=len(prospects),
        prospects=[
            _summary_from_prospect(p, db=db, include_projected_tier=True)
            for p in prospects
        ],
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
    combine_measurements: Optional[CombineMeasurement] = None
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
        combine_measurements = CombineMeasurement(
            combine_year=measurement_row.combine_year,
            height_no_shoes=measurement_row.height_no_shoes,
            height_with_shoes=measurement_row.height_with_shoes,
            weight=measurement_row.weight,
            wingspan=measurement_row.wingspan,
            standing_reach=measurement_row.standing_reach,
            body_fat_pct=measurement_row.body_fat_pct,
            hand_length=measurement_row.hand_length,
            hand_width=measurement_row.hand_width,
            standing_vert=measurement_row.standing_vert,
            max_vert=measurement_row.max_vert,
            lane_agility_seconds=measurement_row.lane_agility_seconds,
            three_quarter_sprint_seconds=measurement_row.three_quarter_sprint_seconds,
            bench_press_135=measurement_row.bench_press_135,
            source=measurement_row.source,
            source_url=measurement_row.source_url,
            as_of=measurement_row.as_of.isoformat() if measurement_row.as_of else None,
        )

    # ── Sprint 100 (Stream C) — additive enriched fields ──────────────
    mock_rankings: List[MockRanking] = []
    try:
        for r in (prospect.mock_rankings or []):
            mock_rankings.append(MockRanking(
                source=r.source,
                source_url=r.source_url,
                as_of=r.as_of.isoformat() if r.as_of else None,
                rank=r.rank,
                tier=r.tier,
                position_projected=r.position_projected,
                comp_player_name=r.comp_player_name,
            ))
    except Exception as exc:  # noqa: BLE001
        logger.warning("mock_rankings assembly failed for prospect=%s: %s", prospect_id, exc)

    international_stats: List[InternationalStatLine] = []
    try:
        intl_rows = (
            db.query(DraftInternationalStat)
            .filter(DraftInternationalStat.prospect_id == prospect_id)
            .order_by(DraftInternationalStat.season.desc())
            .all()
        )
        for row in intl_rows:
            international_stats.append(InternationalStatLine(
                season=row.season,
                league=row.league,
                team_name=row.team_name,
                games=row.games,
                minutes_per_game=row.minutes_per_game,
                ppg=row.ppg,
                rpg=row.rpg,
                apg=row.apg,
                spg=row.spg,
                bpg=row.bpg,
                fg_pct=row.fg_pct,
                three_pct=row.three_pct,
                ft_pct=row.ft_pct,
                usage_rate=row.usage_rate,
                ts_pct=row.ts_pct,
                source=row.source,
                source_url=row.source_url,
                as_of=row.as_of.isoformat() if row.as_of else None,
            ))
    except Exception as exc:  # noqa: BLE001
        logger.warning("international_stats assembly failed for prospect=%s: %s", prospect_id, exc)

    historical_comps: List[HistoricalComp] = []
    try:
        for c in find_nba_comps_v2(db, prospect_id, top_k=5):
            historical_comps.append(HistoricalComp(**c))
    except Exception as exc:  # noqa: BLE001
        logger.warning("find_nba_comps_v2 failed for prospect=%s: %s", prospect_id, exc)

    risk_indicators: Optional[RiskIndicators] = None
    try:
        risk_indicators = RiskIndicators(**compute_risk_indicators(db, prospect))
    except Exception as exc:  # noqa: BLE001
        logger.warning("compute_risk_indicators failed for prospect=%s: %s", prospect_id, exc)

    historical_baseline: Optional[HistoricalBaseline] = None
    try:
        baseline = compute_historical_baseline(db, prospect, top_k=10)
        historical_baseline = HistoricalBaseline(**baseline)
    except Exception as exc:  # noqa: BLE001
        logger.warning("compute_historical_baseline failed for prospect=%s: %s", prospect_id, exc)

    translation_v2: Optional[NbaTranslationV2] = None
    if DRAFT_USE_TRANSLATION_V2:
        try:
            v2_payload = translate_prospect_v2(db, prospect_id)
            if v2_payload is not None:
                translation_v2 = NbaTranslationV2(**v2_payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("translate_prospect_v2 failed for prospect=%s: %s", prospect_id, exc)

    # Sprint 102 (Stream B) — team-fit top-5 against current NBA rosters.
    team_fit_top: Optional[List[ProspectTeamFit]] = None
    try:
        from services.draft_team_fit_service import compute_team_fit_for_prospect

        top = compute_team_fit_for_prospect(db, prospect, limit=5)
        team_fit_top = top if top else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("compute_team_fit_for_prospect failed for prospect=%s: %s", prospect_id, exc)

    # Sprint 104 (Stream B) — algorithmic strengths/weaknesses + archetype.
    profile: Optional[ProspectProfile] = None
    try:
        from services.draft_prospect_profile_service import synthesize_profile

        profile = synthesize_profile(db, prospect)
    except Exception as exc:  # noqa: BLE001
        logger.warning("synthesize_profile failed for prospect=%s: %s", prospect_id, exc)

    return ProspectDetail(
        summary=summary,
        bio=prospect.bio,
        college_stats=college_stats,
        translation=translation,
        measurement=measurement,
        nba_comps=comps,
        mock_rankings=mock_rankings,
        combine_measurements=combine_measurements,
        international_stats=international_stats,
        historical_comps=historical_comps,
        risk_indicators=risk_indicators,
        historical_baseline=historical_baseline,
        translation_v2=translation_v2,
        team_fit_top=team_fit_top,
        profile=profile,
    )


# ── Sprint 100 (Stream C) — historical class endpoint ─────────────────


@router.get("/historical/{draft_year}", response_model=HistoricalClassResponse)
def get_historical_class(
    draft_year: int,
    db: Session = Depends(get_db),
) -> HistoricalClassResponse:
    """Return the historical draft class with NBA career outcomes.

    Years 2016-2025 are supported; outside that range returns 404.
    Built for the ML-validation / calibration view in Sprint 101 — the
    response is intentionally compact (one row per prospect) so it can
    feed a comparison table without further joins.
    """
    if not (HISTORICAL_YEAR_MIN <= draft_year <= HISTORICAL_YEAR_MAX):
        raise HTTPException(
            status_code=404,
            detail=f"historical draft year {draft_year} out of supported range "
                   f"[{HISTORICAL_YEAR_MIN}, {HISTORICAL_YEAR_MAX}]",
        )

    prospects = (
        db.query(DraftProspect)
        .filter(
            DraftProspect.draft_year == draft_year,
            DraftProspect.is_historical.is_(True),
        )
        .all()
    )

    rows: List[HistoricalProspectEntry] = []
    for p in prospects:
        outcome = (
            db.query(DraftOutcome)
            .filter(
                DraftOutcome.draft_year == draft_year,
                DraftOutcome.prospect_id == p.id,
            )
            .order_by(DraftOutcome.id.desc())
            .first()
        )
        # Resolve team abbreviation if a draft pick team is known.
        team_abbr: Optional[str] = None
        team_id = (outcome.draft_team_id if outcome else None) or p.draft_pick_team_id
        if team_id is not None:
            team = db.query(Team).filter(Team.id == team_id).one_or_none()
            if team is not None:
                team_abbr = team.abbreviation if hasattr(team, "abbreviation") else None
        career_summary = None
        if outcome is not None:
            career_summary = {
                "games": outcome.career_games,
                "minutes": outcome.career_minutes,
                "ppg": outcome.career_ppg,
                "career_ws": outcome.career_ws,
                "all_star": outcome.all_star_selections,
                "all_nba": outcome.all_nba_selections,
            }
        # Sprint 102 (Stream B) — denormalize top-1 team-fit per row. Scored
        # against the prospect's draft-season NBA rosters so the "best fit"
        # reflects era-appropriate teammates, not 2025-26 rosters.
        best_team_fit_abbr: Optional[str] = None
        best_team_fit_score: Optional[float] = None
        try:
            from services.draft_team_fit_service import compute_best_team_fit_for_prospect

            historical_season = "{0}-{1}".format(draft_year - 1, str(draft_year)[-2:])
            best_fit = compute_best_team_fit_for_prospect(db, p, season=historical_season)
            if best_fit is not None:
                best_team_fit_abbr = best_fit.team_abbreviation
                best_team_fit_score = best_fit.fit_score
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "best_team_fit failed for historical prospect=%s year=%s: %s",
                p.id, draft_year, exc,
            )

        rows.append(HistoricalProspectEntry(
            prospect_id=p.id,
            name=p.full_name,
            draft_pick=(outcome.draft_pick if outcome else None) or p.draft_pick_number,
            draft_team=team_abbr,
            predicted_tier_at_time=None,  # populated once analyzer-UI rerun lands
            outcome_tier=outcome.outcome_tier if outcome else None,
            career_summary=career_summary,
            best_team_fit_abbr=best_team_fit_abbr,
            best_team_fit_score=best_team_fit_score,
        ))

    rows.sort(key=lambda r: (r.draft_pick if r.draft_pick is not None else 9999, r.name))
    return HistoricalClassResponse(
        draft_year=draft_year,
        prospects=rows,
        as_of=date.today().isoformat(),
    )
