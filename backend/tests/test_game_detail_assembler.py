"""Sprint 77 — tests for ``assemble_game_detail`` (Engineer EA3).

The assembler composes the legacy box-score / timeline walk with the EA1
(WP + lead tracker), EA2 (possession diary + per-quarter +/-), and EA3
(post-game series odds history) derived surfaces.

This module verifies that for a fully-seeded playoff game (PBP + 5 starters
per team + a parent series with at least one completed game) the response
exposes non-None values for every Sprint-77 derived field.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
from typing import List, Tuple

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    GameLog,
    PlayByPlayEvent,
    Player,
    PlayerGameLog,
    PlayoffSeries,
    Team,
    TeamSeasonStat,
    WarehouseGame,
)
from services.game_detail_assembler import assemble_game_detail  # noqa: E402


def _make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def _seed_teams_and_strength_pool(session, season: str) -> Tuple[Team, Team]:
    """Seed two playoff teams + decoys + their regular-season stats so the
    series simulator has a non-empty league pool."""
    okc = Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder")
    hou = Team(id=1610612745, abbreviation="HOU", name="Houston Rockets")
    decoy_a = Team(id=1610612747, abbreviation="LAL", name="Los Angeles Lakers")
    decoy_b = Team(id=1610612744, abbreviation="GSW", name="Golden State Warriors")
    session.add_all([okc, hou, decoy_a, decoy_b])
    session.commit()

    session.add_all(
        [
            TeamSeasonStat(
                team_id=okc.id,
                season=season,
                is_playoff=False,
                gp=82,
                net_rating=8.0,
                pace=99.0,
                ts_pct=0.585,
            ),
            TeamSeasonStat(
                team_id=hou.id,
                season=season,
                is_playoff=False,
                gp=82,
                net_rating=-3.0,
                pace=98.0,
                ts_pct=0.555,
            ),
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
    return okc, hou


def _seed_starters(session, team: Team, base_id: int) -> List[Player]:
    """Five players on a team with positive PlayerGameLog minutes so
    ``_resolve_starters`` picks them up via the PlayerGameLog path."""
    players = [
        Player(
            id=base_id + i,
            full_name=f"{team.abbreviation} Starter {i}",
            first_name=team.abbreviation,
            last_name=f"Starter {i}",
            team_id=team.id,
            is_active=True,
        )
        for i in range(5)
    ]
    session.add_all(players)
    session.commit()
    return players


def _scoring_pbp(
    *,
    game_id: str,
    action_number: int,
    period: int,
    clock: str,
    team_id: int,
    player_id: int,
    points: int,
    score_home: int,
    score_away: int,
) -> PlayByPlayEvent:
    action_type = "3pt" if points == 3 else "2pt"
    return PlayByPlayEvent(
        game_id=game_id,
        season="2025-26",
        action_number=action_number,
        order_index=action_number,
        period=period,
        clock=clock,
        team_id=team_id,
        player_id=player_id,
        action_type=action_type,
        sub_type="made",
        description=f"{action_type} made",
        score_home=score_home,
        score_away=score_away,
    )


def test_assembler_returns_all_fields_for_playoff_game():
    """Full playoff game with PBP, starters, and a parent series — every
    Sprint-77 derived field must be populated."""
    session = _make_session()
    try:
        season = "2025-26"
        okc, hou = _seed_teams_and_strength_pool(session, season)

        okc_starters = _seed_starters(session, okc, base_id=1000)
        hou_starters = _seed_starters(session, hou, base_id=2000)

        series_id = f"{season}-W-R1-OKC-HOU"
        session.add(
            PlayoffSeries(
                season=season,
                round=1,
                series_id=series_id,
                top_seed_team_id=okc.id,
                bottom_seed_team_id=hou.id,
                top_seed=1,
                bottom_seed=8,
                top_wins=1,
                bottom_wins=0,
                status="active",
            )
        )
        session.commit()

        # Game 1: OKC home, OKC wins 110-99 (top seed wins game 1).
        game_id = "0042500001"
        session.add(
            GameLog(
                game_id=game_id,
                season=season,
                game_date=date(2026, 4, 18),
                home_team_id=okc.id,
                away_team_id=hou.id,
                home_score=110,
                away_score=99,
                season_type="Playoffs",
                series_id=series_id,
                series_game_num=1,
            )
        )
        # Sprint 81: PBP rows now hang off WarehouseGame, not GameLog.
        session.add(WarehouseGame(game_id=game_id, season=season))
        session.commit()

        # Player game logs so _resolve_starters' primary path activates.
        for idx, p in enumerate(okc_starters):
            session.add(
                PlayerGameLog(
                    player_id=p.id,
                    game_id=game_id,
                    season=season,
                    season_type="Playoffs",
                    game_date=date(2026, 4, 18),
                    matchup="OKC vs. HOU",
                    wl="W",
                    min=30.0 - idx,  # all positive
                )
            )
        for idx, p in enumerate(hou_starters):
            session.add(
                PlayerGameLog(
                    player_id=p.id,
                    game_id=game_id,
                    season=season,
                    season_type="Playoffs",
                    game_date=date(2026, 4, 18),
                    matchup="HOU @ OKC",
                    wl="L",
                    min=28.0 - idx,
                )
            )
        session.commit()

        # Minimal but sufficient PBP: alternating made FGs from each starter
        # so per-quarter +/- picks up real deltas and possession_diary has
        # several scoring events. Two periods (Q1, Q2) so the WP curve has
        # multiple boundary points.
        pbp_rows: List[PlayByPlayEvent] = []
        action_no = 1
        score_home = 0
        score_away = 0
        # Q1: each of the 5 OKC starters scores 2pt; each of the 5 HOU starters
        # scores 2pt (OKC up 10-10 by end of Q1's scoring exchanges, then OKC
        # adds a 3pt to take the lead).
        clocks = [
            "PT11M00.00S",
            "PT09M30.00S",
            "PT08M00.00S",
            "PT06M00.00S",
            "PT04M30.00S",
        ]
        for idx, p in enumerate(okc_starters):
            score_home += 2
            pbp_rows.append(
                _scoring_pbp(
                    game_id=game_id,
                    action_number=action_no,
                    period=1,
                    clock=clocks[idx],
                    team_id=okc.id,
                    player_id=p.id,
                    points=2,
                    score_home=score_home,
                    score_away=score_away,
                )
            )
            action_no += 1
        clocks_h = [
            "PT10M00.00S",
            "PT08M30.00S",
            "PT07M00.00S",
            "PT05M00.00S",
            "PT03M00.00S",
        ]
        for idx, p in enumerate(hou_starters):
            score_away += 2
            pbp_rows.append(
                _scoring_pbp(
                    game_id=game_id,
                    action_number=action_no,
                    period=1,
                    clock=clocks_h[idx],
                    team_id=hou.id,
                    player_id=p.id,
                    points=2,
                    score_home=score_home,
                    score_away=score_away,
                )
            )
            action_no += 1
        # Q1 closing 3pt by OKC starter 0.
        score_home += 3
        pbp_rows.append(
            _scoring_pbp(
                game_id=game_id,
                action_number=action_no,
                period=1,
                clock="PT01M00.00S",
                team_id=okc.id,
                player_id=okc_starters[0].id,
                points=3,
                score_home=score_home,
                score_away=score_away,
            )
        )
        action_no += 1

        # Q2: a few more buckets so the WP curve has more points.
        for i in range(3):
            score_home += 2
            pbp_rows.append(
                _scoring_pbp(
                    game_id=game_id,
                    action_number=action_no,
                    period=2,
                    clock=f"PT0{9 - i}M30.00S",
                    team_id=okc.id,
                    player_id=okc_starters[i + 1].id,
                    points=2,
                    score_home=score_home,
                    score_away=score_away,
                )
            )
            action_no += 1
            score_away += 2
            pbp_rows.append(
                _scoring_pbp(
                    game_id=game_id,
                    action_number=action_no,
                    period=2,
                    clock=f"PT0{8 - i}M00.00S",
                    team_id=hou.id,
                    player_id=hou_starters[i + 1].id,
                    points=2,
                    score_home=score_home,
                    score_away=score_away,
                )
            )
            action_no += 1

        session.add_all(pbp_rows)
        session.commit()

        response = assemble_game_detail(session, game_id)

        # Base box-score still populated.
        assert response.game_id == game_id
        assert response.home_team_abbreviation == "OKC"
        assert response.away_team_abbreviation == "HOU"
        assert len(response.events) > 0
        assert len(response.timeline) > 0

        # EA1 — win probability + lead tracker.
        assert response.win_probability is not None
        assert len(response.win_probability) > 0
        assert response.lead_tracker is not None
        assert len(response.lead_tracker) > 0

        # EA2 — possession diary + per-quarter +/-.
        assert response.possession_diary is not None
        assert len(response.possession_diary) > 0
        assert response.player_quarter_impact is not None
        assert len(response.player_quarter_impact) > 0

        # EA3 — series odds history with one completed game.
        assert response.series_odds_history is not None
        assert len(response.series_odds_history) == 1
        odds_pt = response.series_odds_history[0]
        assert odds_pt.game_num == 1
        assert odds_pt.winner_team_abbr == "OKC"
        assert 0.0 <= odds_pt.top_seed_post_game_odds <= 1.0
    finally:
        session.close()
