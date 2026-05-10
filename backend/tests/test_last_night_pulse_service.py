"""Sprint 96 — LastNightPulse service tests.

Three guarantees:
  1. An empty (or stale) DB returns all-None tiles.
  2. The hero tile picks the highest Game Score from playoff PlayerGameLog
     rows in the last ~36h.
  3. Series momentum prefers the most recently updated PlayoffSeries row.
"""
from datetime import date, datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    GameLog,
    Player,
    PlayerGameLog,
    PlayoffSeries,
    Team,
)
from services.last_night_pulse_service import (  # noqa: E402
    _game_score,
    compute_last_night_pulse,
)


def _make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def test_empty_db_returns_empty_tiles():
    session = _make_session()
    today = date(2026, 5, 9)
    now = datetime(2026, 5, 9, 12, 0, 0)

    result = compute_last_night_pulse(session, "2025-26", today=today, now=now)

    assert result.season == "2025-26"
    assert result.last_night_hero is None
    assert result.tonight_headliner is None
    assert result.series_momentum is None


def test_hero_picks_highest_game_score():
    session = _make_session()
    session.add(
        Team(
            id=1610612738,
            abbreviation="BOS",
            name="Boston Celtics",
            city="Boston",
        )
    )
    session.add(
        Team(
            id=1610612747,
            abbreviation="LAL",
            name="Los Angeles Lakers",
            city="Los Angeles",
        )
    )
    session.add(Player(id=101, full_name="Alpha Star", is_active=True))
    session.add(Player(id=102, full_name="Beta Player", is_active=True))
    session.add(Player(id=103, full_name="Gamma Player", is_active=True))

    today = date(2026, 5, 9)
    yesterday = today - timedelta(days=1)

    # Three logs from yesterday's game. Alpha's line dominates by Game Score.
    session.add(
        PlayerGameLog(
            player_id=101,
            game_id="0042500301",
            season="2025-26",
            season_type="Playoffs",
            game_date=yesterday,
            matchup="BOS @ LAL",
            pts=42,
            reb=8,
            ast=11,
            fgm=15,
            fga=22,
            fg3m=4,
            fg3a=8,
            ftm=8,
            fta=8,
            oreb=1,
            dreb=7,
            stl=2,
            blk=1,
            pf=2,
            tov=3,
        )
    )
    session.add(
        PlayerGameLog(
            player_id=102,
            game_id="0042500301",
            season="2025-26",
            season_type="Playoffs",
            game_date=yesterday,
            matchup="LAL vs. BOS",
            pts=28,
            reb=5,
            ast=4,
            fgm=10,
            fga=20,
            fg3m=2,
            fg3a=6,
            ftm=6,
            fta=8,
            oreb=0,
            dreb=5,
            stl=1,
            blk=0,
            pf=3,
            tov=4,
        )
    )
    session.add(
        PlayerGameLog(
            player_id=103,
            game_id="0042500301",
            season="2025-26",
            season_type="Playoffs",
            game_date=yesterday,
            matchup="BOS @ LAL",
            pts=14,
            reb=3,
            ast=2,
            fgm=5,
            fga=12,
            fg3m=1,
            fg3a=4,
            ftm=3,
            fta=4,
            oreb=0,
            dreb=3,
            stl=0,
            blk=1,
            pf=4,
            tov=2,
        )
    )
    session.commit()

    now = datetime(2026, 5, 9, 12, 0, 0)
    result = compute_last_night_pulse(session, "2025-26", today=today, now=now)

    assert result.last_night_hero is not None
    hero = result.last_night_hero
    assert hero.player_id == 101
    assert hero.player_name == "Alpha Star"
    assert hero.pts == 42
    assert hero.reb == 8
    assert hero.ast == 11
    assert hero.team_abbreviation == "BOS"
    assert hero.line == "42 PTS · 8 REB · 11 AST"
    assert hero.href == "/games/0042500301"

    # Sanity-check the ranking: Alpha's game score must dominate the others.
    other_logs = (
        session.query(PlayerGameLog)
        .filter(PlayerGameLog.player_id != 101)
        .all()
    )
    other_scores = [_game_score(lg) for lg in other_logs]
    assert hero.game_score >= max(other_scores)


