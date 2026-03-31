from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import Player, SeasonStat, Team  # noqa: E402
from models.leaderboard import CustomMetricComponent, CustomMetricRequest  # noqa: E402
from services.custom_metric_service import build_custom_metric_report  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def seed_metric_pool(session):
    team = Team(id=1610612737, abbreviation="ATL", name="Atlanta Hawks")
    session.add(team)
    stat_rows = [
        (1, "Alpha Guard", "G", 28.0, 8.0, 3.8, 0.58, 2.1),
        (2, "Bravo Guard", "G", 24.0, 7.1, 3.1, 0.61, 1.8),
        (3, "Charlie Wing", "F", 22.0, 4.3, 2.7, 0.56, 1.4),
        (4, "Delta Big", "C", 18.0, 2.9, 1.9, 0.64, 1.2),
        (5, "Echo Sixth", "G", 15.0, 6.2, 2.4, 0.60, 2.8),
        (6, "Foxtrot Sparse", "F", 12.0, 4.8, 2.2, 0.55, None),
    ]
    for player_id, name, position, pts_pg, ast_pg, tov_pg, ts_pct, bpm in stat_rows:
        player = Player(id=player_id, full_name=name, team=team, team_id=team.id, position=position)
        session.add(player)
        session.add(
            SeasonStat(
                player_id=player_id,
                season="2024-25",
                team_abbreviation="ATL",
                is_playoff=False,
                gp=52,
                pts_pg=pts_pg,
                ast_pg=ast_pg,
                tov_pg=tov_pg,
                ts_pct=ts_pct,
                        bpm=bpm,
                    )
        )
    session.commit()


def test_custom_metric_service_normalizes_weights_and_excludes_missing_players():
    session = make_session()
    try:
        seed_metric_pool(session)
        report = build_custom_metric_report(
            session,
            CustomMetricRequest(
                metric_name="",
                player_pool="all",
                season="2024-25",
                components=[
                    CustomMetricComponent(stat_id="pts_pg", label="Points", weight=4.0, inverse=False),
                    CustomMetricComponent(stat_id="ast_pg", label="Assists", weight=3.0, inverse=False),
                        CustomMetricComponent(stat_id="bpm", label="BPM", weight=1.0, inverse=False),
                    ],
                ),
            )

        assert report.player_rankings[0].player_name == "Alpha Guard"
        assert any("normalized proportionally" in warning for warning in report.validation_warnings)
        assert any("Excluded players" in warning for warning in report.validation_warnings)
        assert len(report.player_rankings) == 5
    finally:
        session.close()


def test_custom_metric_service_flags_weight_sensitive_outliers():
    session = make_session()
    try:
        seed_metric_pool(session)
        report = build_custom_metric_report(
            session,
            CustomMetricRequest(
                metric_name="Scoring Spike",
                player_pool="all",
                season="2024-25",
                components=[
                    CustomMetricComponent(stat_id="pts_pg", label="Points", weight=0.92, inverse=False),
                    CustomMetricComponent(stat_id="bpm", label="BPM", weight=0.08, inverse=False),
                ],
            ),
        )

        assert any("heavily concentrated" in warning for warning in report.validation_warnings)
        assert report.anomalies
        assert report.anomalies[0].contribution_pct > 60.0
    finally:
        session.close()


def test_custom_metric_service_rejects_small_player_pool():
    session = make_session()
    try:
        team = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
        session.add(team)
        for player_id in range(1, 5):
            session.add(Player(id=100 + player_id, full_name="Player {0}".format(player_id), team=team, team_id=team.id, position="G"))
            session.add(
                SeasonStat(
                    player_id=100 + player_id,
                    season="2024-25",
                    team_abbreviation="BOS",
                    is_playoff=False,
                    gp=20,
                    pts_pg=10.0 + player_id,
                    ast_pg=3.0 + player_id,
                )
            )
        session.commit()

        with pytest.raises(HTTPException) as exc_info:
            build_custom_metric_report(
                session,
                CustomMetricRequest(
                    season="2024-25",
                    player_pool="all",
                    components=[
                        CustomMetricComponent(stat_id="pts_pg", label="Points", weight=0.5, inverse=False),
                        CustomMetricComponent(stat_id="ast_pg", label="Assists", weight=0.5, inverse=False),
                    ],
                ),
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Insufficient player pool for meaningful ranking."
    finally:
        session.close()
