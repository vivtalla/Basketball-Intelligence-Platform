from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import Team
from services.compare_service import build_team_comparison_report
from services.follow_through_service import build_follow_through_games
from services.lineup_impact_service import build_lineup_impact_report
from services.style_feature_service import build_team_style_profile
from services.intel_math import clamp, safe_round


def _team_lookup(db: Session, team_abbr: str) -> Team:
    team = db.query(Team).filter(Team.abbreviation == team_abbr.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(team_abbr))
    return team


def _flag(
    flag_id: str,
    view: str,
    title: str,
    summary: str,
    severity: str,
    confidence: str,
    evidence: List[Dict[str, Any]],
    drilldowns: List[Dict[str, Any]],
    source_metrics: Optional[Dict[str, Any]] = None,
    source_games: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    return {
        "flag_id": flag_id,
        "view": view,
        "title": title,
        "summary": summary,
        "severity": severity,
        "confidence": confidence,
        "evidence": evidence,
        "drilldowns": drilldowns,
        "source_metrics": source_metrics or {},
        "recommended_games": source_games or [],
    }


def _severity_from_gap(value: Optional[float], thresholds: List[float], higher_is_better: bool = True) -> str:
    if value is None:
        return "low"
    gap = float(value)
    if not higher_is_better:
        gap = -gap
    if gap >= thresholds[1]:
        return "high"
    if gap >= thresholds[0]:
        return "medium"
    return "low"


def _confidence_from_sample(sample_size: int, support_score: float) -> str:
    score = 0.35 + min(0.35, sample_size / 40.0) + min(0.30, support_score)
    if score >= 0.75:
        return "high"
    if score >= 0.55:
        return "medium"
    return "low"


def build_matchup_flag_report(
    db: Session,
    team_abbr: str,
    opponent_abbr: str,
    season: str,
    window_games: int = 10,
) -> Dict[str, Any]:
    team = _team_lookup(db, team_abbr)
    opponent = _team_lookup(db, opponent_abbr)

    compare_report = build_team_comparison_report(db=db, team_a=team.abbreviation, team_b=opponent.abbreviation, season=season)
    team_style = build_team_style_profile(db, team.abbreviation, season, window_games=window_games)
    opponent_style = build_team_style_profile(db, opponent.abbreviation, season, window_games=window_games)
    team_lineups = build_lineup_impact_report(db, team.abbreviation, season, opponent_abbr=opponent.abbreviation, window_games=window_games)
    opponent_lineups = build_lineup_impact_report(db, opponent.abbreviation, season, opponent_abbr=team.abbreviation, window_games=window_games)

    compare_rows = {row.stat_id: row for row in compare_report.rows}
    flags: List[Dict[str, Any]] = []

    def add_compare_flag(stat_id: str, flag_id: str, title: str, summary: str, view: str) -> None:
        row = compare_rows.get(stat_id)
        if not row or row.edge == "even":
            return
        team_advantage = row.edge == "team_a"
        if view == "offense" and not team_advantage:
            return
        if view == "defense" and team_advantage:
            return
        gap = None
        if row.team_a_value is not None and row.team_b_value is not None:
            gap = float(row.team_a_value) - float(row.team_b_value)
        if row.stat_id in {"tov_pg", "pace"}:
            thresholds = [0.6, 1.5] if row.stat_id == "tov_pg" else [1.5, 3.0]
        elif row.stat_id in {"reb_pg"}:
            thresholds = [1.0, 2.5]
        elif row.stat_id in {"ts_pct", "efg_pct"}:
            thresholds = [0.015, 0.03]
        else:
            thresholds = [2.0, 4.0]
        severity = _severity_from_gap(gap, thresholds, higher_is_better=row.higher_better)
        sample_size = len(team_lineups["lineup_rows"]) + len(opponent_lineups["lineup_rows"])
        confidence = _confidence_from_sample(sample_size, 0.2)
        if row.stat_id in {"tov_pg", "reb_pg", "pace"}:
            confidence = "medium" if severity != "low" else "low"
        evidence = [
            {"label": row.label, "team_a_value": row.team_a_value, "team_b_value": row.team_b_value, "edge": row.edge},
            {"label": "Compare story", "value": next((story.summary for story in compare_report.stories if story.edge == row.edge), summary)},
            {"label": "Style note", "value": team_style["style_label"] if team_advantage else opponent_style["style_label"]},
        ]
        context = {
            "signal_magnitude": abs(gap or 0.0),
            "source_style_context": team_style,
            "opponent_context": opponent_style,
        }
        follow_through = build_follow_through_games(
            db=db,
            source_type="matchup_flag",
            source_id=flag_id,
            team_abbreviation=team.abbreviation,
            season=season,
            opponent_abbreviation=opponent.abbreviation,
            lineup_key=None,
            player_ids=None,
            window_games=window_games,
            context=context,
        )
        flags.append(
            _flag(
                flag_id=flag_id,
                view=view,
                title=title,
                summary=summary,
                severity=severity,
                confidence=confidence,
                evidence=evidence,
                drilldowns=[
                    {
                        "label": "Open team compare",
                        "url": "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season),
                    },
                    {
                        "label": "Open follow-through games",
                        "url": follow_through["games"][0]["deep_link_url"] if follow_through["games"] else "/games",
                    },
                ],
                source_metrics={
                    "team_style_label": team_style["style_label"],
                    "opponent_style_label": opponent_style["style_label"],
                    "compare_edge": row.edge,
                },
                source_games=follow_through["games"],
            )
        )

    add_compare_flag("shot-quality", "shot_quality_edge", "Shot quality edge", "This matchup tilts toward the team with the cleaner efficiency profile, so the better shot-quality side should lean into its normal scoring shape.", "offense")
    add_compare_flag("turnovers", "turnover_edge", "Possession edge", "This matchup tilts on turnover control, so the side with the cleaner ball security can press the advantage.", "offense")
    add_compare_flag("rebounds", "glass_edge", "Glass edge", "This matchup favors the team that can finish possessions on the glass or extend them on the offensive board.", "offense")
    add_compare_flag("pace", "pace_edge", "Tempo edge", "This matchup has a clear pace direction, which should shape who gets more of the game they want.", "offense")
    add_compare_flag("net_rating", "overall_profile_edge", "Overall profile edge", "The season profile gap is large enough that it should frame the game plan and the expected margin swing.", "offense")

    opponent_lineup_gap = None
    if opponent_lineups["lineup_rows"]:
        best_lineup = opponent_lineups["lineup_rows"][0]
        worst_lineup = opponent_lineups["lineup_rows"][-1]
        if best_lineup["shrunk_net_rating"] is not None and worst_lineup["shrunk_net_rating"] is not None:
            opponent_lineup_gap = float(best_lineup["shrunk_net_rating"]) - float(worst_lineup["shrunk_net_rating"])
            if opponent_lineup_gap >= 8.0:
                follow_through = build_follow_through_games(
                    db=db,
                    source_type="matchup_flag",
                    source_id="bench-dropoff",
                    team_abbreviation=team.abbreviation,
                    season=season,
                    opponent_abbreviation=opponent.abbreviation,
                    window_games=window_games,
                    context={
                        "signal_magnitude": opponent_lineup_gap,
                        "source_style_context": team_style,
                        "opponent_context": opponent_style,
                    },
                )
                flags.append(
                    _flag(
                        flag_id="attack-bench-units",
                        view="offense",
                        title="Attack bench units",
                        summary="Opponent lineups show a meaningful gap from their best to worst units, so the rotation turns are worth targeting.",
                        severity="high" if opponent_lineup_gap >= 12.0 else "medium",
                        confidence="medium" if opponent_lineup_gap < 12.0 else "high",
                        evidence=[
                            {"label": "Opponent best lineup", "value": best_lineup["shrunk_net_rating"]},
                            {"label": "Opponent worst lineup", "value": worst_lineup["shrunk_net_rating"]},
                            {"label": "Gap", "value": safe_round(opponent_lineup_gap, 2)},
                        ],
                        drilldowns=[
                            {"label": "Open opponent compare", "url": "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.abbreviation, opponent.abbreviation, season)},
                            {"label": "Open follow-through games", "url": follow_through["games"][0]["deep_link_url"] if follow_through["games"] else "/games"},
                        ],
                        source_metrics={"opponent_lineup_gap": safe_round(opponent_lineup_gap, 2)},
                        source_games=follow_through["games"],
                    )
                )

    offense_flags = [flag for flag in flags if flag["view"] == "offense"]
    defense_flags = [flag for flag in flags if flag["view"] == "defense"]
    warnings: List[str] = []
    if not flags:
        warnings.append("No matchup exploit flags crossed the current thresholds.")
    if opponent_lineup_gap is None:
        warnings.append("Opponent lineup sample was too small for a bench-dropoff flag.")

    return {
        "team_abbreviation": team.abbreviation,
        "opponent_abbreviation": opponent.abbreviation,
        "season": season,
        "team_style": team_style,
        "opponent_style": opponent_style,
        "compare_snapshot": compare_report,
        "flags": flags,
        "offense_flags": offense_flags,
        "defense_flags": defense_flags,
        "warnings": warnings,
    }
