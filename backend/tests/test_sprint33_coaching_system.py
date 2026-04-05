from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    GameTeamStat,
    PlayByPlayEvent,
    Player,
    PlayerInjury,
    SeasonStat,
    Team,
    TeamStanding,
    WarehouseGame,
)
from models.trends import WhatIfRequest  # noqa: E402
from models.scouting import ScoutingClipExportRequest  # noqa: E402
from routers.scouting import build_play_type_scouting_report, export_scouting_clip_list  # noqa: E402
from routers.trends import build_what_if_report  # noqa: E402
from services.pre_read_snapshot_service import create_pre_read_snapshot, get_pre_read_snapshot  # noqa: E402
from models.pre_read import PreReadSnapshotCreateRequest  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def seed_context(session):
    today = date.today()
    atl = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks", city="Atlanta", conference="East")
    bos = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics", city="Boston", conference="East")
    nyk = Team(id=1610612752, abbreviation="NYK", name="New York Knicks", city="New York", conference="East")
    session.add_all([atl, bos, nyk])

    session.add_all(
        [
            Player(id=1, full_name="Alpha Guard", first_name="Alpha", last_name="Guard", team_id=atl.id, is_active=True),
            Player(id=2, full_name="Bravo Wing", first_name="Bravo", last_name="Wing", team_id=atl.id, is_active=True),
            Player(id=11, full_name="Delta Guard", first_name="Delta", last_name="Guard", team_id=bos.id, is_active=True),
            Player(id=21, full_name="Foxtrot Guard", first_name="Foxtrot", last_name="Guard", team_id=nyk.id, is_active=True),
        ]
    )
    session.add_all(
        [
            SeasonStat(player_id=1, season="2025-26", team_abbreviation="ATL", is_playoff=False, gp=5, pts_pg=24.5, bpm=4.4),
            SeasonStat(player_id=2, season="2025-26", team_abbreviation="ATL", is_playoff=False, gp=5, pts_pg=14.2, bpm=1.7),
            SeasonStat(player_id=11, season="2025-26", team_abbreviation="BOS", is_playoff=False, gp=5, pts_pg=25.1, bpm=5.0),
            SeasonStat(player_id=21, season="2025-26", team_abbreviation="NYK", is_playoff=False, gp=5, pts_pg=18.3, bpm=2.9),
        ]
    )

    final_games = [
        ("0022600001", today - timedelta(days=4), atl, bos, 112, 104),
        ("0022600002", today - timedelta(days=2), nyk, atl, 106, 111),
        ("0022600003", today - timedelta(days=1), atl, nyk, 118, 109),
    ]
    for game_id, game_date, home, away, home_score, away_score in final_games:
        session.add(
            WarehouseGame(
                game_id=game_id,
                season="2025-26",
                game_date=game_date,
                status="final",
                home_team_id=home.id,
                away_team_id=away.id,
                home_team_abbreviation=home.abbreviation,
                away_team_abbreviation=away.abbreviation,
                home_team_name=home.name,
                away_team_name=away.name,
                home_score=home_score,
                away_score=away_score,
                has_parsed_pbp=True,
            )
        )
        for team in (home, away):
            pts = home_score if team.id == home.id else away_score
            session.add(
                GameTeamStat(
                    game_id=game_id,
                    season="2025-26",
                    team_id=team.id,
                    team_abbreviation=team.abbreviation,
                    is_home=team.id == home.id,
                    won=pts == max(home_score, away_score),
                    pts=pts,
                    reb=41 if team.id == atl.id else 39,
                    ast=24 if team.id == atl.id else 22,
                    tov=11 if team.id == atl.id else 14,
                    fgm=40,
                    fga=84,
                    fg3m=13,
                    fg3a=34,
                    ftm=19,
                    fta=24,
                    oreb=10 if team.id == atl.id else 8,
                    dreb=31,
                    pf=18,
                    minutes=240.0,
                    plus_minus=8.0 if pts == max(home_score, away_score) else -8.0,
                )
            )
        session.add_all(
            [
                PlayByPlayEvent(
                    game_id=game_id,
                    season="2025-26",
                    order_index=1,
                    action_number=1,
                    period=1,
                    team_id=atl.id,
                    player_id=1,
                    action_type="2pt",
                    action_family="rim_pressure",
                    description="Alpha Guard drive to rim",
                ),
                PlayByPlayEvent(
                    game_id=game_id,
                    season="2025-26",
                    order_index=2,
                    action_number=2,
                    period=1,
                    team_id=atl.id,
                    player_id=2,
                    action_type="3pt",
                    action_family="spot_up",
                    description="Bravo Wing catch and shoot three",
                ),
            ]
        )

    session.add(
        WarehouseGame(
            game_id="0022690001",
            season="2025-26",
            game_date=today + timedelta(days=1),
            status="scheduled",
            home_team_id=atl.id,
            away_team_id=bos.id,
            home_team_abbreviation=atl.abbreviation,
            away_team_abbreviation=bos.abbreviation,
            home_team_name=atl.name,
            away_team_name=bos.name,
        )
    )
    session.add_all(
        [
            TeamStanding(team_id=atl.id, season="2025-26", snapshot_date=today, wins=4, losses=1, conference="East", division="Southeast"),
            TeamStanding(team_id=bos.id, season="2025-26", snapshot_date=today, wins=3, losses=2, conference="East", division="Atlantic"),
            TeamStanding(team_id=nyk.id, season="2025-26", snapshot_date=today, wins=2, losses=3, conference="East", division="Atlantic"),
        ]
    )
    session.add(
        PlayerInjury(
            player_id=11,
            team_id=bos.id,
            report_date=today,
            season="2025-26",
            injury_status="Questionable",
            injury_type="Ankle",
            detail="Monitor",
        )
    )
    session.commit()
    return atl, bos, nyk


