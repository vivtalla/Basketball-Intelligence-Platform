"""Career legacy / Hall-of-Fame router. Sprint 78 / CF3.

Single endpoint today: ``GET /api/players/{player_id}/legacy`` returning
the assembled ``CareerLegacyResponse``. Mounted under ``/api/players``
so the frontend Legacy tab consumes a stable, player-scoped path
without owning the Sprint 14 ``players.py`` router.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Player
from models.career_legacy import CareerLegacyResponse
from services.career_legacy_service import (
    compute_era_adjusted_line,
    compute_hof_projection,
)
from services.career_milestone_service import compute_career_milestones
from services.era_peer_service import find_era_peers


router = APIRouter()


@router.get("/{player_id}/legacy", response_model=CareerLegacyResponse)
def get_player_legacy(
    player_id: int,
    peer_count: int = Query(8, ge=3, le=10, description="Era-peer cohort size"),
    db: Session = Depends(get_db),
) -> CareerLegacyResponse:
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(
            status_code=404,
            detail=f"Player {player_id} not found in local warehouse.",
        )

    summary = compute_era_adjusted_line(db, player_id)
    achieved, next_approach = compute_career_milestones(db, player_id)
    peers = find_era_peers(db, player_id, n=peer_count)
    # Awards table doesn't exist yet; pass through anything attached to
    # the player profile via a future hook here.
    accolades: Optional[Dict[str, Any]] = None
    projection = compute_hof_projection(db, player_id, accolades=accolades)

    methodology = {
        "version": "career_legacy_v1",
        "pace_adjustment": "PPG / (league_avg_pace_that_season / 100)",
        "ts_delta": "career-weighted TS% minus career-weighted league TS%",
        "peer_pool": "all qualifying SeasonStat rows (gp >= 20, all similarity stats present)",
        "peer_method": "career-aggregate z-vector, weighted by GP, Euclidean distance",
        "hof_score": "20k pts +30 · MVP/DPOY +20 · All-Stars +15 each (cap 60) · ring +10",
        "hof_bands": {
            "Likely HOF": "score >= 80",
            "Borderline": "50 <= score < 80",
            "Tracking": "score < 50",
        },
    }

    return CareerLegacyResponse(
        player_id=player_id,
        player_name=player.full_name,
        seasons_played=summary.seasons_played,
        era_adjusted_summary=summary,
        milestones_achieved=achieved,
        next_milestone=next_approach,
        era_peers=peers,
        hof_projection=projection,
        methodology_version="career_legacy_v1",
        methodology=methodology,
    )
