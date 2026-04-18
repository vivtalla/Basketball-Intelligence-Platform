from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from db.database import Base  # noqa: E402
from db.models import Player, PlayerGravityStat, SeasonStat, Team  # noqa: E402
from routers.leaderboards import leaderboard  # noqa: E402


def make_session():
    engine = create_engine("sqlite:///:memory:")
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_leaderboard_supports_total_box_score_stats():
    session = make_session()
    try:
        team = Team(id=1610612747, abbreviation="LAL", name="Los Angeles Lakers")
        player_a = Player(id=1, full_name="Alpha Scorer", first_name="Alpha", last_name="Scorer", team_id=team.id, is_active=True)
        player_b = Player(id=2, full_name="Beta Scorer", first_name="Beta", last_name="Scorer", team_id=team.id, is_active=True)
        session.add_all([team, player_a, player_b])
        session.flush()

        session.add_all(
            [
                SeasonStat(
                    player_id=player_a.id,
                    season="2025-26",
                    team_abbreviation="LAL",
                    is_playoff=False,
                    gp=60,
                    pts=1800,
                    pts_pg=30.0,
                ),
                SeasonStat(
                    player_id=player_b.id,
                    season="2025-26",
                    team_abbreviation="LAL",
                    is_playoff=False,
                    gp=62,
                    pts=1500,
                    pts_pg=24.2,
                ),
            ]
        )
        session.commit()

        response = leaderboard(season="2025-26", stat="pts", season_type="Regular Season", limit=25, min_gp=15, team=None, db=session)

        assert response.stat == "pts"
        assert len(response.entries) == 2
        assert response.entries[0].player_name == "Alpha Scorer"
        assert response.entries[0].stat_value == 1800.0
    finally:
        session.close()


def test_leaderboard_derives_shooting_pcts_from_raw_counts_when_stored_column_is_null():
    """Rows synced before efg_pct was computed should still show the derived value."""
    session = make_session()
    try:
        team = Team(id=1610612747, abbreviation="LAL", name="Los Angeles Lakers")
        player = Player(id=3, full_name="Big Man", first_name="Big", last_name="Man", team_id=team.id, is_active=True)
        session.add_all([team, player])
        session.flush()

        stat = SeasonStat(
            player_id=player.id,
            season="2025-26",
            team_abbreviation="LAL",
            is_playoff=False,
            gp=65,
            fgm=400, fga=600,
            fg3m=0, fg3a=0,
            ftm=150, fta=200,
            pts_pg=14.5,
        )
        session.add(stat)
        session.flush()

        # efg_pct has no Column default so it is genuinely NULL after insert.
        # Force fg_pct / ft_pct to NULL as well to test derivation for both paths.
        session.execute(
            text("UPDATE season_stats SET efg_pct = NULL, fg_pct = NULL, ft_pct = NULL WHERE player_id = 3")
        )
        session.commit()
        session.expire_all()

        response = leaderboard(season="2025-26", stat="pts_pg", season_type="Regular Season", limit=25, min_gp=15, team=None, db=session)
        assert len(response.entries) == 1
        mv = response.entries[0].metric_values

        assert mv.get("fg_pct") == round(400 / 600, 3)
        assert mv.get("ft_pct") == round(150 / 200, 3)
        assert mv.get("efg_pct") == round(400 / 600, 3)   # no 3s: efg = fgm/fga
        assert mv.get("fg3_pct") == 0.0                   # stored 0 (default=0, no 3PA)
    finally:
        session.close()


def test_leaderboard_supports_gravity_metrics():
    session = make_session()
    try:
        team = Team(id=1610612747, abbreviation="LAL", name="Los Angeles Lakers")
        player_a = Player(id=4, full_name="Alpha Gravity", first_name="Alpha", last_name="Gravity", team_id=team.id, is_active=True)
        player_b = Player(id=5, full_name="Beta Gravity", first_name="Beta", last_name="Gravity", team_id=team.id, is_active=True)
        session.add_all([team, player_a, player_b])
        session.flush()

        session.add_all(
            [
                SeasonStat(
                    player_id=player_a.id,
                    season="2025-26",
                    team_abbreviation="LAL",
                    is_playoff=False,
                    gp=60,
                    min_total=1900,
                    pts_pg=22.0,
                ),
                SeasonStat(
                    player_id=player_b.id,
                    season="2025-26",
                    team_abbreviation="LAL",
                    is_playoff=False,
                    gp=62,
                    min_total=1850,
                    pts_pg=24.0,
                ),
                PlayerGravityStat(
                    player_id=player_a.id,
                    season="2025-26",
                    season_type="Regular Season",
                    source="courtvue_proxy",
                    overall_gravity=72.5,
                    shooting_gravity=80.0,
                    gravity_confidence="medium",
                    source_note="Test proxy.",
                    warnings=[],
                ),
                PlayerGravityStat(
                    player_id=player_b.id,
                    season="2025-26",
                    season_type="Regular Season",
                    source="courtvue_proxy",
                    overall_gravity=61.0,
                    shooting_gravity=65.0,
                    gravity_confidence="medium",
                    source_note="Test proxy.",
                    warnings=[],
                ),
            ]
        )
        session.commit()

        response = leaderboard(
            season="2025-26",
            stat="overall_gravity",
            season_type="Regular Season",
            limit=25,
            min_gp=15,
            team=None,
            db=session,
        )

        assert response.stat == "overall_gravity"
        assert response.entries[0].player_name == "Alpha Gravity"
        assert response.entries[0].stat_value == 72.5
        assert response.entries[0].metric_values["shooting_gravity"] == 80.0
    finally:
        session.close()
