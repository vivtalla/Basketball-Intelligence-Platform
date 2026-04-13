from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import Player, SeasonStat, Team, TeamSeasonStat, TeamSplitStat  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from routers.teams import team_analytics, team_splits  # noqa: E402
from services.sync_service import sync_official_team_general_splits, sync_official_team_season_stats  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_sync_official_team_season_stats_upserts_dashboard_rows(monkeypatch):
    session = make_session()
    try:
        session.add(Team(id=1610612747, abbreviation="LAL", name="Old Lakers"))
        session.commit()

        def fake_get_team_stats(season: str):
            assert season == "2025-26"
            return {
                "LAL": {
                    "team_id": 1610612747,
                    "abbreviation": "LAL",
                    "name": "Los Angeles Lakers",
                    "season": season,
                    "gp": 64,
                    "w": 42,
                    "l": 22,
                    "w_pct": 0.65625,
                    "pts_pg": 118.4,
                    "ast_pg": 27.1,
                    "reb_pg": 44.2,
                    "tov_pg": 13.0,
                    "blk_pg": 5.2,
                    "stl_pg": 7.9,
                    "fg_pct": 0.491,
                    "fg3_pct": 0.384,
                    "ft_pct": 0.803,
                    "plus_minus_pg": 7.1,
                    "off_rating": 119.8,
                    "def_rating": 112.7,
                    "net_rating": 7.1,
                    "pace": 100.6,
                    "efg_pct": 0.571,
                    "ts_pct": 0.613,
                    "pie": 0.558,
                    "oreb_pct": 27.3,
                    "dreb_pct": 72.1,
                    "tov_pct": 12.8,
                    "ast_pct": 67.4,
                    "off_rating_rank": 3,
                    "def_rating_rank": 7,
                    "net_rating_rank": 2,
                    "pace_rank": 10,
                    "efg_pct_rank": 4,
                    "ts_pct_rank": 2,
                    "oreb_pct_rank": 8,
                    "tov_pct_rank": 12,
                }
            }

        monkeypatch.setattr("services.sync_service.get_team_stats", fake_get_team_stats)

        result = sync_official_team_season_stats(session, "2025-26")

        row = (
            session.query(TeamSeasonStat)
            .filter_by(team_id=1610612747, season="2025-26", is_playoff=False)
            .first()
        )
        assert result["teams_synced"] == 1
        assert row is not None
        assert row.source == "stats.nba.com/team-dashboard"
        assert row.pts_pg == 118.4
        assert row.off_rating == 119.8
        assert row.tov_pct == 12.8
        assert session.query(Team).filter_by(id=1610612747).first().name == "Los Angeles Lakers"
    finally:
        session.close()


def test_team_analytics_reads_persisted_official_team_stats_not_player_aggregation():
    session = make_session()
    try:
        team = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
        player = Player(
            id=42,
            full_name="Mismatch Player",
            first_name="Mismatch",
            last_name="Player",
            team_id=team.id,
            is_active=True,
        )
        session.add_all([team, player])
        session.flush()
        session.add(
            SeasonStat(
                player_id=player.id,
                season="2025-26",
                team_abbreviation="BOS",
                is_playoff=False,
                gp=82,
                pts=4100,
                pts_pg=50.0,
                reb=820,
                reb_pg=10.0,
                ast=820,
                ast_pg=10.0,
            )
        )
        session.add(
            TeamSeasonStat(
                team_id=team.id,
                season="2025-26",
                is_playoff=False,
                source="stats.nba.com/team-dashboard",
                gp=61,
                w=44,
                l=17,
                w_pct=0.721,
                pts_pg=117.2,
                reb_pg=45.0,
                ast_pg=26.3,
                stl_pg=8.1,
                blk_pg=5.7,
                tov_pg=12.6,
                fg_pct=0.487,
                fg3_pct=0.379,
                ft_pct=0.812,
                plus_minus_pg=8.8,
                off_rating=120.1,
                def_rating=111.3,
                net_rating=8.8,
                pace=99.8,
                efg_pct=0.566,
                ts_pct=0.609,
                pie=0.561,
                oreb_pct=28.0,
                dreb_pct=72.8,
                tov_pct=12.2,
                ast_pct=68.1,
                off_rating_rank=1,
                def_rating_rank=4,
                net_rating_rank=1,
                pace_rank=15,
                efg_pct_rank=2,
                ts_pct_rank=2,
                oreb_pct_rank=6,
                tov_pct_rank=9,
            )
        )
        session.commit()

        response = team_analytics("BOS", season="2025-26", db=session)

        assert response.canonical_source == "stats.nba.com/team-dashboard"
        assert response.gp == 61
        assert response.pts_pg == 117.2
        assert response.off_rating == 120.1
        assert response.tov_pct == 12.2
        assert response.last_synced_at is not None
    finally:
        session.close()


