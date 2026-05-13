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
from db.models import (  # noqa: E402
    GameLog,
    LineupStats,
    Player,
    PlayerGameLog,
    PlayoffSeries,
    SeasonStat,
    Team,
    TeamSeasonStat,
    TeamShootingSplitStat,
)
from unittest.mock import MagicMock  # noqa: E402

from routers.playoffs import (  # noqa: E402
    get_bracket,
    get_series,
    get_series_intelligence,
    get_series_player_logs,
    get_series_simulation,
)

# Minimal Request stand-in for route handlers that accept request: Request
# for slowapi rate-limit decoration. slowapi >= 0.1.9 calls
# ``isinstance(request, starlette.requests.Request)`` at decoration time,
# so a real Request — even with a synthetic scope — is required. The
# no-op limiter path (when slowapi import fails) tolerates a MagicMock,
# but Sprint 98 added slowapi to requirements.txt so CI gets the real
# Limiter and a real Request must be passed.
from starlette.requests import Request as _StarletteRequest  # noqa: E402

_MOCK_REQUEST = _StarletteRequest(
    scope={
        "type": "http",
        "method": "POST",
        "path": "/api/playoffs/series/intelligence",
        "headers": [],
        "client": ("127.0.0.1", 0),
        "query_string": b"",
    }
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
    # Sprint 91 — outcomes match the persisted top_wins=3, bottom_wins=1
    # (OKC wins G1/G2/G4; HOU wins G3). Pre-Sprint-91 the series record
    # was read from the denormalized cache so the fixture got away with
    # OKC sweeping all 4. Now _series_to_response counts wins fresh from
    # GameLog, so the fixture has to be self-consistent.
    games_meta = [
        (4, "0042500004", date(2026, 4, 27), okc.id, hou.id, 116, 102),  # OKC
        (1, "0042500001", date(2026, 4, 18), okc.id, hou.id, 110, 99),   # OKC
        (3, "0042500003", date(2026, 4, 24), hou.id, okc.id, 112, 105),  # HOU
        (2, "0042500002", date(2026, 4, 21), okc.id, hou.id, 108, 101),  # OKC
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


def _seed_series_intelligence_data(session, season="2024-25"):
    series_id = _seed_series_with_games(session, season=season)
    session.add_all(
        [
            TeamSeasonStat(
                team_id=1610612760,
                season=season,
                is_playoff=True,
                gp=4,
                net_rating=12.5,
                efg_pct=0.575,
                tov_pct=0.105,
                oreb_pct=0.305,
                pace=98.7,
                ts_pct=0.612,
            ),
            TeamSeasonStat(
                team_id=1610612745,
                season=season,
                is_playoff=True,
                gp=4,
                net_rating=-8.1,
                efg_pct=0.511,
                tov_pct=0.142,
                oreb_pct=0.248,
                pace=98.1,
                ts_pct=0.548,
            ),
            TeamSeasonStat(
                team_id=1610612760,
                season=season,
                is_playoff=False,
                gp=82,
                net_rating=8.7,
                efg_pct=0.56,
                tov_pct=0.118,
                oreb_pct=0.285,
                pace=99.0,
                ts_pct=0.596,
            ),
            TeamSeasonStat(
                team_id=1610612745,
                season=season,
                is_playoff=False,
                gp=82,
                net_rating=1.4,
                efg_pct=0.543,
                tov_pct=0.126,
                oreb_pct=0.271,
                pace=99.4,
                ts_pct=0.575,
            ),
        ]
    )
    session.add_all(
        [
            Player(id=1, full_name="Shai Gilgeous-Alexander", position="G"),
            Player(id=2, full_name="Jalen Williams", position="F"),
            Player(id=11, full_name="Alperen Sengun", position="C"),
            Player(id=12, full_name="Fred VanVleet", position="G"),
        ]
    )
    session.add_all(
        [
            SeasonStat(
                player_id=1,
                season=season,
                team_abbreviation="OKC",
                is_playoff=True,
                gp=4,
                min_total=152,
                min_pg=38.0,
                pts=130,
                pts_pg=32.5,
                usg_pct=34.0,
                ts_pct=0.63,
                bpm=9.2,
                fga=82,
                fta=38,
                fg3a=24,
            ),
            SeasonStat(
                player_id=2,
                season=season,
                team_abbreviation="OKC",
                is_playoff=True,
                gp=4,
                min_total=140,
                min_pg=35.0,
                pts=76,
                pts_pg=19.0,
                usg_pct=23.0,
                ts_pct=0.59,
                bpm=4.5,
                fga=56,
                fta=14,
                fg3a=18,
            ),
            SeasonStat(
                player_id=11,
                season=season,
                team_abbreviation="HOU",
                is_playoff=True,
                gp=4,
                min_total=144,
                min_pg=36.0,
                pts=96,
                pts_pg=24.0,
                usg_pct=29.0,
                ts_pct=0.56,
                bpm=3.6,
                fga=72,
                fta=25,
                fg3a=8,
            ),
            SeasonStat(
                player_id=12,
                season=season,
                team_abbreviation="HOU",
                is_playoff=True,
                gp=4,
                min_total=132,
                min_pg=33.0,
                pts=52,
                pts_pg=13.0,
                usg_pct=21.0,
                ts_pct=0.51,
                bpm=0.4,
                fga=48,
                fta=8,
                fg3a=26,
            ),
            SeasonStat(player_id=1, season=season, team_abbreviation="OKC", is_playoff=False, gp=75, fga=1500, fta=620, fg3a=420),
            SeasonStat(player_id=11, season=season, team_abbreviation="HOU", is_playoff=False, gp=70, fga=1200, fta=410, fg3a=120),
        ]
    )
    session.add_all(
        [
            TeamShootingSplitStat(
                team_id=1610612760,
                season=season,
                is_playoff=True,
                split_family="ShotTypeTeamDashboard",
                split_value="Restricted Area",
                label="Restricted Area",
                fgm=92,
                fga=140,
                efg_pct=0.657,
            ),
            TeamShootingSplitStat(
                team_id=1610612760,
                season=season,
                is_playoff=True,
                split_family="ShotTypeTeamDashboard",
                split_value="Above the Break 3",
                label="Above the Break 3",
                fgm=42,
                fga=118,
                efg_pct=0.534,
                pct_ast_fgm=0.72,
            ),
            TeamShootingSplitStat(
                team_id=1610612745,
                season=season,
                is_playoff=True,
                split_family="ShotTypeTeamDashboard",
                split_value="Restricted Area",
                label="Restricted Area",
                fgm=64,
                fga=118,
                efg_pct=0.542,
            ),
            TeamShootingSplitStat(
                team_id=1610612745,
                season=season,
                is_playoff=True,
                split_family="ShotTypeTeamDashboard",
                split_value="Above the Break 3",
                label="Above the Break 3",
                fgm=30,
                fga=110,
                efg_pct=0.409,
                pct_ast_fgm=0.65,
            ),
        ]
    )
    session.add(
        LineupStats(
            lineup_key="1-2-3-4-5",
            season=season,
            team_id=1610612760,
            is_playoff=True,
            minutes=42.0,
            possessions=86,
            net_rating=18.4,
            ortg=124.2,
            drtg=105.8,
        )
    )
    session.commit()
    return series_id


def test_series_simulation_accepts_hypothetical_overrides_without_mutating_state():
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        series_id = _seed_series_with_games(session, season="2024-25")
        sim = get_series_simulation(
            series_id=series_id,
            override_top_wins=3,
            override_bottom_wins=2,
            db=session,
        )
        stored = get_series(series_id=series_id, db=session)
    finally:
        session.close()

    assert sim.current_state.top_wins == 3
    assert sim.current_state.bottom_wins == 2
    assert sim.current_state.games_played == 5
    assert sim.current_state.status == "active"
    assert stored.top_wins == 3
    assert stored.bottom_wins == 1


def test_series_intelligence_returns_edges_star_burden_and_metadata():
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        series_id = _seed_series_intelligence_data(session, season="2024-25")
        response = get_series_intelligence(request=_MOCK_REQUEST, series_id=series_id, db=session)
    finally:
        session.close()

    assert response.methodology_version == "playoff_series_intelligence_v1"
    assert response.pulse.completed_games == 4
    assert response.data_coverage.playoff_team_stats is True
    assert response.data_coverage.regular_team_baselines is True
    assert response.data_coverage.playoff_player_stats is True
    assert response.analysis_metadata is not None
    assert response.analysis_metadata.confidence in {"medium", "high"}
    assert any(metric.key == "net_rating" and metric.edge_team_abbr == "OKC" for metric in response.four_factors)
    assert response.star_burden[0].player_name == "Shai Gilgeous-Alexander"
    assert response.star_burden[0].position_bucket == "G"
    assert response.best_lineups
    assert response.tactical_edges


def test_series_intelligence_surfaces_thin_data_warnings():
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        series_id = _seed_series_with_games(session, season="2024-25")
        response = get_series_intelligence(request=_MOCK_REQUEST, series_id=series_id, db=session)
    finally:
        session.close()

    assert response.warnings
    assert response.data_coverage.playoff_team_stats is False
    assert response.analysis_metadata is not None
    assert response.analysis_metadata.confidence == "low"


def test_series_intelligence_falls_back_to_regular_season_baseline():
    """Sprint 83c — when playoff TeamSeasonStat rows are missing for a team,
    the four-factor cards should populate from the regular-season row and a
    "regular-season baseline" warning should be surfaced.
    """
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        season = "2024-25"
        series_id = _seed_series_with_games(session, season=season)
        # Seed regular-season rows ONLY (no playoff TeamSeasonStat) so the
        # four-factor builder must fall back.
        session.add_all(
            [
                TeamSeasonStat(
                    team_id=1610612760,
                    season=season,
                    is_playoff=False,
                    gp=82,
                    net_rating=8.7,
                    efg_pct=0.56,
                    tov_pct=0.118,
                    oreb_pct=0.285,
                    pace=99.0,
                    ts_pct=0.596,
                ),
                TeamSeasonStat(
                    team_id=1610612745,
                    season=season,
                    is_playoff=False,
                    gp=82,
                    net_rating=1.4,
                    efg_pct=0.543,
                    tov_pct=0.126,
                    oreb_pct=0.271,
                    pace=99.4,
                    ts_pct=0.575,
                ),
            ]
        )
        session.commit()
        response = get_series_intelligence(request=_MOCK_REQUEST, series_id=series_id, db=session)
    finally:
        session.close()

    # Top team's net_rating card should now carry the regular-season value.
    net_rating_metric = next(
        metric for metric in response.four_factors if metric.key == "net_rating"
    )
    assert net_rating_metric.top_value is not None
    assert abs(net_rating_metric.top_value - 8.7) < 1e-6
    # No playoff-only sample yet, so deltas vs RS should not be computed.
    assert net_rating_metric.top_delta_vs_regular is None
    assert net_rating_metric.bottom_delta_vs_regular is None
    # Regular-season baseline warning is surfaced for both teams.
    baseline_warnings = [
        w for w in response.warnings if "regular-season baseline" in w.lower()
    ]
    assert any("OKC" in w for w in baseline_warnings)
    assert any("HOU" in w for w in baseline_warnings)


def test_star_burden_falls_back_to_regular_season_when_no_playoff_rows():
    """Sprint 91 — when no SeasonStat rows exist with is_playoff=True for a
    team, _star_burden_for_team must fall back to is_playoff=False rows
    and tag every entry with data_source='regular_season' so the UI can
    render a "Regular season" badge until Game 1 finalizes."""
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        season = "2024-25"
        series_id = _seed_series_with_games(session, season=season)
        # Regular-season player rows for OKC and HOU (no is_playoff=True rows
        # present — the fallback should kick in).
        session.add_all(
            [
                SeasonStat(
                    player_id=1, season=season, team_abbreviation="OKC",
                    is_playoff=False, gp=75, min_total=2400, min_pg=32.0,
                    usg_pct=0.32, pts_pg=29.0, ts_pct=0.62, bpm=8.1,
                    fga=1500, fta=620, fg3a=420, pts=2200,
                ),
                SeasonStat(
                    player_id=11, season=season, team_abbreviation="HOU",
                    is_playoff=False, gp=72, min_total=2200, min_pg=30.5,
                    usg_pct=0.27, pts_pg=22.0, ts_pct=0.58, bpm=4.4,
                    fga=1200, fta=410, fg3a=120, pts=1700,
                ),
            ]
        )
        session.commit()
        response = get_series_intelligence(request=_MOCK_REQUEST, series_id=series_id, db=session)
    finally:
        session.close()

    assert response.star_burden, "fallback should produce non-empty star_burden"
    assert all(
        e.data_source == "regular_season" for e in response.star_burden
    ), "every fallback row should be tagged regular_season so the UI can show the badge"
    # Both teams represented.
    teams = {e.team_abbreviation for e in response.star_burden}
    assert "OKC" in teams and "HOU" in teams


def test_shot_diet_falls_back_to_regular_season_splits():
    """Sprint 91 — _shot_diet_for_team falls back to regular-season
    TeamShootingSplitStat rows when no playoff splits exist yet, and tags
    the entry with data_source='regular_season'."""
    from db.models import TeamShootingSplitStat

    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        season = "2024-25"
        series_id = _seed_series_with_games(session, season=season)
        # Regular-season shooting splits for both teams (no is_playoff=True
        # rows). Token "Restricted Area" in label so _share_for_tokens
        # produces a non-zero rim_frequency.
        session.add_all(
            [
                TeamShootingSplitStat(
                    team_id=1610612760, season=season, is_playoff=False,
                    split_family="ShotDashboard", split_value="rim",
                    label="Restricted Area", fga=2000, fgm=1300,
                ),
                TeamShootingSplitStat(
                    team_id=1610612760, season=season, is_playoff=False,
                    split_family="ShotDashboard", split_value="paint",
                    label="In The Paint (Non-RA)", fga=900, fgm=420,
                ),
                TeamShootingSplitStat(
                    team_id=1610612745, season=season, is_playoff=False,
                    split_family="ShotDashboard", split_value="rim",
                    label="Restricted Area", fga=1700, fgm=1090,
                ),
                TeamShootingSplitStat(
                    team_id=1610612745, season=season, is_playoff=False,
                    split_family="ShotDashboard", split_value="paint",
                    label="In The Paint (Non-RA)", fga=850, fgm=380,
                ),
            ]
        )
        session.commit()
        response = get_series_intelligence(request=_MOCK_REQUEST, series_id=series_id, db=session)
    finally:
        session.close()

    assert len(response.shot_diet) == 2
    for entry in response.shot_diet:
        assert entry.data_source == "regular_season"
        assert entry.rim_frequency is not None and entry.rim_frequency > 0
        assert any(
            "regular-season" in note.lower() for note in entry.notes
        ), "fallback note must be present"


# ---------------------------------------------------------------------------
# Sprint 85 — Bracket auto-advancement
# ---------------------------------------------------------------------------


def _seed_west_first_round_with_games(session, season="2024-25"):
    """Seed the four West Round-1 series with enough games for the 1v8 (OKC v
    HOU) and 4v5 (LAC v GSW) matchups to fully close 4-0, while 2v7/3v6 stay
    untouched. Used by the auto-advance tests below.
    """
    teams = WEST_TEAMS
    for tid, abbr, name in teams:
        session.add(Team(id=tid, abbreviation=abbr, name=name))
    session.commit()

    # Standard 1-vs-8 / 4-vs-5 / 3-vs-6 / 2-vs-7 first-round pairings.
    okc = WEST_TEAMS[0]   # 1
    den = WEST_TEAMS[1]   # 2
    minn = WEST_TEAMS[2]  # 3
    lac = WEST_TEAMS[3]   # 4
    gsw = WEST_TEAMS[4]   # 5
    dal = WEST_TEAMS[5]   # 6
    mem = WEST_TEAMS[6]   # 7
    hou = WEST_TEAMS[7]   # 8

    # Build playoff games: OKC sweeps HOU 4-0, LAC sweeps GSW 4-0. The other
    # two series (DEN-MEM, MIN-DAL) get one game each so they exist but stay
    # active. build_or_refresh_bracket walks games into series rows.
    game_id_counter = [1]

    def _emit(home_id, away_id, home_score, away_score, gdate):
        gid = "00425{0:05d}".format(game_id_counter[0])
        game_id_counter[0] += 1
        session.add(
            GameLog(
                game_id=gid,
                season=season,
                game_date=gdate,
                home_team_id=home_id,
                away_team_id=away_id,
                home_score=home_score,
                away_score=away_score,
                season_type="Playoffs",
            )
        )

    # OKC (1) sweeps HOU (8) — 4 OKC wins.
    _emit(okc[0], hou[0], 120, 100, date(2026, 4, 18))
    _emit(okc[0], hou[0], 115, 102, date(2026, 4, 21))
    _emit(hou[0], okc[0], 99, 110, date(2026, 4, 24))
    _emit(hou[0], okc[0], 95, 108, date(2026, 4, 27))

    # LAC (4) sweeps GSW (5) — 4 LAC wins.
    _emit(lac[0], gsw[0], 116, 98, date(2026, 4, 19))
    _emit(lac[0], gsw[0], 110, 105, date(2026, 4, 22))
    _emit(gsw[0], lac[0], 90, 109, date(2026, 4, 25))
    _emit(gsw[0], lac[0], 95, 112, date(2026, 4, 28))

    # DEN (2) v MEM (7) — one game so the series exists but stays active.
    _emit(den[0], mem[0], 105, 100, date(2026, 4, 19))

    # MIN (3) v DAL (6) — one game so the series exists but stays active.
    _emit(minn[0], dal[0], 102, 96, date(2026, 4, 20))

    # Seed regular-season W% rows so _seed_lookup can rank teams 1..8 cleanly.
    # Higher w_pct => lower (better) seed.
    rs_rows = [
        (okc[0], 0.80),   # rank 1
        (den[0], 0.74),   # rank 2
        (minn[0], 0.70),  # rank 3
        (lac[0], 0.65),   # rank 4
        (gsw[0], 0.60),   # rank 5
        (dal[0], 0.55),   # rank 6
        (mem[0], 0.50),   # rank 7
        (hou[0], 0.45),   # rank 8
    ]
    for tid, wpct in rs_rows:
        session.add(
            TeamSeasonStat(
                team_id=tid,
                season=season,
                is_playoff=False,
                gp=82,
                w_pct=wpct,
            )
        )
    session.commit()


def test_round1_close_creates_round2_slot_with_tbd_opponent():
    """When a Round-1 series closes 4-0, build_or_refresh_bracket should stand
    up a Round-2 row with the winner pre-populated and the other side null
    (a TBD slot waiting on the parallel arm)."""
    from db.models import PlayoffSeries
    from services.playoff_bracket_service import build_or_refresh_bracket

    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        season = "2024-25"
        _seed_west_first_round_with_games(session, season=season)
        # Drop the LAC sweep so only OKC closes — that way the R2 slot
        # has exactly one parent populated.
        session.query(GameLog).filter(
            GameLog.home_team_id == 1610612746
        ).delete(synchronize_session=False)
        session.query(GameLog).filter(
            GameLog.away_team_id == 1610612746
        ).delete(synchronize_session=False)
        session.commit()

        build_or_refresh_bracket(session, season)

        r2_rows = (
            session.query(PlayoffSeries)
            .filter(PlayoffSeries.season == season, PlayoffSeries.round == 2)
            .all()
        )
        assert len(r2_rows) == 1, f"expected one R2 slot, got {len(r2_rows)}"
        slot = r2_rows[0]
        # OKC is the 1 seed and won 1v8 — its R2 arm is "TOP", and within that
        # arm the 1v8 winner takes the top_seed seat (vs the 4v5 winner).
        assert slot.top_seed_team_id == 1610612760, "OKC should fill the top seat"
        assert slot.bottom_seed_team_id is None, "bottom seat should remain TBD"
        assert slot.parent_top_series_id is not None
        assert "OKC" in slot.parent_top_series_id
        assert slot.parent_bottom_series_id is None
        assert slot.status == "scheduled"
    finally:
        session.close()


def test_both_round1_parents_close_populates_round2_seeds():
    """When both parents in the same R2 arm close, the slot should hold both
    teams with the lower-seeded parent winner in the top seat."""
    from db.models import PlayoffSeries
    from services.playoff_bracket_service import build_or_refresh_bracket

    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        season = "2024-25"
        _seed_west_first_round_with_games(session, season=season)
        build_or_refresh_bracket(session, season)

        r2_rows = (
            session.query(PlayoffSeries)
            .filter(PlayoffSeries.season == season, PlayoffSeries.round == 2)
            .all()
        )
        # The TOP arm (1v8 + 4v5) both closed. Expect exactly one R2 row in
        # that arm with both teams populated.
        top_arm = [
            r for r in r2_rows
            if (r.parent_top_series_id and "OKC" in r.parent_top_series_id)
            or (r.parent_bottom_series_id and "LAC" in r.parent_bottom_series_id)
        ]
        assert len(top_arm) == 1
        slot = top_arm[0]
        assert slot.top_seed_team_id == 1610612760, "OKC (1 seed) holds the top seat"
        assert slot.bottom_seed_team_id == 1610612746, "LAC (4 seed) holds the bottom seat"
        assert slot.parent_top_series_id is not None
        assert slot.parent_bottom_series_id is not None
    finally:
        session.close()


def test_slot_pairing_math_1v8_advances_against_4v5():
    """Direct unit test for the seed pairing math: 1v8 winner must feed the
    same R2 arm as 4v5 (not 2v7), and (1v8) takes the top seat over (4v5)."""
    from services.playoff_bracket_service import _compute_next_round_slot

    one_v_eight = _compute_next_round_slot(
        season="2024-25",
        conference_token="W",
        round_number=1,
        top_seed=1,
        bottom_seed=8,
    )
    four_v_five = _compute_next_round_slot(
        season="2024-25",
        conference_token="W",
        round_number=1,
        top_seed=4,
        bottom_seed=5,
    )
    two_v_seven = _compute_next_round_slot(
        season="2024-25",
        conference_token="W",
        round_number=1,
        top_seed=2,
        bottom_seed=7,
    )
    three_v_six = _compute_next_round_slot(
        season="2024-25",
        conference_token="W",
        round_number=1,
        top_seed=3,
        bottom_seed=6,
    )

    assert one_v_eight is not None
    assert four_v_five is not None
    # 1v8 and 4v5 share a slot; 2v7 and 3v6 share a different slot.
    assert one_v_eight["slot_id"] == four_v_five["slot_id"]
    assert two_v_seven["slot_id"] == three_v_six["slot_id"]
    assert one_v_eight["slot_id"] != two_v_seven["slot_id"]

    # Within the TOP arm: 1v8 winner = top seat; 4v5 winner = bottom seat.
    assert one_v_eight["child_slot"] == "TOP"
    assert four_v_five["child_slot"] == "BOT"
    # Within the BOT arm: 2v7 winner = top seat; 3v6 winner = bottom seat.
    assert two_v_seven["child_slot"] == "TOP"
    assert three_v_six["child_slot"] == "BOT"

    # Round 2 winners flow into the conference final.
    cf_top_arm = _compute_next_round_slot(
        season="2024-25",
        conference_token="W",
        round_number=2,
        top_seed=1,
        bottom_seed=4,
    )
    cf_bot_arm = _compute_next_round_slot(
        season="2024-25",
        conference_token="W",
        round_number=2,
        top_seed=2,
        bottom_seed=3,
    )
    assert cf_top_arm["slot_id"] == cf_bot_arm["slot_id"], "both arms feed same CF row"
    assert cf_top_arm["child_slot"] == "TOP"
    assert cf_bot_arm["child_slot"] == "BOT"

    # Conference Final winners flow into Finals (East = top, West = bottom).
    finals_east = _compute_next_round_slot(
        season="2024-25",
        conference_token="E",
        round_number=3,
        top_seed=1,
        bottom_seed=2,
    )
    finals_west = _compute_next_round_slot(
        season="2024-25",
        conference_token="W",
        round_number=3,
        top_seed=1,
        bottom_seed=2,
    )
    assert finals_east["slot_id"] == finals_west["slot_id"]
    assert finals_east["child_slot"] == "TOP"
    assert finals_west["child_slot"] == "BOT"

    # Finals (round 4) has no successor.
    assert _compute_next_round_slot(
        season="2024-25",
        conference_token="FIN",
        round_number=4,
        top_seed=1,
        bottom_seed=1,
    ) is None
# ---------------------------------------------------------------------------
# Sprint 85 — Per-series detail page (player game-by-game logs)
# ---------------------------------------------------------------------------


def _seed_series_with_player_game_logs(session, season="2024-25"):
    """Seed a 4-game series with per-team player game logs.

    OKC roster: SGA (heavy minutes — should sort first), Jalen Williams
    (mid minutes), Cason Wallace (low minutes — should sort last).
    HOU roster: Sengun (heavy minutes), Jabari Smith (mid).
    """
    series_id = _seed_series_with_games(session, season=season)

    okc_id = 1610612760
    hou_id = 1610612745

    session.add_all(
        [
            Player(id=101, full_name="Shai Gilgeous-Alexander", team_id=okc_id, headshot_url="https://example.com/101.png"),
            Player(id=102, full_name="Jalen Williams", team_id=okc_id),
            Player(id=103, full_name="Cason Wallace", team_id=okc_id),
            Player(id=201, full_name="Alperen Sengun", team_id=hou_id),
            Player(id=202, full_name="Jabari Smith Jr.", team_id=hou_id),
            # A player whose team is neither — should be filtered out.
            Player(id=999, full_name="Stray Player", team_id=1610612747),  # LAL
        ]
    )

    games_meta = [
        ("0042500001", 1),
        ("0042500002", 2),
        ("0042500003", 3),
        ("0042500004", 4),
    ]

    # Per-game minutes by player_id (used to verify sort-by-total-minutes).
    okc_minutes = {
        101: [38.0, 40.0, 36.0, 39.0],   # SGA: 153.0
        102: [33.0, 34.0, 32.0, 35.0],   # JDub: 134.0
        103: [18.0, 16.0, 22.0, 20.0],   # Wallace: 76.0
    }
    hou_minutes = {
        201: [37.0, 39.0, 36.0, 38.0],   # Sengun: 150.0
        202: [29.0, 31.0, 27.0, 30.0],   # Smith: 117.0
    }

    rows = []
    for game_id, game_num in games_meta:
        for pid, mins_list in okc_minutes.items():
            mins = mins_list[game_num - 1]
            rows.append(
                PlayerGameLog(
                    player_id=pid,
                    game_id=game_id,
                    season=season,
                    season_type="Playoffs",
                    min=mins,
                    pts=int(mins * 0.6),
                    reb=int(mins * 0.18),
                    ast=int(mins * 0.15),
                    stl=1,
                    blk=0,
                    tov=2,
                    fgm=int(mins * 0.25),
                    fga=int(mins * 0.5),
                    fg3m=int(mins * 0.08),
                    fg3a=int(mins * 0.2),
                    ftm=int(mins * 0.12),
                    fta=int(mins * 0.15),
                    plus_minus=8 if pid == 101 else 4,
                )
            )
        for pid, mins_list in hou_minutes.items():
            mins = mins_list[game_num - 1]
            rows.append(
                PlayerGameLog(
                    player_id=pid,
                    game_id=game_id,
                    season=season,
                    season_type="Playoffs",
                    min=mins,
                    pts=int(mins * 0.55),
                    reb=int(mins * 0.22),
                    ast=int(mins * 0.12),
                    stl=1,
                    blk=1,
                    tov=2,
                    fgm=int(mins * 0.22),
                    fga=int(mins * 0.5),
                    fg3m=int(mins * 0.05),
                    fg3a=int(mins * 0.16),
                    ftm=int(mins * 0.1),
                    fta=int(mins * 0.13),
                    plus_minus=-6,
                )
            )
        # Stray player log — wrong team, should be excluded from response.
        rows.append(
            PlayerGameLog(
                player_id=999,
                game_id=game_id,
                season=season,
                season_type="Playoffs",
                min=10.0,
                pts=4,
            )
        )
    session.add_all(rows)
    session.commit()
    return series_id


def test_series_player_logs_returns_grouped_sorted_response():
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        series_id = _seed_series_with_player_game_logs(session, season="2024-25")
        response = get_series_player_logs(series_id=series_id, db=session)
    finally:
        session.close()

    assert response.series_id == series_id
    # 3 OKC players appeared, 2 HOU players, stray player filtered out.
    assert len(response.top_seed) == 3
    assert len(response.bottom_seed) == 2
    stray_pids = {entry.player_id for entry in response.top_seed + response.bottom_seed}
    assert 999 not in stray_pids

    # Sort-by-total-minutes: SGA (153) > JDub (134) > Wallace (76).
    okc_order = [entry.player_name for entry in response.top_seed]
    assert okc_order == [
        "Shai Gilgeous-Alexander",
        "Jalen Williams",
        "Cason Wallace",
    ]
    # And HOU: Sengun (150) > Smith (117).
    hou_order = [entry.player_name for entry in response.bottom_seed]
    assert hou_order == ["Alperen Sengun", "Jabari Smith Jr."]

    sga = response.top_seed[0]
    # Each player has all 4 games.
    assert len(sga.games) == 4
    # Games are ordered by series_game_num.
    assert [g.series_game_num for g in sga.games] == [1, 2, 3, 4]
    # Headshot is forwarded when populated on the Player row.
    assert sga.headshot_url == "https://example.com/101.png"
    assert sga.team_abbreviation == "OKC"
    # series_totals row sums minutes correctly and uses sentinel game_id.
    assert sga.series_totals.game_id == "TOTALS"
    assert sga.series_totals.series_game_num == 0
    assert abs(sga.series_totals.min - 153.0) < 1e-6
    # Plus/minus also accumulates (8 per game × 4 = 32).
    assert sga.series_totals.plus_minus == 32


def test_series_player_logs_returns_404_for_missing_series():
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        from fastapi import HTTPException

        try:
            get_series_player_logs(series_id="2024-25-W-R1-NOPE-NONE", db=session)
        except HTTPException as exc:
            assert exc.status_code == 404
        else:  # pragma: no cover - safety
            raise AssertionError("Expected 404 for missing series")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Sprint 86 — Bracket auto-advance label richness (parent seed + abbrs)
# ---------------------------------------------------------------------------


def test_series_response_includes_parent_seed_when_parent_exists():
    """A Round-2 child slot whose parent_top_series_id is set should expose
    the parent's lower seed and team-abbreviation pair so the frontend can
    render labels like ``"winner of 1v8 (OKC/HOU)"``.
    """
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        season = "2024-25"
        # Seed two West teams + a closed parent 1v8 OKC-HOU series.
        session.add_all(
            [
                Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder"),
                Team(id=1610612745, abbreviation="HOU", name="Houston Rockets"),
            ]
        )
        session.commit()

        parent_id = "{0}-W-R1-OKC-HOU".format(season)
        session.add(
            PlayoffSeries(
                season=season,
                round=1,
                series_id=parent_id,
                top_seed_team_id=1610612760,
                bottom_seed_team_id=1610612745,
                top_seed=1,
                bottom_seed=8,
                top_wins=4,
                bottom_wins=0,
                status="closed",
                winner_team_id=1610612760,
            )
        )
        # Child Round-2 row with parent_top pointer set → response should
        # include parent_top_seed=1 and parent_top_team_abbrs=["OKC", "HOU"].
        child_id = "{0}-W-R2-TOP".format(season)
        session.add(
            PlayoffSeries(
                season=season,
                round=2,
                series_id=child_id,
                top_seed_team_id=1610612760,
                bottom_seed_team_id=None,
                top_seed=1,
                bottom_seed=None,
                top_wins=0,
                bottom_wins=0,
                status="scheduled",
                parent_top_series_id=parent_id,
            )
        )
        session.commit()

        response = get_series(series_id=child_id, db=session)
    finally:
        session.close()

    assert response.parent_top_series_id == parent_id
    assert response.parent_top_seed == 1
    assert response.parent_top_team_abbrs == ["OKC", "HOU"]
    # Bottom side has no parent pointer set → all parent_bottom_* fields null.
    assert response.parent_bottom_series_id is None
    assert response.parent_bottom_seed is None
    assert response.parent_bottom_team_abbrs is None


def test_series_response_omits_parent_fields_for_round_1():
    """Round-1 series have no parents — all parent_* fields must be None."""
    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        series_id = _seed_series_with_games(session, season="2024-25")
        response = get_series(series_id=series_id, db=session)
    finally:
        session.close()

    assert response.parent_top_series_id is None
    assert response.parent_bottom_series_id is None
    assert response.parent_top_seed is None
    assert response.parent_bottom_seed is None
    assert response.parent_top_team_abbrs is None
    assert response.parent_bottom_team_abbrs is None


# ---------------------------------------------------------------------------
# Sprint 92 — bracket builder conference resolution + slot-id guard
# ---------------------------------------------------------------------------


def test_team_conference_falls_back_to_static_abbr_map_when_db_column_empty():
    """Production hit a state where every Team.conference was empty, which
    made `_team_conference` return "X" for every team. That collapsed all
    R1 winners into shared `<season>-X-R2-TOP` / `R2-BOT` slots regardless
    of conference (one R2-TOP row contained OKC West + PHI East). The fix
    is a static abbreviation→conference fallback inside `_team_conference`."""
    from services.playoff_bracket_service import _team_conference

    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        # Real abbrs, but Team.conference is intentionally left empty/null.
        session.add(Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder"))
        session.add(Team(id=1610612765, abbreviation="DET", name="Detroit Pistons"))
        session.add(Team(id=1, abbreviation="ZZZ", name="Made-up team"))
        session.commit()

        cache = {}
        assert _team_conference(session, 1610612760, cache) == "W"
        assert _team_conference(session, 1610612765, cache) == "E"
        # Unknown abbr still falls through to "X" — fallback is conservative.
        assert _team_conference(session, 1, cache) == "X"
    finally:
        session.close()


def test_compute_next_round_slot_refuses_unresolved_conference():
    """`_compute_next_round_slot` must refuse to mint cross-conference R2
    slot ids. If conference resolution returns "X", the auto-advance
    should bail rather than collapse East+West winners into one row."""
    from services.playoff_bracket_service import _compute_next_round_slot

    # A normal East R1-1v8 → R2 slot should resolve cleanly.
    east_slot = _compute_next_round_slot(
        season="2025-26", conference_token="E", round_number=1,
        top_seed=1, bottom_seed=8,
    )
    assert east_slot is not None
    assert east_slot["slot_id"] == "2025-26-E-R2-TOP"

    # Same shape with an unresolved conference must return None.
    blocked = _compute_next_round_slot(
        season="2025-26", conference_token="X", round_number=1,
        top_seed=1, bottom_seed=8,
    )
    assert blocked is None, (
        "advance must not produce -X- slot ids; populate Team.conference instead"
    )

    # Empty / None conf token also blocked.
    assert (
        _compute_next_round_slot(
            season="2025-26", conference_token=None, round_number=1,
            top_seed=1, bottom_seed=8,
        )
        is None
    )


def test_build_or_refresh_self_heals_when_partner_parent_already_advanced():
    """Sprint 92 — when two R1 parents share an R2 slot (e.g. 1v8 and
    4v5 both feed R2-TOP), the self-heal path must fire for BOTH parents
    on a re-run, not just the first. Pre-fix, the second parent's
    self-heal saw a non-null next_row and skipped, leaving the partner
    seat empty.

    Reproduces the production scenario: the repair script wipes R2+ and
    re-runs the builder against existing closed R1 rows (so
    was_closed_before=True for everyone). The first iteration's
    self-heal creates R2-TOP with one seat filled; the second
    iteration's self-heal must fire too to fill the partner seat."""
    from services.playoff_bracket_service import build_or_refresh_bracket

    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        season = "2025-26"
        # 8 East teams so we have a true 1v8 + 4v5 pair both feeding TOP arm.
        bos = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
        nyk = Team(id=1610612752, abbreviation="NYK", name="New York Knicks")
        mil = Team(id=1610612749, abbreviation="MIL", name="Milwaukee Bucks")
        phi = Team(id=1610612755, abbreviation="PHI", name="Philadelphia 76ers")
        mia = Team(id=1610612748, abbreviation="MIA", name="Miami Heat")
        cle = Team(id=1610612739, abbreviation="CLE", name="Cleveland Cavaliers")
        tor = Team(id=1610612761, abbreviation="TOR", name="Toronto Raptors")
        det = Team(id=1610612765, abbreviation="DET", name="Detroit Pistons")
        session.add_all([bos, nyk, mil, phi, mia, cle, tor, det])
        # Records produce BOS=1, NYK=2, MIL=3, PHI=4, MIA=5, CLE=6, TOR=7, DET=8.
        rs = [
            (bos, 0.80), (nyk, 0.74), (mil, 0.70), (phi, 0.65),
            (mia, 0.60), (cle, 0.55), (tor, 0.50), (det, 0.45),
        ]
        for team, w in rs:
            session.add(TeamSeasonStat(team_id=team.id, season=season, is_playoff=False, gp=82, w_pct=w))

        # 1v8: BOS sweeps DET 4-0. 4v5: PHI sweeps MIA 4-0.
        gid = [1]

        def _emit(home, away, hs, as_, gdate):
            session.add(
                GameLog(
                    game_id="00425{0:05d}".format(gid[0]),
                    season=season, game_date=gdate,
                    home_team_id=home.id, away_team_id=away.id,
                    home_score=hs, away_score=as_,
                    season_type="Playoffs",
                )
            )
            gid[0] += 1

        for d in range(4):
            _emit(bos, det, 110, 95, date(2026, 4, 18 + d))
        for d in range(4):
            _emit(phi, mia, 110, 95, date(2026, 4, 19 + d))
        session.commit()

        # First run — R1 series get created and closed; R2 gets populated
        # via the was_closed_before=False direct-advance path.
        build_or_refresh_bracket(session, season)

        # Repair-style: wipe R2 to simulate the production scenario the
        # repair script triggers — re-running the builder against R1 rows
        # that are already closed.
        session.query(PlayoffSeries).filter(
            PlayoffSeries.season == season,
            PlayoffSeries.round >= 2,
        ).delete()
        session.commit()

        # Second run — was_closed_before=True for both R1 series. Self-heal
        # path must fire for BOTH 1v8 (BOS) and 4v5 (PHI), not just the
        # first one to be iterated.
        build_or_refresh_bracket(session, season)

        # E-R2-TOP must have BOTH seats filled.
        r2_top = (
            session.query(PlayoffSeries)
            .filter(PlayoffSeries.season == season, PlayoffSeries.series_id == "2025-26-E-R2-TOP")
            .first()
        )
        assert r2_top is not None, "E-R2-TOP must exist after self-heal"
        assert r2_top.top_seed_team_id == bos.id, "BOS (East 1) fills top seat"
        assert r2_top.bottom_seed_team_id == phi.id, (
            "PHI (East 4) must fill bot seat after self-heal — pre-fix, "
            "the second parent's advance was skipped because the row "
            "already existed when self-heal checked it"
        )
    finally:
        session.close()


def test_seed_lookup_ranks_within_conference_not_league_wide():
    """Sprint 92 — a team's playoff seed must be its rank within its
    conference, not its rank league-wide. Pre-fix, CLE with the 8th-best
    league record was being labeled seed 8 even though they had the
    4th-best East record (true East 4 seed). The downstream seed-arm
    mapping assumes within-conference 1-8 seeding, so league-wide ranks
    silently broke the bracket auto-advance."""
    from services.playoff_bracket_service import _seed_lookup

    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        season = "2025-26"
        # Real abbrs so the static conference fallback can resolve E/W.
        # Teams with the actual 2025-26 record gradient that produced the
        # CLE-as-8 bug in production.
        teams = [
            (1610612760, "OKC", "West", 0.795),
            (1610612759, "SAS", "West", 0.759),
            (1610612765, "DET", "East", 0.722),
            (1610612738, "BOS", "East", 0.679),
            (1610612752, "NYK", "East", 0.646),
            (1610612747, "LAL", "West", 0.641),
            (1610612743, "DEN", "West", 0.641),
            (1610612739, "CLE", "East", 0.633),
        ]
        for team_id, abbr, _, _ in teams:
            session.add(Team(id=team_id, abbreviation=abbr, name=abbr))
        for team_id, _, _, w_pct in teams:
            session.add(
                TeamSeasonStat(
                    team_id=team_id,
                    season=season,
                    is_playoff=False,
                    gp=82,
                    w_pct=w_pct,
                )
            )
        session.commit()

        # League-wide: CLE is 8th. Within East: CLE is 4th (DET, BOS, NYK ahead).
        assert _seed_lookup(1610612739, season, session) == 4, (
            "CLE must be East 4 seed (not league-wide rank 8)"
        )
        # East ordering: DET 1, BOS 2, NYK 3, CLE 4.
        assert _seed_lookup(1610612765, season, session) == 1, "DET = East 1"
        assert _seed_lookup(1610612738, season, session) == 2, "BOS = East 2"
        assert _seed_lookup(1610612752, season, session) == 3, "NYK = East 3"
        # West ordering: OKC 1, SAS 2, LAL 3 (or DEN 3 — tie).
        assert _seed_lookup(1610612760, season, session) == 1, "OKC = West 1"
        assert _seed_lookup(1610612759, season, session) == 2, "SAS = West 2"
        # LAL and DEN tie at 0.641; deterministic by team_id.
        lal_seed = _seed_lookup(1610612747, season, session)
        den_seed = _seed_lookup(1610612743, season, session)
        assert {lal_seed, den_seed} == {3, 4}, "LAL and DEN should be West 3 and 4"
    finally:
        session.close()


def test_build_or_refresh_bracket_routes_east_and_west_into_separate_slots():
    """Reproduce the production bug at the integration level: with
    Team.conference NULL but real abbrs, the builder must still route
    East and West R1 winners into separate R2 slots (`-E-R2-TOP` vs
    `-W-R2-TOP`), not collapse them into shared `-X-R2-TOP`."""
    from services.playoff_bracket_service import build_or_refresh_bracket

    SessionLocal = _make_session_factory()
    session = SessionLocal()
    try:
        season = "2025-26"
        # Two teams from each conference, no Team.conference column set —
        # mimicking the production state.
        bos = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
        mia = Team(id=1610612748, abbreviation="MIA", name="Miami Heat")
        okc = Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder")
        hou = Team(id=1610612745, abbreviation="HOU", name="Houston Rockets")
        session.add_all([bos, mia, okc, hou])
        # Regular-season W% so _seed_lookup ranks them.
        session.add_all([
            TeamSeasonStat(team_id=bos.id, season=season, is_playoff=False, gp=82, w_pct=0.78),
            TeamSeasonStat(team_id=mia.id, season=season, is_playoff=False, gp=82, w_pct=0.51),
            TeamSeasonStat(team_id=okc.id, season=season, is_playoff=False, gp=82, w_pct=0.80),
            TeamSeasonStat(team_id=hou.id, season=season, is_playoff=False, gp=82, w_pct=0.49),
        ])
        # BOS sweeps MIA 4-0 (East 1v8), OKC sweeps HOU 4-0 (West 1v8).
        for i, (home, away) in enumerate([
            (bos, mia), (bos, mia), (mia, bos), (mia, bos),
            (okc, hou), (okc, hou), (hou, okc), (hou, okc),
        ], start=1):
            home_score = 110 if home in (bos, okc) else 95
            away_score = 95 if home in (bos, okc) else 110
            session.add(
                GameLog(
                    game_id="00425{0:05d}".format(i),
                    season=season,
                    game_date=date(2026, 4, 18 + i),
                    home_team_id=home.id, away_team_id=away.id,
                    home_score=home_score, away_score=away_score,
                    season_type="Playoffs",
                )
            )
        session.commit()
        build_or_refresh_bracket(session, season)

        # Two distinct R2 slots — one E, one W. NOT a single -X- row.
        # (Whether the E series ends up TOP or BOT and the W series TOP or
        # BOT depends on _seed_lookup's global w_pct ranking, which isn't
        # what we're locking down here. The bug was both teams collapsing
        # into a *shared* X-R2 row regardless of conference — that's the
        # invariant under test.)
        r2_rows = (
            session.query(PlayoffSeries)
            .filter(PlayoffSeries.season == season, PlayoffSeries.round == 2)
            .all()
        )
        slot_ids = sorted(r.series_id for r in r2_rows)
        e_slots = [sid for sid in slot_ids if sid.startswith("2025-26-E-R2-")]
        w_slots = [sid for sid in slot_ids if sid.startswith("2025-26-W-R2-")]
        x_slots = [sid for sid in slot_ids if "-X-R2" in sid]
        assert e_slots, "East R2 slot must exist (bug: collapsed to X)"
        assert w_slots, "West R2 slot must exist separately from East"
        assert not x_slots, (
            "must not produce cross-conference X-R2 slot ids; "
            "got: {0}".format(x_slots)
        )
        # The East slot must hold an East team; the West slot must hold a
        # West team — never crossed.
        for r in r2_rows:
            if r.series_id.startswith("2025-26-E-R2-"):
                team_id = r.top_seed_team_id or r.bottom_seed_team_id
                assert team_id in (bos.id, mia.id), (
                    "E slot must hold an East team, got team_id={0}".format(team_id)
                )
            elif r.series_id.startswith("2025-26-W-R2-"):
                team_id = r.top_seed_team_id or r.bottom_seed_team_id
                assert team_id in (okc.id, hou.id), (
                    "W slot must hold a West team, got team_id={0}".format(team_id)
                )
    finally:
        session.close()
