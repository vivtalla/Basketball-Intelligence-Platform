"""Advanced basketball metrics calculations.

Simplified versions of standard advanced metrics used in NBA analytics.
Formulas based on Basketball Reference definitions.
"""
from __future__ import annotations


def calculate_ts_pct(pts: int, fga: int, fta: int) -> float | None:
    """True Shooting Percentage: accounts for 2PT, 3PT, and FT efficiency.

    TS% = PTS / (2 * (FGA + 0.44 * FTA))
    """
    denominator = 2 * (fga + 0.44 * fta)
    if denominator == 0:
        return None
    return round(pts / denominator, 3)


def calculate_efg_pct(fgm: int, fg3m: int, fga: int) -> float | None:
    """Effective Field Goal Percentage: adjusts for 3-pointers being worth more.

    eFG% = (FGM + 0.5 * FG3M) / FGA
    """
    if fga == 0:
        return None
    return round((fgm + 0.5 * fg3m) / fga, 3)


def calculate_ast_pct(ast: int, mp: float, team_mp: float, team_fgm: int, fgm: int) -> float | None:
    """Assist Percentage: estimate of teammate FG assisted while on court.

    AST% = 100 * AST / (((MP / (Team_MP / 5)) * Team_FGM) - FGM)
    """
    if mp == 0 or team_mp == 0:
        return None
    denominator = ((mp / (team_mp / 5)) * team_fgm) - fgm
    if denominator <= 0:
        return None
    return round(100 * ast / denominator, 1)


def calculate_reb_pct(reb: int, mp: float, team_mp: float, team_reb: int, opp_reb: int) -> float | None:
    """Rebound Percentage: estimate of available rebounds grabbed.

    REB% = 100 * (REB * (Team_MP / 5)) / (MP * (Team_REB + Opp_REB))
    """
    if mp == 0 or (team_reb + opp_reb) == 0:
        return None
    return round(100 * (reb * (team_mp / 5)) / (mp * (team_reb + opp_reb)), 1)


def calculate_usg_pct(fga: int, fta: int, tov: int, mp: float, team_mp: float, team_fga: int, team_fta: int, team_tov: int) -> float | None:
    """Usage Rate: estimate of team possessions used by a player while on court.

    USG% = 100 * ((FGA + 0.44 * FTA + TOV) * (Team_MP / 5)) / (MP * (Team_FGA + 0.44 * Team_FTA + Team_TOV))
    """
    if mp == 0 or team_mp == 0:
        return None
    denominator = mp * (team_fga + 0.44 * team_fta + team_tov)
    if denominator == 0:
        return None
    numerator = (fga + 0.44 * fta + tov) * (team_mp / 5)
    return round(100 * numerator / denominator, 1)


def calculate_per_simplified(stats: dict) -> float | None:
    """Simplified Player Efficiency Rating.

    This is a simplified version that doesn't require league pace adjustments.
    Uses the unadjusted PER formula as a reasonable approximation.

    uPER = (1/MP) * [3P + (2/3)*AST + (2-factor)*FGM + FTM*0.5*(1+(1-factor)+(2/3)*factor)
           - VOP*TOV - VOP*DRB%*(FGA-FGM) - VOP*0.44*(0.44+(0.56*DRB%))*FTA_miss
           + VOP*(1-DRB%)*(REB - OREB) + VOP*DRB%*OREB + VOP*STL + VOP*DRB%*BLK
           - PF*((lg_FT/lg_PF) - 0.44*(lg_FTA/lg_PF)*VOP)]

    For simplicity, we use a points-based approximation:
    """
    mp = stats.get("min_total", 0)
    if mp == 0:
        return None

    pts = stats.get("pts", 0)
    reb = stats.get("reb", 0)
    ast = stats.get("ast", 0)
    stl = stats.get("stl", 0)
    blk = stats.get("blk", 0)
    tov = stats.get("tov", 0)
    fgm = stats.get("fgm", 0)
    fga = stats.get("fga", 0)
    ftm = stats.get("ftm", 0)
    fta = stats.get("fta", 0)
    pf = stats.get("pf", 0)

    fga_miss = fga - fgm
    fta_miss = fta - ftm

    # Simplified PER approximation (Hollinger-style, unnormalized)
    value = (
        pts
        + reb * 1.2
        + ast * 1.5
        + stl * 2.0
        + blk * 2.0
        - tov * 1.0
        - fga_miss * 0.7
        - fta_miss * 0.5
        - pf * 0.5
    )

    per_minute = value / mp
    # Scale to PER range (~15 is league average)
    per = per_minute * 36  # per-36 scaling

    return round(per, 1)


def calculate_vorp(bpm: float | None, mp: float, team_gp: int) -> float | None:
    """Value Over Replacement Player.

    VORP = [BPM - (-2.0)] * (% of possessions played) * (team_GP / 82)
    Approximate % possessions as MP / (team_GP * 48 * 5) simplified to MP / (team_GP * 240)
    """
    if bpm is None or team_gp == 0:
        return None
    replacement_level = -2.0
    poss_pct = mp / (team_gp * 240) if team_gp > 0 else 0
    vorp = (bpm - replacement_level) * poss_pct * (team_gp / 82)
    return round(vorp, 1)


def enrich_season_with_advanced(season_data: dict, advanced_data: dict | None) -> dict:
    """Merge nba_api advanced stats into a season stats dict."""
    if advanced_data is None:
        # Calculate what we can from box score
        season_data["ts_pct"] = calculate_ts_pct(
            season_data.get("pts", 0),
            season_data.get("fga", 0),
            season_data.get("fta", 0),
        )
        season_data["efg_pct"] = calculate_efg_pct(
            season_data.get("fgm", 0),
            season_data.get("fg3m", 0),
            season_data.get("fga", 0),
        )
        season_data["per"] = calculate_per_simplified(season_data)
        return season_data

    # Use nba_api advanced stats where available
    season_data["ts_pct"] = advanced_data.get("TS_PCT")
    season_data["efg_pct"] = advanced_data.get("EFG_PCT")
    season_data["usg_pct"] = advanced_data.get("USG_PCT")
    season_data["off_rating"] = advanced_data.get("OFF_RATING")
    season_data["def_rating"] = advanced_data.get("DEF_RATING")
    season_data["net_rating"] = advanced_data.get("NET_RATING")
    season_data["pie"] = advanced_data.get("PIE")
    season_data["pace"] = advanced_data.get("PACE")

    # Calculate metrics not provided by the league dash endpoint
    season_data["per"] = calculate_per_simplified(season_data)
    bpm = advanced_data.get("PLUS_MINUS")  # Use +/- as BPM proxy
    season_data["bpm"] = round(bpm, 1) if bpm is not None else None
    season_data["vorp"] = calculate_vorp(
        bpm, season_data.get("min_total", 0), season_data.get("gp", 0)
    )

    return season_data