def test_sync_official_team_general_splits_upserts_and_filters_rows(monkeypatch):
    session = make_session()
    try:
        session.add_all(
            [
                Team(id=1610612738, abbreviation="BOS", name="Boston Celtics"),
                Team(id=1610612747, abbreviation="LAL", name="Los Angeles Lakers"),
            ]
        )
        session.add(
            TeamSplitStat(
                team_id=1610612738,
                season="2025-26",
                is_playoff=False,
                split_family="LocationTeamDashboard",
                split_value="Road",
                label="Road",
                gp=12,
            )
        )
        session.commit()

        def fake_get_team_general_splits(season: str, team_id: int):
            assert season == "2025-26"
            if team_id == 1610612738:
                return [
                    {
                        "team_id": team_id,
                        "season": season,
                        "is_playoff": False,
                        "split_family": "LocationTeamDashboard",
                        "split_value": "Home",
                        "label": "Home",
                        "gp": 40,
                        "w": 31,
                        "l": 9,
                        "w_pct": 0.775,
                        "min": 1920.0,
                        "pts": 4850.0,
                        "reb": 1800.0,
                        "ast": 1120.0,
                        "tov": 480.0,
                        "stl": 330.0,
                        "blk": 220.0,
                        "fg_pct": 0.501,
                        "fg3_pct": 0.392,
                        "ft_pct": 0.82,
                        "plus_minus": 510.0,
                    }
                ]
            return [
                {
                    "team_id": team_id,
                    "season": season,
                    "split_family": "LocationTeamDashboard",
                    "split_value": "Home",
                    "label": "Home",
                    "gp": 40,
                }
            ]

        monkeypatch.setattr("services.sync_service.get_team_general_splits", fake_get_team_general_splits)

        result = sync_official_team_general_splits(session, "2025-26", team_ids=[1610612738])

        rows = session.query(TeamSplitStat).filter_by(team_id=1610612738, season="2025-26").all()
        assert result["status"] == "ok"
        assert result["teams_synced"] == 1
        assert result["split_rows_synced"] == 1
        assert result["split_rows_created"] == 1
        assert result["split_rows_deleted"] == 1
        assert len(rows) == 1
        assert rows[0].split_family == "LocationTeamDashboard"
        assert rows[0].split_value == "Home"
        assert rows[0].pts == 4850.0
        assert rows[0].source == "stats.nba.com/team-general-splits"
        assert session.query(TeamSplitStat).filter_by(team_id=1610612747).count() == 0
    finally:
        session.close()


def test_team_splits_reads_persisted_official_split_rows():
    session = make_session()
    try:
        team = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
        session.add(team)
        session.add_all(
            [
                TeamSplitStat(
                    team_id=team.id,
                    season="2025-26",
                    is_playoff=False,
                    split_family="LocationTeamDashboard",
                    split_value="Home",
                    label="Home",
                    gp=40,
                    w=31,
                    l=9,
                    w_pct=0.775,
                    pts=4850.0,
                    plus_minus=510.0,
                ),
                TeamSplitStat(
                    team_id=team.id,
                    season="2025-26",
                    is_playoff=False,
                    split_family="WinsLossesTeamDashboard",
                    split_value="Wins",
                    label="Wins",
                    gp=55,
                    w=55,
                    l=0,
                    w_pct=1.0,
                ),
            ]
        )
        session.commit()

        response = team_splits("BOS", season="2025-26", db=session)

        assert response.team_id == team.id
        assert response.abbreviation == "BOS"
        assert response.canonical_source == "stats.nba.com/team-general-splits"
        assert response.last_synced_at is not None
        assert len(response.splits) == 2
        assert response.splits[0].split_family == "LocationTeamDashboard"
        assert response.splits[0].pts == 4850.0
    finally:
        session.close()


def test_team_splits_raises_404_for_missing_persisted_rows():
    session = make_session()
    try:
        session.add(Team(id=1610612738, abbreviation="BOS", name="Boston Celtics"))
        session.commit()

        try:
            team_splits("BOS", season="2025-26", db=session)
            assert False, "Expected missing split rows to raise HTTPException"
        except HTTPException as exc:
            assert exc.status_code == 404
            assert "No official team splits" in exc.detail
    finally:
        session.close()
