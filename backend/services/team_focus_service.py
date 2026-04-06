from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import GameTeamStat, Team
from models.team import TeamFactorRow, TeamFocusLever, TeamFocusLeversReport


def _safe_round(value: Optional[float], digits: int = 2) -> Optional[float]:
    if value is None:
        return None
    return round(value, digits)


def _factor_note(label: str, gap: Optional[float], higher_better: bool) -> str:
    if gap is None:
        return "{0} is missing enough data that this lever should stay directional only.".format(label)
    if higher_better:
        if gap >= 0:
            return "{0} is currently running above the league baseline.".format(label)
        return "{0} sits below the league baseline and is the clearer pressure point.".format(label)
    if gap <= 0:
        return "{0} is under the league baseline in a good way.".format(label)
    return "{0} is above the league baseline and is leaking possessions.".format(label)


def _impact_label(factor_id: str, gap: Optional[float], higher_better: bool) -> str:
    if gap is None:
        return "monitor only"
    direction_good = gap >= 0 if higher_better else gap <= 0
    if direction_good:
        if factor_id == "shooting":
            return "protect 2-4 scoring points"
        if factor_id == "turnovers":
            return "protect 1-2 possessions"
        if factor_id == "rebounding":
            return "protect 2-3 second chances"
        return "protect foul-pressure edge"
    if factor_id == "shooting":
        return "swing 2-4 scoring points"
    if factor_id == "turnovers":
        return "recover 1-3 possessions"
    if factor_id == "rebounding":
        return "win 2-3 second chances"
    return "create 2-4 foul-line points"


def _projected_impact(row: TeamFactorRow) -> str:
    gap = abs(row.margin_signal or 0.0)
    if row.margin_signal is None:
        return "Directional only until the local team-game sample gets deeper."
    if row.factor_id == "shooting":
        if gap >= 0.03:
            return "Large enough to swing roughly 3-5 points if the shot diet holds."
        if gap >= 0.015:
            return "Worth roughly 2-3 points if the shot quality moves the right way."
        return "Probably a 1-2 point lever rather than a full identity change."
    if row.factor_id == "turnovers":
        if gap >= 2.0:
            return "Big enough to swing about 3-4 possessions."
        if gap >= 1.0:
            return "Likely worth about 2 possessions."
        return "Closer to a one-possession clean-up lever."
    if row.factor_id == "rebounding":
        if gap >= 3.0:
            return "Big enough to swing 3 or more second-chance opportunities."
        if gap >= 1.5:
            return "Likely worth 2 extra possession finishes."
        return "Mostly a one-board margin lever."
    if gap >= 0.06:
        return "Could be worth 4-6 foul-line points if the pressure is real."
    if gap >= 0.03:
        return "Likely worth 2-4 foul-line points."
    return "More of a light whistle-pressure nudge than a full scheme change."


def _coaching_prompt(row: TeamFactorRow, opponent_abbr: Optional[str]) -> str:
    opponent_phrase = " against {0}".format(opponent_abbr) if opponent_abbr else ""
    if row.factor_id == "shooting":
        return "Open with cleaner rim pressure and catch-and-shoot creation{0} before settling for contested pull-ups.".format(opponent_phrase)
    if row.factor_id == "turnovers":
        return "Simplify the first pass and second-side action{0} so the possession count stays in your favor.".format(opponent_phrase)
    if row.factor_id == "rebounding":
        return "Put an early body on the glass{0} so misses end with one stop instead of a scramble.".format(opponent_phrase)
    return "Force the paint touch first{0} and make the whistle prove it can ignore repeated pressure.".format(opponent_phrase)


def _avg(rows: List[GameTeamStat], attr: str) -> Optional[float]:
    if not rows:
        return None
    values = [float(getattr(row, attr) or 0.0) for row in rows]
    return sum(values) / float(len(values))


def _rate_ts(rows: List[GameTeamStat]) -> Optional[float]:
    pts = sum(float(row.pts or 0.0) for row in rows)
    fga = sum(float(row.fga or 0.0) for row in rows)
    fta = sum(float(row.fta or 0.0) for row in rows)
    denominator = 2.0 * (fga + (0.44 * fta))
    if denominator <= 0:
        return None
    return pts / denominator


def _ft_rate(rows: List[GameTeamStat]) -> Optional[float]:
    fga = sum(float(row.fga or 0.0) for row in rows)
    fta = sum(float(row.fta or 0.0) for row in rows)
    if fga <= 0:
        return None
    return fta / fga


def _build_factor_rows(team_rows: List[GameTeamStat], opponent_rows: List[GameTeamStat], league_rows: List[GameTeamStat]) -> List[TeamFactorRow]:
    factor_values: Dict[str, Tuple[Optional[float], Optional[float], Optional[float], bool, str, int]] = {
        "shooting": (_rate_ts(team_rows), _rate_ts(opponent_rows), _rate_ts(league_rows), True, "Shooting", 3),
        "turnovers": (_avg(team_rows, "tov"), _avg(opponent_rows, "tov"), _avg(league_rows, "tov"), False, "Turnovers", 1),
        "rebounding": (_avg(team_rows, "reb"), _avg(opponent_rows, "reb"), _avg(league_rows, "reb"), True, "Rebounding", 1),
        "free_throws": (_ft_rate(team_rows), _ft_rate(opponent_rows), _ft_rate(league_rows), True, "Free Throw Pressure", 3),
    }

    rows: List[TeamFactorRow] = []
    for factor_id, (team_value, opponent_value, league_reference, higher_better, label, digits) in factor_values.items():
        gap = None
        if team_value is not None and league_reference is not None:
            gap = team_value - league_reference
        rows.append(
            TeamFactorRow(
                factor_id=factor_id,
                label=label,
                team_value=_safe_round(team_value, digits),
                opponent_value=_safe_round(opponent_value, digits),
                league_reference=_safe_round(league_reference, digits),
                margin_signal=_safe_round(gap, digits),
                note=_factor_note(label, gap, higher_better),
            )
        )
    return rows


