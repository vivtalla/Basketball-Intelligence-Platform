from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import PlayByPlayEvent, Team, WarehouseGame
from models.scouting import (
    PlayTypeScoutingReportResponse,
    ScoutingClaim,
    ScoutingClipAnchor,
    ScoutingClipExportRequest,
    ScoutingClipExportResponse,
    ScoutingEvidence,
    ScoutingLaunchContext,
    ScoutingSection,
)
from routers.decision import build_matchup_flags_report, build_play_type_ev_report
from routers.styles import build_team_style_profile
from services.compare_service import build_team_comparison_report
from services.team_focus_service import build_team_focus_levers_report
from services.team_rotation_service import build_team_rotation_report

router = APIRouter()


def _claim_id(section_key: str, index: int) -> str:
    return "{0}-{1}".format(section_key, index)


def _launch_context(team: str, opponent: str, season: str) -> ScoutingLaunchContext:
    return ScoutingLaunchContext(
        pre_read_url="/pre-read?team={0}&opponent={1}&season={2}".format(team, opponent, season),
        scouting_url="/pre-read?team={0}&opponent={1}&season={2}&mode=scouting".format(team, opponent, season),
        compare_url="/compare?mode=teams&team_a={0}&team_b={1}&season={2}&source_type=scouting-report&source_id={0}-{1}&reason=play-type+scouting&return_to={3}".format(
            team,
            opponent,
            season,
            "/pre-read?team={0}&opponent={1}&season={2}&mode=scouting".format(team, opponent, season).replace(" ", "+"),
        ),
        export_url="/api/scouting/clip-export",
    )


def _normalized_tokens(value: str) -> List[str]:
    return [
        token
        for token in "".join(ch.lower() if ch.isalnum() else " " for ch in value).split()
        if len(token) >= 4
    ]


def _claim_tokens(claim: ScoutingClaim) -> Tuple[set[str], set[str], set[str]]:
    title_tokens = set(_normalized_tokens(claim.title))
    summary_tokens = set(_normalized_tokens(claim.summary))
    evidence_tokens = set()
    for item in claim.evidence:
        if item.label:
            evidence_tokens.update(_normalized_tokens(item.label))
        if item.context:
            evidence_tokens.update(_normalized_tokens(item.context))
    return title_tokens, summary_tokens, evidence_tokens


def _score_event_for_claim(claim: ScoutingClaim, event: PlayByPlayEvent) -> int:
    title_lower = claim.title.lower()
    summary_lower = claim.summary.lower()
    family_hint = None
    if "(" in claim.title and ")" in claim.title:
        family_hint = claim.title.split("(")[-1].split(")")[0].strip().lower()
    title_tokens, summary_tokens, evidence_tokens = _claim_tokens(claim)
    action_family = (event.action_family or "").lower()
    description = (event.description or "").lower()
    action_type = (event.action_type or "").lower()
    sub_type = (event.sub_type or "").lower()
    score = 0
    if family_hint and family_hint == action_family:
        score += 8
    elif family_hint and family_hint in action_family:
        score += 6
    elif family_hint and family_hint in description:
        score += 4
    if action_type and action_type in title_lower:
        score += 3
    if sub_type and sub_type in summary_lower:
        score += 2
    score += sum(2 for token in title_tokens if token in description or token in action_family)
    score += sum(1 for token in summary_tokens if token in description)
    score += sum(1 for token in evidence_tokens if token in description or token in action_family)
    if "turnover" in title_lower and action_type == "turnover":
        score += 4
    if "rebound" in title_lower and action_type == "rebound":
        score += 4
    if ("3pt" in title_lower or "three" in title_lower) and action_type == "3pt":
        score += 4
    if ("2pt" in title_lower or "paint" in title_lower or "rim" in title_lower) and action_type == "2pt":
        score += 3
    return score


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
                claim_id="",
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


def _recent_games(db: Session, team_id: int, season: str, opponent_id: Optional[int] = None) -> List[WarehouseGame]:
    query = (
        db.query(WarehouseGame)
        .filter(
            WarehouseGame.season == season,
            WarehouseGame.status == "final",
            ((WarehouseGame.home_team_id == team_id) | (WarehouseGame.away_team_id == team_id)),
        )
        .order_by(WarehouseGame.game_date.desc().nullslast(), WarehouseGame.game_id.desc())
    )
    if opponent_id is not None:
        query = query.filter(
            ((WarehouseGame.home_team_id == opponent_id) & (WarehouseGame.away_team_id == team_id))
            | ((WarehouseGame.away_team_id == opponent_id) & (WarehouseGame.home_team_id == team_id))
        )
    return query.limit(6).all()


