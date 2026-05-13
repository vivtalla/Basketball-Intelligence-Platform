from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from data.nba_client import _active_nba_season
from db.database import get_db
from models.mvp import (
    MvpCandidateCaseResponse,
    MvpCoverageResponse,
    MvpContextMapResponse,
    MvpGravityLeaderboardResponse,
    MvpRaceResponse,
    MvpSensitivityResponse,
    MvpTimelineResponse,
    MvpVoterRoomResponse,
)
from services.mvp_service import (
    AVAILABLE_PROFILES,
    build_mvp_candidate_case,
    build_mvp_coverage,
    build_mvp_context_map,
    build_mvp_gravity_leaderboard,
    build_mvp_race,
    build_mvp_race_playoff,
    build_mvp_sensitivity,
    build_mvp_snapshot_freshness,
    build_mvp_voter_room,
)
from services.mvp_timeline_service import build_mvp_timeline

router = APIRouter()

_PROFILE_DESCRIPTION = (
    "Scoring profile: one of box_first, balanced, impact_consensus. Default: balanced."
)


@router.get("/race", response_model=MvpRaceResponse)
def get_mvp_race(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    top: int = Query(default=10, ge=1, le=25, description="Number of candidates to return"),
    min_gp: Optional[int] = Query(default=None, ge=1, le=82, description="Minimum games played; defaults to 20 (Regular Season) / 1 (Playoffs)"),
    position: Optional[str] = Query(default=None, description="Optional position token, e.g. G, F, C"),
    profile: Optional[str] = Query(default=None, description=_PROFILE_DESCRIPTION),
    season_type: str = Query(default="Regular Season", description='"Regular Season" or "Playoffs"'),
    db: Session = Depends(get_db),
) -> MvpRaceResponse:
    """Return the top-N MVP candidates with case data and pillar scoring.

    Sprint 99 — Wrapped in an in-process TTL cache (4h, matching the
    Cloudflare ``cache-control: max-age=14400`` on the response). The
    underlying compute costs ~10s on cold cache (PBP iteration +
    per-candidate sub-profiles). Cloudflare's edge cache covers the warm
    steady state; this layer covers the gunicorn-worker-cold-but-Cloudflare-
    expired window where a user would otherwise wait 10s. The cron warmer
    in ``scripts/warm_mvp_cache.py`` keeps Cloudflare itself warm.
    """
    from services.mvp_race_cache import mvp_race_cache, cache_key

    resolved_season = season or _active_nba_season()
    if season_type == "Playoffs":
        gp_floor = min_gp if min_gp is not None else 1
    else:
        gp_floor = min_gp if min_gp is not None else 20

    key = cache_key(resolved_season, top, gp_floor, position, profile, season_type)

    def _compute() -> MvpRaceResponse:
        if season_type == "Playoffs":
            # Playoff samples are tiny (3-4 games per team in round 1); use the
            # playoff-specific composite that pulls from playoff SeasonStat rows.
            return build_mvp_race_playoff(db, season=resolved_season, top=top, min_gp=gp_floor)
        return build_mvp_race(
            db, season=resolved_season, top=top, min_gp=gp_floor, position=position, profile=profile
        )

    return mvp_race_cache.get_or_compute(key, _compute)


