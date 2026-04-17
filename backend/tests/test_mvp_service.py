from datetime import date, timedelta
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    PlayByPlayEvent,
    Player,
    PlayerGameLog,
    PlayerOnOff,
    SeasonStat,
    Team,
    TeamSeasonStat,
)
from routers.mvp import get_mvp_candidate_case, get_mvp_context_map, get_mvp_race  # noqa: E402
from services.mvp_service import build_mvp_candidate_case, build_mvp_context_map, build_mvp_race  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _seed_player_case(session):
    team_a = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
    team_b = Team(id=1610612743, abbreviation="DEN", name="Denver Nuggets")
    session.add_all([team_a, team_b])
    session.flush()

    alpha = Player(id=1, full_name="Alpha Star", first_name="Alpha", last_name="Star", team_id=team_a.id, position="G")
    beta = Player(id=2, full_name="Beta Center", first_name="Beta", last_name="Center", team_id=team_b.id, position="C")
    gamma = Player(id=3, full_name="Gamma Wing", first_name="Gamma", last_name="Wing", team_id=team_b.id, position="F")
    session.add_all([alpha, beta, gamma])
    session.flush()

    session.add_all(
        [
            TeamSeasonStat(
                team_id=team_a.id,
                season="2025-26",
                is_playoff=False,
                gp=30,
                w=24,
                l=6,
                w_pct=0.800,
                net_rating=10.2,
                off_rating=121.3,
                def_rating=111.1,
            ),
            TeamSeasonStat(
                team_id=team_b.id,
                season="2025-26",
                is_playoff=False,
                gp=30,
                w=18,
                l=12,
                w_pct=0.600,
                net_rating=3.1,
                off_rating=116.0,
                def_rating=112.9,
            ),
        ]
    )
    session.add_all(
        [
            SeasonStat(
                player_id=alpha.id,
                season="2025-26",
                team_abbreviation="OLD",
                is_playoff=False,
                gp=22,
                min_total=704.0,
                min_pg=32.0,
                pts=550,
                pts_pg=25.0,
                reb_pg=5.0,
                ast_pg=6.0,
                fgm=190,
                fga=380,
                fg3m=70,
                fta=130,
                ts_pct=0.610,
                efg_pct=0.592,
                usg_pct=28.0,
                bpm=5.0,
                vorp=2.0,
                ws=4.0,
            ),
            SeasonStat(
                player_id=alpha.id,
                season="2025-26",
                team_abbreviation="TOT",
                is_playoff=False,
                gp=25,
                min_total=850.0,
                min_pg=34.0,
                pts=800,
                pts_pg=32.0,
                reb_pg=7.0,
                ast_pg=8.0,
                fgm=280,
                fga=560,
                fg3m=100,
                fta=200,
                ts_pct=0.640,
                efg_pct=0.589,
                usg_pct=31.0,
                bpm=8.0,
                obpm=6.0,
                dbpm=2.0,
                vorp=3.2,
                ws=6.0,
                pie=0.210,
                net_rating=12.0,
                clutch_pts=42,
                clutch_fga=20,
                clutch_fg_pct=0.550,
                second_chance_pts=30,
                fast_break_pts=80,
            ),
            SeasonStat(
                player_id=beta.id,
                season="2025-26",
                team_abbreviation="DEN",
                is_playoff=False,
                gp=24,
                min_total=792.0,
                min_pg=33.0,
                pts=620,
                pts_pg=25.8,
                reb_pg=13.0,
                ast_pg=9.5,
                fgm=240,
                fga=420,
                fg3m=15,
                fta=160,
                ts_pct=0.650,
                efg_pct=0.590,
                usg_pct=27.0,
                bpm=7.0,
                vorp=2.8,
                ws=5.4,
                clutch_pts=20,
            ),
            SeasonStat(
                player_id=gamma.id,
                season="2025-26",
                team_abbreviation="DEN",
                is_playoff=False,
                gp=23,
                min_total=713.0,
                min_pg=31.0,
                pts=520,
                pts_pg=22.6,
                reb_pg=6.0,
                ast_pg=4.0,
                fgm=190,
                fga=390,
                fg3m=60,
                fta=120,
                ts_pct=0.590,
                usg_pct=24.0,
            ),
        ]
    )
    session.add_all(
        [
            PlayerOnOff(
                player_id=alpha.id,
                season="2025-26",
                is_playoff=False,
                on_minutes=900,
                off_minutes=300,
                on_net_rating=14.0,
                off_net_rating=1.0,
                on_off_net=13.0,
                on_ortg=122.0,
                on_drtg=108.0,
                off_ortg=111.0,
                off_drtg=110.0,
            ),
            PlayerOnOff(
                player_id=beta.id,
                season="2025-26",
                is_playoff=False,
                on_minutes=850,
                off_minutes=320,
                on_net_rating=8.0,
                off_net_rating=2.0,
                on_off_net=6.0,
            ),
        ]
    )
    base_date = date(2026, 1, 1)
    for index in range(12):
        session.add(
            PlayerGameLog(
                player_id=alpha.id,
                game_id=f"00225000{index:02d}",
                season="2025-26",
                season_type="Regular Season",
                game_date=base_date + timedelta(days=index),
                matchup="BOS vs DEN" if index % 2 == 0 else "BOS @ DEN",
                wl="W" if index % 3 else "L",
                min=34.0,
                pts=30 + index,
                reb=5,
                ast=6,
                fga=20,
                fta=8,
                plus_minus=8 - index,
            )
        )
    session.add_all(
        [
            PlayByPlayEvent(
                game_id="0022500001",
                season="2025-26",
                order_index=1,
                team_id=team_a.id,
                player_id=alpha.id,
                action_type="2pt",
                action_family="shot",
                sub_type="made",
                description="Alpha Star isolation pull-up made shot",
            ),
            PlayByPlayEvent(
                game_id="0022500001",
                season="2025-26",
                order_index=2,
                team_id=team_a.id,
                player_id=alpha.id,
                action_type="3pt",
                action_family="shot",
                sub_type="made",
                description="Alpha Star catch and shoot corner three",
            ),
            PlayByPlayEvent(
                game_id="0022500001",
                season="2025-26",
                order_index=3,
                team_id=team_a.id,
                player_id=alpha.id,
                action_type="turnover",
                action_family="turnover",
                sub_type="lost ball",
                description="Alpha Star bad pass turnover",
            ),
        ]
    )
    session.commit()
    return alpha, beta, gamma


