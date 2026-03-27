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


def calculate_bpm(stats: dict) -> float | None:
    """Box Plus/Minus approximation using PER with defensive adjustments.

    Calibrated to Basketball Reference scale: league average ≈ 0,
    replacement level ≈ -2. Cannot replicate the full Myers formula without
    team-level context, so treats this as a per-player box-score estimate.

    PER component captures offensive efficiency; stl/blk add defensive credit;
    usage penalty prevents high-volume inefficient scorers from being overstated.
    """
    per = stats.get("per")
    if per is None:
        return None
    gp = stats.get("gp", 0) or 1
    mp = stats.get("min_total", 0)
    if mp == 0:
        return None

    stl_pg = stats.get("stl_pg") or (stats.get("stl", 0) / gp)
    blk_pg = stats.get("blk_pg") or (stats.get("blk", 0) / gp)
    usg = stats.get("usg_pct") or 20.0

    bpm = (
        (per - 15.0) * 0.36              # PER above league average (15)
        + stl_pg * 0.45                  # steals: strong on-ball defensive indicator
        + blk_pg * 0.20                  # blocks: rim protection
        - max(0.0, usg - 20.0) * 0.03   # penalise high usage without efficiency gain
        - 0.50                           # shift to replacement-level baseline
    )
    return round(bpm, 1)


def calculate_win_shares(bpm: float | None, mp: float) -> float | None:
    """Simplified Win Shares approximation derived from BPM and minutes.

    WS ≈ (BPM + 2.0) × (MP / 2400)
    Calibrated so an average player (BPM = 0) playing full starter minutes
    (~2400 min/season) contributes ~2 WS — consistent with Basketball Reference
    norms. Career WS should be summed across seasons.
    """
    if bpm is None or mp == 0:
        return None
    return round(max((bpm + 2.0) * (mp / 2400.0), -1.0), 1)


def compute_age_at_season(birth_date_str: str | None, season: str) -> float | None:
    """Compute player age on October 1st of the given season year.

    More reliable than the PLAYER_AGE field returned by the NBA API, which
    is sometimes missing for historical seasons.
    """
    if not birth_date_str or not season:
        return None
    try:
        from datetime import datetime
        # birth_date stored as "1984-12-30T00:00:00" or "1984-12-30"
        bd = datetime.fromisoformat(birth_date_str.split("T")[0])
        season_year = int(season.split("-")[0])
        season_start = datetime(season_year, 10, 1)
        return round((season_start - bd).days / 365.25, 1)
    except (ValueError, TypeError, AttributeError):
        return None


def calculate_darko(age: float | None, per: float | None, ts_pct: float | None, usg_pct: float | None) -> float | None:
    """DARKO: draft-age adjusted impact projection (approximation)."""
    if age is None or age <= 0 or per is None:
        return None

    age_factor = max(0, 24 - age) / 5  # younger players score higher
    ts_factor = ts_pct if ts_pct is not None else 0.5
    usg_factor = usg_pct if usg_pct is not None else 20.0

    darko_value = (per * 0.15) + (ts_factor * 10 * 0.05) + (age_factor * 6) - (usg_factor * 0.01)
    return round(darko_value, 2)


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
        season_data["epm"] = None
        season_data["rapm"] = None
    else:
        # Use nba_api advanced stats where available
        season_data["ts_pct"] = advanced_data.get("TS_PCT")
        season_data["efg_pct"] = advanced_data.get("EFG_PCT")
        season_data["usg_pct"] = advanced_data.get("USG_PCT")
        season_data["off_rating"] = advanced_data.get("OFF_RATING")
        season_data["def_rating"] = advanced_data.get("DEF_RATING")
        season_data["net_rating"] = advanced_data.get("NET_RATING")
        season_data["pie"] = advanced_data.get("PIE")
        season_data["pace"] = advanced_data.get("PACE")
        season_data["epm"] = None  # requires external CSV import
        season_data["rapm"] = None  # requires external CSV import

    # Calculated metrics — applied regardless of whether advanced_data is available
    season_data["per"] = calculate_per_simplified(season_data)
    season_data["bpm"] = calculate_bpm(season_data)
    season_data["ws"] = calculate_win_shares(season_data["bpm"], season_data.get("min_total", 0))
    season_data["vorp"] = calculate_vorp(
        season_data["bpm"], season_data.get("min_total", 0), season_data.get("gp", 0)
    )
    season_data["darko"] = calculate_darko(
        season_data.get("age"),
        season_data.get("per"),
        season_data.get("ts_pct"),
        season_data.get("usg_pct"),
    )

    return season_data
