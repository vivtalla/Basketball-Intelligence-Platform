from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import GamePlayerStat, PlayByPlay, PlayByPlayEvent, PlayerShotChart, ShotLabSnapshot, Team, WarehouseGame
from models.shotchart import (
    ShotCompletenessDomain,
    ShotCompletenessEntity,
    ShotCompletenessReportResponse,
    ShotCompletenessSummary,
    ShotLabSnapshotCreateRequest,
    ShotLabSnapshotPayload,
    ShotLabSnapshotResponse,
)

SHOT_CONTEXT_FIELDS = [
    "game_id",
    "game_date",
    "period",
    "clock",
    "minutes_remaining",
    "seconds_remaining",
    "shot_value",
    "team_id",
    "opponent_team_id",
]
SUPPORTED_COMPLETENESS_SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26"]


def _serialize_dt(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def matches_season_type(game_id: Optional[str], season_type: str) -> bool:
    if not game_id:
        return season_type == "Regular Season"
    if season_type == "Playoffs":
        return str(game_id).startswith("004")
    return not str(game_id).startswith("004")


def summarize_shot_completeness(raw_shots: Sequence[dict]) -> ShotCompletenessSummary:
    total_shots = len(raw_shots)
    if total_shots == 0:
        return ShotCompletenessSummary(
            status="ready",
            total_shots=0,
            contextual_shots=0,
            linked_shots=0,
            exact_linked_shots=0,
            completeness_pct=1.0,
            linked_pct=1.0,
            missing_context_fields=[],
        )

    contextual_shots = 0
    linked_shots = 0
    exact_linked_shots = 0
    missing_context_fields = set()

    for shot in raw_shots:
        has_context = True
        for field in SHOT_CONTEXT_FIELDS:
            if shot.get(field) in (None, ""):
                has_context = False
                missing_context_fields.add(field)
        if has_context:
            contextual_shots += 1
        if shot.get("shot_event_id") and shot.get("event_order_index") is not None:
            linked_shots += 1
            if shot.get("linkage_mode") == "exact":
                exact_linked_shots += 1

    completeness_pct = contextual_shots / float(total_shots)
    linked_pct = linked_shots / float(total_shots)
    if contextual_shots == 0:
        status = "legacy"
    elif contextual_shots < total_shots or linked_shots < total_shots:
        status = "partial"
    else:
        status = "ready"

    return ShotCompletenessSummary(
        status=status,
        total_shots=total_shots,
        contextual_shots=contextual_shots,
        linked_shots=linked_shots,
        exact_linked_shots=exact_linked_shots,
        completeness_pct=round(completeness_pct, 4),
        linked_pct=round(linked_pct, 4),
        missing_context_fields=sorted(missing_context_fields),
    )


def build_shot_completeness_fields(raw_shots: Sequence[dict]) -> dict:
    summary = summarize_shot_completeness(raw_shots)
    return {
        "completeness_status": summary.status,
        "missing_context_fields": summary.missing_context_fields,
        "exact_event_linked_attempts": summary.exact_linked_shots,
        "completeness": summary,
    }


def _data_status_for_row(row: Optional[PlayerShotChart], now: datetime) -> str:
    if row is None:
        return "missing"
    if row.expires_at and row.expires_at > now:
        return "ready"
    return "stale"


def get_team_defense_raw_shots(
    db: Session,
    team_id: int,
    season: str,
    season_type: str,
) -> Tuple[Team, List[dict], str, Optional[str]]:
    team, player_ids, game_ids = get_team_defense_player_ids(db, team_id, season, season_type)
    if not player_ids:
        return team, [], "missing", None

    now = datetime.utcnow()
    chart_rows = (
        db.query(PlayerShotChart)
        .filter(
            PlayerShotChart.season == season,
            PlayerShotChart.season_type == season_type,
            PlayerShotChart.player_id.in_(player_ids),
        )
        .all()
    )
    last_synced_at = max((_serialize_dt(row.fetched_at) for row in chart_rows if row.fetched_at), default=None)

    if not chart_rows:
        return team, [], "missing", last_synced_at

    data_status = "ready"
    if any(_data_status_for_row(row, now) == "stale" for row in chart_rows):
        data_status = "stale"
    if len(chart_rows) < len(player_ids):
        data_status = "stale"

    raw_shots: List[dict] = []
    for row in chart_rows:
        enriched_row_shots = enrich_player_shot_payload(db, row.player_id, row.shots or [])
        for shot in enriched_row_shots:
            if shot.get("game_id") in game_ids:
                raw_shots.append(dict(shot))
    return team, raw_shots, data_status, last_synced_at


def get_team_defense_player_ids(
    db: Session,
    team_id: int,
    season: str,
    season_type: str,
) -> Tuple[Team, List[int], set[str]]:
    team = db.query(Team).filter(Team.id == team_id).first()
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found.")

    games = [
        row
        for row in (
            db.query(WarehouseGame)
            .filter(
                WarehouseGame.season == season,
                (WarehouseGame.home_team_id == team_id) | (WarehouseGame.away_team_id == team_id),
            )
            .all()
        )
        if matches_season_type(row.game_id, season_type)
    ]
    game_ids = {row.game_id for row in games}
    if not game_ids:
        return team, [], set()

    opponent_rows = (
        db.query(GamePlayerStat)
        .filter(
            GamePlayerStat.season == season,
            GamePlayerStat.game_id.in_(list(game_ids)),
            GamePlayerStat.team_id.isnot(None),
            GamePlayerStat.team_id != team_id,
        )
        .all()
    )
    player_ids = sorted({row.player_id for row in opponent_rows if row.player_id is not None})
    return team, player_ids, game_ids


def enrich_player_shot_payload(
    db: Session,
    player_id: int,
    raw_shots: Sequence[dict],
) -> List[dict]:
    game_ids = sorted({shot.get("game_id") for shot in raw_shots if shot.get("game_id")})
    if not game_ids:
        return [dict(shot) for shot in raw_shots]

    team_rows = {
        row.game_id: row
        for row in db.query(GamePlayerStat).filter(
            GamePlayerStat.player_id == player_id,
            GamePlayerStat.game_id.in_(game_ids),
        ).all()
    }
    games = {
        row.game_id: row
        for row in db.query(WarehouseGame).filter(WarehouseGame.game_id.in_(game_ids)).all()
    }
    event_rows = (
        db.query(PlayByPlayEvent)
        .filter(
            PlayByPlayEvent.player_id == player_id,
            PlayByPlayEvent.game_id.in_(game_ids),
            PlayByPlayEvent.action_type.in_(["2pt", "3pt"]),
        )
        .order_by(PlayByPlayEvent.game_id.asc(), PlayByPlayEvent.order_index.asc())
        .all()
    )
    events_by_game: Dict[str, List[PlayByPlayEvent]] = {}
    exact_lookup: Dict[str, Dict[str, PlayByPlayEvent]] = {}
    for row in event_rows:
        events_by_game.setdefault(row.game_id, []).append(row)
        if row.source_event_id:
            exact_lookup.setdefault(row.game_id, {})[str(row.source_event_id)] = row

    used_order_indexes = set()
    enriched: List[dict] = []
    for original in raw_shots:
        shot = dict(original)
        game_id = shot.get("game_id")
        team_row = team_rows.get(game_id)
        game = games.get(game_id)
        if team_row is not None:
            shot["team_id"] = team_row.team_id
            shot["team_abbreviation"] = team_row.team_abbreviation
        if game is not None and team_row is not None and team_row.team_id is not None:
            is_home = game.home_team_id == team_row.team_id
            shot["opponent_team_id"] = game.away_team_id if is_home else game.home_team_id
            shot["opponent_team_abbreviation"] = game.away_team_abbreviation if is_home else game.home_team_abbreviation

        matched_event = None
        linkage_mode = None
        shot_event_id = shot.get("shot_event_id")
        if game_id and shot_event_id:
            matched_event = exact_lookup.get(game_id, {}).get(str(shot_event_id))
            linkage_mode = "exact" if matched_event is not None else None

        if matched_event is None and game_id:
            for candidate in events_by_game.get(game_id, []):
                candidate_key = (candidate.game_id, candidate.order_index)
                if candidate_key in used_order_indexes:
                    continue
                if candidate.period != shot.get("period"):
                    continue
                if (candidate.clock or None) != (shot.get("clock") or None):
                    continue
                expected_type = "3pt" if int(shot.get("shot_value") or 2) == 3 else "2pt"
                if (candidate.action_type or "").lower() != expected_type:
                    continue
                if shot.get("shot_made") is True and (candidate.sub_type or "").lower() != "made":
                    continue
                if shot.get("shot_made") is False and (candidate.sub_type or "").lower() == "made":
                    continue
                matched_event = candidate
                linkage_mode = "derived"
                break

        if matched_event is not None:
            used_order_indexes.add((matched_event.game_id, matched_event.order_index))
            shot["shot_event_id"] = shot.get("shot_event_id") or matched_event.source_event_id
            shot["event_order_index"] = matched_event.order_index
            shot["action_number"] = matched_event.action_number
            shot["home_score"] = matched_event.score_home
            shot["away_score"] = matched_event.score_away
            if game is not None and team_row is not None and team_row.team_id is not None:
                if matched_event.team_id == game.home_team_id:
                    shot["score_margin"] = (matched_event.score_home or 0) - (matched_event.score_away or 0)
                elif matched_event.team_id == game.away_team_id:
                    shot["score_margin"] = (matched_event.score_away or 0) - (matched_event.score_home or 0)
            shot["linkage_mode"] = linkage_mode or "derived"
        else:
            shot["linkage_mode"] = shot.get("linkage_mode") or "none"
        enriched.append(shot)
    return enriched


def get_shot_completeness_report(
    db: Session,
    season: str,
    season_type: str,
) -> ShotCompletenessReportResponse:
    from services.warehouse_service import _eligible_shot_chart_player_ids

    now = datetime.utcnow()
    player_ids = _eligible_shot_chart_player_ids(db, season, season_type)
    player_rows = {
        row.player_id: row
        for row in db.query(PlayerShotChart).filter(
            PlayerShotChart.season == season,
            PlayerShotChart.season_type == season_type,
            PlayerShotChart.player_id.in_(player_ids),
        ).all()
    } if player_ids else {}

    shot_entities: List[ShotCompletenessEntity] = []
    shot_counts = {"ready": 0, "partial": 0, "legacy": 0, "missing": 0}
    for player_id in player_ids:
        row = player_rows.get(player_id)
        if row is None:
            shot_counts["missing"] += 1
            shot_entities.append(
                ShotCompletenessEntity(
                    entity_id=str(player_id),
                    entity_type="player_shot_chart",
                    data_status="missing",
                    completeness_status="missing",
                    total_shots=0,
                    contextual_shots=0,
                    linked_shots=0,
                    exact_linked_shots=0,
                    last_synced_at=None,
                )
            )
            continue
        summary = summarize_shot_completeness(row.shots or [])
        shot_counts[summary.status] += 1
        shot_entities.append(
            ShotCompletenessEntity(
                entity_id=str(player_id),
                entity_type="player_shot_chart",
                data_status=_data_status_for_row(row, now),
                completeness_status=summary.status,
                total_shots=summary.total_shots,
                contextual_shots=summary.contextual_shots,
                linked_shots=summary.linked_shots,
                exact_linked_shots=summary.exact_linked_shots,
                last_synced_at=_serialize_dt(row.fetched_at),
            )
        )

    games = [
        row
        for row in db.query(WarehouseGame).filter(WarehouseGame.season == season).all()
        if matches_season_type(row.game_id, season_type)
    ]
    legacy_game_ids = {
        row[0]
        for row in (
            db.query(PlayByPlay.game_id)
            .filter(PlayByPlay.game_id.in_([game.game_id for game in games]))
            .distinct()
            .all()
        )
    } if games else set()
    event_entities: List[ShotCompletenessEntity] = []
    event_counts = {"ready": 0, "partial": 0, "legacy": 0, "missing": 0}
    for game in games:
        if game.has_parsed_pbp:
            status = "ready"
            data_status = "ready"
        elif game.has_pbp_payload:
            status = "partial"
            data_status = "stale"
        elif game.game_id in legacy_game_ids:
            status = "legacy"
            data_status = "ready"
        else:
            status = "missing"
            data_status = "missing"
        event_counts[status] += 1
        event_entities.append(
            ShotCompletenessEntity(
                entity_id=game.game_id,
                entity_type="game_event_stream",
                data_status=data_status,
                completeness_status=status,
                total_shots=0,
                contextual_shots=0,
                linked_shots=0,
                exact_linked_shots=0,
                last_synced_at=_serialize_dt(game.last_pbp_sync_at),
            )
        )

    shot_domain = ShotCompletenessDomain(
        domain="player_shot_chart",
        eligible_count=len(player_ids),
        ready_count=shot_counts["ready"],
        partial_count=shot_counts["partial"],
        legacy_count=shot_counts["legacy"],
        missing_count=shot_counts["missing"],
        completeness_pct=round(
            (shot_counts["ready"] / float(len(player_ids))) if player_ids else 0.0,
            4,
        ),
    )
    event_domain = ShotCompletenessDomain(
        domain="game_event_stream",
        eligible_count=len(games),
        ready_count=event_counts["ready"],
        partial_count=event_counts["partial"],
        legacy_count=event_counts["legacy"],
        missing_count=event_counts["missing"],
        completeness_pct=round(
            (event_counts["ready"] / float(len(games))) if games else 0.0,
            4,
        ),
    )
    return ShotCompletenessReportResponse(
        season=season,
        season_type=season_type,
        supported_seasons=list(SUPPORTED_COMPLETENESS_SEASONS),
        domains=[shot_domain, event_domain],
        rows=shot_entities + event_entities,
    )


def create_shot_lab_snapshot(
    db: Session,
    payload: ShotLabSnapshotCreateRequest,
) -> ShotLabSnapshotResponse:
    snapshot_id = str(uuid.uuid4())
    stored_payload = ShotLabSnapshotPayload(
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        compare_subject_id=payload.compare_subject_id,
        team_id=payload.team_id,
        season=payload.season,
        season_type=payload.season_type,
        active_view=payload.active_view,
        route_path=payload.route_path,
        filters=payload.filters,
        metadata=payload.metadata or {},
    )
    row = ShotLabSnapshot(
        snapshot_id=snapshot_id,
        snapshot_type="shot_lab",
        subject_kind=payload.subject_type,
        subject_id=str(
            payload.subject_id
            if payload.subject_id is not None
            else payload.team_id
            if payload.team_id is not None
            else payload.compare_subject_id
            if payload.compare_subject_id is not None
            else "shared"
        ),
        season=payload.season,
        season_type=payload.season_type,
        route_path=payload.route_path,
        payload=stored_payload.model_dump(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    share_url = "{0}{1}shot_snapshot_id={2}".format(
        payload.route_path,
        "&" if "?" in payload.route_path else "?",
        snapshot_id,
    )
    return ShotLabSnapshotResponse(
        snapshot_id=snapshot_id,
        share_url=share_url,
        created_at=_serialize_dt(row.created_at),
        payload=stored_payload,
    )


def get_shot_lab_snapshot(db: Session, snapshot_id: str) -> ShotLabSnapshotResponse:
    row = db.query(ShotLabSnapshot).filter(ShotLabSnapshot.snapshot_id == snapshot_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Shot-lab snapshot not found.")
    payload = ShotLabSnapshotPayload(**(row.payload or {}))
    share_url = "{0}{1}shot_snapshot_id={2}".format(
        row.route_path,
        "&" if "?" in row.route_path else "?",
        row.snapshot_id,
    )
    return ShotLabSnapshotResponse(
        snapshot_id=row.snapshot_id,
        share_url=share_url,
        created_at=_serialize_dt(row.created_at),
        payload=payload,
    )
