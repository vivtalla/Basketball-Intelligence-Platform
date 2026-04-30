"""Sprint 78 FO4 — Multi-Year Team Arc Projection.

Projects a team's roster forward 0..N years by applying empirical aging-curve
deltas to each rostered player and aggregating to team-level expected
outcomes (proxy off / def / net rating, total win shares, projected wins).

Levers
------
The optional ``levers`` argument lets a user explore "what-if" scenarios:

* ``incoming_picks``   — drafted prospects added at year 1+ with conservative
  rookie projections (10 mpg, 0.05 ws/48). Slot range modestly weights pts_pg.
* ``incoming_signings``— free agent additions (player_id + salary). The
  player is projected from their own SeasonStat history and added to the
  roster from year 1+.
* ``outgoing_releases``— player_ids removed from the projection from year 1+.

Outputs
-------
``TeamArcResponse`` carries per-year aggregate ratings, a roster summary with
contract context (when PlayerContract has rows for that season), a cap-state
strip, and the list of levers actually applied.

This service intentionally does *not* mutate any DB rows. It is purely a
computed view for the new Arc tab on ``/teams/[abbr]``.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import DraftPickAsset, Player, PlayerContract, SeasonStat, Team
from models.team_arc import (
    CapState,
    IncomingPick,
    IncomingSigning,
    ProjectedSeason,
    RosterSummary,
    TeamArcLevers,
    TeamArcResponse,
    TeamArcYear,
)
from services.aging_curve_service import (
    _player_age_at_season,
    _season_start_year,
    project_player_next_n,
)


# League average reference (used to derive proxy off/def/net ratings).
_LEAGUE_AVG_OFF_RTG = 114.0
_LEAGUE_AVG_DEF_RTG = 114.0
_LEAGUE_AVG_WS_TOTAL = 41.0  # roughly the league-median per-team win-share total


def _next_season_label(season: str, offset: int) -> str:
    start = _season_start_year(season)
    if start is None:
        return season
    new_start = start + offset
    return "{0}-{1:02d}".format(new_start, (new_start + 1) % 100)


def _resolve_team(db: Session, team_abbr: str) -> Team:
    team = db.query(Team).filter(Team.abbreviation == team_abbr.upper()).first()
    if team is None:
        raise ValueError("Team '{0}' not found".format(team_abbr))
    return team


def _roster_for_season(
    db: Session,
    team: Team,
    season: str,
) -> List[Player]:
    """Players on the team for a given season.

    Prefers PlayerContract rows for the season (so we capture contract-driven
    roster context). Falls back to ``Player.team_id == team.id`` if the
    contract table is empty for that season.
    """
    contract_rows = (
        db.query(PlayerContract)
        .filter(
            PlayerContract.team_id == team.id,
            PlayerContract.season == season,
        )
        .all()
    )
    if contract_rows:
        player_ids = [row.player_id for row in contract_rows]
        return (
            db.query(Player)
            .filter(Player.id.in_(player_ids))
            .all()
        )

    return (
        db.query(Player)
        .filter(Player.team_id == team.id, Player.is_active == True)  # noqa: E712
        .all()
    )


def _contract_for(
    contracts: List[PlayerContract],
    player_id: int,
) -> Optional[PlayerContract]:
    for row in contracts:
        if row.player_id == player_id:
            return row
    return None


def _contract_status(contract: Optional[PlayerContract]) -> Optional[str]:
    if contract is None:
        return None
    if contract.is_player_option:
        return "player_option"
    if contract.is_team_option:
        return "team_option"
    if contract.is_non_guaranteed:
        return "non_guaranteed"
    if contract.years_remaining is not None and contract.years_remaining <= 1:
        return "expiring"
    return "guaranteed"


def _project_pick(pick: IncomingPick, year_offset: int) -> ProjectedSeason:
    """Conservative rookie projection for an incoming draft pick.

    We use a slot-based pts_pg anchor (lottery picks get a higher base) and a
    flat 0.04 ws/48 baseline that's typical for rookies. The synthetic
    ``player_id`` is negative so it never collides with a real NBA id.
    """
    slot_low = pick.expected_slot_low or 30
    slot_high = pick.expected_slot_high or slot_low
    avg_slot = (slot_low + slot_high) / 2.0
    # Lottery vs late-1st vs 2nd-round pts_pg anchor
    if avg_slot <= 14:
        pts = 11.0
        min_pg = 22.0
    elif avg_slot <= 30:
        pts = 7.0
        min_pg = 16.0
    else:
        pts = 4.0
        min_pg = 10.0

    synthetic_id = -(pick.draft_year * 100 + int(avg_slot))
    label = "Pick {0}-{1} ({2})".format(slot_low, slot_high, pick.draft_year)

    return ProjectedSeason(
        player_id=synthetic_id,
        player_name=label,
        age=20,
        year_offset=year_offset,
        pts_pg=round(pts, 2),
        ts_pct=0.530,
        ws_per_48=0.040,
        min_pg=round(min_pg, 2),
        usg_pct=20.0,
        win_share_total=round(0.040 * min_pg * 70.0 / 48.0, 2),
        notes="incoming pick",
    )


def _aggregate_year(
    projections: List[ProjectedSeason],
) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Return (off_rtg, def_rtg, net_rtg, win_share_total) for a year.

    Off/def proxies center on the league average and shift in proportion to
    how the team's projected aggregate win-share total compares to the
    league-average team. This yields plausible per-season trajectory
    movement without claiming to be a calibrated rating model.
    """
    if not projections:
        return None, None, None, None

    ws_values = [p.win_share_total for p in projections if p.win_share_total is not None]
    if not ws_values:
        return None, None, None, None

    ws_total = sum(ws_values)
    # ±1 ws above league avg ~ ±0.1 net rtg point.
    ws_swing = ws_total - _LEAGUE_AVG_WS_TOTAL
    net_rtg = round(ws_swing * 0.10, 2)
    # Split the swing roughly 60/40 between offense and defense.
    off_rtg = round(_LEAGUE_AVG_OFF_RTG + ws_swing * 0.06, 2)
    def_rtg = round(_LEAGUE_AVG_DEF_RTG - ws_swing * 0.04, 2)
    return off_rtg, def_rtg, net_rtg, round(ws_total, 2)