def test_pre_read_snapshot_is_frozen_after_underlying_data_changes():
    session = make_session()
    try:
        atl, bos, _ = seed_context(session)
        snapshot = create_pre_read_snapshot(
            session,
            PreReadSnapshotCreateRequest(
                team=atl.abbreviation,
                opponent=bos.abbreviation,
                season="2025-26",
                source_view="prep-queue-card",
            ),
        )
        original_headline = snapshot.deck.prep_context.headline if snapshot.deck.prep_context else None
        session.add(
            TeamStanding(
                team_id=bos.id,
                season="2025-26",
                snapshot_date=date.today() + timedelta(days=1),
                wins=20,
                losses=1,
                conference="East",
                division="Atlantic",
            )
        )
        session.commit()

        reopened = get_pre_read_snapshot(session, snapshot.snapshot_id)
        assert reopened.deck.snapshot is not None
        assert reopened.deck.snapshot.snapshot_id == snapshot.snapshot_id
        assert (reopened.deck.prep_context.headline if reopened.deck.prep_context else None) == original_headline
    finally:
        session.close()


def test_what_if_response_keeps_opponent_specific_context_and_links():
    session = make_session()
    try:
        atl, bos, nyk = seed_context(session)
        bos_response = build_what_if_report(
            session,
            WhatIfRequest(team=atl.abbreviation, opponent=bos.abbreviation, season="2025-26", scenario_type="raise_3pa_rate", delta=0.03),
        )
        nyk_response = build_what_if_report(
            session,
            WhatIfRequest(team=atl.abbreviation, opponent=nyk.abbreviation, season="2025-26", scenario_type="raise_3pa_rate", delta=0.03),
        )
        assert bos_response.context.opponent == "BOS"
        assert nyk_response.context.opponent == "NYK"
        assert bos_response.launch_links.compare_url != nyk_response.launch_links.compare_url
        assert bos_response.data_status in {"ready", "partial", "limited"}
        assert bos_response.style_implication.archetype
    finally:
        session.close()


def test_what_if_accepts_legacy_aliases_and_returns_source_aware_compare_links():
    session = make_session()
    try:
        atl, bos, _ = seed_context(session)
        response = build_what_if_report(
            session,
            WhatIfRequest(
                team=atl.abbreviation,
                opponent=bos.abbreviation,
                season="2025-26",
                scenario_type="increase_pnr_handoff_proxy",
                delta=0.02,
            ),
        )

        assert response.scenario_type == "increase_pnr_proxy"
        assert response.scenario_label == "Protect shot quality"
        assert "source_type=what-if" in response.launch_links.compare_url
        assert "return_to=" in response.launch_links.compare_url
        assert response.directional_note is not None
    finally:
        session.close()


def test_scouting_report_and_export_include_claim_linked_clip_anchors():
    session = make_session()
    try:
        atl, bos, _ = seed_context(session)
        report = build_play_type_scouting_report(session, atl.abbreviation, bos.abbreviation, "2025-26", window=5)
        assert report.data_status in {"ready", "partial", "limited"}
        assert report.sections
        claim_ids = {claim.claim_id for section in report.sections for claim in section.claims}
        assert claim_ids
        assert report.clip_anchors
        assert all(anchor.claim_id in claim_ids for anchor in report.clip_anchors)
        assert "source_type=scouting-report" in report.launch_context.compare_url
        assert all("source=scouting-report" in anchor.deep_link_url for anchor in report.clip_anchors)
        assert all(anchor.linkage_quality in {"derived", "timeline"} for anchor in report.clip_anchors)
        assert all("focus_window=1" in anchor.deep_link_url for anchor in report.clip_anchors)
        assert all("source_id=" in anchor.deep_link_url for anchor in report.clip_anchors)
        assert any(anchor.action_number is not None for anchor in report.clip_anchors)
        assert any(anchor.source_context and anchor.source_context.get("source") == "scouting-report" for anchor in report.clip_anchors)

        export = export_scouting_clip_list(
            ScoutingClipExportRequest(team=atl.abbreviation, opponent=bos.abbreviation, season="2025-26"),
            db=session,
        )
        assert export.clip_count == len(export.clip_anchors)
        assert export.data_status in {"ready", "partial", "limited"}
        assert all(anchor.linkage_quality in {"derived", "timeline"} for anchor in export.clip_anchors)
    finally:
        session.close()
