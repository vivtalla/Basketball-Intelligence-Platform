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


def test_get_team_general_splits_normalizes_supported_general_dashboards(monkeypatch):
    rows_by_dataset = {
        "LocationTeamDashboard": [
            {
                "TEAM_GAME_LOCATION": "Home",
                "GP": 40,
                "W": 30,
                "L": 10,
                "W_PCT": 0.75,
                "MIN": 1920,
                "PTS": 4800,
                "REB": 1800,
                "AST": 1100,
                "TOV": 500,
                "STL": 320,
                "BLK": 210,
                "FG_PCT": 0.49,
                "FG3_PCT": 0.38,
                "FT_PCT": 0.81,
                "PLUS_MINUS": 420,
            }
        ],
        "WinsLossesTeamDashboard": [
            {
                "GAME_RESULT": "Wins",
                "GP": 55,
                "W": 55,
                "L": 0,
                "W_PCT": 1.0,
                "MIN": 2640,
                "PTS": 6600,
                "REB": 2400,
                "AST": 1500,
                "TOV": 650,
                "STL": 430,
                "BLK": 300,
                "FG_PCT": 0.51,
                "FG3_PCT": 0.4,
                "FT_PCT": 0.83,
                "PLUS_MINUS": 800,
            }
        ],
        "DaysRestTeamDashboard": [{"TEAM_DAYS_REST_RANGE": "1 Days Rest", "GP": 20, "W": 12, "L": 8}],
        "MonthTeamDashboard": [{"SEASON_MONTH_NAME": "January", "GP": 14, "W": 9, "L": 5}],
        "PrePostAllStarTeamDashboard": [{"SEASON_SEGMENT": "Post All-Star", "GP": 23, "W": 17, "L": 6}],
        "OverallTeamDashboard": [{"SEASON_YEAR": "2025-26", "GP": 82, "W": 60, "L": 22}],
    }

    class FakeDash:
        def __init__(self, team_id: int, season: str, per_mode_detailed: str, season_type_all_star: str, timeout: int):
            self.team_id = team_id
            self.season = season
            self.per_mode_detailed = per_mode_detailed
            self.season_type_all_star = season_type_all_star

        def get_normalized_dict(self):
            return rows_by_dataset

    monkeypatch.setattr(nba_client, "_rate_limit", lambda: None)
    monkeypatch.setattr(nba_client.teamdashboardbygeneralsplits, "TeamDashboardByGeneralSplits", FakeDash)

    result = nba_client.get_team_general_splits("2025-26", 1610612738)

    assert [row["split_family"] for row in result] == [
        "LocationTeamDashboard",
        "WinsLossesTeamDashboard",
        "DaysRestTeamDashboard",
        "MonthTeamDashboard",
        "PrePostAllStarTeamDashboard",
    ]
    assert result[0]["team_id"] == 1610612738
    assert result[0]["split_value"] == "Home"
    assert result[0]["pts"] == 4800.0
    assert result[1]["label"] == "Wins"
    assert result[1]["plus_minus"] == 800.0


def test_get_team_shooting_splits_normalizes_supported_dashboards_and_ignores_assisted_by(monkeypatch):
    rows_by_dataset = {
        "ShotAreaTeamDashboard": [
            {
                "GROUP_VALUE": "Restricted Area",
                "FGM": 500,
                "FGA": 710,
                "FG_PCT": 0.704,
                "FG3M": 0,
                "FG3A": 0,
                "FG3_PCT": 0,
                "EFG_PCT": 0.704,
                "BLKA": 35,
                "PCT_AST_2PM": 0.62,
                "PCT_UAST_2PM": 0.38,
                "PCT_AST_3PM": 0.0,
                "PCT_UAST_3PM": 0.0,
                "PCT_AST_FGM": 0.62,
                "PCT_UAST_FGM": 0.38,
            }
        ],
        "ShotTypeTeamDashboard": [
            {
                "GROUP_VALUE": "Above the Break 3",
                "FGM": 290,
                "FGA": 810,
                "FG_PCT": 0.358,
                "FG3M": 290,
                "FG3A": 810,
                "FG3_PCT": 0.358,
                "EFG_PCT": 0.537,
                "BLKA": 18,
                "PCT_AST_2PM": 0.0,
                "PCT_UAST_2PM": 0.0,
                "PCT_AST_3PM": 0.88,
                "PCT_UAST_3PM": 0.12,
                "PCT_AST_FGM": 0.88,
                "PCT_UAST_FGM": 0.12,
            }
        ],
        "Shot8FTTeamDashboard": [
            {"GROUP_VALUE": "24+ ft.", "FGM": 310, "FGA": 870, "FG_PCT": 0.356, "FG3M": 310, "FG3A": 870, "FG3_PCT": 0.356, "EFG_PCT": 0.534}
        ],
        "Shot5FTTeamDashboard": [
            {"GROUP_VALUE": "24+ ft.", "FGM": 305, "FGA": 860, "FG_PCT": 0.355, "FG3M": 305, "FG3A": 860, "FG3_PCT": 0.355, "EFG_PCT": 0.532}
        ],
        "AssitedShotTeamDashboard": [
            {"GROUP_VALUE": "Assisted", "FGM": 720, "FGA": 1280, "FG_PCT": 0.563, "FG3M": 410, "FG3A": 920, "FG3_PCT": 0.446, "EFG_PCT": 0.723, "PCT_AST_FGM": 1.0, "PCT_UAST_FGM": 0.0}
        ],
        "OverallTeamDashboard": [
            {"GROUP_VALUE": "Overall", "FGM": 980, "FGA": 1980, "FG_PCT": 0.495, "FG3M": 420, "FG3A": 1120, "FG3_PCT": 0.375, "EFG_PCT": 0.601}
        ],
        "AssistedBy": [
            {"GROUP_VALUE": "Ignored Player", "FGM": 12, "FGA": 20}
        ],
    }

    class FakeDash:
        def __init__(self, team_id: int, season: str, per_mode_detailed: str, season_type_all_star: str, timeout: int):
            self.team_id = team_id
            self.season = season
            self.per_mode_detailed = per_mode_detailed
            self.season_type_all_star = season_type_all_star

        def get_normalized_dict(self):
            return rows_by_dataset

    monkeypatch.setattr(nba_client, "_rate_limit", lambda: None)
    monkeypatch.setattr(nba_client.teamdashboardbyshootingsplits, "TeamDashboardByShootingSplits", FakeDash)

    result = nba_client.get_team_shooting_splits("2025-26", 1610612738)

    assert [row["split_family"] for row in result] == [
        "ShotAreaTeamDashboard",
        "ShotTypeTeamDashboard",
        "Shot8FTTeamDashboard",
        "Shot5FTTeamDashboard",
        "AssitedShotTeamDashboard",
        "OverallTeamDashboard",
    ]
    assert all(row["split_family"] != "AssistedBy" for row in result)
    assert result[0]["team_id"] == 1610612738
    assert result[0]["split_value"] == "Restricted Area"
    assert result[1]["fg3a"] == 810.0
    assert result[4]["pct_ast_fgm"] == 1.0
