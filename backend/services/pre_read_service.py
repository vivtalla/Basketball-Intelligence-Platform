from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from models.pre_read import PreReadAdjustment, PreReadDeckResponse, PreReadSlide
from services.compare_service import build_team_comparison_report
from services.team_availability_service import build_team_availability
from services.team_focus_service import build_team_focus_levers_report


def build_pre_read_deck(db: Session, team: str, opponent: str, season: str) -> PreReadDeckResponse:
    focus_report = build_team_focus_levers_report(db=db, abbr=team, season=season)
    comparison = build_team_comparison_report(db=db, team_a=team, team_b=opponent, season=season)
    team_availability = build_team_availability(db=db, abbr=team, season=season)
    opponent_availability = build_team_availability(db=db, abbr=opponent, season=season)

    matchup_advantages = [
        story.summary
        for story in comparison.stories
        if story.edge == "team_a"
    ][:2]
    if len(matchup_advantages) < 2:
        matchup_advantages.extend([
            story.summary
            for story in comparison.stories
            if story.edge == "even"
        ][: 2 - len(matchup_advantages)])

    adjustments: List[PreReadAdjustment] = []
    for lever in focus_report.focus_levers[:3]:
        adjustments.append(
            PreReadAdjustment(
                label=lever.title,
                recommendation=lever.summary,
            )
        )

    slides = [
        PreReadSlide(
            eyebrow="Tonight",
            title="{0} vs {1}".format(team.upper(), opponent.upper()),
            bullets=[
                "Season frame: {0}".format(season),
                "{0}: {1}".format(team.upper(), team_availability.summary),
                "{0}: {1}".format(opponent.upper(), opponent_availability.summary),
                "Primary coach prompt: use the focus levers to decide what gets emphasized first.",
                "Use the matchup edge slide to decide where the first few possessions should tilt.",
            ],
        ),
        PreReadSlide(
            eyebrow="Focus Levers",
            title="Tonight's top three levers",
            bullets=[
                "{0}: {1}".format(lever.title, lever.summary)
                for lever in focus_report.focus_levers[:3]
            ],
        ),
        PreReadSlide(
            eyebrow="Matchup",
            title="Best edges to press",
            bullets=matchup_advantages or ["No clear matchup edge surfaced from the current team profile data."],
        ),
        PreReadSlide(
            eyebrow="Adjustments",
            title="One-line tactical adjustments",
            bullets=[
                "{0}: {1}".format(adjustment.label, adjustment.recommendation)
                for adjustment in adjustments
            ] or ["No tactical adjustments generated."],
        ),
    ]

    return PreReadDeckResponse(
        season=season,
        team_abbreviation=team.upper(),
        opponent_abbreviation=opponent.upper(),
        focus_levers=focus_report.focus_levers,
        matchup_advantages=matchup_advantages,
        adjustments=adjustments,
        team_availability=team_availability,
        opponent_availability=opponent_availability,
        slides=slides,
    )
