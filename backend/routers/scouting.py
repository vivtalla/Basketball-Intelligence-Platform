from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from models.scouting import PlayTypeScoutingReportResponse, ScoutingClaim, ScoutingEvidence, ScoutingSection
from routers.decision import build_matchup_flags_report, build_play_type_ev_report
from routers.styles import build_team_style_profile
from services.compare_service import build_team_comparison_report
from services.team_focus_service import build_team_focus_levers_report
from services.team_rotation_service import build_team_rotation_report

router = APIRouter()


def _style_claims(profile) -> List[ScoutingClaim]:
    claims: List[ScoutingClaim] = []
    drift_rows = sorted(
        [row for row in profile.recent_drift if row.recent_delta is not None],
        key=lambda row: abs(row.recent_delta or 0.0),
        reverse=True,
    )
    if drift_rows:
        top = drift_rows[0]
        claims.append(
            ScoutingClaim(
                title="{0} is the clearest recent shift".format(top.label),
                summary=top.note,
                evidence=[
                    ScoutingEvidence(label="Season value", value=top.team_value, context=top.label),
                    ScoutingEvidence(label="Recent value", value=top.recent_value, context=top.label),
                    ScoutingEvidence(label="Recent delta", value=top.recent_delta, context=top.label),
                ],
            )
        )
    return claims


def build_play_type_scouting_report(
    db: Session,
    team: str,
    opponent: str,
    season: str,
    window: int = 10,
) -> PlayTypeScoutingReportResponse:
    team_style = build_team_style_profile(db=db, abbr=team, season=season, window=window, opponent_abbr=opponent)
    play_type_report = build_play_type_ev_report(db=db, team_abbr=team, season=season, opponent_abbr=opponent, window_games=window)
    matchup_flags = build_matchup_flags_report(db=db, team_abbr=team, opponent_abbr=opponent, season=season)
    comparison = build_team_comparison_report(db=db, team_a=team, team_b=opponent, season=season)
    rotation = build_team_rotation_report(db=db, abbr=team, season=season)
    focus = build_team_focus_levers_report(db=db, abbr=team, season=season)

    sections: List[ScoutingSection] = []

    action_claims: List[ScoutingClaim] = []
    for row in play_type_report.action_rows[:3]:
        action_claims.append(
            ScoutingClaim(
                title="{0} ({1})".format(row.label, row.action_family),
                summary=row.note,
                evidence=[
                    ScoutingEvidence(label="Usage share", value=row.usage_share, context=row.label),
                    ScoutingEvidence(label="Points / possession", value=row.points_per_possession, context=row.label),
                    ScoutingEvidence(label="EV score", value=row.ev_score, context=row.label),
                ],
            )
        )
    for flag in play_type_report.overused_flags[:2]:
        action_claims.append(
            ScoutingClaim(
                title=flag.label,
                summary=flag.reason,
                evidence=[
                    ScoutingEvidence(label="Severity", context=flag.severity),
                    ScoutingEvidence(label="Confidence", context=flag.confidence),
                ],
            )
        )
    if action_claims:
        sections.append(
            ScoutingSection(
                eyebrow="Actions",
                title="Top actions to press or trim",
                claims=action_claims,
            )
        )

    coverage_claims: List[ScoutingClaim] = []
    for flag in matchup_flags.flags[:3]:
        coverage_claims.append(
            ScoutingClaim(
                title=flag.title,
                summary=flag.summary,
                evidence=[
                    ScoutingEvidence(label=item.label, value=item.team_value, context=item.note)
                    for item in flag.evidence[:2]
                ],
            )
        )
    for story in comparison.stories[:2]:
        coverage_claims.append(
            ScoutingClaim(
                title=story.label,
                summary=story.summary,
                evidence=[
                    ScoutingEvidence(label="Matchup edge", context=story.edge),
                ],
            )
        )
    if coverage_claims:
        sections.append(
            ScoutingSection(
                eyebrow="Coverage",
                title="Weak coverages and pressure points",
                claims=coverage_claims,
            )
        )

    rotation_claims: List[ScoutingClaim] = []
    rotation_claims.append(
        ScoutingClaim(
            title="Rotation stability",
            summary=rotation.starter_stability,
            evidence=[
                ScoutingEvidence(label="Recent starters", value=float(len(rotation.recent_starters)), context="starter pool"),
                ScoutingEvidence(label="Minute leaders", value=float(len(rotation.minute_load_leaders)), context="minute load"),
            ],
        )
    )
    for row in rotation.rotation_risers[:2]:
        rotation_claims.append(
            ScoutingClaim(
                title="{0} is gaining trust".format(row.player_name),
                summary="Recent minute growth suggests the rotation is tilting toward this player.",
                evidence=[
                    ScoutingEvidence(label="Season minutes", value=row.avg_minutes_season, context=row.player_name),
                    ScoutingEvidence(label="Recent minutes", value=row.avg_minutes_last_10, context=row.player_name),
                ],
            )
        )
    for lever in focus.focus_levers[:2]:
        rotation_claims.append(
            ScoutingClaim(
                title=lever.title,
                summary=lever.summary,
                evidence=[
                    ScoutingEvidence(label="Impact", context=lever.impact_label),
                ],
            )
        )
    sections.append(
        ScoutingSection(
            eyebrow="Rotation",
            title="Preferred rotation patterns",
            claims=rotation_claims,
        )
    )

    shift_claims: List[ScoutingClaim] = _style_claims(team_style)
    if not shift_claims:
        shift_claims.append(
            ScoutingClaim(
                title="No major drift",
                summary="The recent style window is staying close to the season baseline.",
                evidence=[
                    ScoutingEvidence(label="Season profile", context=season),
                    ScoutingEvidence(label="Window", value=float(team_style.window_games), context="recent form"),
                ],
            )
        )
    sections.append(
        ScoutingSection(
            eyebrow="Shifts",
            title="Recent shifts to watch",
            claims=shift_claims,
        )
    )

    warnings: List[str] = []
    warnings.extend(team_style.warnings[:2])
    warnings.extend(play_type_report.warnings[:2])
    warnings.extend(matchup_flags.warnings[:2])
    if not sections:
        warnings.append("The scouting report is limited by sparse season data.")

    print_meta = {
        "report_title": "{0} vs {1}".format(team.upper(), opponent.upper()),
        "season": season,
        "format": "browser-print",
        "generated_from": "Sprint 25 decision/support stack",
    }
    return PlayTypeScoutingReportResponse(
        team_abbreviation=team.upper(),
        opponent_abbreviation=opponent.upper(),
        season=season,
        sections=sections,
        print_meta=print_meta,
        warnings=warnings,
    )


@router.get("/play-types", response_model=PlayTypeScoutingReportResponse)
def get_play_type_scouting_report(
    team: str = Query(...),
    opponent: str = Query(...),
    season: str = Query("2025-26"),
    window: int = Query(10, ge=3, le=20),
    db: Session = Depends(get_db),
):
    return build_play_type_scouting_report(
        db=db,
        team=team,
        opponent=opponent,
        season=season,
        window=window,
    )
