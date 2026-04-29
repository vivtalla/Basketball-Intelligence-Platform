"""Sprint 77 — Playoff leaders endpoint sorts by playoff PPG and computes a
correct trend symbol from recent vs season pts.
"""
from pathlib import Path
import sys
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import Player, PlayerGameLog, SeasonStat, Team  # noqa: E402
from routers.playoffs import get_playoff_leaders  # noqa: E402
from services.playoff_leaders_service import compute_playoff_leaders  # noqa: E402


def _make_session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _ppg_from_line(line: str) -> float:
    """Extract the PPG number from the formatted line, e.g. '31.4 PPG · ...' -> 31.4."""
    head = line.split(" PPG", 1)[0]
    return float(head.split()[-1])


def _seed_eight_playoff_scorers(session, season: str = "2024-25"):
    team = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics", city="Boston")
    session.add(team)
    # 8 players with descending playoff PPG so the sort order is deterministic.
    ppgs = [33.0, 28.5, 25.4, 22.1, 19.8, 17.0, 14.5, 11.2]
    for idx, pts in enumerate(ppgs, start=1):
        session.add(Player(id=idx, full_name="Player {0}".format(idx), is_active=True))
        session.add(
            SeasonStat(
                player_id=idx,
                season=season,
                team_abbreviation="BOS",
                is_playoff=True,
                gp=10,
                pts=int(pts * 10),
                pts_pg=pts,
                ast_pg=5.0,
                ts_pct=0.58,
            )
        )
    session.commit()


def _seed_trend_player(
    session,
    season: str,
    player_id: int,
    season_avg: float,
    last_three_pts: list,
):
    """Create a single playoff-PPG player with controlled per-game pts history."""
    if not session.query(Team).filter_by(id=1610612738).first():
        session.add(Team(id=1610612738, abbreviation="BOS", name="Boston Celtics", city="Boston"))
    session.add(Player(id=player_id, full_name="Trend Player {0}".format(player_id), is_active=True))
    session.add(
        SeasonStat(
            player_id=player_id,
            season=season,
            team_abbreviation="BOS",
            is_playoff=True,
            gp=10,
            pts=int(season_avg * 10),
            pts_pg=season_avg,
            ast_pg=5.0,
            ts_pct=0.58,
        )
    )
    # Insert per-game logs in reverse-chronological order (most recent first).
    base_day = 28
    for idx, pts in enumerate(last_three_pts):
        # Decreasing day number → earlier date for older games when ordered desc.
        game_date = date(2026, 4, base_day - idx)
        session.add(
            PlayerGameLog(
                player_id=player_id,
                game_id="00425{0:02d}{1:02d}".format(player_id, idx),
                season=season,
                season_type="Playoffs",
                game_date=game_date,
                pts=pts,
            )
        )
    session.commit()


def test_leaders_sorted_by_playoff_ppg_desc():
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        _seed_eight_playoff_scorers(session)
        response = get_playoff_leaders(season="2024-25", limit=5, db=session)
    finally:
        session.close()

    assert response.season == "2024-25"
    assert len(response.leaders) == 5
    leaders = response.leaders
    # Ranks should be 1..5
    assert [leader.rank for leader in leaders] == [1, 2, 3, 4, 5]
    # PPG should be strictly descending.
    ppgs = [_ppg_from_line(leader.line) for leader in leaders]
    assert ppgs == sorted(ppgs, reverse=True), "leaders are not PPG-desc: {0}".format(ppgs)
    assert ppgs[0] > ppgs[1], "expected leaders[0].ppg > leaders[1].ppg"


def test_trend_matches_recent_vs_baseline_delta():
    SessionLocal = _make_session_factory()
    season = "2024-25"

    # Player 101 — last-3 avg = 35 PPG vs season 28 → ▲
    session_up = SessionLocal()
    try:
        _seed_trend_player(session_up, season, player_id=101, season_avg=28.0, last_three_pts=[36, 34, 35])
        leaders_up = compute_playoff_leaders(session_up, season, limit=5)
    finally:
        session_up.close()
    entry_up = next((leader for leader in leaders_up if leader.player_id == 101), None)
    assert entry_up is not None, "player 101 missing from leaders"
    assert entry_up.trend == "▲", "expected up-trend, got {0!r}".format(entry_up.trend)

    # Player 102 — last-3 avg = 22 PPG vs season 28 → ▼
    session_down = SessionLocal()
    try:
        _seed_trend_player(session_down, season, player_id=102, season_avg=28.0, last_three_pts=[20, 24, 22])
        leaders_down = compute_playoff_leaders(session_down, season, limit=5)
    finally:
        session_down.close()
    entry_down = next((leader for leader in leaders_down if leader.player_id == 102), None)
    assert entry_down is not None, "player 102 missing from leaders"
    assert entry_down.trend == "▼", "expected down-trend, got {0!r}".format(entry_down.trend)

    # Player 103 — last-3 avg = 29 PPG vs season 28 → →
    session_flat = SessionLocal()
    try:
        _seed_trend_player(session_flat, season, player_id=103, season_avg=28.0, last_three_pts=[28, 30, 29])
        leaders_flat = compute_playoff_leaders(session_flat, season, limit=5)
    finally:
        session_flat.close()
    entry_flat = next((leader for leader in leaders_flat if leader.player_id == 103), None)
    assert entry_flat is not None, "player 103 missing from leaders"
    assert entry_flat.trend == "→", "expected flat trend, got {0!r}".format(entry_flat.trend)
