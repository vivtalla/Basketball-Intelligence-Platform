"""Sprint 67 (B2) — similarity mode + archetype attachment tests.

Covers:
  - age parser (parse_age_as_of_season)
  - find_similar_players_with_archetype returns comps with archetype_key/label/confidence
  - season mode filters to same-season candidates
  - age mode excludes the subject player across all seasons and keeps only age±1
  - team_fit mode raises NotImplementedError (deferred to B10)
  - legacy find_similar_players signature unchanged (no regression on the old path)
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
    clear_archetype_cache,
    parse_age_as_of_season,
)
from services.similarity_service import (  # noqa: E402
    SIMILARITY_STATS,
    SIMILARITY_STATS_V2,
    find_similar_players,
    find_similar_players_with_archetype,
)


def make_session():
    engine = create_engine("sqlite:///:memory:")
    TS = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    _PENDING_PLAYERS.clear()
    return TS()


_PENDING_PLAYERS: set = set()


def _add_row(db, pid: int, name: str, birth: str, season: str, height: str = "6-6", **stats):
    # Use a per-test sentinel so multi-season inserts for the same player don't
    # violate UNIQUE(players.id). db.query() doesn't see pre-flush adds, so track here.
    if pid not in _PENDING_PLAYERS and db.query(Player).filter(Player.id == pid).first() is None:
        db.add(Player(id=pid, full_name=name, height=height, birth_date=birth))
        _PENDING_PLAYERS.add(pid)
    defaults = dict(
        player_id=pid, season=season, team_abbreviation="TOT", is_playoff=False,
        gp=70, min_pg=32.0,
        pts_pg=18.0, reb_pg=5.0, ast_pg=4.5, stl_pg=1.0, blk_pg=0.5, tov_pg=2.2,
        fgm=6.5, fga=14.0, fg_pct=0.464,
        fg3m=2.0, fg3a=5.5, fg3_pct=0.363,
        ftm=3.0, fta=4.0, ft_pct=0.750,
        oreb=1.0, dreb=4.0, pf=2.5,
        usg_pct=22.0, ts_pct=0.570, efg_pct=0.540, per=16.0, bpm=0.0,
        off_rating=112.0, def_rating=112.0, net_rating=0.0,
        pace=100.0, pie=0.12, darko=0.0, epm=0.0, rapm=0.0, obpm=0.0, dbpm=0.0,
        ftr=0.29, par3=0.40, ast_tov=2.0, oreb_pct=4.0,
    )
    defaults.update(stats)
    db.add(SeasonStat(**defaults))


# --- Age parser -------------------------------------------------------------


def test_age_parser_common_formats():
    assert parse_age_as_of_season("1998-02-01", "2023-24") == 25
    assert parse_age_as_of_season("Feb 1, 1998", "2023-24") == 25
    assert parse_age_as_of_season("02/01/1998", "2023-24") == 25


def test_age_parser_returns_none_on_bad_input():
    assert parse_age_as_of_season(None, "2023-24") is None
    assert parse_age_as_of_season("", "2023-24") is None
    assert parse_age_as_of_season("garbage", "2023-24") is None


def test_age_parser_handles_birthday_before_vs_after_oct_1():
    # Oct 1, 2023 reference: Sept 30 birthday has already been celebrated, age +1
    assert parse_age_as_of_season("1998-09-30", "2023-24") == 25
    # Oct 2 birthday hasn't yet, age one lower
    assert parse_age_as_of_season("1998-10-02", "2023-24") == 24


# --- Feature count regression ----------------------------------------------


def test_v2_feature_count_is_nine_plus_four():
    assert len(SIMILARITY_STATS_V2) == len(SIMILARITY_STATS) + 4
    new_keys = {k for k, _ in SIMILARITY_STATS_V2} - {k for k, _ in SIMILARITY_STATS}
    assert new_keys == {"par3", "ftr", "stl_pg", "blk_pg"} - {k for k, _ in SIMILARITY_STATS}
    # stl_pg and blk_pg already exist in SIMILARITY_STATS, so the *added* keys are just par3 + ftr
    # plus the (stl_pg, blk_pg) re-weighting copies; this check confirms the new role-aware
    # dimensions (par3, ftr) landed.
    assert {"par3", "ftr"}.issubset({k for k, _ in SIMILARITY_STATS_V2})


# --- Season mode -----------------------------------------------------------


def test_season_mode_returns_archetype_labels_and_filters_to_same_season():
    clear_archetype_cache()
    db = make_session()
    try:
        # Subject in 2023-24
        _add_row(db, 1, "Subject", "1998-01-01", "2023-24",
                 usg_pct=30.0, ast_pg=8.0, obpm=5.0, pts_pg=28.0, per=25.0)
        # Close season-24 comps (varied to anchor z-scores)
        for i in range(12):
            _add_row(db, 100 + i, f"Peer 24 {i}", "1998-01-01", "2023-24",
                     usg_pct=18.0 + i * 0.5, ast_pg=3.0 + i * 0.3, pts_pg=12.0 + i)
        # Decoy rows from a different season; must NOT appear in season mode
        for i in range(5):
            _add_row(db, 200 + i, f"Peer 22 {i}", "1998-01-01", "2021-22",
                     usg_pct=28.0 + i * 0.4, ast_pg=7.0 + i * 0.3, pts_pg=25.0 + i)
        db.commit()

        comps = find_similar_players_with_archetype(db, 1, "2023-24", mode="season", n=8)
        assert comps, "expected at least one comp"
        assert all(c["season"] == "2023-24" for c in comps)
        assert all(c["player_id"] != 1 for c in comps)
        # Archetype attached on every comp
        assert all("archetype_key" in c and c["archetype_key"] for c in comps)
        assert all("archetype_label" in c and c["archetype_label"] for c in comps)
        assert all("archetype_confidence" in c for c in comps)
    finally:
        db.close()


# --- Age mode --------------------------------------------------------------


def test_age_mode_excludes_subject_across_seasons_and_filters_to_age_window():
    clear_archetype_cache()
    db = make_session()
    try:
        # Subject born 1999-01 — age on 2023-10-01 = 24
        _add_row(db, 1, "Subject", "1999-01-01", "2023-24", usg_pct=30.0, ast_pg=8.0, obpm=5.0, pts_pg=28.0)
        # Subject's OTHER season — must be excluded
        _add_row(db, 1, "Subject", "1999-01-01", "2022-23", usg_pct=26.0, ast_pg=6.0, obpm=3.0, pts_pg=23.0)

        # Same-age peer in any season (age 23–25 on Oct 1 of that season start year)
        _add_row(db, 10, "Age Peer A", "1998-06-01", "2022-23", usg_pct=25.0, ast_pg=6.0, pts_pg=22.0)  # age 24
        _add_row(db, 11, "Age Peer B", "2000-03-01", "2023-24", usg_pct=24.0, ast_pg=5.0, pts_pg=20.0)  # age 23

        # Out-of-window peer (age 30 in his season) — must be excluded
        _add_row(db, 20, "Old Peer", "1993-01-01", "2023-24", usg_pct=22.0, ast_pg=5.0, pts_pg=18.0)

        # Filler to give z-scores a real distribution per-season
        for i in range(10):
            _add_row(db, 100 + i, f"Filler 24 {i}", "1998-01-01", "2023-24",
                     usg_pct=18.0 + i * 0.5, ast_pg=3.0 + i * 0.3, pts_pg=12.0 + i)
        for i in range(10):
            _add_row(db, 200 + i, f"Filler 23 {i}", "1998-01-01", "2022-23",
                     usg_pct=18.0 + i * 0.5, ast_pg=3.0 + i * 0.3, pts_pg=12.0 + i)
        db.commit()

        comps = find_similar_players_with_archetype(db, 1, "2023-24", mode="age", n=8)
        ids = {c["player_id"] for c in comps}
        assert 1 not in ids, "age mode must exclude the subject player entirely"
        assert 20 not in ids, "age mode must filter out players outside the age window"
    finally:
        db.close()


# --- team_fit mode (Sprint 68) ---------------------------------------------


def test_team_fit_mode_returns_same_season_comps_excluding_subject():
    clear_archetype_cache()
    db = make_session()
    try:
        _add_row(db, 1, "Subject", "1998-01-01", "2023-24",
                 team_abbreviation="BOS",
                 usg_pct=28.0, ast_pg=7.0, pts_pg=24.0)
        for i in range(12):
            team = "BOS" if i % 3 == 0 else "LAL"
            _add_row(db, 100 + i, f"Peer {i}", "1998-01-01", "2023-24",
                     team_abbreviation=team,
                     usg_pct=18.0 + i * 0.5, ast_pg=3.0 + i * 0.3, pts_pg=12.0 + i)
        db.commit()
        comps = find_similar_players_with_archetype(db, 1, "2023-24", mode="team_fit", n=5)
        assert comps, "team_fit should return comps now (Sprint 68)"
        ids = {c["player_id"] for c in comps}
        assert 1 not in ids
        # All comps must be same-season
        assert all(c["season"] == "2023-24" for c in comps)
        # Archetype labels attached
        assert all("archetype_key" in c for c in comps)


    finally:
        db.close()


def test_team_fit_weight_overrides_penalize_duplicated_features():
    """Unit-level check on the penalty mechanism: when the subject and a
    same-team teammate have similar z-scores on a feature (|gap| < 0.5), the
    weight override for that feature is 0.4× baseline. Features without a
    teammate match keep the 1.0× multiplier."""
    from services.similarity_service import (
        _team_fit_weight_overrides,
        _qualified_rows_v2,
        _season_norms_v2,
        _TEAM_FIT_PENALTY,
    )
    clear_archetype_cache()
    db = make_session()
    try:
        # Subject and teammate both high-usage (overlap on usg_pct)
        _add_row(db, 1, "Subject", "1998-01-01", "2023-24",
                 team_abbreviation="BOS",
                 usg_pct=30.0, ast_pg=5.0)
        _add_row(db, 2, "Teammate", "1998-01-01", "2023-24",
                 team_abbreviation="BOS",
                 usg_pct=29.5, ast_pg=2.5)  # close on usg, far on ast
        for i in range(15):
            _add_row(db, 100 + i, f"Filler {i}", "1998-01-01", "2023-24",
                     team_abbreviation="CHI",
                     usg_pct=18.0 + i * 0.3, ast_pg=3.0 + i * 0.2)
        db.commit()

        all_rows = _qualified_rows_v2(db)
        norms = _season_norms_v2(all_rows)
        subject = next(r for r in all_rows if r.player_id == 1)
        overrides = _team_fit_weight_overrides(subject, all_rows, norms)

        # usg should be penalized (subject and teammate both high)
        assert overrides["usg_pct"] == _TEAM_FIT_PENALTY
        # ast should NOT be penalized (teammate is low vs subject high, gap > 0.5)
        assert overrides["ast_pg"] == 1.0
    finally:
        db.close()


def test_team_fit_changes_ranking_vs_season_mode():
    """When a teammate duplicates a feature, team_fit should produce a
    DIFFERENT top-N ordering than season mode. We don't care which comp wins;
    we care that the penalty actually shifts the ranking."""
    clear_archetype_cache()
    db = make_session()
    try:
        # Subject has high usage AND high assists on BOS; teammate ALSO has
        # high usage but low assists → only usage is "covered" by team.
        _add_row(db, 1, "Subject", "1998-01-01", "2023-24",
                 team_abbreviation="BOS",
                 usg_pct=30.0, ast_pg=7.0, pts_pg=26.0, ts_pct=0.580, per=22.0)
        _add_row(db, 2, "BOS Teammate", "1998-01-01", "2023-24",
                 team_abbreviation="BOS",
                 usg_pct=29.5, ast_pg=2.5, pts_pg=18.0, ts_pct=0.540, per=14.0)
        # Candidate A: matches subject on usg, differs on ast (duplicates covered)
        _add_row(db, 10, "High-Usg Low-Ast", "1998-01-01", "2023-24",
                 team_abbreviation="LAL",
                 usg_pct=30.5, ast_pg=2.0, pts_pg=25.0, ts_pct=0.555, per=20.0)
        # Candidate B: differs on usg, matches subject on ast (complement)
        _add_row(db, 11, "Low-Usg High-Ast", "1998-01-01", "2023-24",
                 team_abbreviation="LAL",
                 usg_pct=18.0, ast_pg=7.5, pts_pg=14.0, ts_pct=0.560, per=15.0)
        for i in range(15):
            _add_row(db, 200 + i, f"Filler {i}", "1998-01-01", "2023-24",
                     team_abbreviation="CHI",
                     usg_pct=18.0 + i * 0.3, ast_pg=3.0 + i * 0.25,
                     pts_pg=12.0 + i * 0.4, ts_pct=0.540, per=13.0 + i * 0.1)
        db.commit()

        season_comps = find_similar_players_with_archetype(db, 1, "2023-24", mode="season", n=6)
        team_fit_comps = find_similar_players_with_archetype(db, 1, "2023-24", mode="team_fit", n=6)

        # Ordering must differ between the two modes — that's the point of the penalty.
        season_ids = tuple(c["player_id"] for c in season_comps)
        team_fit_ids = tuple(c["player_id"] for c in team_fit_comps)
        assert season_ids != team_fit_ids, (
            "team_fit should produce a different ranking than season mode when "
            "a teammate duplicates the subject's usage profile."
        )
        # Subject excluded from both
        assert 1 not in season_ids
        assert 1 not in team_fit_ids
    finally:
        db.close()


# --- Legacy compatibility --------------------------------------------------


def test_legacy_find_similar_players_unchanged():
    """The pre-Sprint-67 /api/similarity path still returns the original fields
    with no archetype keys, so existing frontend consumers don't break."""
    clear_archetype_cache()
    db = make_session()
    try:
        _add_row(db, 1, "Subject", "1998-01-01", "2023-24", usg_pct=30.0, ast_pg=8.0, pts_pg=28.0, per=24.0)
        for i in range(12):
            _add_row(db, 100 + i, f"Filler {i}", "1998-01-01", "2023-24",
                     usg_pct=18.0 + i * 0.5, ast_pg=3.0 + i * 0.3, pts_pg=12.0 + i)
        db.commit()
        comps = find_similar_players(db, 1, "2023-24", n=5, cross_era=False)
        assert comps
        expected_keys = {"player_id", "player_name", "season", "team_abbreviation",
                         "similarity_score", "gp", "pts_pg", "reb_pg", "ast_pg",
                         "ts_pct", "usg_pct", "per"}
        for c in comps:
            assert expected_keys.issubset(c.keys())
            assert "archetype_key" not in c  # legacy path does not attach archetype
    finally:
        db.close()
