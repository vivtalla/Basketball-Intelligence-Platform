"""Sprint 77 — tests for ``compute_series_odds_history`` (Engineer EA3).

Three scenarios:

1. Series with no completed games — returns empty list.
2. Series where the top seed wins games 1, 2, 3 — post-game odds are
   monotonically non-decreasing for the top seed.
3. Regular-season game (no ``series_id``) — assembled detail response has
   ``series_odds_history is None``.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
from typing import List, Optional, Tuple

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    GameLog,
    PlayByPlayEvent,
    PlayoffSeries,
    Team,
    TeamSeasonStat,
    WarehouseGame,
)
from services.game_detail_assembler import assemble_game_detail  # noqa: E402
from services.playoff_simulator_service import (  # noqa: E402
    compute_series_odds_history,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def _seed_two_teams(session) -> Tuple[Team, Team]:
    okc = Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder")
    hou = Team(id=1610612745, abbreviation="HOU", name="Houston Rockets")
    session.add_all([okc, hou])
    session.commit()
    return okc, hou


def _seed_strength_pool(session, top_team: Team, bottom_team: Team, season: str) -> None:
    """Add minimal regular-season stats for both teams + a couple of decoys
    so the simulator has a non-empty league pool to z-score against."""
    # The two series teams.
    session.add_all(
        [
            TeamSeasonStat(
                team_id=top_team.id,
                season=season,
                is_playoff=False,
                gp=82,
                net_rating=8.0,
                pace=99.0,
                ts_pct=0.585,
            ),
            TeamSeasonStat(
                team_id=bottom_team.id,
                season=season,
                is_playoff=False,
                gp=82,
                net_rating=-3.0,
                pace=98.0,
                ts_pct=0.555,
            ),
        ]
    )
    # Two decoys so statistics.pstdev has variance to work with.
    decoy_a = Team(
        id=1610612747,
        abbreviation="LAL",
        name="Los Angeles Lakers",
    )
    decoy_b = Team(
        id=1610612744,
        abbreviation="GSW",
        name="Golden State Warriors",
    )
    session.add_all([decoy_a, decoy_b])
    session.commit()
    session.add_all(
        [
            TeamSeasonStat(
                team_id=decoy_a.id,
                season=season,
                is_playoff=False,
                gp=82,
                net_rating=2.0,
                pace=98.5,
                ts_pct=0.570,
            ),
            TeamSeasonStat(
                team_id=decoy_b.id,
                season=season,
                is_playoff=False,
                gp=82,
                net_rating=0.0,
                pace=99.5,
                ts_pct=0.560,
            ),
        ]
    )
    session.commit()


def _seed_series(
    session,
    season: str,
    top_team: Team,
    bottom_team: Team,
    top_wins: int = 0,
    bottom_wins: int = 0,
    status: str = "scheduled",
) -> str:
    series_id = f"{season}-W-R1-{top_team.abbreviation}-{bottom_team.abbreviation}"
    session.add(
        PlayoffSeries(
            season=season,
            round=1,
            series_id=series_id,
            top_seed_team_id=top_team.id,
            bottom_seed_team_id=bottom_team.id,
            top_seed=1,
            bottom_seed=8,
            top_wins=top_wins,
            bottom_wins=bottom_wins,
            status=status,
        )
    )
    session.commit()
    return series_id


def _add_game(
    session,
    *,
    game_id: str,
    season: str,
    series_id: Optional[str],
    series_game_num: Optional[int],
    game_date: date,
    home_team: Team,
    away_team: Team,
    home_score: Optional[int],
    away_score: Optional[int],
    season_type: str = "Playoffs",
) -> None:
    session.add(
        GameLog(
            game_id=game_id,
            season=season,
            game_date=game_date,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=home_score,
            away_score=away_score,
            season_type=season_type,
            series_id=series_id,
            series_game_num=series_game_num,
        )
    )
    session.commit()


def _add_minimal_pbp(session, game_id: str) -> None:
    """Insert a couple of PBP rows so the assembler can find a play-by-play
    stream and not 404 on the base builder."""
    if not session.query(WarehouseGame).filter_by(game_id=game_id).first():
        session.add(WarehouseGame(game_id=game_id, season="2024-25"))
        session.flush()
    session.add_all(
        [
            PlayByPlayEvent(
                game_id=game_id,
                season="2024-25",
                action_number=1,
                order_index=1,
                period=1,
                clock="PT12M00.00S",
                action_type="period",
                sub_type="start",
                score_home=0,
                score_away=0,
            ),
            PlayByPlayEvent(
                game_id=game_id,
                season="2024-25",
                action_number=2,
                order_index=2,
                period=1,
                clock="PT11M30.00S",
                action_type="2pt",
                sub_type="made",
                score_home=2,
                score_away=0,
            ),
        ]
    )
    session.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_series_odds_at_pre_series_matches_prior():
    """No completed games => empty history list."""
    session = _make_session()
    try:
        season = "2025-26"
        top, bottom = _seed_two_teams(session)
        _seed_strength_pool(session, top, bottom, season)
        series_id = _seed_series(
            session,
            season=season,
            top_team=top,
            bottom_team=bottom,
            top_wins=0,
            bottom_wins=0,
            status="scheduled",
        )

        history = compute_series_odds_history(session, series_id)
        assert history == [], f"expected [], got {history}"
    finally:
        session.close()


def test_series_odds_monotonic_toward_winning_side():
    """Top seed wins games 1, 2, 3 — odds must be non-decreasing for top seed
    after each win, and the swing for at least one game must be positive."""
    session = _make_session()
    try:
        season = "2025-26"
        top, bottom = _seed_two_teams(session)
        _seed_strength_pool(session, top, bottom, season)
        series_id = _seed_series(
            session,
            season=season,
            top_team=top,
            bottom_team=bottom,
            top_wins=3,
            bottom_wins=0,
            status="active",
        )

        # Top seed (OKC) wins games 1, 2, 3. Game 1 + 2 are at top-seed home,
        # game 3 is at bottom-seed home.
        _add_game(
            session,
            game_id="0042500001",
            season=season,
            series_id=series_id,
            series_game_num=1,
            game_date=date(2026, 4, 18),
            home_team=top,
            away_team=bottom,
            home_score=110,
            away_score=99,
        )
        _add_game(
            session,
            game_id="0042500002",
            season=season,
            series_id=series_id,
            series_game_num=2,
            game_date=date(2026, 4, 21),
            home_team=top,
            away_team=bottom,
            home_score=108,
            away_score=101,
        )
        _add_game(
            session,
            game_id="0042500003",
            season=season,
            series_id=series_id,
            series_game_num=3,
            game_date=date(2026, 4, 24),
            home_team=bottom,
            away_team=top,
            home_score=95,
            away_score=104,
        )

        history = compute_series_odds_history(session, series_id)

        assert len(history) == 3
        game_nums = [pt.game_num for pt in history]
        assert game_nums == [1, 2, 3]
        winners = [pt.winner_team_abbr for pt in history]
        assert winners == ["OKC", "OKC", "OKC"], winners

        # Monotonic non-decreasing odds for top seed.
        odds: List[float] = [pt.top_seed_post_game_odds for pt in history]
        for i in range(1, len(odds)):
            assert odds[i] >= odds[i - 1] - 1e-9, (
                f"top-seed odds dropped at game {history[i].game_num}: "
                f"{odds}"
            )
        # All odds must be valid probabilities.
        assert all(0.0 <= o <= 1.0 for o in odds), odds
        # At least one swing should be positive given top seed wins.
        assert any(pt.swing_pp > 0 for pt in history), [pt.swing_pp for pt in history]
    finally:
        session.close()


def test_regular_season_game_has_no_series_odds():
    """A regular-season GameLog row (no ``series_id``) yields ``None`` for
    ``series_odds_history`` on the assembled response."""
    session = _make_session()
    try:
        season = "2025-26"
        top, bottom = _seed_two_teams(session)

        game_id = "0022500777"
        _add_game(
            session,
            game_id=game_id,
            season=season,
            series_id=None,
            series_game_num=None,
            game_date=date(2025, 11, 5),
            home_team=top,
            away_team=bottom,
            home_score=112,
            away_score=104,
            season_type="Regular Season",
        )
        _add_minimal_pbp(session, game_id)

        response = assemble_game_detail(session, game_id)

        assert response.series_odds_history is None
    finally:
        session.close()
