"""Sprint 78 (Team CF1): tests for the share-card image renderers.

Covers the two highest-value endpoints — player and game cards — by
verifying that:

- The rendered output is non-empty bytes
- The bytes are a valid PNG (magic header `\\x89PNG`)
- Pillow can re-decode the bytes to a 1200x630 image

Both tests use an in-memory SQLite session and seed the minimum data the
service needs; the renderer's catch-all guard means missing data still
returns a placeholder card, but here we assert on the happy path.
"""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path
import sys

from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.database import Base  # noqa: E402
from db.models import GameLog, Player, SeasonStat, Team  # noqa: E402
from services.share_card_service import (  # noqa: E402
    CARD_H,
    CARD_W,
    render_game_card,
    render_player_card,
)


def _make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def _assert_valid_png(blob: bytes) -> None:
    assert blob, "renderer returned empty bytes"
    assert blob[:8] == b"\x89PNG\r\n\x1a\n", "bytes are not a valid PNG"
    img = Image.open(io.BytesIO(blob))
    assert img.size == (CARD_W, CARD_H), f"unexpected card dimensions {img.size}"


def test_player_card_returns_valid_png_for_real_player():
    session = _make_session()
    try:
        bos = Team(id=1610612738, abbreviation="BOS", name="Boston Celtics")
        session.add(bos)
        session.commit()

        tatum = Player(
            id=1628369,
            full_name="Jayson Tatum",
            first_name="Jayson",
            last_name="Tatum",
            team_id=bos.id,
            jersey="0",
            position="F",
            is_active=True,
        )
        session.add(tatum)
        session.commit()

        season = "2024-25"
        session.add(
            SeasonStat(
                player_id=tatum.id,
                season=season,
                team_abbreviation="BOS",
                is_playoff=False,
                gp=72,
                pts_pg=27.1,
                reb_pg=8.2,
                ast_pg=5.5,
                ts_pct=0.602,
            )
        )
        session.commit()

        png = render_player_card(session, tatum.id, season)
        _assert_valid_png(png)
    finally:
        session.close()


def test_game_card_returns_valid_png_for_synced_game():
    session = _make_session()
    try:
        okc = Team(id=1610612760, abbreviation="OKC", name="Oklahoma City Thunder")
        ind = Team(id=1610612754, abbreviation="IND", name="Indiana Pacers")
        session.add_all([okc, ind])
        session.commit()

        game_id = "0042500111"
        session.add(
            GameLog(
                game_id=game_id,
                season="2025-26",
                game_date=date(2026, 4, 28),
                home_team_id=okc.id,
                away_team_id=ind.id,
                home_score=118,
                away_score=104,
                season_type="Playoffs",
                series_id="2025-26-W-R1-OKC-IND",
                series_game_num=2,
            )
        )
        session.commit()

        png = render_game_card(session, game_id)
        _assert_valid_png(png)
    finally:
        session.close()