def _projected_wins(net_rtg: Optional[float]) -> Optional[float]:
    if net_rtg is None:
        return None
    # Each +1 point of net rating ≈ 2.7 additional wins per 82 games (well-known
    # rule of thumb). Anchor at 41-41 for a 0 net rating team.
    wins = 41.0 + (net_rtg * 2.7)
    return round(max(0.0, min(82.0, wins)), 1)


def _build_cap_strip(
    db: Session,
    team: Team,
    seasons: List[str],
) -> List[CapState]:
    """Per-season summary of contracts on the books for the team."""
    out: List[CapState] = []
    for season in seasons:
        contracts = (
            db.query(PlayerContract)
            .filter(
                PlayerContract.team_id == team.id,
                PlayerContract.season == season,
            )
            .all()
        )
        if not contracts:
            out.append(CapState(
                season=season,
                total_committed=0,
                contracts_counted=0,
                expiring_count=0,
                has_data=False,
            ))
            continue
        total = sum(int(row.salary or 0) for row in contracts)
        expiring = sum(1 for row in contracts if (row.years_remaining or 0) <= 1)
        out.append(CapState(
            season=season,
            total_committed=int(total),
            contracts_counted=len(contracts),
            expiring_count=expiring,
            has_data=True,
        ))
    return out


def _resolve_levers(
    db: Session,
    levers: Optional[TeamArcLevers],
) -> Tuple[List[IncomingPick], List[IncomingSigning], List[int], List[str]]:
    if levers is None:
        return [], [], [], []
    applied: List[str] = []
    if levers.incoming_picks:
        applied.append("{0} incoming pick(s)".format(len(levers.incoming_picks)))
    if levers.incoming_signings:
        applied.append("{0} incoming signing(s)".format(len(levers.incoming_signings)))
    if levers.outgoing_releases:
        applied.append("{0} outgoing release(s)".format(len(levers.outgoing_releases)))
    return (
        list(levers.incoming_picks or []),
        list(levers.incoming_signings or []),
        list(levers.outgoing_releases or []),
        applied,
    )


