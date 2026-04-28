"""Sprint 73 — playoff API route + simulator tests.

Three scenarios:

1. Bracket route returns a 4-east + 4-west shape for a fully-seeded first round.
2. Single-series route returns games sorted by ``series_game_num``.
3. Simulator output is deterministic for a given series_id.

We call the route handlers directly with a SQLite in-memory session rather
than spinning up the full FastAPI app + ``TestClient``, because ``httpx`` is
not part of the project's pinned dev dependencies. The handlers are normal
Python functions and the response models round-trip identically either way.
"""
from pathlib import Path
import sys
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GameLog, PlayoffSeries, Team  # noqa: E402
from routers.playoffs import (  # noqa: E402
    get_bracket,
    get_series,
    get_series_simulation,
)
from services.playoff_simulator_service import simulate_series  # noqa: E402


def _make_session_factory():
    """Build an in-memory SQLite session factory shared across sessions.

    StaticPool + a shared connection is required for in-memory SQLite when
    multiple sessions need to see each other's writes (e.g. seeding in one
    session and reading in another).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


# Use real NBA team_ids so the conference fallback (EAST/WEST abbr map) works.
EAST_TEAMS = [
    (1610612738, "BOS", "Boston Celtics"),  # 1
    (1610612752, "NYK", "New York Knicks"),  # 2
    (1610612749, "MIL", "Milwaukee Bucks"),  # 3
    (1610612755, "PHI", "Philadelphia 76ers"),  # 4
    (1610612748, "MIA", "Miami Heat"),  # 5
    (1610612739, "CLE", "Cleveland Cavaliers"),  # 6
    (1610612761, "TOR", "Toronto Raptors"),  # 7
    (1610612765, "DET", "Detroit Pistons"),  # 8
]
WEST_TEAMS = [
    (1610612760, "OKC", "Oklahoma City Thunder"),  # 1
    (1610612743, "DEN", "Denver Nuggets"),  # 2
    (1610612750, "MIN", "Minnesota Timberwolves"),  # 3
    (1610612746, "LAC", "LA Clippers"),  # 4
    (1610612744, "GSW", "Golden State Warriors"),  # 5
    (1610612742, "DAL", "Dallas Mavericks"),  # 6
    (1610612763, "MEM", "Memphis Grizzlies"),  # 7
    (1610612745, "HOU", "Houston Rockets"),  # 8
]


def _seed_first_round_bracket(session, season="2024-25"):
    teams = EAST_TEAMS + WEST_TEAMS
    for tid, abbr, name in teams:
        session.add(Team(id=tid, abbreviation=abbr, name=name))
    session.commit()

    # Standard 1-vs-8 / 4-vs-5 / 3-vs-6 / 2-vs-7 first-round pairings.
    pairings = [(1, 8), (4, 5), (3, 6), (2, 7)]

    east_series = []
    for top_idx, bot_idx in pairings:
        top = EAST_TEAMS[top_idx - 1]
        bot = EAST_TEAMS[bot_idx - 1]
        east_series.append(
            PlayoffSeries(
                season=season,
                round=1,
                series_id=f"{season}-E-R1-{top[1]}-{bot[1]}",
                top_seed_team_id=top[0],
                bottom_seed_team_id=bot[0],
                top_seed=top_idx,
                bottom_seed=bot_idx,
                top_wins=0,
                bottom_wins=0,
                status="scheduled",
            )
        )

    west_series = []
    for top_idx, bot_idx in pairings:
        top = WEST_TEAMS[top_idx - 1]
        bot = WEST_TEAMS[bot_idx - 1]
        west_series.append(
            PlayoffSeries(
                season=season,
                round=1,
                series_id=f"{season}-W-R1-{top[1]}-{bot[1]}",
                top_seed_team_id=top[0],
                bottom_seed_team_id=bot[0],
                top_seed=top_idx,
                bottom_seed=bot_idx,
                top_wins=0,
                bottom_wins=0,
                status="scheduled",
            )
        )

    session.add_all(east_series + west_series)
    session.commit()


def test_bracket_returns_correct_shape_for_first_round():
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        _seed_first_round_bracket(session, season="2024-25")
        bracket = get_bracket(season="2024-25", db=session)
    finally:
        session.close()

    assert bracket.season == "2024-25"
    assert len(bracket.east) == 4
    assert len(bracket.west) == 4
    assert bracket.finals is None

    east_abbrs = {s.top_seed_team_abbr for s in bracket.east}
    assert east_abbrs == {"BOS", "NYK", "MIL", "PHI"}
    west_abbrs = {s.top_seed_team_abbr for s in bracket.west}
    assert west_abbrs == {"OKC", "DEN", "MIN", "LAC"}


def _seed_series_with_games(session, season="2024-25"):
    okc = Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder")
    hou = Team(id=1610612745, abbreviation="HOU", name="Houston Rockets")
    session.add_all([okc, hou])
    session.commit()

    series_id = f"{season}-W-R1-OKC-HOU"
    series = PlayoffSeries(
        season=season,
        round=1,
        series_id=series_id,
        top_seed_team_id=okc.id,
        bottom_seed_team_id=hou.id,
        top_seed=1,
        bottom_seed=8,
        top_wins=3,
        bottom_wins=1,
        status="active",
    )
    session.add(series)

    # Insert games out of order to verify ordering by series_game_num.
    games_meta = [
        (4, "0042500004", date(2026, 4, 27), okc.id, hou.id, 116, 102),
        (1, "0042500001", date(2026, 4, 18), okc.id, hou.id, 110, 99),
        (3, "0042500003", date(2026, 4, 24), hou.id, okc.id, 105, 112),
        (2, "0042500002", date(2026, 4, 21), okc.id, hou.id, 108, 101),
    ]
    for game_num, gid, gdate, home_id, away_id, hs, as_ in games_meta:
        session.add(
            GameLog(
                game_id=gid,
                season=season,
                game_date=gdate,
                home_team_id=home_id,
                away_team_id=away_id,
                home_score=hs,
                away_score=as_,
                season_type="Playoffs",
                series_id=series_id,
                series_game_num=game_num,
            )
        )
    session.commit()
    return series_id


def test_series_route_returns_games_in_order():
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        series_id = _seed_series_with_games(session, season="2024-25")
        response = get_series(series_id=series_id, db=session)
    finally:
        session.close()

    assert response.season == "2024-25"
    assert response.top_seed_team_abbr == "OKC"
    assert response.bottom_seed_team_abbr == "HOU"
    assert response.top_wins == 3
    assert response.bottom_wins == 1
    nums = [g.series_game_num for g in response.games]
    assert nums == [1, 2, 3, 4], f"games not sorted by series_game_num: {nums}"


def test_series_simulation_deterministic():
    SessionLocal = _make_session_factory()
    setup_session = SessionLocal()
    try:
        series_id = _seed_series_with_games(setup_session, season="2024-25")
    finally:
        setup_session.close()

    session_a = SessionLocal()
    try:
        sim_a = simulate_series(session_a, series_id)
    finally:
        session_a.close()

    session_b = SessionLocal()
    try:
        sim_b = simulate_series(session_b, series_id)
    finally:
        session_b.close()

    payload_a = sim_a.model_dump()
    payload_b = sim_b.model_dump()
    assert payload_a == payload_b
    assert 0.0 <= sim_a.top_seed_series_win_prob <= 1.0
    assert 0.0 <= sim_a.bottom_seed_series_win_prob <= 1.0

    # Also exercise the route wrapper to make sure it's wired correctly.
    session_c = SessionLocal()
    try:
        route_resp = get_series_simulation(series_id=series_id, db=session_c)
    finally:
        session_c.close()
    assert route_resp.series_id == series_id
