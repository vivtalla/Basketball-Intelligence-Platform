"""Sprint 78 FO4 — Multi-Year Team Trajectory + Aging Curves.

Pydantic response shapes for the team-arc projection surface. All fields are
``Optional`` where the underlying data may be missing (e.g. PlayerContract
table empty), so the frontend can render a graceful placeholder.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class AgingCurvePoint(BaseModel):
    """One age bucket of an empirical aging curve."""
    age: int
    sample_size: int
    pts_pg: Optional[float] = None
    ts_pct: Optional[float] = None
    ws_per_48: Optional[float] = None
    min_pg: Optional[float] = None
    usg_pct: Optional[float] = None


class AgingCurveResponse(BaseModel):
    position_bucket: str           # "G" | "F" | "C" | "all"
    seasons_used: int              # how many distinct seasons fed the fit
    points: List[AgingCurvePoint]


class ProjectedSeason(BaseModel):
    player_id: int
    player_name: str
    age: int
    year_offset: int               # 0 = current, 1 = next, ...
    pts_pg: Optional[float] = None
    ts_pct: Optional[float] = None
    ws_per_48: Optional[float] = None
    min_pg: Optional[float] = None
    usg_pct: Optional[float] = None
    win_share_total: Optional[float] = None
    notes: Optional[str] = None    # e.g. "off-roster (FA)" / "rookie"


class RosterSummary(BaseModel):
    player_id: int
    player_name: str
    age: int
    position: Optional[str] = None
    projected_pts_pg: Optional[float] = None
    projected_ts_pct: Optional[float] = None
    projected_min_pg: Optional[float] = None
    projected_win_share: Optional[float] = None
    salary: Optional[int] = None
    contract_status: Optional[str] = None  # "guaranteed" | "player_option" | "team_option" | "expiring" | "incoming" | None


class TeamArcYear(BaseModel):
    year_offset: int               # 0..n
    season_label: str              # "2025-26", "2026-27", ...
    projected_off_rtg: Optional[float] = None
    projected_def_rtg: Optional[float] = None
    projected_net_rtg: Optional[float] = None
    win_share_total: Optional[float] = None
    projected_wins: Optional[float] = None
    roster_summary: List[RosterSummary] = []


class CapState(BaseModel):
    season: str
    total_committed: int
    contracts_counted: int
    expiring_count: int
    has_data: bool


class IncomingPick(BaseModel):
    draft_year: int
    round: int
    expected_slot_low: Optional[int] = None
    expected_slot_high: Optional[int] = None
    projected_position: Optional[str] = None  # "G" | "F" | "C"


class IncomingSigning(BaseModel):
    player_id: int
    salary: Optional[int] = None
    years: int = 1


class TeamArcLevers(BaseModel):
    incoming_picks: List[IncomingPick] = []
    incoming_signings: List[IncomingSigning] = []
    outgoing_releases: List[int] = []  # player_id list


class TeamArcResponse(BaseModel):
    team_id: int
    team_abbreviation: str
    team_name: str
    base_season: str
    years: List[TeamArcYear]
    cap_state: List[CapState]
    levers_applied: List[str]
    methodology_version: str = "team_arc_v1"
    warnings: List[str] = []


class TeamArcLeversRequest(BaseModel):
    levers: Optional[TeamArcLevers] = None
    years: int = 3
