from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import PreReadSnapshot
from models.pre_read import (
    PreReadContext,
    PreReadDeckResponse,
    PreReadPacketSelection,
    PreReadPacketSummary,
    PreReadScoutingPacket,
    PreReadScoutingPacketClaim,
    PreReadSnapshotCreateRequest,
    PreReadSnapshotListResponse,
    PreReadSnapshotRef,
    PreReadSnapshotResponse,
    PreReadSnapshotSummary,
    PreReadSnapshotUpdateRequest,
)
from routers.scouting import build_play_type_scouting_report
from services.pre_read_service import build_pre_read_deck


def _share_url(snapshot_id: str) -> str:
    return "/pre-read?snapshot_id={0}".format(snapshot_id)


def _scouting_url(team: str, opponent: str, season: str) -> str:
    return "/pre-read?team={0}&opponent={1}&season={2}&mode=scouting".format(team, opponent, season)


def _deck_from_payload(payload: dict) -> PreReadDeckResponse:
    return PreReadDeckResponse(**payload)


def _normalized_title(title: Optional[str]) -> Optional[str]:
    if title is None:
        return None
    value = title.strip()
    return value or None


def _normalized_note(note: Optional[str]) -> Optional[str]:
    if note is None:
        return None
    value = note.strip()
    return value or None


def _packet_summary(packet: Optional[PreReadScoutingPacket]) -> Optional[PreReadPacketSummary]:
    if packet is None or not packet.claims:
        return None
    return PreReadPacketSummary(
        claim_count=len(packet.claims),
        clip_count=sum(len(claim.clip_anchors) for claim in packet.claims),
        claim_titles=[claim.title for claim in packet.claims[:3]],
    )


def _default_title(
    team: str,
    opponent: str,
    season: str,
    game_date: Optional[str] = None,
    created_at: Optional[str] = None,
) -> str:
    label = game_date or (created_at[:10] if created_at else season)
    return "{0} vs {1} Packet - {2}".format(team.upper(), opponent.upper(), label)


def _snapshot_ref(
    snapshot_id: str,
    created_at: str,
    title: Optional[str],
    note: Optional[str],
    packet: Optional[PreReadScoutingPacket],
) -> PreReadSnapshotRef:
    return PreReadSnapshotRef(
        snapshot_id=snapshot_id,
        share_url=_share_url(snapshot_id),
        created_at=created_at,
        title=title,
        note=note,
        packet_summary=_packet_summary(packet),
    )


def _build_scouting_packet(
    db: Session,
    team: str,
    opponent: str,
    season: str,
    selection: Optional[PreReadPacketSelection],
) -> Optional[PreReadScoutingPacket]:
    if selection is None or not selection.claim_ids:
        return None

    report = build_play_type_scouting_report(
        db=db,
        team=team,
        opponent=opponent,
        season=season,
        window=10,
    )
    claims_by_id = {
        claim.claim_id: claim
        for section in report.sections
        for claim in section.claims
    }
    anchors_by_claim = {}
    for anchor in report.clip_anchors:
        anchors_by_claim.setdefault(anchor.claim_id, []).append(anchor)

    selected_anchor_ids = set(selection.clip_anchor_ids)
    packet_claims = []
    packet_anchor_ids: list[str] = []

    for claim_id in selection.claim_ids[:3]:
        claim = claims_by_id.get(claim_id)
        if claim is None:
            continue
        ranked_anchors = anchors_by_claim.get(claim_id, [])
        chosen = [anchor for anchor in ranked_anchors if anchor.clip_anchor_id in selected_anchor_ids][:2]
        if len(chosen) < 2:
            existing_ids = {anchor.clip_anchor_id for anchor in chosen}
            for anchor in ranked_anchors:
                if anchor.clip_anchor_id in existing_ids:
                    continue
                chosen.append(anchor)
                existing_ids.add(anchor.clip_anchor_id)
                if len(chosen) == 2:
                    break
        packet_anchor_ids.extend(anchor.clip_anchor_id for anchor in chosen)
        packet_claims.append(
            PreReadScoutingPacketClaim(
                claim_id=claim.claim_id,
                title=claim.title,
                summary=claim.summary,
                evidence=claim.evidence,
                inference_confidence=claim.inference_confidence,
                clip_anchors=chosen,
            )
        )

    if not packet_claims:
        return None

    return PreReadScoutingPacket(
        selection=PreReadPacketSelection(
            claim_ids=[claim.claim_id for claim in packet_claims],
            clip_anchor_ids=packet_anchor_ids,
        ),
        claims=packet_claims,
        generated_at=datetime.utcnow().isoformat(),
        source_url=_scouting_url(team.upper(), opponent.upper(), season),
    )