def test_series_momentum_picks_most_recent_update():
    session = _make_session()
    session.add(
        Team(
            id=1610612738,
            abbreviation="BOS",
            name="Boston Celtics",
            city="Boston",
        )
    )
    session.add(
        Team(
            id=1610612747,
            abbreviation="LAL",
            name="Los Angeles Lakers",
            city="Los Angeles",
        )
    )
    session.add(
        Team(
            id=1610612744,
            abbreviation="GSW",
            name="Golden State Warriors",
            city="Golden State",
        )
    )
    session.add(
        Team(
            id=1610612752,
            abbreviation="NYK",
            name="New York Knicks",
            city="New York",
        )
    )

    older_update = datetime(2026, 5, 8, 8, 0, 0)
    newer_update = datetime(2026, 5, 9, 22, 0, 0)
    session.add(
        PlayoffSeries(
            season="2025-26",
            round=2,
            series_id="2025-26-E-R2-BOS-NYK",
            top_seed_team_id=1610612738,
            bottom_seed_team_id=1610612752,
            top_seed=1,
            bottom_seed=4,
            top_wins=2,
            bottom_wins=1,
            status="active",
            updated_at=older_update,
        )
    )
    session.add(
        PlayoffSeries(
            season="2025-26",
            round=2,
            series_id="2025-26-W-R2-LAL-GSW",
            top_seed_team_id=1610612747,
            bottom_seed_team_id=1610612744,
            top_seed=2,
            bottom_seed=3,
            top_wins=3,
            bottom_wins=2,
            status="active",
            updated_at=newer_update,
        )
    )
    session.commit()

    now = datetime(2026, 5, 10, 0, 0, 0)
    result = compute_last_night_pulse(
        session, "2025-26", today=date(2026, 5, 10), now=now
    )

    assert result.series_momentum is not None
    momentum = result.series_momentum
    assert momentum.series_id == "2025-26-W-R2-LAL-GSW"
    assert momentum.matchup == "LAL vs GSW"
    assert "LAL leads 3-2" in momentum.summary
    assert momentum.href == "/pre-read?series_id=2025-26-W-R2-LAL-GSW"


def test_tonight_headliner_picks_lowest_seed_sum():
    """Marquee matchup = lowest combined seed sum (1+4=5 beats 2+3=5? no, equal — pick by game_id).
    Test 1v8 (seed sum 9) vs 4v5 (seed sum 9) won't differentiate; instead use 1v4 vs 2v3.
    Use 1v8 vs 4v5: 9 vs 9 — same. Use 1v8 vs 2v7: 9 vs 9 still same. Pick clearly
    differentiated 1v4 (seed sum 5) vs 3v6 (seed sum 9)."""
    session = _make_session()
    for team_id, abbr, name, city in [
        (1610612738, "BOS", "Boston Celtics", "Boston"),
        (1610612747, "LAL", "Los Angeles Lakers", "Los Angeles"),
        (1610612744, "GSW", "Golden State Warriors", "Golden State"),
        (1610612752, "NYK", "New York Knicks", "New York"),
    ]:
        session.add(Team(id=team_id, abbreviation=abbr, name=name, city=city))

    today = date(2026, 5, 9)
    # Marquee: 1v4 series — sum 5
    session.add(
        PlayoffSeries(
            season="2025-26",
            round=2,
            series_id="2025-26-E-R2-BOS-NYK",
            top_seed_team_id=1610612738,
            bottom_seed_team_id=1610612752,
            top_seed=1,
            bottom_seed=4,
            top_wins=2,
            bottom_wins=1,
            status="active",
        )
    )
    # Underdog: 3v6 series — sum 9
    session.add(
        PlayoffSeries(
            season="2025-26",
            round=2,
            series_id="2025-26-W-R2-LAL-GSW",
            top_seed_team_id=1610612747,
            bottom_seed_team_id=1610612744,
            top_seed=3,
            bottom_seed=6,
            top_wins=1,
            bottom_wins=1,
            status="active",
        )
    )
    # Two playoff games tonight, scheduled (home_score is null).
    session.add(
        GameLog(
            game_id="0042500999",
            season="2025-26",
            game_date=today,
            home_team_id=1610612738,
            away_team_id=1610612752,
            season_type="Playoffs",
            series_id="2025-26-E-R2-BOS-NYK",
        )
    )
    session.add(
        GameLog(
            game_id="0042500998",
            season="2025-26",
            game_date=today,
            home_team_id=1610612747,
            away_team_id=1610612744,
            season_type="Playoffs",
            series_id="2025-26-W-R2-LAL-GSW",
        )
    )
    session.commit()

    now = datetime(2026, 5, 9, 12, 0, 0)
    result = compute_last_night_pulse(session, "2025-26", today=today, now=now)

    assert result.tonight_headliner is not None
    head = result.tonight_headliner
    assert head.series_id == "2025-26-E-R2-BOS-NYK"
    assert head.home_team_abbr == "BOS"
    assert head.away_team_abbr == "NYK"
    assert head.matchup == "NYK at BOS"
    assert head.seeds_label == "#1 vs #4"
    assert head.series_state == "BOS leads 2-1"
    assert head.href == "/pre-read?series_id=2025-26-E-R2-BOS-NYK"
