from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.pre_read import (
    PreReadAdjustment,
    PreReadContext,
    PreReadDeckResponse,
    PreReadPrepContext,
    PreReadSlide,
    PreReadSnapshotRef,
    WorkflowLaunchLinks,
)
from services.compare_service import build_team_comparison_report
from services.team_availability_service import build_team_availability
from services.team_focus_service import build_team_focus_levers_report
from services.team_prep_service import build_team_prep_queue


def _build_launch_links(team: str, opponent: str, season: str) -> WorkflowLaunchLinks:
    return WorkflowLaunchLinks(
        pre_read_url="/pre-read?team={0}&opponent={1}&season={2}".format(team, opponent, season),
        scouting_url="/pre-read?team={0}&opponent={1}&season={2}&mode=scouting".format(team, opponent, season),
        compare_url="/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team, opponent, season),
        prep_url="/teams/{0}?tab=prep&season={1}".format(team, season),
        follow_through_url="/teams/{0}?tab=decision&season={1}&opponent={2}".format(team, season, opponent),
        game_review_url="/games?team={0}&season={1}&opponent={2}".format(team, season, opponent),
    )


def build_pre_read_deck(
    db: Session,
    team: str,
    opponent: str,
    season: str,
    snapshot_ref: PreReadSnapshotRef | None = None,
    source_context: PreReadContext | None = None,
) -> PreReadDeckResponse:
    warnings: List[str] = []

    try:
        focus_report = build_team_focus_levers_report(db=db, abbr=team, season=season, opponent_abbr=opponent)
    except HTTPException:
        focus_report = None
        warnings.append("Focus levers are directional only until more team-game stats are synced.")

    try:
        comparison = build_team_comparison_report(db=db, team_a=team, team_b=opponent, season=season)
    except HTTPException:
        comparison = None
        warnings.append("Matchup edges are limited because comparison coverage is still sparse.")

    team_availability = build_team_availability(db=db, abbr=team, season=season)
    opponent_availability = build_team_availability(db=db, abbr=opponent, season=season)

    matchup_advantages = [
        story.summary
        for story in (comparison.stories if comparison else [])
        if story.edge == "team_a"
    ][:2]
    if len(matchup_advantages) < 2:
        matchup_advantages.extend([
            story.summary
            for story in (comparison.stories if comparison else [])
            if story.edge == "even"
        ][: 2 - len(matchup_advantages)])

    adjustments: List[PreReadAdjustment] = []
    for lever in (focus_report.focus_levers if focus_report else [])[:3]:
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
                for lever in (focus_report.focus_levers if focus_report else [])[:3]
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

    prep_item = None
    prep_context = None
    try:
        prep_queue = build_team_prep_queue(db=db, abbr=team, season=season, days=14)
        prep_item = next(
            (
                item
                for item in prep_queue.items
                if item.opponent_abbreviation == opponent.upper()
            ),
            None,
        )
    except HTTPException:
        prep_item = None
    if prep_item is not None:
        prep_context = PreReadPrepContext(
            prep_item=prep_item,
            urgency=prep_item.prep_urgency,
            headline=prep_item.prep_headline,
        )

    if focus_report is None and comparison is None:
        data_status = "limited"
    elif warnings:
        data_status = "partial"
    else:
        data_status = "ready"

    return PreReadDeckResponse(
        season=season,
        team_abbreviation=team.upper(),
        opponent_abbreviation=opponent.upper(),
        data_status=data_status,
        canonical_source="warehouse-plus-derived",
        generated_at=datetime.utcnow().isoformat(),
        focus_levers=focus_report.focus_levers if focus_report else [],
        matchup_advantages=matchup_advantages,
        adjustments=adjustments,
        team_availability=team_availability,
        opponent_availability=opponent_availability,
        slides=slides,
        launch_links=_build_launch_links(team.upper(), opponent.upper(), season),
        prep_context=prep_context,
        snapshot=snapshot_ref,
        warnings=warnings,
    )
