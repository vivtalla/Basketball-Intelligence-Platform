from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from datetime import date, timedelta

from db.models import Base, GameTeamStat, Team, TeamSeasonStat, TeamStanding, WarehouseGame
from routers.standings import _standings_from_team_season_stats, get_standings


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def test_standings_falls_back_to_official_team_season_stats():
    session = make_session()
    try:
        session.add_all(
            [
                Team(id=1610612738, abbreviation="BOS", name="Boston Celtics"),
                Team(id=1610612752, abbreviation="NYK", name="New York Knicks"),
                Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder"),
                Team(id=1610612743, abbreviation="DEN", name="Denver Nuggets"),
                WarehouseGame(
                    game_id="0022500001",
                    season="2025-26",
                    game_date=date.today() - timedelta(days=1),
                    status="final",
                    home_team_abbreviation="OKC",
                    away_team_abbreviation="DEN",
                    home_score=120,
                    away_score=110,
                ),
                WarehouseGame(
                    game_id="0022500002",
                    season="2025-26",
                    game_date=date.today() - timedelta(days=2),
                    status="final",
                    home_team_abbreviation="BOS",
                    away_team_abbreviation="OKC",
                    home_score=112,
                    away_score=118,
                ),
                WarehouseGame(
                    game_id="0022500003",
                    season="2025-26",
                    game_date=date.today() - timedelta(days=3),
                    status="final",
                    home_team_abbreviation="OKC",
                    away_team_abbreviation="NYK",
                    home_score=105,
                    away_score=111,
                ),
                GameTeamStat(
                    game_id="0022500001",
                    season="2025-26",
                    team_id=1610612760,
                    team_abbreviation="OKC",
                    is_home=True,
                    won=True,
                    pts=120,
                ),
                GameTeamStat(
                    game_id="0022500002",
                    season="2025-26",
                    team_id=1610612760,
                    team_abbreviation="OKC",
                    is_home=False,
                    won=True,
                    pts=118,
                ),
                GameTeamStat(
                    game_id="0022500003",
                    season="2025-26",
                    team_id=1610612760,
                    team_abbreviation="OKC",
                    is_home=True,
                    won=False,
                    pts=105,
                ),
                TeamSeasonStat(
                    team_id=1610612738,
                    season="2025-26",
                    is_playoff=False,
                    w=53,
                    l=25,
                    w_pct=0.679,
                    pts_pg=114.6,
                    plus_minus_pg=7.6,
                ),
                TeamSeasonStat(
                    team_id=1610612752,
                    season="2025-26",
                    is_playoff=False,
                    w=51,
                    l=28,
                    w_pct=0.646,
                    pts_pg=116.8,
                    plus_minus_pg=6.5,
                ),
                TeamSeasonStat(
                    team_id=1610612760,
                    season="2025-26",
                    is_playoff=False,
                    gp=78,
                    w=62,
                    l=16,
                    w_pct=0.795,
                    pts_pg=119.2,
                    reb_pg=44.2,
                    ast_pg=27.1,
                    tov_pg=11.4,
                    stl_pg=8.8,
                    blk_pg=5.6,
                    fg_pct=0.489,
                    fg3_pct=0.382,
                    ft_pct=0.814,
                    plus_minus_pg=11.7,
                    off_rating=121.4,
                    def_rating=109.7,
                    net_rating=11.7,
                    pace=99.3,
                    efg_pct=0.574,
                    ts_pct=0.612,
                    pie=0.571,
                    oreb_pct=0.271,
                    dreb_pct=0.724,
                    tov_pct=0.112,
                    ast_pct=0.641,
                    off_rating_rank=1,
                    def_rating_rank=2,
                    net_rating_rank=1,
                    pace_rank=12,
                    efg_pct_rank=3,
                    ts_pct_rank=2,
                    oreb_pct_rank=8,
                    tov_pct_rank=4,
                ),
                TeamSeasonStat(
                    team_id=1610612743,
                    season="2025-26",
                    is_playoff=False,
                    w=50,
                    l=28,
                    w_pct=0.641,
                    pts_pg=121.6,
                    plus_minus_pg=4.7,
                ),
            ]
        )
        session.commit()

        entries = _standings_from_team_season_stats("2025-26", session)

        assert entries is not None
        by_abbr = {entry.abbreviation: entry for entry in entries}
        assert by_abbr["BOS"].conference == "East"
        assert by_abbr["BOS"].playoff_rank == 1
        assert by_abbr["NYK"].games_back == 2.5
        assert by_abbr["OKC"].conference == "West"
        assert by_abbr["OKC"].playoff_rank == 1
        assert by_abbr["DEN"].games_back == 12.0
        assert by_abbr["OKC"].team_city == ""
        assert by_abbr["OKC"].team_name == "Oklahoma City Thunder"
        assert by_abbr["OKC"].gp == 78
        assert by_abbr["OKC"].reb_pg == 44.2
        assert by_abbr["OKC"].ast_pg == 27.1
        assert by_abbr["OKC"].fg3_pct == 0.382
        assert by_abbr["OKC"].opp_pts_pg == 107.5
        assert by_abbr["OKC"].diff_pts_pg == 11.7
        assert by_abbr["OKC"].off_rating == 121.4
        assert by_abbr["OKC"].def_rating == 109.7
        assert by_abbr["OKC"].net_rating == 11.7
        assert by_abbr["OKC"].pace == 99.3
        assert by_abbr["OKC"].efg_pct == 0.574
        assert by_abbr["OKC"].ts_pct == 0.612
        assert by_abbr["OKC"].pie == 0.571
        assert by_abbr["OKC"].off_rating_rank == 1
        assert by_abbr["OKC"].def_rating_rank == 2
        assert by_abbr["OKC"].net_rating_rank == 1
        assert by_abbr["OKC"].l10 == "2-1"
        assert by_abbr["OKC"].home_record == "1-1"
        assert by_abbr["OKC"].road_record == "1-0"
        assert by_abbr["OKC"].current_streak == "W2"
        assert by_abbr["OKC"].recent_trend is not None
        assert by_abbr["OKC"].recent_trend.last_10_record == "2-1"
        assert by_abbr["OKC"].recent_trend.avg_margin == 3.3
        assert by_abbr["OKC"].recent_trend.direction == "positive"
        assert [game.margin for game in by_abbr["OKC"].recent_trend.games] == [-6, 6, 10]
        assert [game.opponent_abbreviation for game in by_abbr["OKC"].recent_trend.games] == ["NYK", "BOS", "DEN"]
    finally:
        session.close()


