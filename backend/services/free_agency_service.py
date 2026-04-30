"""Sprint 78 — FO2 Free Agency Workspace service.

Builds the league-wide expiring-contract leaderboard plus per-player team-fit
rankings. The service is deliberately resilient: if the backing
`player_contracts` table is empty (FO1 ingestion not yet run), every entry
point returns an empty response with `is_empty_dataset=True` rather than
raising — the workspace shows an empty-state.

Reuses (does not rebuild):
- `services.team_fit_service` for roster-fit scoring
- `services.similarity_service._qualified_rows_v2 / _season_norms_v2` via the
  team-fit pipeline
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import Player, PlayerContract, SeasonStat, Team
from models.free_agency import (
    ExpiringContract,
    FitRationaleChip,
    FreeAgencyMethodology,
    FreeAgencyResponse,
    FreeAgentFitsResponse,
    FreeAgentTier,
    TeamFitForPlayer,
)
from services.team_fit_service import build_team_fit_report


METHODOLOGY_VERSION = "free_agency_v1"

# Approximate cap-tier thresholds in USD for the 2025-26 cap landscape. These
# are intentionally directional — full CBA fidelity (apron/tax/exceptions)
# is out of scope per Sprint 78 user-confirmed scope. Tiers are recomputed at
# runtime so a future season's cap shifts only require updating the table.
TIER_THRESHOLDS_USD: Dict[str, int] = {
    # Salary >= max_floor → "max" (≈30% of cap, $40M+ for veterans).
    "max_floor": 40_000_000,
    # Salary >= above_mid_floor → "above_mid" (taxpayer/mid + bird-rights deals).
    "above_mid_floor": 14_500_000,
    # Salary >= mid_level_floor → "mid_level" (room/bi-annual exception bands).
    "mid_level_floor": 4_500_000,
    # Salary >= minimum_floor → "minimum" (veteran-min table).
    "minimum_floor": 1_000_000,
    # Below minimum_floor → "two_way".
}

EXPIRING_WINDOW_DAYS = 365


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def tier_for_contract(salary: Optional[int]) -> FreeAgentTier:
    """Bucket a contract by approximate cap tier.

    Used for both the leaderboard tier filter and the per-row pill. `None`
    salary defaults to "two_way" because that is the safest no-data bucket
    (smallest cap impact, most permissive filter).
    """
    if salary is None or salary <= 0:
        return "two_way"
    s = int(salary)
    if s >= TIER_THRESHOLDS_USD["max_floor"]:
        return "max"
    if s >= TIER_THRESHOLDS_USD["above_mid_floor"]:
        return "above_mid"
    if s >= TIER_THRESHOLDS_USD["mid_level_floor"]:
        return "mid_level"
    if s >= TIER_THRESHOLDS_USD["minimum_floor"]:
        return "minimum"
    return "two_way"


def compute_expiring_contracts(
    db: Session,
    season: str,
    *,
    tier: Optional[str] = None,
    position: Optional[str] = None,
    age_max: Optional[int] = None,
) -> FreeAgencyResponse:
    """Return the league-wide expiring-contract leaderboard for `season`.

    Empty `player_contracts` -> empty response with `is_empty_dataset=True`.
    """
    methodology = _build_methodology()

    total_count = db.query(PlayerContract).count()
    if total_count == 0:
        return FreeAgencyResponse(
            season=season,
            total_count=0,
            filtered_count=0,
            contracts=[],
            available_tiers=[],
            methodology=methodology,
            is_empty_dataset=True,
            warnings=["No player_contracts rows ingested yet — empty workspace."],
        )

    today = date.today()
    cutoff = today + timedelta(days=EXPIRING_WINDOW_DAYS)

    # An expiring contract: years_remaining <= 1 OR expires_on within 12 months.
    # We pull the candidate set first then filter in Python — keeps the
    # SQL portable across SQLite (tests) and Postgres.
    rows: List[PlayerContract] = (
        db.query(PlayerContract)
        .filter(PlayerContract.season == season)
        .all()
    )

    expiring_rows: List[PlayerContract] = []
    for row in rows:
        years_remaining = row.years_remaining if row.years_remaining is not None else 0
        is_expiring_by_years = years_remaining <= 1
        is_expiring_by_date = (
            row.expires_on is not None
            and today <= row.expires_on <= cutoff
        )
        if is_expiring_by_years or is_expiring_by_date:
            expiring_rows.append(row)

    if not expiring_rows:
        return FreeAgencyResponse(
            season=season,
            total_count=total_count,
            filtered_count=0,
            contracts=[],
            available_tiers=[],
            methodology=methodology,
            is_empty_dataset=False,
            warnings=[
                "No expiring contracts in {0} (years_remaining<=1 or expires_on within 12 months).".format(season)
            ],
        )

    # Hydrate Player + Team + latest qualified SeasonStat for each contract.
    player_ids = list({row.player_id for row in expiring_rows})
    players: Dict[int, Player] = {
        p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()
    }
    team_ids = list({row.team_id for row in expiring_rows if row.team_id is not None})
    teams: Dict[int, Team] = {
        t.id: t for t in db.query(Team).filter(Team.id.in_(team_ids)).all()
    } if team_ids else {}

    season_stats = _latest_qualified_stats_by_player(db, player_ids)

    contracts: List[ExpiringContract] = []
    for row in expiring_rows:
        player = players.get(row.player_id)
        if player is None:
            # Orphaned contract — skip rather than crash.
            continue
        team = teams.get(row.team_id) if row.team_id is not None else None
        stat = season_stats.get(row.player_id)
        contracts.append(
            ExpiringContract(
                player_id=row.player_id,
                player_name=player.full_name,
                team_abbreviation=(team.abbreviation if team is not None else None),
                team_id=(team.id if team is not None else None),
                position=player.position,
                age=_age_for_player(player),
                season=row.season,
                salary=row.salary,
                years_remaining=row.years_remaining,
                is_player_option=bool(row.is_player_option),
                is_team_option=bool(row.is_team_option),
                is_non_guaranteed=bool(row.is_non_guaranteed),
                no_trade_clause=bool(row.no_trade_clause),
                contract_type=row.contract_type,
                expires_on=(row.expires_on.isoformat() if row.expires_on is not None else None),
                tier=tier_for_contract(row.salary),
                stat_season=(stat.season if stat is not None else None),
                gp=(stat.gp if stat is not None else None),
                min_pg=(stat.min_pg if stat is not None else None),
                pts_pg=(stat.pts_pg if stat is not None else None),
                reb_pg=(stat.reb_pg if stat is not None else None),
                ast_pg=(stat.ast_pg if stat is not None else None),
                ts_pct=(stat.ts_pct if stat is not None else None),
                usg_pct=(stat.usg_pct if stat is not None else None),
                net_rating=(stat.net_rating if stat is not None else None),
                source=row.source,
            )
        )

    # Filter pipeline.
    available_tiers = sorted({c.tier for c in contracts})
    filtered = _apply_filters(contracts, tier=tier, position=position, age_max=age_max)
    # Sort by salary desc (None last), then by pts_pg desc.
    filtered.sort(
        key=lambda c: (
            -(c.salary or 0),
            -(c.pts_pg or 0.0),
            c.player_name,
        )
    )

    return FreeAgencyResponse(
        season=season,
        total_count=total_count,
        filtered_count=len(filtered),
        contracts=filtered,
        available_tiers=available_tiers,  # type: ignore[arg-type]
        methodology=methodology,
        is_empty_dataset=False,
        warnings=[],
    )


def top_team_fits_for_player(
    db: Session,
    player_id: int,
    *,
    season: str,
    k: int = 10,
) -> FreeAgentFitsResponse:
    """Return the top-k team-fit rankings for a free agent.

    Wraps `team_fit_service.build_team_fit_report` and translates its
    alternative-team payload into the FA workspace's row shape with
    rationale chips. Any exception from the underlying team-fit pipeline
    (e.g. player has no qualified SeasonStat) is captured as a warning so
    the FA detail panel renders gracefully instead of returning a 5xx.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    player_name = player.full_name if player is not None else "Player {0}".format(player_id)

    contract_row = (
        db.query(PlayerContract)
        .filter(
            PlayerContract.player_id == player_id,
            PlayerContract.season == season,
        )
        .first()
    )
    contract_payload: Optional[ExpiringContract] = None
    if contract_row is not None and player is not None:
        team_row = (
            db.query(Team).filter(Team.id == contract_row.team_id).first()
            if contract_row.team_id is not None
            else None
        )
        stat = _latest_qualified_stats_by_player(db, [player_id]).get(player_id)
        contract_payload = ExpiringContract(
            player_id=player_id,
            player_name=player.full_name,
            team_abbreviation=(team_row.abbreviation if team_row is not None else None),
            team_id=(team_row.id if team_row is not None else None),
            position=player.position,
            age=_age_for_player(player),
            season=contract_row.season,
            salary=contract_row.salary,
            years_remaining=contract_row.years_remaining,
            is_player_option=bool(contract_row.is_player_option),
            is_team_option=bool(contract_row.is_team_option),
            is_non_guaranteed=bool(contract_row.is_non_guaranteed),
            no_trade_clause=bool(contract_row.no_trade_clause),
            contract_type=contract_row.contract_type,
            expires_on=(
                contract_row.expires_on.isoformat()
                if contract_row.expires_on is not None
                else None
            ),
            tier=tier_for_contract(contract_row.salary),
            stat_season=(stat.season if stat is not None else None),
            gp=(stat.gp if stat is not None else None),
            min_pg=(stat.min_pg if stat is not None else None),
            pts_pg=(stat.pts_pg if stat is not None else None),
            reb_pg=(stat.reb_pg if stat is not None else None),
            ast_pg=(stat.ast_pg if stat is not None else None),
            ts_pct=(stat.ts_pct if stat is not None else None),
            usg_pct=(stat.usg_pct if stat is not None else None),
            net_rating=(stat.net_rating if stat is not None else None),
            source=contract_row.source,
        )

    warnings: List[str] = []
    fits: List[TeamFitForPlayer] = []
    try:
        # Team-Fit caps `limit` at 10. Capping `k` here mirrors that.
        report = build_team_fit_report(
            db=db,
            player_id=player_id,
            season=season,
            limit=max(1, min(k, 10)),
        )
    except Exception as exc:  # noqa: BLE001 — defensive: surface as warning.
        warnings.append(
            "Team-fit scoring unavailable for {0}: {1}".format(player_name, str(exc))
        )
    else:
        warnings.extend(report.warnings or [])
        for idx, alt in enumerate(report.alternative_teams or [], start=1):
            chips = _rationale_chips_from_alternative(alt)
            fits.append(
                TeamFitForPlayer(
                    rank=idx,
                    team_abbreviation=alt.team_abbreviation,
                    team_name=alt.team_name,
                    fit_score=alt.fit_score,
                    skill_supply_score=alt.skill_supply_score,
                    roster_need_score=alt.roster_need_score,
                    role_competition_score=alt.role_competition_score,
                    confidence=alt.confidence,
                    summary=alt.summary,
                    rationale_chips=chips,
                )
            )

    return FreeAgentFitsResponse(
        player_id=player_id,
        player_name=player_name,
        season=season,
        contract=contract_payload,
        fits=fits,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _build_methodology() -> FreeAgencyMethodology:
    return FreeAgencyMethodology(
        version=METHODOLOGY_VERSION,
        tier_thresholds_usd=TIER_THRESHOLDS_USD,
        notes=[
            "Expiring = years_remaining <= 1 OR expires_on within the next 12 months.",
            "Tier thresholds are directional cap bands (max / above-MLE / MLE / vet-min / two-way); full CBA fidelity is out of Sprint 78 scope.",
            "Per-player team fits reuse `team_fit_service` (team_fit_v3) — the same scoring used for `/api/team-fit/{player_id}`.",
            "Production stats use the latest qualified SeasonStat (regular-season, non-TOT preferred) attached to each free agent.",
            "Empty `player_contracts` returns an empty workspace; ingestion is tracked separately by FO1.",
        ],
    )


def _apply_filters(
    contracts: List[ExpiringContract],
    *,
    tier: Optional[str],
    position: Optional[str],
    age_max: Optional[int],
) -> List[ExpiringContract]:
    out: List[ExpiringContract] = list(contracts)
    if tier:
        wanted = tier.lower().strip()
        if wanted:
            out = [c for c in out if c.tier == wanted]
    if position:
        wanted_pos = position.lower().strip()
        if wanted_pos:
            out = [
                c
                for c in out
                if c.position is not None
                and wanted_pos in c.position.lower()
            ]
    if age_max is not None:
        out = [c for c in out if c.age is None or c.age <= int(age_max)]
    return out


def _latest_qualified_stats_by_player(
    db: Session, player_ids: List[int]
) -> Dict[int, SeasonStat]:
    """Return the latest non-TOT regular-season SeasonStat per player.

    Falls back to a TOT row only if no team-specific row exists for the
    player. Picks "latest" by descending season-start year.
    """
    if not player_ids:
        return {}

    rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id.in_(player_ids),
            SeasonStat.is_playoff == False,  # noqa: E712 — SQLAlchemy filter
        )
        .all()
    )

    by_player: Dict[int, List[SeasonStat]] = defaultdict(list)
    for row in rows:
        by_player[row.player_id].append(row)

    out: Dict[int, SeasonStat] = {}
    for pid, candidates in by_player.items():
        candidates.sort(
            key=lambda r: (
                _season_start_int(r.season),
                0 if (r.team_abbreviation or "").upper() != "TOT" else -1,
                float(r.min_pg or 0.0),
            ),
            reverse=True,
        )
        out[pid] = candidates[0]
    return out