def _team_owned_pick_levers(
    db: Session,
    team: Team,
    base_year: int,
    n_years: int,
) -> List[IncomingPick]:
    """Pull DraftPickAsset rows owned by this team for the projected window.

    Used to seed default lever values when the caller hasn't supplied any.
    Falls back to an empty list if the table is empty (handled gracefully).
    """
    rows = (
        db.query(DraftPickAsset)
        .filter(
            DraftPickAsset.owner_team_id == team.id,
            DraftPickAsset.draft_year >= base_year,
            DraftPickAsset.draft_year <= base_year + n_years,
            DraftPickAsset.is_conveyed == False,  # noqa: E712
        )
        .all()
    )
    return [
        IncomingPick(
            draft_year=row.draft_year,
            round=row.round,
            expected_slot_low=row.expected_slot_low,
            expected_slot_high=row.expected_slot_high,
        )
        for row in rows
    ]


def project_team_arc(
    db: Session,
    team_abbr: str,
    n_years: int = 3,
    levers: Optional[TeamArcLevers] = None,
    base_season: Optional[str] = None,
) -> TeamArcResponse:
    """Compute a multi-year team arc projection.

    Parameters
    ----------
    team_abbr   Three-letter team abbreviation (e.g. ``"BOS"``).
    n_years     Forward horizon in seasons. Year 0 is included as the baseline.
    levers      Optional what-if scenario inputs.
    base_season Override for the baseline season; defaults to the latest
                ``SeasonStat`` season available for the roster.
    """
    team = _resolve_team(db, team_abbr)
    n_years = max(0, min(int(n_years), 6))
    warnings: List[str] = []

    # Resolve baseline season — most recent SeasonStat row for any roster player.
    if base_season is None:
        latest_row = (
            db.query(SeasonStat)
            .order_by(SeasonStat.season.desc())
            .first()
        )
        base_season = latest_row.season if latest_row else "2024-25"

    base_year = _season_start_year(base_season) or 2024
    seasons = [_next_season_label(base_season, offset) for offset in range(n_years + 1)]

    base_roster = _roster_for_season(db, team, base_season)
    if not base_roster:
        warnings.append("No roster found for {0} in {1}; falling back to current Player.team_id roster.".format(team.abbreviation, base_season))

    # Resolve levers and synthesize defaults from DraftPickAsset if caller
    # supplied none.
    incoming_picks, incoming_signings, outgoing_releases, applied = _resolve_levers(db, levers)
    if levers is None or not levers.incoming_picks:
        owned_picks = _team_owned_pick_levers(db, team, base_year + 1, n_years)
        if owned_picks:
            incoming_picks = owned_picks
            applied.append("{0} owned-pick(s) auto-loaded".format(len(owned_picks)))

    # Per-player projections for the base roster.
    base_projections: Dict[int, List[ProjectedSeason]] = {}
    for player in base_roster:
        rows = project_player_next_n(db, player.id, n_years=n_years, base_season=base_season)
        if not rows:
            # Not enough SeasonStat history — keep the player on the roster
            # with placeholder projection rows so they still show up.
            age = _player_age_at_season(player, base_season) or 25
            placeholder = [
                ProjectedSeason(
                    player_id=player.id,
                    player_name=player.full_name,
                    age=age + offset,
                    year_offset=offset,
                    pts_pg=None,
                    ts_pct=None,
                    ws_per_48=None,
                    min_pg=None,
                    usg_pct=None,
                    win_share_total=None,
                    notes="no prior SeasonStat",
                )
                for offset in range(n_years + 1)
            ]
            base_projections[player.id] = placeholder
        else:
            base_projections[player.id] = rows

    # Incoming signings — project each like a normal player, but starting from year 1.
    signing_projections: Dict[int, Tuple[List[ProjectedSeason], IncomingSigning]] = {}
    for signing in incoming_signings:
        rows = project_player_next_n(db, signing.player_id, n_years=n_years, base_season=base_season)
        if rows:
            signing_projections[signing.player_id] = (rows, signing)

    years: List[TeamArcYear] = []
    for offset in range(n_years + 1):
        season_label = seasons[offset]
        contracts_for_year = (
            db.query(PlayerContract)
            .filter(
                PlayerContract.team_id == team.id,
                PlayerContract.season == season_label,
            )
            .all()
        )

        # Compose the year's roster.
        year_projections: List[ProjectedSeason] = []
        roster_rows: List[RosterSummary] = []
        for player in base_roster:
            if offset > 0 and player.id in outgoing_releases:
                continue
            projections = base_projections.get(player.id) or []
            year_proj = next((p for p in projections if p.year_offset == offset), None)
            if year_proj is None:
                continue
            year_projections.append(year_proj)
            contract = _contract_for(contracts_for_year, player.id)
            roster_rows.append(RosterSummary(
                player_id=player.id,
                player_name=player.full_name,
                age=year_proj.age,
                position=player.position,
                projected_pts_pg=year_proj.pts_pg,
                projected_ts_pct=year_proj.ts_pct,
                projected_min_pg=year_proj.min_pg,
                projected_win_share=year_proj.win_share_total,
                salary=int(contract.salary) if contract and contract.salary is not None else None,
                contract_status=_contract_status(contract),
            ))

        # Add incoming signings (year 1+).
        if offset >= 1:
            for player_id, (rows, signing) in signing_projections.items():
                row = next((r for r in rows if r.year_offset == offset), None)
                if row is None:
                    continue
                row = row.model_copy(update={"notes": "incoming signing"})
                year_projections.append(row)
                roster_rows.append(RosterSummary(
                    player_id=player_id,
                    player_name=row.player_name,
                    age=row.age,
                    position=None,
                    projected_pts_pg=row.pts_pg,
                    projected_ts_pct=row.ts_pct,
                    projected_min_pg=row.min_pg,
                    projected_win_share=row.win_share_total,
                    salary=signing.salary,
                    contract_status="incoming",
                ))

        # Add incoming picks (year 1+).
        if offset >= 1:
            for pick in incoming_picks:
                if pick.draft_year != base_year + offset:
                    continue
                projection = _project_pick(pick, offset)
                year_projections.append(projection)
                roster_rows.append(RosterSummary(
                    player_id=projection.player_id,
                    player_name=projection.player_name,
                    age=projection.age,
                    position=pick.projected_position,
                    projected_pts_pg=projection.pts_pg,
                    projected_ts_pct=projection.ts_pct,
                    projected_min_pg=projection.min_pg,
                    projected_win_share=projection.win_share_total,
                    salary=None,
                    contract_status="incoming",
                ))

        off_rtg, def_rtg, net_rtg, ws_total = _aggregate_year(year_projections)
        # Sort roster: descending projected win share, with None last.
        roster_rows.sort(key=lambda r: (r.projected_win_share is None, -(r.projected_win_share or 0.0)))

        years.append(TeamArcYear(
            year_offset=offset,
            season_label=season_label,
            projected_off_rtg=off_rtg,
            projected_def_rtg=def_rtg,
            projected_net_rtg=net_rtg,
            win_share_total=ws_total,
            projected_wins=_projected_wins(net_rtg),
            roster_summary=roster_rows,
        ))

    cap_state = _build_cap_strip(db, team, seasons)
    if not any(c.has_data for c in cap_state):
        warnings.append("PlayerContract table is empty for {0}; cap state shown as placeholder.".format(team.abbreviation))

    return TeamArcResponse(
        team_id=team.id,
        team_abbreviation=team.abbreviation,
        team_name=team.name or team.abbreviation,
        base_season=base_season,
        years=years,
        cap_state=cap_state,
        levers_applied=applied,
        warnings=warnings,
    )
