"""Pydantic models for the Sprint 78 FO1 Trade Machine.

`POST /api/trade/validate` and `POST /api/trade/impact` both accept a
``TradeRequest`` (a list of ``TradePackage`` blobs, one per team) and return
either a ``TradeValidationResult`` (rule-engine pass) or a
``TradeImpactResult`` (rotation projection pass).

The salary-matching rule is the canonical NBA ±125% rule. Apron / tax /
BYC / TPE constraints are surfaced as ``TradeWarning`` entries with severity
levels — never silently enforced — so the front-of-house can show what would
break without blocking exploration.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class TradePlayerEntry(BaseModel):
    """A single player + salary line on one side of a trade package."""
    player_id: int
    player_name: str
    salary: int = 0
    contract_type: Optional[str] = None
    years_remaining: Optional[int] = None
    is_player_option: bool = False
    is_team_option: bool = False


class TradePackage(BaseModel):
    """One team's outgoing + incoming side of a multi-team trade."""
    team_abbr: str
    outgoing_player_ids: List[int] = Field(default_factory=list)
    incoming_player_ids: List[int] = Field(default_factory=list)


class TradeWarning(BaseModel):
    """A flagged-but-not-enforced league rule for a given team's package.

    ``severity`` is one of: ``info``, ``warning``, ``hard_block``. The Trade
    Machine surfaces all severities; only ``hard_block`` flips
    ``valid=False`` on the validation response.
    """
    team_abbr: str
    rule: str            # "salary_match" | "tax_line" | "first_apron" | ...
    severity: str        # "info" | "warning" | "hard_block"
    message: str
    detail: Optional[dict] = None


class TeamSalaryLine(BaseModel):
    """Per-team salary roll-up shown in the validation card."""
    team_abbr: str
    outgoing_salary: int
    incoming_salary: int
    delta: int                          # incoming - outgoing
    salary_match_ratio: Optional[float] = None  # outgoing / incoming
    outgoing_players: List[TradePlayerEntry] = Field(default_factory=list)
    incoming_players: List[TradePlayerEntry] = Field(default_factory=list)


class TradeValidationResult(BaseModel):
    """Rule-engine pass output."""
    valid: bool
    team_count: int
    team_salary_lines: List[TeamSalaryLine] = Field(default_factory=list)
    warnings: List[TradeWarning] = Field(default_factory=list)
    summary: Optional[str] = None


class ArchetypeGap(BaseModel):
    """A gap callout for a team's projected post-trade rotation."""
    archetype: str
    direction: str       # "added" | "lost" | "shifted"
    note: str


class TeamImpactProjection(BaseModel):
    """Per-team rotation projection for the impact pass."""
    team_abbr: str
    confidence: str      # "ready" | "thin_sample" | "no_data"
    baseline_net_rating: Optional[float] = None
    projected_net_rating: Optional[float] = None
    net_rating_delta: Optional[float] = None
    rotation_health_score: Optional[float] = None
    archetype_gaps: List[ArchetypeGap] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class TradeImpactResult(BaseModel):
    """Multi-team rotation impact projection."""
    season: str
    teams: List[TeamImpactProjection] = Field(default_factory=list)
    methodology_version: str = "trade_impact_v1"


class TradeRequest(BaseModel):
    """Request body shared by validate + impact endpoints."""
    season: str = "2025-26"
    packages: List[TradePackage] = Field(default_factory=list, min_length=2, max_length=4)


class TeamContractEntry(BaseModel):
    """Roster row for the per-team contracts panel."""
    player_id: int
    player_name: str
    team_abbr: str
    season: str
    salary: int
    years_remaining: Optional[int] = None
    is_player_option: bool = False
    is_team_option: bool = False
    contract_type: Optional[str] = None


class TeamContractsResponse(BaseModel):
    team_abbr: str
    season: str
    total_salary: int
    contracts: List[TeamContractEntry] = Field(default_factory=list)
