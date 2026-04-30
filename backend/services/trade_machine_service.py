"""Trade rule engine — Sprint 78 FO1.

`validate_trade(db, packages, season)` runs every per-team package through
the canonical NBA salary-matching rule (±125%) plus a set of soft-flag rules
for tax line, first apron, second apron, BYC, and the traded-player
exception. Soft flags do not invalidate the trade — they show up as
``TradeWarning`` rows so the front-of-house can render them inline.

The numbers are the published 2025-26 thresholds:

    - Salary cap:        ~$140.6M
    - Luxury tax line:   ~$170.8M
    - First apron:       ~$178.1M
    - Second apron:      ~$188.9M

These constants live here (not in `config.py`) because they are league rules,
not deployment knobs. They will tick year-over-year — when they do, update
this file alongside the seed CSV.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import Player, PlayerContract, Team
from models.trade import (
    TeamSalaryLine,
    TradePackage,
    TradePlayerEntry,
    TradeValidationResult,
    TradeWarning,
)

logger = logging.getLogger(__name__)

# 2025-26 published thresholds (USD).
CAP_2025_26 = 140_600_000
TAX_LINE_2025_26 = 170_800_000
FIRST_APRON_2025_26 = 178_100_000
SECOND_APRON_2025_26 = 188_900_000

# Salary-match rule per the 2023 CBA: outgoing must be within 125% of
# incoming (with the $250k cushion). Below this is always legal.
SALARY_MATCH_LOWER_RATIO = 1.0 / 1.25       # 0.80
SALARY_MATCH_UPPER_RATIO = 1.25
SALARY_MATCH_CUSHION = 250_000              # absolute small-trade cushion


def _player_entry(
    player: Player,
    contract: Optional[PlayerContract],
) -> TradePlayerEntry:
    return TradePlayerEntry(
        player_id=player.id,
        player_name=player.full_name,
        salary=int(contract.salary) if contract and contract.salary is not None else 0,
        contract_type=contract.contract_type if contract else None,
        years_remaining=contract.years_remaining if contract else None,
        is_player_option=bool(contract.is_player_option) if contract else False,
        is_team_option=bool(contract.is_team_option) if contract else False,
    )


def _load_player_entries(
    db: Session,
    player_ids: List[int],
    season: str,
) -> Dict[int, TradePlayerEntry]:
    if not player_ids:
        return {}
    players = (
        db.query(Player)
        .filter(Player.id.in_(player_ids))
        .all()
    )
    contracts = (
        db.query(PlayerContract)
        .filter(
            PlayerContract.player_id.in_(player_ids),
            PlayerContract.season == season,
        )
        .all()
    )
    contract_by_pid = dict((c.player_id, c) for c in contracts)
    return dict(
        (p.id, _player_entry(p, contract_by_pid.get(p.id)))
        for p in players
    )


def _team_total_salary(db: Session, team_abbr: str, season: str) -> int:
    team = db.query(Team).filter(Team.abbreviation == team_abbr).first()
    if not team:
        return 0
    rows = (
        db.query(PlayerContract)
        .filter(
            PlayerContract.team_id == team.id,
            PlayerContract.season == season,
        )
        .all()
    )
    return int(sum((r.salary or 0) for r in rows))


def _salary_match_warning(
    team_abbr: str,
    outgoing: int,
    incoming: int,
) -> Optional[TradeWarning]:
    """Apply the ±125% salary-match rule. The rule only runs over-the-cap;
    we always run it conservatively here since real cap-room status is
    out of scope. Returns a warning row when out-of-band, ``None`` if
    the trade matches.
    """
    if outgoing == 0 and incoming == 0:
        return None

    # Symmetric small-trade cushion: if either side is within $250k, allow.
    if abs(outgoing - incoming) <= SALARY_MATCH_CUSHION:
        return None

    incoming_floor = int(outgoing * SALARY_MATCH_LOWER_RATIO) - SALARY_MATCH_CUSHION
    incoming_ceiling = int(outgoing * SALARY_MATCH_UPPER_RATIO) + SALARY_MATCH_CUSHION

    if incoming_floor <= incoming <= incoming_ceiling:
        return None

    direction = "too high" if incoming > incoming_ceiling else "too low"
    return TradeWarning(
        team_abbr=team_abbr,
        rule="salary_match",
        severity="hard_block",
        message=(
            "Incoming salary $%s is %s vs outgoing $%s (allowed $%s–$%s)."
            % (
                "{:,}".format(incoming),
                direction,
                "{:,}".format(outgoing),
                "{:,}".format(max(0, incoming_floor)),
                "{:,}".format(max(0, incoming_ceiling)),
            )
        ),
        detail={
            "outgoing": outgoing,
            "incoming": incoming,
            "lower_ratio": SALARY_MATCH_LOWER_RATIO,
            "upper_ratio": SALARY_MATCH_UPPER_RATIO,
            "cushion": SALARY_MATCH_CUSHION,
        },
    )


def _apron_warnings(
    team_abbr: str,
    pre_total: int,
    post_total: int,
) -> List[TradeWarning]:
    warnings: List[TradeWarning] = []

    def _maybe(rule: str, threshold: int, label: str, severity: str) -> None:
        crossed = pre_total <= threshold < post_total
        already_over = pre_total > threshold
        if crossed:
            warnings.append(TradeWarning(
                team_abbr=team_abbr,
                rule=rule,
                severity=severity,
                message="%s pushes payroll over the %s ($%s)." % (
                    team_abbr, label, "{:,}".format(threshold)
                ),
                detail={"pre": pre_total, "post": post_total, "threshold": threshold},
            ))
        elif already_over and post_total > threshold:
            warnings.append(TradeWarning(
                team_abbr=team_abbr,
                rule=rule,
                severity="info",
                message="%s remains over the %s ($%s)." % (
                    team_abbr, label, "{:,}".format(threshold)
                ),
                detail={"pre": pre_total, "post": post_total, "threshold": threshold},
            ))

    _maybe("tax_line", TAX_LINE_2025_26, "luxury-tax line", "warning")
    _maybe("first_apron", FIRST_APRON_2025_26, "first apron", "warning")
    _maybe("second_apron", SECOND_APRON_2025_26, "second apron", "warning")
    return warnings


def _byc_warnings(
    team_abbr: str,
    incoming: List[TradePlayerEntry],
) -> List[TradeWarning]:
    """BYC (Bird Year Control) shorthand: any incoming player on a rookie-
    scale extension or a recently-signed long deal *can* trigger BYC
    valuation. Without a sign-date feed we surface this as ``info`` only.
    """
    flagged = [
        p for p in incoming
        if (p.contract_type or "").lower() in {"rookie", "supermax"}
        and (p.years_remaining or 0) >= 3
    ]
    if not flagged:
        return []
    names = ", ".join(p.player_name for p in flagged[:3])
    return [TradeWarning(
        team_abbr=team_abbr,
        rule="byc",
        severity="info",
        message="Incoming long-term deal(s) may trigger Bird-rights / BYC handling: %s." % names,
        detail={"player_ids": [p.player_id for p in flagged]},
    )]


def _tpe_warnings(
    team_abbr: str,
    outgoing: int,
    incoming: int,
) -> List[TradeWarning]:
    """Traded-Player Exception heuristic. If outgoing exceeds incoming by
    more than $1M we flag the gap as TPE-eligible — actual TPE creation
    requires the trade to be done as a non-simultaneous swap.
    """
    delta = outgoing - incoming
    if delta <= 1_000_000:
        return []
    return [TradeWarning(
        team_abbr=team_abbr,
        rule="traded_player_exception",
        severity="info",
        message=(
            "%s could create a $%s Trade-Player Exception by sending out more salary than it absorbs."
            % (team_abbr, "{:,}".format(delta))
        ),
        detail={"delta": delta},
    )]


def validate_trade(
    db: Session,
    packages: List[TradePackage],
    season: str = "2025-26",
) -> TradeValidationResult:
    if len(packages) < 2:
        return TradeValidationResult(
            valid=False,
            team_count=len(packages),
            warnings=[TradeWarning(
                team_abbr="",
                rule="structure",
                severity="hard_block",
                message="A trade requires at least 2 teams.",
            )],
        )
    if len(packages) > 4:
        return TradeValidationResult(
            valid=False,
            team_count=len(packages),
            warnings=[TradeWarning(
                team_abbr="",
                rule="structure",
                severity="hard_block",
                message="The Trade Machine supports up to 4 teams per deal.",
            )],
        )

    # Stage 1: collect every player_id touched by any side, fetch one batch.
    all_pids: List[int] = []
    for pkg in packages:
        all_pids.extend(pkg.outgoing_player_ids or [])
        all_pids.extend(pkg.incoming_player_ids or [])
    entries = _load_player_entries(db, sorted(set(all_pids)), season)

    # Stage 2: for each team build a salary line + collect warnings.
    team_lines: List[TeamSalaryLine] = []
    warnings: List[TradeWarning] = []

    for pkg in packages:
        outgoing_entries = [entries[p] for p in (pkg.outgoing_player_ids or []) if p in entries]
        incoming_entries = [entries[p] for p in (pkg.incoming_player_ids or []) if p in entries]
        outgoing_salary = int(sum(e.salary for e in outgoing_entries))
        incoming_salary = int(sum(e.salary for e in incoming_entries))

        ratio: Optional[float] = None
        if incoming_salary:
            ratio = round(outgoing_salary / incoming_salary, 3)

        team_lines.append(TeamSalaryLine(
            team_abbr=pkg.team_abbr,
            outgoing_salary=outgoing_salary,
            incoming_salary=incoming_salary,
            delta=incoming_salary - outgoing_salary,
            salary_match_ratio=ratio,
            outgoing_players=outgoing_entries,
            incoming_players=incoming_entries,
        ))

        match_warning = _salary_match_warning(pkg.team_abbr, outgoing_salary, incoming_salary)
        if match_warning is not None:
            warnings.append(match_warning)

        pre_total = _team_total_salary(db, pkg.team_abbr, season)
        post_total = pre_total - outgoing_salary + incoming_salary
        warnings.extend(_apron_warnings(pkg.team_abbr, pre_total, post_total))
        warnings.extend(_byc_warnings(pkg.team_abbr, incoming_entries))
        warnings.extend(_tpe_warnings(pkg.team_abbr, outgoing_salary, incoming_salary))

    has_hard_block = any(w.severity == "hard_block" for w in warnings)
    summary: Optional[str] = None
    if has_hard_block:
        summary = "Trade blocked by salary-matching rule(s)."
    elif warnings:
        summary = "Trade is legal — see flagged warnings."
    else:
        summary = "Trade is legal."

    return TradeValidationResult(
        valid=not has_hard_block,
        team_count=len(packages),
        team_salary_lines=team_lines,
        warnings=warnings,
        summary=summary,
    )