def _snapshot_context_from_row(row: PreReadSnapshot) -> PreReadContext:
    persisted_context = row.payload.get("_snapshot_context", {}) if isinstance(row.payload, dict) else {}
    return PreReadContext(
        team_abbreviation=persisted_context.get("team_abbreviation", row.team_abbreviation),
        opponent_abbreviation=persisted_context.get("opponent_abbreviation", row.opponent_abbreviation),
        season=persisted_context.get("season", row.season),
        game_id=persisted_context.get("game_id", row.game_id),
        source_view=persisted_context.get("source_view", row.saved_from),
        source_snapshot_id=persisted_context.get("source_snapshot_id"),
        extras=persisted_context.get("extras", {}),
    )


def _resolved_title(row: PreReadSnapshot, deck: PreReadDeckResponse) -> str:
    return row.title or _default_title(
        row.team_abbreviation,
        row.opponent_abbreviation,
        row.season,
        game_date=(deck.prep_context.prep_item.game_date if deck.prep_context and deck.prep_context.prep_item else None),
        created_at=row.created_at.isoformat() if row.created_at else deck.generated_at,
    )


def _response_from_row(row: PreReadSnapshot) -> PreReadSnapshotResponse:
    deck = _deck_from_payload(row.payload)
    created_at = row.created_at.isoformat() if row.created_at else ""
    title = _resolved_title(row, deck)
    note = _normalized_note(row.note)
    deck.snapshot = _snapshot_ref(
        snapshot_id=row.snapshot_id,
        created_at=created_at,
        title=title,
        note=note,
        packet=deck.scouting_packet,
    )
    return PreReadSnapshotResponse(
        snapshot_id=row.snapshot_id,
        share_url=_share_url(row.snapshot_id),
        created_at=created_at,
        title=title,
        note=note,
        packet_summary=_packet_summary(deck.scouting_packet),
        context=_snapshot_context_from_row(row),
        deck=deck,
    )


