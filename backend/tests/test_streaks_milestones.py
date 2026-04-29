"""Sprint 78 CF5 — streaks & milestones service + route tests.

Covers:

1. ``compute_player_streaks`` correctly counts consecutive 30+ point games
   walking backwards from the most-recent game.
2. ``compute_player_milestones`` returns games_to_milestone consistent
   with the player's current per-game pace.
3. The ``/api/milestones/active-streaks`` endpoint returns rows ordered
   by streak length (descending).

We call the route handlers directly with an in-memory SQLite session
rather than spinning up the full FastAPI app + TestClient, matching the
pattern in ``test_playoff_routes.py`` (httpx isn't a pinned dev dep).
"""
from datetime import date
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    Player,
    PlayerGameLog,
    PlayerStreak,
    SeasonStat,
    Team,
)
from routers.milestones import (  # noqa: E402
    get_active_streaks,
    get_approaching_milestones,
)
from services.milestone_proximity_service import compute_player_milestones  # noqa: E402
from services.streak_detection_service import (  # noqa: E402
    compute_player_streaks,
    fetch_player_longest_active_streak,
)


def _make_session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _seed_team(session, team_id=1610612747, abbr="LAL", name="Los Angeles Lakers"):
    session.add(Team(id=team_id, abbreviation=abbr, name=name, city="Los Angeles"))
    session.flush()


def _seed_player(session, player_id=1, full_name="Test Player", team_id=1610612747):
    session.add(
        Player(id=player_id, full_name=full_name, is_active=True, team_id=team_id)
    )
    session.flush()


def _add_game_log(
    session,
    player_id,
    game_id,
    game_date,
    pts,
    reb=0,
    ast=0,
    fgm=0,
    fga=0,
    fg_pct=None,
    fg3m=0,
    season="2025-26",
    season_type="Regular Season",
):
    session.add(
        PlayerGameLog(
            player_id=player_id,
            game_id=game_id,
            season=season,
            season_type=season_type,
            game_date=game_date,
            pts=pts,
            reb=reb,
            ast=ast,
            fgm=fgm,
            fga=fga,
            fg_pct=fg_pct,
            fg3m=fg3m,
        )
    )


def test_streak_detection_counts_consecutive_30plus_pt_games():
    """A 4-game 30+pt run preceded by a 25-pt game produces a streak of 4."""
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        _seed_team(session)
        _seed_player(session, player_id=42, full_name="Streak Star")

        # Five games oldest → newest. The oldest is a miss (25 pts).
        # The four most-recent qualify as 30+ pt games. Active streak = 4.
        _add_game_log(session, 42, "G001", date(2026, 4, 1), pts=25)
        _add_game_log(session, 42, "G002", date(2026, 4, 5), pts=33)
        _add_game_log(session, 42, "G003", date(2026, 4, 8), pts=41)
        _add_game_log(session, 42, "G004", date(2026, 4, 11), pts=30)
        _add_game_log(session, 42, "G005", date(2026, 4, 14), pts=38)
        session.commit()

        compute_player_streaks(session, 42)
        session.commit()

        rows = (
            session.query(PlayerStreak)
            .filter(PlayerStreak.player_id == 42)
            .all()
        )
        by_type = {r.streak_type: r for r in rows}
        assert "30plus_pts" in by_type, "expected 30plus_pts streak row"
        assert by_type["30plus_pts"].length == 4, (
            "expected 4-game 30+pt streak, got {0}".format(by_type["30plus_pts"].length)
        )
        assert by_type["30plus_pts"].last_game_id == "G005"
        assert by_type["30plus_pts"].started_on == date(2026, 4, 5)

        # Convenience helper picks the longest active streak.
        longest = fetch_player_longest_active_streak(session, 42)
        assert longest is not None
        assert longest["length"] == 4
        assert longest["streak_type"] == "30plus_pts"
    finally:
        session.close()


def test_streak_breaks_when_most_recent_game_misses():
    """If the latest game fails the criterion, no active streak is recorded."""
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        _seed_team(session)
        _seed_player(session, player_id=43, full_name="Cooled Off")

        _add_game_log(session, 43, "G010", date(2026, 4, 1), pts=33)
        _add_game_log(session, 43, "G011", date(2026, 4, 4), pts=35)
        _add_game_log(session, 43, "G012", date(2026, 4, 7), pts=22)  # streak break
        session.commit()

        compute_player_streaks(session, 43)
        session.commit()

        rows = (
            session.query(PlayerStreak)
            .filter(
                PlayerStreak.player_id == 43,
                PlayerStreak.streak_type == "30plus_pts",
            )
            .all()
        )
        assert rows == [], "expected no active 30+pt streak after a miss"
    finally:
        session.close()