def test_mvp_race_builds_case_payload_and_dedupes_trade_rows():
    session = make_session()
    try:
        alpha, _, _ = _seed_player_case(session)
        response = build_mvp_race(session, season="2025-26", top=3)

        assert response.scoring_profile == "mvp_case_v1"
        assert len(response.candidates) == 3

        alpha_case = next(row for row in response.candidates if row.player_id == alpha.id)
        assert alpha_case.team_abbreviation == "TOT"
        assert alpha_case.gp == 25
        assert alpha_case.score_pillars["production"].weight == 0.25
        assert alpha_case.team_context is not None
        assert alpha_case.team_context.win_pct_rank == 1
        assert alpha_case.on_off is not None
        assert alpha_case.on_off.on_off_net == 13.0
        assert alpha_case.on_off.confidence == "medium"
        assert alpha_case.advanced_profile is not None
        assert alpha_case.advanced_profile.obpm == 6.0
        assert alpha_case.advanced_profile.win_shares_per_48 == round(6.0 * 48.0 / 850.0, 3)
        assert alpha_case.clutch_and_pace is not None
        assert alpha_case.clutch_and_pace.fast_break_pts == 80.0
        assert alpha_case.play_style
        assert alpha_case.eligibility is not None
        assert alpha_case.eligibility.minutes_qualified_games == 12
        assert alpha_case.eligibility.eligibility_status == "ineligible"
        assert alpha_case.opponent_context is not None
        assert alpha_case.opponent_context.rows
        assert alpha_case.support_burden is not None
        assert alpha_case.impact_metric_coverage is not None
        assert "EPM" in alpha_case.impact_metric_coverage.external_metrics_missing
        assert alpha_case.visual_coordinates is not None
        assert alpha_case.data_coverage is not None
        assert alpha_case.data_coverage.has_play_style is True
        assert alpha_case.data_coverage.has_eligibility is True
        assert alpha_case.case_summary
    finally:
        session.close()