def _season_start_int(season: Optional[str]) -> int:
    try:
        return int((season or "").split("-", 1)[0])
    except (TypeError, ValueError):
        return 0


def _age_for_player(player: Player) -> Optional[int]:
    if not player or not player.birth_date:
        return None
    raw = str(player.birth_date).strip()
    if not raw:
        return None
    # birth_date is stored as a string with varying NBA-API formats; try a few.
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            parsed = datetime.strptime(raw[: len(fmt) + 4 if fmt.endswith("Z") else len(fmt)], fmt)
            today = date.today()
            return today.year - parsed.year - (
                (today.month, today.day) < (parsed.month, parsed.day)
            )
        except ValueError:
            continue
    return None


def _rationale_chips_from_alternative(alt) -> List[FitRationaleChip]:
    """Translate AlternativeTeamFit drivers into 2–4 short chips."""
    chips: List[FitRationaleChip] = []
    for driver in (alt.value_drivers or [])[:2]:
        chips.append(
            FitRationaleChip(
                label=driver.label,
                detail="Skill supply",
                contribution=getattr(driver, "contribution", None),
            )
        )
    for driver in (alt.role_runway_drivers or [])[:2]:
        # Avoid duplicating a driver label that already appears as a value driver.
        if any(c.label == driver.label for c in chips):
            continue
        chips.append(
            FitRationaleChip(
                label=driver.label,
                detail="Role runway",
                contribution=getattr(driver, "contribution", None),
            )
        )
    if not chips and getattr(alt, "summary", None):
        chips.append(FitRationaleChip(label=alt.summary, detail=None, contribution=None))
    return chips[:4]