@router.get("/gravity", response_model=MvpGravityLeaderboardResponse)
def get_mvp_gravity(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    top: int = Query(default=20, ge=1, le=50, description="Number of gravity profiles to return"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    position: Optional[str] = Query(default=None, description="Optional position token, e.g. G, F, C"),
    db: Session = Depends(get_db),
) -> MvpGravityLeaderboardResponse:
    """Return lightweight MVP Gravity leaderboard context."""
    resolved_season = season or _active_nba_season()
    return build_mvp_gravity_leaderboard(db, season=resolved_season, top=top, min_gp=min_gp, position=position)


@router.get("/candidates/{player_id}/case", response_model=MvpCandidateCaseResponse)
def get_mvp_candidate_case(
    player_id: int,
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    position: Optional[str] = Query(default=None, description="Optional position token, e.g. G, F, C"),
    profile: Optional[str] = Query(default=None, description=_PROFILE_DESCRIPTION),
    db: Session = Depends(get_db),
) -> MvpCandidateCaseResponse:
    """Return one candidate's full MVP case plus nearby rank context."""
    resolved_season = season or _active_nba_season()
    return build_mvp_candidate_case(
        db,
        season=resolved_season,
        player_id=player_id,
        min_gp=min_gp,
        position=position,
        profile=profile,
    )


@router.get("/context-map", response_model=MvpContextMapResponse)
def get_mvp_context_map(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    top: int = Query(default=20, ge=1, le=50, description="Number of candidates to return"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    position: Optional[str] = Query(default=None, description="Optional position token, e.g. G, F, C"),
    profile: Optional[str] = Query(default=None, description=_PROFILE_DESCRIPTION),
    db: Session = Depends(get_db),
) -> MvpContextMapResponse:
    """Return lightweight MVP case-map coordinates and evidence."""
    resolved_season = season or _active_nba_season()
    return build_mvp_context_map(
        db, season=resolved_season, top=top, min_gp=min_gp, position=position, profile=profile
    )


@router.get("/sensitivity", response_model=MvpSensitivityResponse)
def get_mvp_sensitivity(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    top: int = Query(default=15, ge=1, le=30, description="Number of candidates to include"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    position: Optional[str] = Query(default=None, description="Optional position token, e.g. G, F, C"),
    db: Session = Depends(get_db),
) -> MvpSensitivityResponse:
    """Return rank-by-profile for the top-N candidates — used by the ranking-shift slope chart."""
    resolved_season = season or _active_nba_season()
    return build_mvp_sensitivity(
        db, season=resolved_season, top=top, min_gp=min_gp, position=position
    )


@router.get("/timeline", response_model=MvpTimelineResponse)
def get_mvp_timeline(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    profile: Optional[str] = Query(default=None, description=_PROFILE_DESCRIPTION),
    days: int = Query(default=210, ge=2, le=240, description="Number of recent timeline days to include"),
    top: int = Query(default=8, ge=1, le=15, description="Number of latest candidates to include"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    db: Session = Depends(get_db),
) -> MvpTimelineResponse:
    """Return persisted MVP race movement across daily snapshots."""
    resolved_season = season or _active_nba_season()
    return build_mvp_timeline(
        db,
        season=resolved_season,
        profile=profile or "balanced",
        days=days,
        top=top,
        min_gp=min_gp,
    )


@router.get("/voter-room", response_model=MvpVoterRoomResponse)
def get_mvp_voter_room(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    player_ids: str = Query(default="", description="Comma-separated player IDs to compare, 2-3 candidates"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    db: Session = Depends(get_db),
) -> MvpVoterRoomResponse:
    """Return MVP case-comparison payload for a 2-3 candidate Voter Room."""
    resolved_season = season or _active_nba_season()
    parsed_ids = []
    for token in (player_ids or "").split(","):
        token = token.strip()
        if not token:
            continue
        try:
            parsed_ids.append(int(token))
        except ValueError:
            continue
    return build_mvp_voter_room(db, season=resolved_season, player_ids=parsed_ids, min_gp=min_gp)


@router.get("/coverage", response_model=MvpCoverageResponse)
def get_mvp_coverage(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    top: int = Query(default=10, ge=1, le=25, description="Number of candidates to inspect"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    db: Session = Depends(get_db),
) -> MvpCoverageResponse:
    """Return MVP-specific source and snapshot coverage health."""
    resolved_season = season or _active_nba_season()
    return build_mvp_coverage(db, season=resolved_season, top=top, min_gp=min_gp)


@router.get("/snapshot-freshness")
def get_mvp_snapshot_freshness(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    db: Session = Depends(get_db),
):
    """Return lightweight persisted MVP snapshot freshness for product badges."""
    resolved_season = season or _active_nba_season()
    return build_mvp_snapshot_freshness(db, resolved_season)


@router.get("/profiles")
def get_mvp_profiles() -> dict:
    """Return the list of available scoring profile names (stable for UI pill groups)."""
    return {"profiles": AVAILABLE_PROFILES, "default": "balanced"}