def _game_opponent_abbreviation(game: WarehouseGame, team_id: int) -> Optional[str]:
    if game.home_team_id == team_id:
        return game.away_team_abbreviation
    if game.away_team_id == team_id:
        return game.home_team_abbreviation
    return None


def _game_link(
    team: str,
    opponent: str,
    season: str,
    game_id: str,
    claim_id: str,
    clip_anchor_id: str,
    claim_title: str,
    reason: str,
    linkage_quality: str,
    focus_event_id: Optional[str],
    focus_action_number: Optional[int],
) -> str:
    params = [
        "source=scouting-report",
        "source_id={0}".format(claim_id),
        "source_label={0}".format(claim_title.replace(" ", "+")),
        "team={0}".format(team),
        "opponent={0}".format(opponent),
        "season={0}".format(season),
        "claim_id={0}".format(claim_id),
        "clip_anchor_id={0}".format(clip_anchor_id),
        "reason={0}".format(reason.replace(" ", "+")),
        "linkage_quality={0}".format(linkage_quality),
        "focus_window=1",
        "return_to={0}".format(
            "/pre-read?team={0}&opponent={1}&season={2}&mode=scouting".format(team, opponent, season).replace(" ", "+")
        ),
    ]
    if focus_event_id:
        params.append("focus_event_id={0}".format(focus_event_id))
    if focus_action_number is not None:
        params.append("focus_action_number={0}".format(focus_action_number))
    return "/games/{0}?{1}".format(game_id, "&".join(params))


def _derive_clip_anchors(
    db: Session,
    team_id: int,
    team: str,
    opponent: str,
    season: str,
    claims: List[ScoutingClaim],
) -> List[ScoutingClipAnchor]:
    opponent_team = db.query(Team).filter(Team.abbreviation == opponent.upper()).first()
    recent_games = _recent_games(db=db, team_id=team_id, season=season, opponent_id=opponent_team.id if opponent_team else None)
    if not recent_games:
        recent_games = _recent_games(db=db, team_id=team_id, season=season)
    game_ids = [game.game_id for game in recent_games]
    events = (
        db.query(PlayByPlayEvent)
        .filter(PlayByPlayEvent.game_id.in_(game_ids), PlayByPlayEvent.team_id == team_id)
        .order_by(PlayByPlayEvent.game_id.desc(), PlayByPlayEvent.order_index.asc())
        .all()
        if game_ids
        else []
    )
    events_by_game: Dict[str, List[PlayByPlayEvent]] = {}
    for event in events:
        events_by_game.setdefault(event.game_id, []).append(event)

    anchors: List[ScoutingClipAnchor] = []
    for claim in claims:
        scored_games: List[Tuple[int, WarehouseGame, Optional[PlayByPlayEvent]]] = []
        for game in recent_games:
            best_match: Optional[Tuple[int, PlayByPlayEvent]] = None
            for event in events_by_game.get(game.game_id, []):
                score = _score_event_for_claim(claim, event)
                if score < 4:
                    continue
                if best_match is None or score > best_match[0]:
                    best_match = (score, event)
            scored_games.append((best_match[0] if best_match else 0, game, best_match[1] if best_match else None))

        scored_games.sort(key=lambda item: (item[2] is not None, item[0]), reverse=True)
        clip_anchor_ids: List[str] = []
        for anchor_index, (match_score, game, event) in enumerate(scored_games[:2], start=1):
            clip_anchor_id = "{0}-clip-{1}".format(claim.claim_id, anchor_index)
            clip_anchor_ids.append(clip_anchor_id)
            reason = claim.summary[:100]
            anchor_linkage_quality = "derived" if event is not None else "timeline"
            source_context = {
                "source": "scouting-report",
                "source_id": claim.claim_id,
                "source_label": claim.title,
                "reason": reason,
                "claim_id": claim.claim_id,
                "clip_anchor_id": clip_anchor_id,
                "linkage_quality": anchor_linkage_quality,
            }
            anchors.append(
                ScoutingClipAnchor(
                    clip_anchor_id=clip_anchor_id,
                    claim_id=claim.claim_id,
                    game_id=game.game_id,
                    game_date=game.game_date.isoformat() if game.game_date else None,
                    opponent_abbreviation=_game_opponent_abbreviation(game, team_id),
                    event_id=event.id if event else None,
                    source_event_id=event.source_event_id if event else None,
                    action_number=(event.action_number or event.order_index) if event else None,
                    order_index=event.order_index if event else None,
                    period=event.period if event else None,
                    clock=event.clock if event else None,
                    event_type=event.action_type if event else None,
                    action_family=event.action_family if event else None,
                    title=claim.title,
                    reason=reason,
                    evidence_summary=(event.description or claim.evidence[0].label) if event else claim.evidence[0].label,
                    event_description=event.description if event else None,
                    linkage_quality=anchor_linkage_quality,
                    source_context=source_context,
                    deep_link_url=_game_link(
                        team,
                        opponent,
                        season,
                        game.game_id,
                        claim.claim_id,
                        clip_anchor_id,
                        claim.title,
                        reason,
                        anchor_linkage_quality,
                        event.source_event_id if event else None,
                        (event.action_number or event.order_index) if event else None,
                    ),
                )
            )
        claim.clip_anchor_ids = clip_anchor_ids
    return anchors


