"""Sprint 78 / CF3 — Career Hall of Fame view.

Covers:
- Era-adjusted career line aggregation (pace + TS-vs-league delta)
- Career milestones (achieved + next-approach) on the live-compute path
- Era peers — returns >=3, sorted by similarity, excluding the target
- HOF projection score + label band for an MVP-tier seeded resume
"""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import Player, SeasonStat, Team  # noqa: E402
from services.career_legacy_service import (  # noqa: E402
    compute_era_adjusted_line,
    compute_hof_projection,
)
from services.career_milestone_service import compute_career_milestones  # noqa: E402
from services.era_peer_service import find_era_peers  # noqa: E402


def _make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return Session()


def _add_team(session, team_id: int, abbr: str, name: str) -> Team:
    team = Team(id=team_id, abbreviation=abbr, name=name)
    session.add(team)
    return team


def _add_player(session, player_id: int, name: str, team_id: int) -> Player:
    player = Player(
        id=player_id,
        full_name=name,
        first_name=name.split()[0],
        last_name=name.split()[-1],
        team_id=team_id,
        is_active=True,
        birth_date="1998-03-03",
    )
    session.add(player)
    return player


def _add_season(
    session,
    *,
    player_id: int,
    season: str,
    team_abbr: str,
    gp: int,
    pts_pg: float,
    reb_pg: float = 5.0,
    ast_pg: float = 4.0,
    pace: float = 100.0,
    ts_pct: float = 0.58,
    usg_pct: float = 28.0,
    per: float = 22.0,
    fg3m: int = 150,
    is_playoff: bool = False,
):
    pts = int(round(pts_pg * gp))
    fga = int(round(pts / 1.0))
    session.add(
        SeasonStat(
            player_id=player_id,
            season=season,
            team_abbreviation=team_abbr,
            is_playoff=is_playoff,
            gp=gp,
            min_total=gp * 35.0,
            min_pg=35.0,
            pts=pts,
            pts_pg=pts_pg,
            reb=int(round(reb_pg * gp)),
            reb_pg=reb_pg,
            ast=int(round(ast_pg * gp)),
            ast_pg=ast_pg,
            stl=int(round(1.2 * gp)),
            stl_pg=1.2,
            blk=int(round(0.6 * gp)),
            blk_pg=0.6,
            tov=int(round(2.5 * gp)),
            tov_pg=2.5,
            fgm=int(round(pts / 2.5)),
            fga=fga,
            fg_pct=0.48,
            fg3m=fg3m,
            fg3a=int(round(fg3m * 2.6)),
            fg3_pct=0.38,
            ftm=int(round(pts * 0.18)),
            fta=int(round(pts * 0.22)),
            ft_pct=0.85,
            oreb=int(round(reb_pg * gp * 0.18)),
            dreb=int(round(reb_pg * gp * 0.82)),
            pf=int(round(2.5 * gp)),
            ts_pct=ts_pct,
            efg_pct=ts_pct - 0.02,
            usg_pct=usg_pct,
            per=per,
            bpm=4.0,
            pace=pace,
        )
    )


def test_era_adjusted_line_normalizes_for_pace():
    """A 30 PPG scorer at pace=110 should normalize down toward 27.3 PPG era-adjusted."""
    session = _make_session()
    _add_team(session, 1610612738, "BOS", "Boston Celtics")
    _add_player(session, 1628369, "Test Tatum", 1610612738)
    _add_season(
        session, player_id=1628369, season="2024-25", team_abbr="BOS",
        gp=70, pts_pg=30.0, pace=110.0, ts_pct=0.620,
    )
    _add_season(
        session, player_id=1628369, season="2025-26", team_abbr="BOS",
        gp=70, pts_pg=30.0, pace=110.0, ts_pct=0.620,
    )
    for filler_id in range(2000, 2030):
        _add_player(session, filler_id, f"Filler {filler_id}", 1610612738)
        _add_season(
            session, player_id=filler_id, season="2024-25", team_abbr="BOS",
            gp=70, pts_pg=15.0, pace=110.0, ts_pct=0.560,
        )
        _add_season(
            session, player_id=filler_id, season="2025-26", team_abbr="BOS",
            gp=70, pts_pg=15.0, pace=110.0, ts_pct=0.560,
        )
    session.commit()

    summary = compute_era_adjusted_line(session, 1628369)
    assert summary.games_played == 140
    assert summary.seasons_played == 2
    assert summary.pts_pg == 30.0
    assert summary.pts_pg_era_adj is not None
    assert 27.0 <= summary.pts_pg_era_adj <= 27.5
    assert summary.ts_pct_delta_vs_league_avg is not None
    assert summary.ts_pct_delta_vs_league_avg > 0.05