def test_mvp_eligibility_counts_near_miss_games():
    session = make_session()
    try:
        alpha, _, _ = _seed_player_case(session)
        base_date = date(2026, 2, 1)
        for index in range(53):
            session.add(
                PlayerGameLog(
                    player_id=alpha.id,
                    game_id=f"00225010{index:02d}",
                    season="2025-26",
                    season_type="Regular Season",
                    game_date=base_date + timedelta(days=index),
                    matchup="BOS vs DEN",
                    wl="W",
                    min=16.0 if index < 3 else 22.0,
                    pts=24,
                    reb=5,
                    ast=6,
                    fga=16,
                    fta=6,
                )
            )
        session.commit()

        response = build_mvp_race(session, season="2025-26", top=3)
        alpha_case = next(row for row in response.candidates if row.player_id == alpha.id)

        assert alpha_case.eligibility is not None
        assert alpha_case.eligibility.minutes_qualified_games == 62
        assert alpha_case.eligibility.near_miss_games == 3
        assert alpha_case.eligibility.eligible_games == 64
        assert alpha_case.eligibility.games_needed == 1
        assert alpha_case.eligibility.eligibility_status == "at_risk"
    finally:
        session.close()


def test_mvp_race_keeps_missing_impact_data_candidates_with_warnings():
    session = make_session()
    try:
        _, _, gamma = _seed_player_case(session)
        response = build_mvp_race(session, season="2025-26", top=5)
        gamma_case = next(row for row in response.candidates if row.player_id == gamma.id)

        assert gamma_case.bpm is None
        assert gamma_case.on_off is None
        assert gamma_case.play_style == []
        assert gamma_case.data_coverage is not None
        assert "On/off impact is missing for this candidate." in gamma_case.data_coverage.warnings
    finally:
        session.close()


def test_mvp_routes_support_filters_and_candidate_case():
    session = make_session()
    try:
        alpha, _, _ = _seed_player_case(session)
        race = get_mvp_race(season="2025-26", top=2, min_gp=20, position="G", db=session)
        assert len(race.candidates) == 1
        assert race.candidates[0].player_id == alpha.id

        case = get_mvp_candidate_case(player_id=alpha.id, season="2025-26", min_gp=20, position=None, db=session)
        assert case.candidate.player_id == alpha.id
        assert case.nearby

        context_map = get_mvp_context_map(season="2025-26", top=2, min_gp=20, position=None, db=session)
        assert context_map.points
        assert context_map.points[0].quick_evidence
    finally:
        session.close()


def test_mvp_context_map_returns_lightweight_coordinates():
    session = make_session()
    try:
        _seed_player_case(session)
        response = build_mvp_context_map(session, season="2025-26", top=2)

        assert response.scoring_profile == "mvp_case_v1"
        assert response.default_x == "team_success"
        assert len(response.points) == 2
        assert 0 <= response.points[0].x_team_success <= 100
        assert 0 <= response.points[0].y_individual_impact <= 100
    finally:
        session.close()


def test_mvp_candidate_case_raises_for_missing_candidate():
    session = make_session()
    try:
        _seed_player_case(session)
        with pytest.raises(HTTPException):
            build_mvp_candidate_case(session, season="2025-26", player_id=999999)
    finally:
        session.close()


def test_mvp_race_empty_season_response():
    session = make_session()
    try:
        response = build_mvp_race(session, season="1999-00", top=10)
        assert response.candidates == []
        assert response.weights["impact"] == 0.25
    finally:
        session.close()