def build_play_type_scouting_report(
    db: Session,
    team: str,
    opponent: str,
    season: str,
    window: int = 10,
) -> PlayTypeScoutingReportResponse:
    team_row = db.query(Team).filter(Team.abbreviation == team.upper()).first()
    opponent_row = db.query(Team).filter(Team.abbreviation == opponent.upper()).first()
    team_style = build_team_style_profile(db=db, abbr=team, season=season, window=window, opponent_abbr=opponent)
    play_type_report = build_play_type_ev_report(db=db, team_abbr=team, season=season, opponent_abbr=opponent, window_games=window)
    matchup_flags = build_matchup_flags_report(db=db, team_abbr=team, opponent_abbr=opponent, season=season)
    comparison = build_team_comparison_report(db=db, team_a=team, team_b=opponent, season=season)
    rotation = build_team_rotation_report(db=db, team=team_row, season=season) if team_row else None
    focus = build_team_focus_levers_report(db=db, abbr=team, season=season, opponent_abbr=opponent)

    sections: List[ScoutingSection] = []

    action_claims: List[ScoutingClaim] = []
    for index, row in enumerate(play_type_report.action_rows[:3], start=1):
        action_claims.append(
            ScoutingClaim(
                claim_id=_claim_id("actions", index),
                title="{0} ({1})".format(row.label, row.action_family),
                summary=row.note,
                evidence=[
                    ScoutingEvidence(label="Usage share", value=row.usage_share, context=row.label),
                    ScoutingEvidence(label="Points / possession", value=row.points_per_possession, context=row.label),
                    ScoutingEvidence(label="EV score", value=row.ev_score, context=row.label),
                ],
                drilldowns=[
                    "/pre-read?team={0}&opponent={1}&season={2}&mode=scouting".format(team.upper(), opponent.upper(), season)
                ],
            )
        )
    for flag_index, flag in enumerate(play_type_report.overused_flags[:2], start=len(action_claims) + 1):
        action_claims.append(
            ScoutingClaim(
                claim_id=_claim_id("actions", flag_index),
                title=flag.label,
                summary=flag.reason,
                evidence=[
                    ScoutingEvidence(label="Severity", context=flag.severity),
                    ScoutingEvidence(label="Confidence", context=flag.confidence),
                ],
                drilldowns=[
                    "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.upper(), opponent.upper(), season)
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
    for index, flag in enumerate(matchup_flags.flags[:3], start=1):
        coverage_claims.append(
            ScoutingClaim(
                claim_id=_claim_id("coverage", index),
                title=flag.title,
                summary=flag.summary,
                evidence=[
                    ScoutingEvidence(label=item.label, value=item.team_value, context=item.note)
                    for item in flag.evidence[:2]
                ],
                drilldowns=flag.drilldowns,
            )
        )
    for story_index, story in enumerate(comparison.stories[:2], start=len(coverage_claims) + 1):
        coverage_claims.append(
            ScoutingClaim(
                claim_id=_claim_id("coverage", story_index),
                title=story.label,
                summary=story.summary,
                evidence=[
                    ScoutingEvidence(label="Matchup edge", context=story.edge),
                ],
                drilldowns=[
                    "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.upper(), opponent.upper(), season)
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
            claim_id=_claim_id("rotation", 1),
            title="Rotation stability",
            summary=rotation.starter_stability if rotation else "Rotation context is still filling in.",
            evidence=[
                ScoutingEvidence(label="Recent starters", value=float(len(rotation.recent_starters)) if rotation else None, context="starter pool"),
                ScoutingEvidence(label="Minute leaders", value=float(len(rotation.minute_load_leaders)) if rotation else None, context="minute load"),
            ],
            drilldowns=["/teams/{0}?tab=rotation&season={1}".format(team.upper(), season)],
        )
    )
    for row_index, row in enumerate((rotation.rotation_risers if rotation else [])[:2], start=2):
        rotation_claims.append(
            ScoutingClaim(
                claim_id=_claim_id("rotation", row_index),
                title="{0} is gaining trust".format(row.player_name),
                summary="Recent minute growth suggests the rotation is tilting toward this player.",
                evidence=[
                    ScoutingEvidence(label="Season minutes", value=row.avg_minutes_season, context=row.player_name),
                    ScoutingEvidence(label="Recent minutes", value=row.avg_minutes_last_10, context=row.player_name),
                ],
                drilldowns=["/teams/{0}?tab=roster&season={1}".format(team.upper(), season)],
            )
        )
    for lever_index, lever in enumerate(focus.focus_levers[:2], start=len(rotation_claims) + 1):
        rotation_claims.append(
            ScoutingClaim(
                claim_id=_claim_id("rotation", lever_index),
                title=lever.title,
                summary=lever.summary,
                evidence=[
                    ScoutingEvidence(label="Impact", context=lever.impact_label),
                ],
                drilldowns=["/pre-read?team={0}&opponent={1}&season={2}".format(team.upper(), opponent.upper(), season)],
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
                claim_id=_claim_id("shifts", 1),
                title="No major drift",
                summary="The recent style window is staying close to the season baseline.",
                evidence=[
                    ScoutingEvidence(label="Season profile", context=season),
                    ScoutingEvidence(label="Window", value=float(team_style.window_games), context="recent form"),
                ],
                drilldowns=["/insights?tab=trends&team={0}&season={1}".format(team.upper(), season)],
            )
        )
    else:
        for index, claim in enumerate(shift_claims, start=1):
            claim.claim_id = _claim_id("shifts", index)
            claim.drilldowns = ["/insights?tab=trends&team={0}&season={1}".format(team.upper(), season)]
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
    clip_anchors = _derive_clip_anchors(
        db=db,
        team_id=team_row.id if team_row else -1,
        team=team.upper(),
        opponent=opponent.upper(),
        season=season,
        claims=[claim for section in sections for claim in section.claims],
    ) if team_row else []
    if not clip_anchors:
        warnings.append("Clip anchors are limited because recent event-level support is thin.")
    data_status = "limited" if not sections else "partial" if warnings else "ready"

    print_meta = {
        "report_title": "{0} vs {1}".format(team.upper(), opponent.upper()),
        "season": season,
        "format": "browser-print",
        "generated_from": "Sprint 40 event-centered replay workflow",
    }
    return PlayTypeScoutingReportResponse(
        team_abbreviation=team.upper(),
        opponent_abbreviation=opponent.upper(),
        season=season,
        data_status=data_status,
        sections=sections,
        clip_anchors=clip_anchors,
        launch_context=_launch_context(team.upper(), opponent.upper(), season),
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


@router.post("/clip-export", response_model=ScoutingClipExportResponse)
def export_scouting_clip_list(
    payload: ScoutingClipExportRequest,
    db: Session = Depends(get_db),
):
    report = build_play_type_scouting_report(
        db=db,
        team=payload.team,
        opponent=payload.opponent,
        season=payload.season,
        window=10,
    )
    clip_anchors = report.clip_anchors
    if payload.claim_ids:
        clip_anchors = [anchor for anchor in clip_anchors if anchor.claim_id in payload.claim_ids]
    if payload.clip_anchor_ids:
        clip_anchors = [anchor for anchor in clip_anchors if anchor.clip_anchor_id in payload.clip_anchor_ids]
    warnings = list(report.warnings)
    if not clip_anchors:
        warnings.append("No clip anchors matched the requested filters.")
    return ScoutingClipExportResponse(
        team_abbreviation=report.team_abbreviation,
        opponent_abbreviation=report.opponent_abbreviation,
        season=report.season,
        data_status=report.data_status,
        export_title="{0} vs {1} clip list".format(report.team_abbreviation, report.opponent_abbreviation),
        clip_count=len(clip_anchors),
        clip_anchors=clip_anchors,
        warnings=warnings,
    )
