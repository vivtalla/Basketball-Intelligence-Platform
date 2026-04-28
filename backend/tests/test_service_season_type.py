"""Sprint 73 — verify season_type plumbing across services and routers.

EA3 deliverable: ensure callers can request playoff-aware reads from the
unblocked services without breaking the default `Regular Season` behaviour.
"""
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import Player, SeasonStat, Team, TeamSeasonStat  # noqa: E402
from routers.standings import _standings_from_team_season_stats  # noqa: E402
from services.player_archetype_service import (  # noqa: E402
    classify_player_archetype,
    clear_archetype_cache,
)
from services.team_fit_service import build_team_fit_report  # noqa: E402


SEASON = "2025-26"


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal()


def _add_player(db, pid: int, name: str, height: str = "6-7", position: str = "Forward", team_id=None):
    if db.query(Player).filter(Player.id == pid).first() is None:
        db.add(Player(id=pid, full_name=name, height=height, position=position, team_id=team_id))


def _stat_row(db, pid: int, season: str = SEASON, is_playoff: bool = False, **stat_overrides):
    """Add a SeasonStat row. Player must already exist."""
    defaults = dict(
        player_id=pid, season=season, team_abbreviation="TOT", is_playoff=is_playoff,
        gp=70, min_pg=32.0,
        pts_pg=15.0, reb_pg=5.0, ast_pg=4.0, stl_pg=1.0, blk_pg=0.5, tov_pg=2.0,
        fgm=5.6, fga=12.0, fg_pct=0.467,
        fg3m=1.8, fg3a=4.8, fg3_pct=0.375,
        ftm=2.8, fta=3.6, ft_pct=0.778,
        oreb=1.0, dreb=4.0, pf=2.0,
        usg_pct=20.0, ts_pct=0.560, efg_pct=0.540, per=15.0, bpm=0.0,
        off_rating=112.0, def_rating=112.0, net_rating=0.0,
        pace=100.0, pie=0.10, darko=0.0, epm=0.0, rapm=0.0,
        obpm=0.0, dbpm=0.0,
        ftr=0.30, par3=0.40, ast_tov=2.0, oreb_pct=4.0,
    )
    defaults.update(stat_overrides)
    db.add(SeasonStat(**defaults))


def _seed_archetype_pool(db, is_playoff: bool, anchor_count: int = 30) -> None:
    """Seed a rotation-player pool with enough spread for stable z-scores.

    Even playoff fillers carry GP >= MIN_GP so they qualify for the season frame;
    real-world playoff GP would be lower, but the SeasonStat MIN_GP gate is
    shared with the regular-season path.
    """
    import random
    rng = random.Random(123 if is_playoff else 42)
    base_pid = 5000 if is_playoff else 1000
    for i in range(anchor_count):
        slot = i % 5
        gp = rng.randint(55, 78)
        height = ["6-3", "6-7", "6-10", "7-0", "6-5"][slot]
        _add_player(db, base_pid + i, "Filler {0}".format(i), height=height)
        _stat_row(
            db,
            base_pid + i,
            is_playoff=is_playoff,
            team_abbreviation=["BOS", "LAL", "CHI", "ORL"][i % 4],
            gp=gp,
            min_pg=rng.uniform(18.0, 34.0),
            usg_pct=rng.uniform(14.0, 26.0),
            ast_pg=rng.uniform(1.5, 6.0),
            stl_pg=rng.uniform(0.5, 1.5),
            blk_pg=rng.uniform(0.2, 1.0),
            tov_pg=rng.uniform(1.0, 2.5),
            par3=rng.uniform(0.25, 0.55),
            ftr=rng.uniform(0.18, 0.35),
            ts_pct=rng.uniform(0.520, 0.610),
            obpm=rng.uniform(-2.0, 3.0),
            dbpm=rng.uniform(-2.0, 2.0),
            oreb_pct=rng.uniform(2.0, 7.0),
            ast_tov=rng.uniform(1.2, 3.0),
            fg3a=rng.randint(80, 250), fg3_pct=rng.uniform(0.320, 0.400),
        )


# ---------------------------------------------------------------------------
# 1. Archetype service routes to playoff rows when season_type="Playoffs".
# ---------------------------------------------------------------------------

def test_archetype_service_returns_different_archetype_for_playoff():
    db = make_session()
    try:
        clear_archetype_cache()

        _seed_archetype_pool(db, is_playoff=False)
        _seed_archetype_pool(db, is_playoff=True)

        subject_pid = 99
        _add_player(db, subject_pid, "Subject Player", height="6-7", position="Forward")

        # Regular-season profile: balanced wing.
        _stat_row(
            db,
            subject_pid,
            is_playoff=False,
            team_abbreviation="BOS",
            gp=72, min_pg=33.0,
            usg_pct=20.0, ast_pg=4.0, stl_pg=1.0, blk_pg=0.4,
            par3=0.40, ftr=0.25, ts_pct=0.56, obpm=0.0, dbpm=0.0,
            oreb_pct=4.0, ast_tov=2.0,
            fg3a=200, fg3_pct=0.36,
        )
        # Playoff profile: heliocentric usage, elite playmaking, elite efficiency.
        # GP set above MIN_GP so the subject qualifies for the playoff peer pool.
        _stat_row(
            db,
            subject_pid,
            is_playoff=True,
            team_abbreviation="BOS",
            gp=22, min_pg=38.0,
            usg_pct=34.0, ast_pg=9.5, stl_pg=1.6, blk_pg=0.7,
            par3=0.42, ftr=0.42, ts_pct=0.64, obpm=8.0, dbpm=2.5,
            oreb_pct=6.0, ast_tov=3.0,
            fg3a=80, fg3_pct=0.42,
        )
        db.commit()

        regular = classify_player_archetype(db, subject_pid, SEASON, season_type="Regular Season")
        playoff = classify_player_archetype(db, subject_pid, SEASON, season_type="Playoffs")

        assert regular.confidence_note is None
        assert playoff.confidence_note == "Playoff sample — confidence reduced one tier"
        # Different archetype OR different payload (confidence_note guarantees the
        # latter; assert payload differs at minimum).
        assert (regular.archetype_key, regular.confidence_note) != (
            playoff.archetype_key,
            playoff.confidence_note,
        )
    finally:
        clear_archetype_cache()
        db.close()


