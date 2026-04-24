from pathlib import Path
import sys

from sqlalchemy import inspect

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db.models import PlayByPlayEvent, PreReadSnapshot
from models.pre_read import PreReadPacketSelection, PreReadSnapshotCreateRequest, PreReadSnapshotUpdateRequest
from routers.scouting import build_play_type_scouting_report
from services.pre_read_snapshot_service import (
    create_pre_read_snapshot,
    export_pre_read_snapshot_markdown,
    get_pre_read_snapshot,
    list_pre_read_snapshots,
    update_pre_read_snapshot,
)
from test_sprint33_coaching_system import make_session, seed_context


def _first_packet_selection(session):
    atl, bos, _ = seed_context(session)
    report = build_play_type_scouting_report(session, atl.abbreviation, bos.abbreviation, "2025-26", window=5)
    first_claim = report.sections[0].claims[0]
    anchors = [anchor.clip_anchor_id for anchor in report.clip_anchors if anchor.claim_id == first_claim.claim_id][:2]
    return atl, bos, PreReadPacketSelection(claim_ids=[first_claim.claim_id], clip_anchor_ids=anchors)


def test_pre_read_snapshot_model_exposes_title_and_note_columns():
    session = make_session()
    try:
        columns = {column["name"] for column in inspect(session.bind).get_columns(PreReadSnapshot.__tablename__)}
        assert "title" in columns
        assert "note" in columns
    finally:
        session.close()


def test_staff_packet_snapshot_freezes_selected_scouting_claims_and_lists_by_scope():
    session = make_session()
    try:
        atl, bos, selection = _first_packet_selection(session)
        snapshot = create_pre_read_snapshot(
            session,
            PreReadSnapshotCreateRequest(
                team=atl.abbreviation,
                opponent=bos.abbreviation,
                season="2025-26",
                title="Atlanta packet",
                note="Emphasize early pressure.",
                packet_selection=selection,
                source_view="pre-read-scouting",
            ),
        )

        assert snapshot.title == "Atlanta packet"
        assert snapshot.note == "Emphasize early pressure."
        assert snapshot.packet_summary is not None
        assert snapshot.packet_summary.claim_count == 1
        assert snapshot.deck.scouting_packet is not None
        assert snapshot.deck.scouting_packet.claims[0].claim_id == selection.claim_ids[0]
        frozen_anchor_ids = [anchor.clip_anchor_id for anchor in snapshot.deck.scouting_packet.claims[0].clip_anchors]
        assert frozen_anchor_ids == selection.clip_anchor_ids

        session.query(PlayByPlayEvent).delete()
        session.commit()

        reopened = get_pre_read_snapshot(session, snapshot.snapshot_id)
        assert reopened.title == "Atlanta packet"
        assert reopened.deck.scouting_packet is not None
        assert reopened.deck.scouting_packet.claims[0].claim_id == selection.claim_ids[0]
        assert [anchor.clip_anchor_id for anchor in reopened.deck.scouting_packet.claims[0].clip_anchors] == frozen_anchor_ids

        matchup_items = list_pre_read_snapshots(
            session,
            team=atl.abbreviation,
            opponent=bos.abbreviation,
            season="2025-26",
            limit=5,
        ).items
        assert len(matchup_items) == 1
        assert matchup_items[0].title == "Atlanta packet"
        assert matchup_items[0].packet_summary is not None
        assert matchup_items[0].packet_summary.claim_count == 1

        team_history_items = list_pre_read_snapshots(session, team=atl.abbreviation, season="2025-26", limit=5).items
        assert len(team_history_items) == 1
    finally:
        session.close()


def test_pre_read_snapshot_update_and_markdown_export_include_packet_metadata():
    session = make_session()
    try:
        atl, bos, selection = _first_packet_selection(session)
        snapshot = create_pre_read_snapshot(
            session,
            PreReadSnapshotCreateRequest(
                team=atl.abbreviation,
                opponent=bos.abbreviation,
                season="2025-26",
                packet_selection=selection,
                source_view="prep-queue-card",
            ),
        )

        updated = update_pre_read_snapshot(
            session,
            snapshot.snapshot_id,
            PreReadSnapshotUpdateRequest(
                title="ATL vs BOS Staff Packet",
                note="Keep two actions ready for the first timeout.",
            ),
        )
        assert updated.title == "ATL vs BOS Staff Packet"
        assert updated.note == "Keep two actions ready for the first timeout."
        assert updated.deck.snapshot is not None
        assert updated.deck.snapshot.title == "ATL vs BOS Staff Packet"

        markdown = export_pre_read_snapshot_markdown(session, snapshot.snapshot_id)
        assert "# ATL vs BOS Staff Packet" in markdown
        assert "## Prep Headline" in markdown
        assert "## Focus Levers" in markdown
        assert "## Tactical Adjustments" in markdown
        assert "## Selected Scouting Claims" in markdown
        assert "Confidence:" in markdown
        assert updated.deck.scouting_packet is not None
        assert updated.deck.scouting_packet.claims[0].title in markdown
        assert updated.deck.scouting_packet.claims[0].clip_anchors[0].deep_link_url in markdown
    finally:
        session.close()