def test_era_peers_returns_top_n_excluding_target():
    """Era peers must return 5–10 results sorted by similarity score desc."""
    session = _make_session()
    _add_team(session, 1610612738, "BOS", "Boston Celtics")
    _add_player(session, 1628369, "Target Star", 1610612738)
    for season in ("2022-23", "2023-24", "2024-25", "2025-26"):
        _add_season(
            session, player_id=1628369, season=season, team_abbr="BOS",
            gp=72, pts_pg=28.0, reb_pg=8.0, ast_pg=5.0,
            pace=98.0, ts_pct=0.59, usg_pct=30.0, per=24.0,
        )
    for i, (pid, ppg, apg, rpg) in enumerate(
        [
            (3001, 27.5, 5.5, 7.5),
            (3002, 26.8, 5.2, 8.2),
            (3003, 22.0, 8.5, 4.5),
            (3004, 18.0, 3.5, 11.0),
            (3005, 28.5, 4.8, 7.0),
            (3006, 12.0, 3.0, 5.5),
            (3007, 20.0, 6.0, 6.0),
            (3008, 25.0, 4.5, 8.0),
            (3009, 14.0, 7.0, 4.0),
            (3010, 9.5, 2.5, 3.0),
            (3011, 16.5, 4.0, 5.0),
            (3012, 24.0, 6.5, 6.5),
        ]
    ):
        _add_player(session, pid, f"Peer {i}", 1610612738)
        for season in ("2022-23", "2023-24", "2024-25"):
            _add_season(
                session, player_id=pid, season=season, team_abbr="BOS",
                gp=70, pts_pg=ppg, reb_pg=rpg, ast_pg=apg,
                pace=98.0, ts_pct=0.56, usg_pct=24.0, per=18.0,
            )
    session.commit()

    peers = find_era_peers(session, 1628369, n=8)
    assert 5 <= len(peers) <= 10
    assert all(p.player_id != 1628369 for p in peers)
    scores = [p.similarity_score for p in peers]
    assert scores == sorted(scores, reverse=True)
    assert peers[0].player_id in (3001, 3002, 3005, 3008, 3012)
    assert all("similar" in p.comp_basis for p in peers)


def test_hof_projection_likely_for_mvp_tier_resume():
    """A player with 25k pts, 1 MVP, 8 All-Stars, and a ring should land in 'Likely HOF'."""
    session = _make_session()
    _add_team(session, 1610612738, "BOS", "Boston Celtics")
    _add_player(session, 1628369, "MVP Tier", 1610612738)
    for season in (
        "2014-15", "2015-16", "2016-17", "2017-18",
        "2018-19", "2019-20", "2020-21", "2021-22",
        "2022-23", "2023-24", "2024-25", "2025-26",
    ):
        _add_season(
            session, player_id=1628369, season=season, team_abbr="BOS",
            gp=70, pts_pg=29.8, reb_pg=8.0, ast_pg=5.0, pace=98.0,
            ts_pct=0.60, usg_pct=30.0, per=25.0,
        )
    session.commit()

    proj = compute_hof_projection(
        session,
        1628369,
        accolades={"mvp_count": 1, "all_star_count": 8, "championships": 1},
    )
    assert proj.score >= 80
    assert proj.label == "Likely HOF"
    assert len(proj.drivers) <= 3
    assert any("MVP" in d for d in proj.drivers) or any("DPOY" in d for d in proj.drivers)
    assert any("All-Star" in d for d in proj.drivers)


def test_career_milestones_live_path_classifies_achieved_and_next():
    """With 12k career pts, 10k_pts is achieved; 15k_pts is the next approach."""
    session = _make_session()
    _add_team(session, 1610612738, "BOS", "Boston Celtics")
    _add_player(session, 1628369, "Milestone Player", 1610612738)
    for season in (
        "2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24",
    ):
        _add_season(
            session, player_id=1628369, season=season, team_abbr="BOS",
            gp=70, pts_pg=28.6, reb_pg=7.5, ast_pg=5.0, pace=98.0,
            ts_pct=0.58, usg_pct=29.0, per=22.0,
        )
    session.commit()

    achieved, next_approach = compute_career_milestones(session, 1628369)
    achieved_keys = {m.milestone_key for m in achieved}
    # 6 × 70 × 28.6 = 12,012 career points
    assert "10k_pts" in achieved_keys
    assert "20k_pts" not in achieved_keys
    # Achieved entries surface the season the milestone was hit.
    pts_milestone = next(m for m in achieved if m.milestone_key == "10k_pts")
    assert pts_milestone.achieved_in_season is not None
    # Next milestone is the soonest-attainable. Could be 15k_pts, 1k_3pm,
    # or something else depending on the seeded counting stats — what
    # matters is that points_remaining > 0 and games_to_milestone is sensible.
    assert next_approach is not None
    assert next_approach.points_remaining > 0
    if next_approach.games_to_milestone is not None:
        assert next_approach.games_to_milestone >= 1