def test_milestone_proximity_uses_current_season_pace():
    """A player at 9,800 career pts averaging 25/game should be ~8 games away from 10k."""
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        _seed_team(session)
        _seed_player(session, player_id=99, full_name="Milestone Tracker")

        # Career so far: 9,800 pts / 4,800 reb / 2,800 ast / 800 3PM (regular season).
        session.add(
            SeasonStat(
                player_id=99,
                season="2024-25",
                team_abbreviation="LAL",
                is_playoff=False,
                gp=82,
                pts=9800,
                pts_pg=119.5,  # nonsense but career total is what matters
                reb=4800,
                reb_pg=58.5,
                ast=2800,
                ast_pg=34.1,
                fg3m=800,
            )
        )
        # Current season pace: 25 PPG, 5 APG, 5 RPG, 2 3PM/g over 50 games.
        session.add(
            SeasonStat(
                player_id=99,
                season="2025-26",
                team_abbreviation="LAL",
                is_playoff=False,
                gp=50,
                pts=1250,
                pts_pg=25.0,
                reb=250,
                reb_pg=5.0,
                ast=250,
                ast_pg=5.0,
                fg3m=100,
            )
        )
        session.commit()

        rows = compute_player_milestones(session, player_id=99, season="2025-26")
        session.commit()

        by_key = {r.milestone_key: r for r in rows}
        # Career total = 9,800 + 1,250 = 11,050 → 10k already achieved, 15k pending.
        assert "10k_pts" in by_key
        assert by_key["10k_pts"].current_value == 11050.0
        assert by_key["10k_pts"].games_to_milestone is None  # already achieved

        # 15k pts: 15000 - 11050 = 3950 remaining at 25 PPG → 158 games.
        assert "15k_pts" in by_key
        assert by_key["15k_pts"].games_to_milestone == 158, (
            "expected 158 games to 15k, got {0}".format(by_key["15k_pts"].games_to_milestone)
        )

        # 1k 3PM: 800 + 100 = 900 career, target 1000 → 100 remaining at 2/g → 50 games.
        assert "1k_fg3m" in by_key
        assert by_key["1k_fg3m"].games_to_milestone == 50

        # 5k assists: 2800 + 250 = 3050 career, target 5000 → 1950 remaining at 5/g → 390 games.
        assert "5k_ast" in by_key
        assert by_key["5k_ast"].games_to_milestone == 390
    finally:
        session.close()


def test_active_streaks_endpoint_orders_by_length_desc():
    """The /active-streaks endpoint should return streaks ordered longest-first."""
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        _seed_team(session, team_id=1610612747, abbr="LAL")
        _seed_team(session, team_id=1610612738, abbr="BOS")
        _seed_player(session, player_id=10, full_name="Long Streaker", team_id=1610612747)
        _seed_player(session, player_id=11, full_name="Short Streaker", team_id=1610612738)

        # Player 10 — six straight 30+ pt games.
        for i, day in enumerate([1, 4, 7, 10, 13, 16]):
            _add_game_log(session, 10, "L00{0}".format(i), date(2026, 4, day), pts=33 + i)
        # Player 11 — three straight 30+ pt games.
        for i, day in enumerate([2, 5, 8]):
            _add_game_log(session, 11, "S00{0}".format(i), date(2026, 4, day), pts=31 + i)

        session.commit()

        compute_player_streaks(session, 10)
        compute_player_streaks(session, 11)
        session.commit()

        response = get_active_streaks(season=None, limit=10, db=session)

        assert len(response.streaks) == 2, (
            "expected 2 active streaks, got {0}".format(len(response.streaks))
        )
        # Longest first.
        assert response.streaks[0].player_id == 10
        assert response.streaks[0].length == 6
        assert response.streaks[1].player_id == 11
        assert response.streaks[1].length == 3
        # Read-side label is rendered, not the raw key.
        assert response.streaks[0].streak_label == "30+ point games"
    finally:
        session.close()


def test_approaching_milestones_endpoint_orders_by_proximity():
    """The /approaching endpoint sorts by games_to_milestone ascending."""
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        _seed_team(session)

        # Player A — 50 games from 10k (25 PPG, 9750 pts → 250 / 25 = 10).
        _seed_player(session, player_id=20, full_name="Player A", team_id=1610612747)
        session.add(
            SeasonStat(
                player_id=20, season="2025-26", team_abbreviation="LAL",
                is_playoff=False, gp=50, pts=9750, pts_pg=25.0,
            )
        )
        # Player B — much further away from 10k (8000 pts at 20 PPG).
        _seed_player(session, player_id=21, full_name="Player B", team_id=1610612747)
        session.add(
            SeasonStat(
                player_id=21, season="2025-26", team_abbreviation="LAL",
                is_playoff=False, gp=50, pts=8000, pts_pg=20.0,
            )
        )
        session.commit()

        compute_player_milestones(session, player_id=20, season="2025-26")
        compute_player_milestones(session, player_id=21, season="2025-26")
        session.commit()

        response = get_approaching_milestones(limit=20, db=session)
        # Ordering: nearest first. Player A's 10k pts is 10 games out.
        first = response.milestones[0]
        assert first.player_id == 20
        assert first.milestone_key == "10k_pts"
        assert first.games_to_milestone == 10

        # Player B's nearest milestone (10k pts, 100 games away at 20 PPG) is later in the list.
        keys_for_b = [m for m in response.milestones if m.player_id == 21]
        assert keys_for_b, "Player B should have at least one approaching milestone"
        assert keys_for_b[0].games_to_milestone is not None
        assert keys_for_b[0].games_to_milestone > first.games_to_milestone
    finally:
        session.close()