def test_standings_prefers_official_rows_when_snapshots_are_less_complete():
    session = make_session()
    try:
        session.add_all(
            [
                Team(id=1610612738, abbreviation="BOS", name="Boston Celtics"),
                Team(id=1610612752, abbreviation="NYK", name="New York Knicks"),
                TeamSeasonStat(
                    team_id=1610612738,
                    season="2025-26",
                    is_playoff=False,
                    w=53,
                    l=25,
                    w_pct=0.679,
                    pts_pg=114.6,
                    plus_minus_pg=7.6,
                ),
                TeamSeasonStat(
                    team_id=1610612752,
                    season="2025-26",
                    is_playoff=False,
                    w=51,
                    l=28,
                    w_pct=0.646,
                    pts_pg=116.8,
                    plus_minus_pg=6.5,
                ),
                TeamStanding(
                    team_id=1610612738,
                    season="2025-26",
                    snapshot_date=date.today(),
                    wins=18,
                    losses=20,
                    conference="East",
                    division="Atlantic",
                ),
                TeamStanding(
                    team_id=1610612752,
                    season="2025-26",
                    snapshot_date=date.today(),
                    wins=19,
                    losses=20,
                    conference="East",
                    division="Atlantic",
                ),
            ]
        )
        session.commit()

        entries = get_standings("2025-26", session)

        by_abbr = {entry.abbreviation: entry for entry in entries}
        assert by_abbr["BOS"].wins == 53
        assert by_abbr["BOS"].playoff_rank == 1
        assert by_abbr["NYK"].games_back == 2.5
    finally:
        session.close()


def test_standings_keeps_snapshot_fallback_without_official_rows():
    session = make_session()
    try:
        session.add_all(
            [
                Team(
                    id=1610612738,
                    abbreviation="BOS",
                    city="Boston",
                    name="Celtics",
                ),
                Team(
                    id=1610612752,
                    abbreviation="NYK",
                    city="New York",
                    name="Knicks",
                ),
                TeamStanding(
                    team_id=1610612738,
                    season="2023-24",
                    snapshot_date=date.today(),
                    wins=64,
                    losses=18,
                    home_wins=37,
                    home_losses=4,
                    road_wins=27,
                    road_losses=14,
                    last_10_wins=8,
                    last_10_losses=2,
                    current_streak=2,
                    streak_type="W",
                    conference="East",
                    division="Atlantic",
                ),
                TeamStanding(
                    team_id=1610612752,
                    season="2023-24",
                    snapshot_date=date.today(),
                    wins=50,
                    losses=32,
                    home_wins=27,
                    home_losses=14,
                    road_wins=23,
                    road_losses=18,
                    last_10_wins=6,
                    last_10_losses=4,
                    current_streak=-1,
                    streak_type="L",
                    conference="East",
                    division="Atlantic",
                ),
            ]
        )
        session.commit()

        entries = get_standings("2023-24", session)

        by_abbr = {entry.abbreviation: entry for entry in entries}
        assert by_abbr["BOS"].wins == 64
        assert by_abbr["BOS"].home_record == "37-4"
        assert by_abbr["BOS"].l10 == "8-2"
        assert by_abbr["BOS"].current_streak == "W2"
        assert by_abbr["BOS"].off_rating is None
        assert by_abbr["BOS"].recent_trend is None
    finally:
        session.close()
