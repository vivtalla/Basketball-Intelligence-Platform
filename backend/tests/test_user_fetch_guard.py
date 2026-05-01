"""Sprint 82d — verify NBA_API_USER_FETCH_DISABLED blocks live fetches."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data import nba_client  # noqa: E402
from data.nba_client import LiveFetchBlockedError  # noqa: E402


def test_block_helper_raises_when_flag_on(monkeypatch):
    monkeypatch.setattr("config.NBA_API_USER_FETCH_DISABLED", True)
    with pytest.raises(LiveFetchBlockedError, match="cache miss"):
        nba_client._block_live_fetch_if_user_mode("test_method", "test:key")


def test_block_helper_noop_when_flag_off(monkeypatch):
    monkeypatch.setattr("config.NBA_API_USER_FETCH_DISABLED", False)
    # Should not raise
    nba_client._block_live_fetch_if_user_mode("test_method", "test:key")


def test_get_career_stats_cache_hit_returns_without_block(monkeypatch):
    monkeypatch.setattr("config.NBA_API_USER_FETCH_DISABLED", True)
    cached_value = {
        "season_totals": [],
        "career_totals": [],
        "post_season_totals": [],
        "post_career_totals": [],
    }
    with patch("data.nba_client.CacheManager.get", return_value=cached_value):
        result = nba_client.get_career_stats(2544)
    assert result == cached_value


def test_get_career_stats_cache_miss_blocks_in_user_mode(monkeypatch):
    monkeypatch.setattr("config.NBA_API_USER_FETCH_DISABLED", True)
    with patch("data.nba_client.CacheManager.get", return_value=None):
        with pytest.raises(LiveFetchBlockedError):
            nba_client.get_career_stats(2544)


def test_get_player_info_cache_miss_blocks_in_user_mode(monkeypatch):
    monkeypatch.setattr("config.NBA_API_USER_FETCH_DISABLED", True)
    with patch("data.nba_client.CacheManager.get", return_value=None):
        with pytest.raises(LiveFetchBlockedError):
            nba_client.get_player_info(2544)


def test_get_team_game_log_cache_miss_blocks_in_user_mode(monkeypatch):
    monkeypatch.setattr("config.NBA_API_USER_FETCH_DISABLED", True)
    with patch("data.nba_client.CacheManager.get", return_value=None):
        with pytest.raises(LiveFetchBlockedError):
            nba_client.get_team_game_log(1610612738, "2024-25")


def test_stats_service_returns_empty_on_block(monkeypatch):
    """User-facing service catches the block and returns graceful empty."""
    from services import stats_service

    monkeypatch.setattr("config.NBA_API_USER_FETCH_DISABLED", True)
    with patch("data.nba_client.CacheManager.get", return_value=None):
        # Service should NOT raise — should return an empty career shape
        result = stats_service.get_player_career_stats(2544, player_name="LeBron")

    assert result is not None
    assert result["player_id"] == 2544
    assert result["seasons"] == []
    assert result["career_totals"] is None
    assert result["playoff_seasons"] == []
