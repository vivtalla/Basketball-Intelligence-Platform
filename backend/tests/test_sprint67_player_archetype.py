"""Sprint 67 — player archetype classifier tests.

Covers:
  - height parser
  - subject-row selection (TOT preferred, split-season ambiguity)
  - rule routing for each non-fallback archetype that's cheap to synthesize
  - the two known regression bugs: Gobert-type → defensive_anchor (not
    interior_finisher), and SGA-band → iso_scorer (not balanced_role)
  - fallbacks: developmental (thin sample) vs balanced_role
  - confidence bands
"""
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import Player, SeasonStat  # noqa: E402
from services.player_archetype_service import (  # noqa: E402
    METHODOLOGY_VERSION,
    _select_subject_row,
    clear_archetype_cache,
    classify_player_archetype,
    parse_height_to_inches,
)


SEASON = "2025-26"


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TS = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TS()


def _stat_row(db, pid: int, season: str = SEASON, **stat_overrides):
    """Add a SeasonStat row for a player that already exists in the DB.
    Use this when a single Player spans multiple seasons — _add_player()
    would re-insert the Player and violate UNIQUE(players.id).
    """
    defaults = dict(
        player_id=pid, season=season, team_abbreviation="TOT", is_playoff=False,
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


def _add_player(db, pid: int, name: str, height: str, **stat_overrides):
    """Add one Player + one SeasonStat with sensible rotation defaults, then override."""
    db.add(Player(id=pid, full_name=name, height=height))
    defaults = dict(
        player_id=pid, season=SEASON, team_abbreviation="TOT", is_playoff=False,
        gp=70, min_pg=32.0,
        # Baseline role-average profile — each archetype test overrides the features it cares about.
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


def _seed_league(db, anchor_count: int = 40) -> None:
    """Seed a realistic rotation-player pool with enough spread on every feature
    that z-scores behave like a real league distribution (std bounded away from zero).
    """
    import random
    rng = random.Random(42)
    for i in range(anchor_count):
        # Bucket the pool into rough role slots so each feature has variance.
        slot = i % 5  # 0 guard-creator, 1 wing, 2 stretch-big, 3 interior-big, 4 bench
        base = dict(
            gp=rng.randint(55, 78), min_pg=rng.uniform(18.0, 34.0),
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
        if slot == 2:  # stretch bigs bias
            base.update(par3=rng.uniform(0.38, 0.58), oreb_pct=rng.uniform(3.0, 8.0))
            height = "6-10"
        elif slot == 3:  # interior bigs bias
            base.update(par3=rng.uniform(0.02, 0.15), blk_pg=rng.uniform(0.8, 2.0), oreb_pct=rng.uniform(8.0, 14.0))
            height = "7-0"
        elif slot == 0:  # guards
            height = "6-3"
        elif slot == 1:  # wings
            height = "6-7"
        else:
            height = "6-5"
        _add_player(db, 1000 + i, f"Filler {i}", height, **base)
    db.commit()


def _classify(db, pid: int):
    clear_archetype_cache()
    return classify_player_archetype(db, pid, SEASON)


# --- Height parser ----------------------------------------------------------


def test_height_parser_variants():
    assert parse_height_to_inches("6-7") == 79
    assert parse_height_to_inches("6'7") == 79
    assert parse_height_to_inches("6'7\"") == 79
    assert parse_height_to_inches("6’7") == 79
    assert parse_height_to_inches("7-0") == 84
    assert parse_height_to_inches("5-11") == 71


def test_height_parser_rejects_garbage():
    assert parse_height_to_inches(None) is None
    assert parse_height_to_inches("") is None
    assert parse_height_to_inches("unknown") is None
    # Out of NBA sanity range
    assert parse_height_to_inches("2-0") is None
    assert parse_height_to_inches("9-5") is None


# --- Subject-row selection --------------------------------------------------


def test_select_subject_prefers_tot():
    tot = SeasonStat(player_id=1, season=SEASON, team_abbreviation="TOT", is_playoff=False, gp=70)
    lac = SeasonStat(player_id=1, season=SEASON, team_abbreviation="LAC", is_playoff=False, gp=40)
    nyk = SeasonStat(player_id=1, season=SEASON, team_abbreviation="NYK", is_playoff=False, gp=30)
    assert _select_subject_row([lac, tot, nyk]) is tot


def test_select_subject_single_rs_row():
    row = SeasonStat(player_id=1, season=SEASON, team_abbreviation="BOS", is_playoff=False, gp=70)
    assert _select_subject_row([row]) is row


def test_select_subject_split_season_without_tot_is_ambiguous():
    a = SeasonStat(player_id=1, season=SEASON, team_abbreviation="LAC", is_playoff=False, gp=40)
    b = SeasonStat(player_id=1, season=SEASON, team_abbreviation="NYK", is_playoff=False, gp=30)
    assert _select_subject_row([a, b]) is None


def test_select_subject_ignores_playoff_rows():
    rs = SeasonStat(player_id=1, season=SEASON, team_abbreviation="BOS", is_playoff=False, gp=70)
    po = SeasonStat(player_id=1, season=SEASON, team_abbreviation="BOS", is_playoff=True, gp=12)
    assert _select_subject_row([po, rs]) is rs


# --- Classifier rule routing ------------------------------------------------


def test_heliocentric_creator_fires():
    db = make_session()
    try:
        _seed_league(db)
        _add_player(
            db, 1, "Heliocentric Star", "6-7",
            usg_pct=34.0,      # z high
            ast_pg=10.0,       # ast_rate z high
            obpm=9.0,          # z high
            ts_pct=0.620,
        )
        db.commit()
        a = _classify(db, 1)
        assert a.archetype_key == "heliocentric_creator"
        assert a.confidence == "high"
        assert a.methodology_version == METHODOLOGY_VERSION
        assert a.contributors  # fingerprint populated
    finally:
        db.close()


def test_iso_scorer_sga_band_fires_not_balanced():
    """Regression: SGA-band (high usage, moderate assists, low 3PA, high FTR)
    must route to iso_scorer, not fall through to balanced_role."""
    db = make_session()
    try:
        _seed_league(db)
        _add_player(
            db, 2, "Mid-range Creator", "6-6",
            usg_pct=32.0,      # z high
            ast_pg=5.5,        # ast_rate z ~ moderate (0.5-0.8 band)
            obpm=3.0,          # not elite; misses heliocentric
            par3=0.30,         # below league avg → par3_z < 0
            ftr=0.45,          # elite ftr
            ts_pct=0.600,
        )
        db.commit()
        a = _classify(db, 2)
        assert a.archetype_key == "iso_scorer"
        assert a.archetype_key != "balanced_role"
    finally:
        db.close()


def test_gobert_profile_routes_to_defensive_anchor_not_interior_finisher():
    """Regression for the ordering bug: a rim-protecting big with a Gobert-style
    offensive profile (elite TS, very low par3, high oreb) must route to
    defensive_anchor at rank 9, not interior_finisher at rank 10."""
    db = make_session()
    try:
        _seed_league(db)
        _add_player(
            db, 3, "Rim Protector Big", "7-1",
            usg_pct=18.0,
            ast_pg=1.5,
            blk_pg=2.8,        # elite blk_rate
            dbpm=4.5,          # elite dbpm
            obpm=1.0,
            par3=0.03,         # almost no 3s
            ftr=0.50,
            ts_pct=0.680,      # elite TS
            oreb_pct=15.0,     # high oreb
        )
        db.commit()
        a = _classify(db, 3)
        assert a.archetype_key == "defensive_anchor"
        assert a.archetype_key != "interior_finisher"
    finally:
        db.close()


def test_stretch_big_fires_only_after_defensive_anchor_fails():
    db = make_session()
    try:
        _seed_league(db)
        _add_player(
            db, 4, "Stretch Five", "6-11",
            blk_pg=0.8,        # blk_rate moderate — fails DA's 1.0 floor
            dbpm=0.3,          # fails DA's 0.8 floor
            par3=0.60,         # high par3
            fg3a=180, fg3_pct=0.382,
            usg_pct=22.0, ts_pct=0.580, ast_pg=2.0, ftr=0.22, oreb_pct=6.0,
        )
        db.commit()
        a = _classify(db, 4)
        assert a.archetype_key == "stretch_big"
    finally:
        db.close()


def test_movement_shooter_fires():
    db = make_session()
    try:
        _seed_league(db)
        _add_player(
            db, 5, "Specialist Spacer", "6-6",
            usg_pct=14.0,      # low usage
            ast_pg=2.0,
            par3=0.82,         # very high 3PA rate
            fg3a=400, fg3_pct=0.420,  # volume + accuracy
            ts_pct=0.620, ftr=0.12, oreb_pct=1.5,
            dbpm=-0.5,
        )
        db.commit()
        a = _classify(db, 5)
        assert a.archetype_key == "movement_shooter"
    finally:
        db.close()


def test_balanced_role_when_no_rule_fires():
    db = make_session()
    try:
        _seed_league(db)
        # All features at league-average defaults — no trigger fires.
        _add_player(db, 6, "League-Average Starter", "6-6", gp=70, min_pg=28.0)
        db.commit()
        a = _classify(db, 6)
        assert a.archetype_key == "balanced_role"
        assert a.confidence == "low"
        assert "near league average" in a.reason
    finally:
        db.close()


def test_developmental_on_thin_sample():
    db = make_session()
    try:
        _seed_league(db)
        # Sub-threshold minutes/games → never enters the peer pool.
        _add_player(db, 7, "Thin-Sample Rookie", "6-6", gp=10, min_pg=8.0)
        db.commit()
        a = _classify(db, 7)
        assert a.archetype_key == "developmental"
        assert a.sample.peer_pool_size > 0  # pool still computed; this player just isn't in it
    finally:
        db.close()


def test_developmental_when_no_row_at_all():
    db = make_session()
    try:
        _seed_league(db)
        db.commit()
        a = _classify(db, 99999)  # player that doesn't exist
        assert a.archetype_key == "developmental"
        assert "No regular-season row" in a.reason
    finally:
        db.close()


# --- Sprint 68 — multi-season archetype history ----------------------------


def test_archetype_history_returns_entries_oldest_to_newest():
    from services.player_archetype_service import build_archetype_history

    db = make_session()
    try:
        # Add the subject Player row ONCE (UNIQUE players.id)
        db.add(Player(id=1, full_name="Subject", height="6-7"))
        # Add a filler pool per season (each filler is a new Player + SeasonStat)
        for season_idx, (season, usg) in enumerate(
            (("2022-23", 28.0), ("2023-24", 31.0), ("2024-25", 33.0))
        ):
            for i in range(15):
                filler_id = 2000 + season_idx * 100 + i
                db.add(Player(id=filler_id, full_name=f"Filler {season}-{i}", height="6-6"))
                _stat_row(db, filler_id, season, gp=65, min_pg=28.0,
                          usg_pct=18.0 + i * 0.5, ast_pg=3.0 + i * 0.1)
            # Subject's SeasonStat for this season (Player row already exists)
            _stat_row(db, 1, season, gp=70, min_pg=34.0, usg_pct=usg,
                      ast_pg=8.0, obpm=5.0, pts_pg=25.0)
        db.commit()
        clear_archetype_cache()

        history = build_archetype_history(db, 1)
        seasons = [h.season for h in history]
        assert seasons == sorted(seasons)  # oldest → newest
        assert len(history) == 3
        # Every entry has a real archetype key (Literal) even when fallback fires
        assert all(h.archetype_key for h in history)
    finally:
        db.close()


def test_archetype_history_handles_player_with_no_rows():
    from services.player_archetype_service import build_archetype_history

    db = make_session()
    try:
        _seed_league(db)
        db.commit()
        history = build_archetype_history(db, 99999)
        assert history == []
    finally:
        db.close()
