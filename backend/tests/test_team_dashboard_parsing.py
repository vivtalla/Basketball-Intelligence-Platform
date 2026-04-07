from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data import nba_client  # noqa: E402


def test_get_team_stats_recovers_abbreviation_when_dashboard_omits_it(monkeypatch):
    base_rows = [
        {
            "TEAM_ID": 1610612737,
            "TEAM_NAME": "Atlanta Hawks",
            "GP": 79,
            "W": 45,
            "L": 34,
            "W_PCT": 0.57,
            "PTS": 9357,
            "AST": 2390,
            "REB": 3435,
            "TOV": 1119,
            "BLK": 372,
            "STL": 745,
            "FG_PCT": 0.474,
            "FG3_PCT": 0.371,
            "FT_PCT": 0.776,
            "PLUS_MINUS": 208.0,
        },
        {
            "TEAM_ID": 1610612738,
            "TEAM_NAME": "Boston Celtics",
            "GP": 80,
            "W": 59,
            "L": 21,
            "W_PCT": 0.738,
            "PTS": 9530,
            "AST": 2240,
            "REB": 3600,
            "TOV": 1040,
            "BLK": 430,
            "STL": 610,
            "FG_PCT": 0.489,
            "FG3_PCT": 0.383,
            "FT_PCT": 0.799,
            "PLUS_MINUS": 630.0,
        },
    ]
    advanced_rows = [
        {
            "TEAM_ID": 1610612737,
            "OFF_RATING": 119.2,
            "DEF_RATING": 116.5,
            "NET_RATING": 2.7,
            "PACE": 100.4,
            "EFG_PCT": 0.564,
            "TS_PCT": 0.603,
            "PIE": 0.523,
            "OREB_PCT": 27.3,
            "DREB_PCT": 72.2,
            "TM_TOV_PCT": 12.6,
            "AST_PCT": 67.1,
            "OFF_RATING_RANK": 5,
            "DEF_RATING_RANK": 18,
            "NET_RATING_RANK": 11,
            "PACE_RANK": 9,
            "EFG_PCT_RANK": 7,
            "TS_PCT_RANK": 6,
            "OREB_PCT_RANK": 8,
            "TM_TOV_PCT_RANK": 10,
        },
        {
            "TEAM_ID": 1610612738,
            "OFF_RATING": 121.5,
            "DEF_RATING": 110.7,
            "NET_RATING": 10.8,
            "PACE": 99.1,
            "EFG_PCT": 0.579,
            "TS_PCT": 0.617,
            "PIE": 0.571,
            "OREB_PCT": 28.1,
            "DREB_PCT": 73.3,
            "TM_TOV_PCT": 11.9,
            "AST_PCT": 68.2,
            "OFF_RATING_RANK": 1,
            "DEF_RATING_RANK": 3,
            "NET_RATING_RANK": 1,
            "PACE_RANK": 17,
            "EFG_PCT_RANK": 2,
            "TS_PCT_RANK": 1,
            "OREB_PCT_RANK": 5,
            "TM_TOV_PCT_RANK": 8,
        },
    ]

    class FakeDash:
        def __init__(self, season: str, measure_type_detailed_defense: str, timeout: int):
            self.measure_type_detailed_defense = measure_type_detailed_defense

        def get_normalized_dict(self):
            rows = base_rows if self.measure_type_detailed_defense == "Base" else advanced_rows
            return {"LeagueDashTeamStats": rows}

    monkeypatch.setattr(nba_client, "_rate_limit", lambda: None)
    monkeypatch.setattr(nba_client.leaguedashteamstats, "LeagueDashTeamStats", FakeDash)

    result = nba_client.get_team_stats("2025-26")

    assert set(result.keys()) == {"ATL", "BOS"}
    assert result["ATL"]["name"] == "Atlanta Hawks"
    assert result["ATL"]["pts_pg"] == 118.4
    assert result["BOS"]["off_rating"] == 121.5
    assert result["BOS"]["tov_pct"] == 11.9