def create_pre_read_snapshot(db: Session, payload: PreReadSnapshotCreateRequest) -> PreReadSnapshotResponse:
    snapshot_id = str(uuid.uuid4())
    context = PreReadContext(
        team_abbreviation=payload.team.upper(),
        opponent_abbreviation=payload.opponent.upper(),
        season=payload.season,
        game_id=payload.game_id,
        source_view=payload.source_view,
        source_snapshot_id=payload.source_snapshot_id,
        extras=payload.context,
    )
    scouting_packet = _build_scouting_packet(
        db=db,
        team=payload.team,
        opponent=payload.opponent,
        season=payload.season,
        selection=payload.packet_selection,
    )
    deck = build_pre_read_deck(
        db=db,
        team=payload.team,
        opponent=payload.opponent,
        season=payload.season,
        scouting_packet=scouting_packet,
        snapshot_ref=PreReadSnapshotRef(
            snapshot_id=snapshot_id,
            share_url=_share_url(snapshot_id),
            created_at="",
        ),
        source_context=context,
    )
    title = _normalized_title(payload.title) or _default_title(
        payload.team,
        payload.opponent,
        payload.season,
        game_date=(deck.prep_context.prep_item.game_date if deck.prep_context and deck.prep_context.prep_item else None),
        created_at=deck.generated_at,
    )
    note = _normalized_note(payload.note)
    deck.snapshot = _snapshot_ref(snapshot_id, deck.generated_at or "", title, note, scouting_packet)

    payload_json = json.loads(deck.model_dump_json())
    payload_json["_snapshot_context"] = context.model_dump()

    row = PreReadSnapshot(
        snapshot_id=snapshot_id,
        team_abbreviation=payload.team.upper(),
        opponent_abbreviation=payload.opponent.upper(),
        season=payload.season,
        game_id=payload.game_id,
        saved_from=payload.source_view,
        title=title,
        note=note,
        payload=payload_json,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _response_from_row(row)


def get_pre_read_snapshot(db: Session, snapshot_id: str) -> PreReadSnapshotResponse:
    row = (
        db.query(PreReadSnapshot)
        .filter(PreReadSnapshot.snapshot_id == snapshot_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Pre-read snapshot not found.")
    return _response_from_row(row)


def list_pre_read_snapshots(
    db: Session,
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    season: Optional[str] = None,
    limit: int = 10,
) -> PreReadSnapshotListResponse:
    query = db.query(PreReadSnapshot)
    if team:
        query = query.filter(PreReadSnapshot.team_abbreviation == team.upper())
    if opponent:
        query = query.filter(PreReadSnapshot.opponent_abbreviation == opponent.upper())
    if season:
        query = query.filter(PreReadSnapshot.season == season)

    rows = (
        query.order_by(PreReadSnapshot.created_at.desc(), PreReadSnapshot.id.desc())
        .limit(limit)
        .all()
    )
    items = []
    for row in rows:
        deck = _deck_from_payload(row.payload)
        items.append(
            PreReadSnapshotSummary(
                snapshot_id=row.snapshot_id,
                share_url=_share_url(row.snapshot_id),
                created_at=row.created_at.isoformat() if row.created_at else "",
                team_abbreviation=row.team_abbreviation,
                opponent_abbreviation=row.opponent_abbreviation,
                season=row.season,
                game_id=row.game_id,
                prep_headline=deck.prep_context.headline if deck.prep_context else None,
                saved_from=row.saved_from,
                title=_resolved_title(row, deck),
                note=_normalized_note(row.note),
                packet_summary=_packet_summary(deck.scouting_packet),
            )
        )
    return PreReadSnapshotListResponse(items=items)


def update_pre_read_snapshot(
    db: Session,
    snapshot_id: str,
    payload: PreReadSnapshotUpdateRequest,
) -> PreReadSnapshotResponse:
    row = (
        db.query(PreReadSnapshot)
        .filter(PreReadSnapshot.snapshot_id == snapshot_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Pre-read snapshot not found.")

    deck = _deck_from_payload(row.payload)
    if payload.title is not None:
        row.title = _normalized_title(payload.title) or _default_title(
            row.team_abbreviation,
            row.opponent_abbreviation,
            row.season,
            game_date=(deck.prep_context.prep_item.game_date if deck.prep_context and deck.prep_context.prep_item else None),
            created_at=row.created_at.isoformat() if row.created_at else deck.generated_at,
        )
    if payload.note is not None:
        row.note = _normalized_note(payload.note)

    db.add(row)
    db.commit()
    db.refresh(row)
    return _response_from_row(row)


def export_pre_read_snapshot_markdown(db: Session, snapshot_id: str) -> str:
    snapshot = get_pre_read_snapshot(db=db, snapshot_id=snapshot_id)
    deck = snapshot.deck

    lines = [
        "# {0}".format(snapshot.title or "{0} vs {1}".format(deck.team_abbreviation, deck.opponent_abbreviation)),
        "",
        "{0} vs {1} | {2} | saved {3}".format(
            deck.team_abbreviation,
            deck.opponent_abbreviation,
            deck.season,
            snapshot.created_at[:16].replace("T", " "),
        ),
    ]
    if snapshot.note:
        lines.extend(["", snapshot.note])

    if deck.prep_context and deck.prep_context.headline:
        lines.extend(["", "## Prep Headline", "", deck.prep_context.headline])
        if deck.prep_context.first_adjustment_rationale:
            lines.extend(["", deck.prep_context.first_adjustment_rationale])

    lines.extend(["", "## Focus Levers", ""])
    if deck.focus_levers:
        for lever in deck.focus_levers[:3]:
            lines.append("- {0}: {1}".format(lever.title, lever.summary))
    else:
        lines.append("- No focus levers generated.")

    lines.extend(["", "## Tactical Adjustments", ""])
    if deck.adjustments:
        for adjustment in deck.adjustments:
            lines.append("- {0}: {1}".format(adjustment.label, adjustment.recommendation))
    else:
        lines.append("- No tactical adjustments generated.")

    lines.extend(["", "## Matchup Advantages", ""])
    if deck.matchup_advantages:
        for advantage in deck.matchup_advantages:
            lines.append("- {0}".format(advantage))
    else:
        lines.append("- No clear matchup edge surfaced from the current packet.")

    if deck.scouting_packet and deck.scouting_packet.claims:
        lines.extend(["", "## Selected Scouting Claims", ""])
        for claim in deck.scouting_packet.claims:
            lines.append("### {0}".format(claim.title))
            if claim.inference_confidence:
                reasons = ", ".join(claim.inference_confidence.reasons) or "No confidence reasons provided."
                lines.append(
                    "Confidence: {0} ({1} anchored plays, {2} vs opponent)".format(
                        claim.inference_confidence.level.upper(),
                        claim.inference_confidence.anchored_event_count,
                        claim.inference_confidence.opponent_specific_event_count,
                    )
                )
                lines.append("Why: {0}".format(reasons))
            lines.append(claim.summary)
            if claim.clip_anchors:
                lines.append("")
                lines.append("Clip links:")
                for anchor in claim.clip_anchors:
                    lines.append(
                        "- {0} - {1}: {2}".format(
                            anchor.game_date or "Game",
                            anchor.evidence_summary,
                            anchor.deep_link_url,
                        )
                    )
            lines.append("")

    return "\n".join(lines).strip() + "\n"