# ---------------------------------------------------------------------------
# 2. Team-Fit emits low-sample warning when playoff sample is below threshold.
# ---------------------------------------------------------------------------

def _seed_team_fit_pool(db, is_playoff: bool, gp: int = 70):
    """Spread enough V2-qualifying rows on a single team for Team-Fit to score.

    `_qualified_rows_v2` enforces a season-type aware MIN_GP (20 regular,
    PLAYOFF_MIN_GP=4 playoff). Tests pick `gp` to stay above whichever gate
    applies for the configured season type.
    """
    teams = [(1, "BOS", "Boston Celtics"), (2, "ORL", "Orlando Magic")]
    for tid, abbr, name in teams:
        if db.query(Team).filter(Team.id == tid).first() is None:
            db.add(Team(id=tid, abbreviation=abbr, name=name))

    # 24 spread rows ensure stable per-season z-scores.
    for i in range(24):
        pid = (7000 if is_playoff else 2000) + i
        team = ["BOS", "ORL"][i % 2]
        _add_player(db, pid, "Filler {0}".format(i), position=["Guard", "Forward", "Center"][i % 3])
        _stat_row(
            db,
            pid,
            is_playoff=is_playoff,
            team_abbreviation=team,
            gp=gp,
            usg_pct=13.0 + (i % 8) * 2.0,
            pts_pg=9.0 + (i % 9) * 2.0,
            ast_pg=1.5 + (i % 6) * 0.8,
            reb_pg=3.0 + (i % 7) * 1.0,
            stl_pg=0.4 + (i % 5) * 0.25,
            blk_pg=0.1 + (i % 5) * 0.25,
            ts_pct=0.50 + (i % 8) * 0.015,
            per=10.0 + (i % 9) * 1.5,
            par3=0.18 + (i % 7) * 0.07,
            ftr=0.14 + (i % 6) * 0.05,
        )


def test_team_fit_low_sample_warning_for_playoffs():
    db = make_session()
    try:
        # Seed enough rows on BOS so Team-Fit can score the current team.
        # Playoff filler GP=12 stays above PLAYOFF_MIN_GP but well above the
        # 8-game low-sample threshold, so they don't trigger the warning.
        _seed_team_fit_pool(db, is_playoff=True, gp=12)

        subject_pid = 1
        _add_player(db, subject_pid, "Subject Player", position="Forward")
        # GP=5 is below PLAYOFF_LOW_SAMPLE_THRESHOLD (8) but at/above
        # PLAYOFF_MIN_GP (4) so the subject row still qualifies for the V2 pool.
        _stat_row(
            db,
            subject_pid,
            is_playoff=True,
            team_abbreviation="BOS",
            gp=5,
            min_pg=34.0,
            usg_pct=27.0,
            pts_pg=22.0,
            ast_pg=6.0,
            reb_pg=6.5,
            stl_pg=1.4,
            blk_pg=0.7,
            ts_pct=0.59,
            per=22.0,
            par3=0.46,
            ftr=0.36,
        )
        db.commit()

        report = build_team_fit_report(
            db, subject_pid, SEASON, limit=3, season_type="Playoffs"
        )
        assert report.low_sample_warning is not None
        assert "Limited playoff sample" in report.low_sample_warning
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3. Standings returns playoff record when season_type="Playoffs".
# ---------------------------------------------------------------------------

def test_standings_respects_season_type():
    db = make_session()
    try:
        bos = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
        db.add(bos)

        # Both regular-season and playoff rows for the same team / season.
        db.add_all(
            [
                TeamSeasonStat(
                    team_id=bos.id,
                    season=SEASON,
                    is_playoff=False,
                    gp=72,
                    w=58,
                    l=14,
                    w_pct=0.806,
                    pts_pg=120.0,
                    plus_minus_pg=10.0,
                ),
                TeamSeasonStat(
                    team_id=bos.id,
                    season=SEASON,
                    is_playoff=True,
                    gp=3,
                    w=2,
                    l=1,
                    w_pct=0.667,
                    pts_pg=112.0,
                    plus_minus_pg=4.0,
                ),
            ]
        )
        db.commit()

        regular = _standings_from_team_season_stats(SEASON, db, season_type="Regular Season")
        playoff = _standings_from_team_season_stats(SEASON, db, season_type="Playoffs")

        assert regular is not None and len(regular) == 1
        assert (regular[0].wins, regular[0].losses) == (58, 14)

        assert playoff is not None and len(playoff) == 1
        assert (playoff[0].wins, playoff[0].losses) == (2, 1)
    finally:
        db.close()
