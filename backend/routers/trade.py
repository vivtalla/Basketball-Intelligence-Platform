"""Trade Machine API surface (Sprint 78 FO1).

Routes::

    POST /api/trade/validate            -> TradeValidationResult
    POST /api/trade/impact              -> TradeImpactResult
    GET  /api/trade/contracts/{abbr}    -> TeamContractsResponse
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Player, PlayerContract, Team
from models.trade import (
    TeamContractEntry,
    TeamContractsResponse,
    TradeImpactResult,
    TradeRequest,
    TradeValidationResult,
)
from services.trade_impact_service import project_trade_impact
from services.trade_machine_service import validate_trade

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/validate", response_model=TradeValidationResult)
def post_validate_trade(
    payload: TradeRequest,
    db: Session = Depends(get_db),
) -> TradeValidationResult:
    return validate_trade(db, packages=payload.packages, season=payload.season)


@router.post("/impact", response_model=TradeImpactResult)
def post_trade_impact(
    payload: TradeRequest,
    db: Session = Depends(get_db),
) -> TradeImpactResult:
    return project_trade_impact(db, packages=payload.packages, season=payload.season)


@router.get("/contracts/{team_abbr}", response_model=TeamContractsResponse)
def get_team_contracts(
    team_abbr: str,
    season: str = Query("2025-26", description="Season string, e.g. 2025-26"),
    db: Session = Depends(get_db),
) -> TeamContractsResponse:
    abbr = (team_abbr or "").upper()
    team = db.query(Team).filter(Team.abbreviation == abbr).first()
    if team is None:
        raise HTTPException(status_code=404, detail="Team %s not found" % abbr)

    rows = (
        db.query(PlayerContract, Player)
        .join(Player, Player.id == PlayerContract.player_id)
        .filter(
            PlayerContract.team_id == team.id,
            PlayerContract.season == season,
        )
        .order_by(PlayerContract.salary.desc())
        .all()
    )

    contracts = [
        TeamContractEntry(
            player_id=player.id,
            player_name=player.full_name,
            team_abbr=abbr,
            season=contract.season,
            salary=int(contract.salary or 0),
            years_remaining=contract.years_remaining,
            is_player_option=bool(contract.is_player_option),
            is_team_option=bool(contract.is_team_option),
            contract_type=contract.contract_type,
        )
        for contract, player in rows
    ]

    total_salary = int(sum(c.salary for c in contracts))
    return TeamContractsResponse(
        team_abbr=abbr,
        season=season,
        total_salary=total_salary,
        contracts=contracts,
    )