def _opponent_phrase(
    row: TeamFactorRow,
    opponent_abbr: Optional[str],
) -> Optional[str]:
    if not opponent_abbr or row.team_value is None or row.opponent_value is None:
        return None
    if row.factor_id == "shooting":
        if row.opponent_value >= row.team_value:
            return "{0} has matched or exceeded this scoring lever recently, so forcing harder attempts matters.".format(opponent_abbr)
        return "{0} has not matched this shot-quality level, so keeping the better looks should travel.".format(opponent_abbr)
    if row.factor_id == "turnovers":
        if row.opponent_value <= row.team_value:
            return "{0} has protected the ball better, so simplifying the first pass and second action matters.".format(opponent_abbr)
        return "{0} has been looser with possessions, so pressure can create extra transition chances.".format(opponent_abbr)
    if row.factor_id == "rebounding":
        if row.opponent_value >= row.team_value:
            return "{0} can compete on the glass, so finishing possessions early needs extra emphasis.".format(opponent_abbr)
        return "{0} has been softer on the glass, so second-ball pressure is a real edge.".format(opponent_abbr)
    if row.opponent_value >= row.team_value:
        return "{0} can meet this pressure point, so the lever stays important but less one-sided.".format(opponent_abbr)
    return "{0} is less forceful here, which makes this a cleaner matchup lever.".format(opponent_abbr)


def _build_levers(factor_rows: List[TeamFactorRow], opponent_abbr: Optional[str] = None) -> List[TeamFocusLever]:
    priorities: List[Tuple[float, TeamFactorRow]] = []
    for row in factor_rows:
        if row.margin_signal is None:
            continue
        severity = -row.margin_signal if row.factor_id in {"shooting", "rebounding", "free_throws"} else row.margin_signal
        priorities.append((severity, row))

    priorities.sort(key=lambda item: item[0], reverse=True)

    levers: List[TeamFocusLever] = []
    for _, row in priorities[:3]:
        if row.factor_id == "shooting":
            title = "Sharpen shot quality"
            summary = "Your scoring efficiency is lagging the league baseline, so cleaner rim and catch-and-shoot possessions should be the first lever."
        elif row.factor_id == "turnovers":
            title = "Trim live-ball waste"
            summary = "Turnovers are leaking too many possessions, so simplifying advantage creation should stabilize the offense."
        elif row.factor_id == "rebounding":
            title = "Win the glass earlier"
            summary = "The rebounding base is softening your margin for error, so ending possessions cleanly needs more emphasis."
        else:
            title = "Pressure the rim"
            summary = "The free-throw profile needs more force, so push for more paint touches before settling."

        opponent_phrase = _opponent_phrase(row, opponent_abbr)
        if opponent_phrase:
            summary = "{0} {1}".format(summary, opponent_phrase)

        levers.append(
            TeamFocusLever(
                title=title,
                summary=summary,
                impact_label=_impact_label(row.factor_id, row.margin_signal, row.factor_id != "turnovers"),
                factor_id=row.factor_id,
                rationale="{0}{1}".format(
                    row.note,
                    " {0}".format(opponent_phrase) if opponent_phrase else "",
                ),
                coaching_prompt=_coaching_prompt(row, opponent_abbr),
                projected_impact=_projected_impact(row),
                opponent_context=opponent_phrase,
            )
        )

    return levers


def build_team_focus_levers_report(
    db: Session,
    abbr: str,
    season: str,
    opponent_abbr: Optional[str] = None,
) -> TeamFocusLeversReport:
    team = db.query(Team).filter(Team.abbreviation == abbr.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(abbr))

    team_rows = db.query(GameTeamStat).filter(GameTeamStat.season == season, GameTeamStat.team_id == team.id).all()
    if not team_rows:
        raise HTTPException(status_code=404, detail="No team game stats found for {0} in {1}.".format(abbr.upper(), season))

    if opponent_abbr:
        opponent = db.query(Team).filter(Team.abbreviation == opponent_abbr.upper()).first()
        opponent_rows = (
            db.query(GameTeamStat)
            .filter(GameTeamStat.season == season, GameTeamStat.team_id == opponent.id if opponent else -1)
            .all()
        )
    else:
        game_ids = [row.game_id for row in team_rows]
        opponent_rows = (
            db.query(GameTeamStat)
            .filter(GameTeamStat.season == season, GameTeamStat.game_id.in_(game_ids), GameTeamStat.team_id != team.id)
            .all()
        )
    league_rows = db.query(GameTeamStat).filter(GameTeamStat.season == season).all()

    factor_rows = _build_factor_rows(team_rows, opponent_rows, league_rows)
    return TeamFocusLeversReport(
        team_abbreviation=team.abbreviation,
        team_name=team.name,
        season=season,
        factor_rows=factor_rows,
        focus_levers=_build_levers(factor_rows, opponent_abbr.upper() if opponent_abbr else None),
    )
