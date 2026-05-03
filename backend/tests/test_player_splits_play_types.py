"""Sprint 81 — player_split_stats + play_type_stats sync + endpoint tests.

Calls route handlers directly with an in-memory SQLite session rather than
spinning up FastAPI's TestClient (httpx isn't a pinned dev dep).
"""
from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from db.database import Base  # noqa: E402
from db.models import (  # noqa: E402
    PlayTypeStat,
    Player,
    PlayerHustleStat,
    PlayerSplitStat,
    PlayerTrackingStat,
    SeasonStat,
    Team,
)
from routers.players import (  # noqa: E402
    get_player_hustle_endpoint,
    get_player_play_types,
    get_player_splits,
    get_player_tracking_endpoint,
)
from services.sync_service import (  # noqa: E402
    sync_official_play_type_stats,
    sync_official_player_general_splits,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()
    engine.dispose()


def _seed_player(session, player_id: int, name: str = "Test Player") -> None:
    session.add(Player(id=player_id, full_name=name, first_name="Test", last_name="Player"))
    session.add(SeasonStat(
        player_id=player_id, season="2024-25",
        team_abbreviation="BOS", is_playoff=False, gp=70,
    ))
    session.commit()


# ---------------------------------------------------------------------------
# Player splits sync
# ---------------------------------------------------------------------------


def test_player_splits_sync_upserts_rows(session) -> None:
    _seed_player(session, 977)
    fake_splits = [
        {
            "player_id": 977, "season": "2024-25", "is_playoff": False,
            "split_family": "LocationPlayerDashboard",
            "split_value": "Home", "label": "Home",
            "gp": 35, "w": 22, "l": 13, "w_pct": 0.629, "min": 32.5,
            "pts": 28.0, "reb": 7.0, "ast": 5.5, "tov": 2.5, "stl": 1.0, "blk": 0.5,
            "fg_pct": 0.49, "fg3_pct": 0.39, "ft_pct": 0.85,
            "ts_pct": 0.61, "usg_pct": 0.30, "plus_minus": 4.5,
        },
        {
            "player_id": 977, "season": "2024-25", "is_playoff": False,
            "split_family": "LocationPlayerDashboard",
            "split_value": "Road", "label": "Road",
            "gp": 35, "w": 18, "l": 17, "w_pct": 0.514, "min": 31.0,
            "pts": 25.0, "reb": 6.5, "ast": 5.0, "tov": 2.8, "stl": 0.8, "blk": 0.4,
            "fg_pct": 0.46, "fg3_pct": 0.36, "ft_pct": 0.84,
            "ts_pct": 0.58, "usg_pct": 0.29, "plus_minus": 1.5,
        },
    ]

    with patch(
        "services.sync_service.get_player_general_splits",
        return_value=fake_splits,
    ):
        result = sync_official_player_general_splits(
            session, season="2024-25", player_ids=[977]
        )

    assert result["players_synced"] == 1
    assert result["split_rows_synced"] == 2
    rows = session.query(PlayerSplitStat).all()
    assert len(rows) == 2
    home = next(r for r in rows if r.split_value == "Home")
    assert home.pts == 28.0
    assert home.ts_pct == 0.61


def test_player_splits_sync_idempotent(session) -> None:
    _seed_player(session, 977)
    fake = [{
        "player_id": 977, "season": "2024-25", "is_playoff": False,
        "split_family": "WinsLossesPlayerDashboard",
        "split_value": "W", "label": "W",
        "gp": 40, "pts": 30, "ts_pct": 0.62,
    }]

    with patch("services.sync_service.get_player_general_splits", return_value=fake):
        sync_official_player_general_splits(session, season="2024-25", player_ids=[977])
        first_count = session.query(PlayerSplitStat).count()
        sync_official_player_general_splits(session, season="2024-25", player_ids=[977])
        second_count = session.query(PlayerSplitStat).count()

    assert first_count == 1
    assert second_count == 1


# ---------------------------------------------------------------------------
# Play type sync
# ---------------------------------------------------------------------------


def test_play_type_sync_upserts_per_family_rows(session) -> None:
    _seed_player(session, 1628401, "Derrick White")

    def _fake_synergy(season, season_type, play_type, type_grouping):
        if play_type == "Isolation":
            return [{
                "PLAYER_ID": 1628401, "TEAM_ID": 1610612738,
                "GP": 70, "POSS": 250, "POSS_PCT": 0.18,
                "PTS": 280, "FGM": 100, "FGA": 220, "FG_PCT": 0.455,
                "EFG_PCT": 0.51, "TS_PCT": 0.55,
                "FTM": 50, "FTA": 60, "FT_PCT": 0.83,
                "PPP": 1.12, "PERCENTILE": 0.78,
                "SCORE_FREQUENCY": 0.50, "SF_FREQUENCY": 0.10, "TOV_FREQUENCY": 0.12,
            }]
        if play_type == "Spotup":
            return [{
                "PLAYER_ID": 1628401, "TEAM_ID": 1610612738,
                "GP": 70, "POSS": 600, "POSS_PCT": 0.30,
                "PTS": 750, "FGM": 280, "FGA": 600, "FG_PCT": 0.467,
                "EFG_PCT": 0.58, "TS_PCT": 0.62,
                "PPP": 1.25, "PERCENTILE": 0.85,
                "SCORE_FREQUENCY": 0.55, "SF_FREQUENCY": 0.05, "TOV_FREQUENCY": 0.08,
            }]
        return []

    with patch("services.sync_service.get_synergy_player_play_types", side_effect=_fake_synergy):
        result = sync_official_play_type_stats(session, season="2024-25")

    assert result["families_synced"] == 2
    assert result["rows_upserted"] == 2
    rows = session.query(PlayTypeStat).order_by(PlayTypeStat.poss.desc()).all()
    assert len(rows) == 2
    assert rows[0].play_type == "Spotup"
    assert rows[0].ppp == 1.25
    assert rows[1].play_type == "Isolation"


# ---------------------------------------------------------------------------
# Endpoints — verify shape against the in-memory DB
# ---------------------------------------------------------------------------


def test_splits_endpoint_groups_by_family(session) -> None:
    _seed_player(session, 977)
    session.add_all([
        PlayerSplitStat(
            player_id=977, season="2024-25", is_playoff=False,
            split_family="LocationPlayerDashboard", split_value="Home", label="Home",
            gp=35, pts=28.0, ts_pct=0.61,
        ),
        PlayerSplitStat(
            player_id=977, season="2024-25", is_playoff=False,
            split_family="LocationPlayerDashboard", split_value="Road", label="Road",
            gp=35, pts=25.0, ts_pct=0.58,
        ),
        PlayerSplitStat(
            player_id=977, season="2024-25", is_playoff=False,
            split_family="WinsLossesPlayerDashboard", split_value="W", label="W",
            gp=40, pts=30.0, ts_pct=0.62,
        ),
    ])
    session.commit()

    body = get_player_splits(player_id=977, season="2024-25", is_playoff=False, db=session)
    assert body["player_id"] == 977
    assert "LocationPlayerDashboard" in body["families"]
    assert len(body["families"]["LocationPlayerDashboard"]) == 2
    assert body["families"]["WinsLossesPlayerDashboard"][0]["pts"] == 30.0


def test_play_types_endpoint_returns_volume_sorted(session) -> None:
    _seed_player(session, 977)
    session.add_all([
        PlayTypeStat(
            player_id=977, season="2024-25", is_playoff=False,
            play_type="Isolation", play_role="primary",
            gp=70, poss=250, ppp=1.12, percentile=0.78,
        ),
        PlayTypeStat(
            player_id=977, season="2024-25", is_playoff=False,
            play_type="Spotup", play_role="primary",
            gp=70, poss=600, ppp=1.25, percentile=0.85,
        ),
    ])
    session.commit()

    body = get_player_play_types(player_id=977, season="2024-25", is_playoff=False, db=session)
    types = body["play_types"]
    assert len(types) == 2
    # Sorted by poss desc → Spotup first
    assert types[0]["play_type"] == "Spotup"
    assert types[0]["ppp"] == 1.25
    assert types[1]["play_type"] == "Isolation"


def test_splits_endpoint_404s_for_unknown_player(session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_player_splits(player_id=9999999, season="2024-25", is_playoff=False, db=session)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Sprint 85 (C) — Tracking + Hustle endpoints
# ---------------------------------------------------------------------------


def test_player_tracking_endpoint_returns_three_families(session) -> None:
    _seed_player(session, 1628983, "Shai Gilgeous-Alexander")
    session.add_all([
        PlayerTrackingStat(
            player_id=1628983, season="2024-25", season_type="Regular Season",
            tracking_family="shots", split_key="overall",
            gp=70, touches=70.5, drives=20.0,
        ),
        PlayerTrackingStat(
            player_id=1628983, season="2024-25", season_type="Regular Season",
            tracking_family="passing", split_key="overall",
            gp=70, passes_made=55.0, passes_received=60.0,
        ),
        PlayerTrackingStat(
            player_id=1628983, season="2024-25", season_type="Regular Season",
            tracking_family="shot_defense", split_key="2-4 Feet - Very Tight",
            gp=70,
        ),
    ])
    session.commit()

    body = get_player_tracking_endpoint(
        player_id=1628983, season="2024-25", is_playoff=False, db=session
    )
    assert body["player_id"] == 1628983
    assert body["season"] == "2024-25"
    assert body["is_playoff"] is False

    families = body["families"]
    # Public family labels are always present, even when empty.
    assert "Shot Creation" in families
    assert "Passing" in families
    assert "Shot Defense" in families

    # Raw `shots` family maps to `Shot Creation`.
    assert len(families["Shot Creation"]) == 1
    assert families["Shot Creation"][0]["touches"] == 70.5
    assert families["Shot Creation"][0]["drives"] == 20.0
    assert families["Passing"][0]["passes_made"] == 55.0
    assert families["Shot Defense"][0]["split_key"] == "2-4 Feet - Very Tight"


def test_player_tracking_endpoint_404s_for_unknown_player(session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_player_tracking_endpoint(
            player_id=9999999, season="2024-25", is_playoff=False, db=session
        )
    assert exc_info.value.status_code == 404


def test_player_hustle_endpoint_returns_aggregate(session) -> None:
    _seed_player(session, 1628983, "Shai Gilgeous-Alexander")
    session.add(PlayerHustleStat(
        player_id=1628983, season="2024-25", season_type="Regular Season",
        team_abbreviation="OKC", gp=70, minutes=2400.0,
        contested_shots=350.0, deflections=120.0, charges_drawn=8.0,
        screen_assists=15.0, screen_assist_points=35.0,
        loose_balls_recovered=42.0, box_outs=180.0,
    ))
    session.commit()

    body = get_player_hustle_endpoint(
        player_id=1628983, season="2024-25", is_playoff=False, db=session
    )
    assert body["player_id"] == 1628983
    assert body["season"] == "2024-25"
    assert body["is_playoff"] is False
    stats = body["stats"]
    assert stats is not None
    assert stats["contested_shots"] == 350.0
    assert stats["deflections"] == 120.0
    assert stats["charges_drawn"] == 8.0
    assert stats["screen_assists"] == 15.0
    assert stats["screen_assist_points"] == 35.0
    assert stats["loose_balls_recovered"] == 42.0
    assert stats["box_outs"] == 180.0
    assert stats["team_abbreviation"] == "OKC"
    assert stats["gp"] == 70


def test_player_hustle_endpoint_returns_null_stats_when_missing(session) -> None:
    _seed_player(session, 1628983, "Shai Gilgeous-Alexander")
    # No PlayerHustleStat row, but on-demand sync will be attempted. Patch
    # the sync to be a no-op so we exercise the empty-payload path
    # deterministically without hitting the network.
    with patch(
        "services.player_hustle_service.sync_player_hustle_stats",
        return_value={"status": "ok", "rows_synced": 0, "rows_created": 0},
    ):
        body = get_player_hustle_endpoint(
            player_id=1628983, season="2024-25", is_playoff=False, db=session
        )
    assert body["stats"] is None


def test_player_hustle_endpoint_404s_for_unknown_player(session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        get_player_hustle_endpoint(
            player_id=9999999, season="2024-25", is_playoff=False, db=session
        )
    assert exc_info.value.status_code == 404
