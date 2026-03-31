from __future__ import annotations

from collections import defaultdict
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import PlayerGameLog, Team
from models.standings import StandingsEntry

router = APIRouter()

TEAM_METADATA_FALLBACK = {
    "ATL": {"conference": "East", "division": "Southeast"},
    "BOS": {"conference": "East", "division": "Atlantic"},
    "BKN": {"conference": "East", "division": "Atlantic"},
    "CHA": {"conference": "East", "division": "Southeast"},
    "CHI": {"conference": "East", "division": "Central"},
    "CLE": {"conference": "East", "division": "Central"},
    "DET": {"conference": "East", "division": "Central"},
    "IND": {"conference": "East", "division": "Central"},
    "MIA": {"conference": "East", "division": "Southeast"},
    "MIL": {"conference": "East", "division": "Central"},
    "NYK": {"conference": "East", "division": "Atlantic"},
    "ORL": {"conference": "East", "division": "Southeast"},
    "PHI": {"conference": "East", "division": "Atlantic"},
    "TOR": {"conference": "East", "division": "Atlantic"},
    "WAS": {"conference": "East", "division": "Southeast"},
    "DAL": {"conference": "West", "division": "Southwest"},
    "DEN": {"conference": "West", "division": "Northwest"},
    "GSW": {"conference": "West", "division": "Pacific"},
    "HOU": {"conference": "West", "division": "Southwest"},
    "LAC": {"conference": "West", "division": "Pacific"},
    "LAL": {"conference": "West", "division": "Pacific"},
    "MEM": {"conference": "West", "division": "Southwest"},
    "MIN": {"conference": "West", "division": "Northwest"},
    "NOP": {"conference": "West", "division": "Southwest"},
    "OKC": {"conference": "West", "division": "Northwest"},
    "PHX": {"conference": "West", "division": "Pacific"},
    "POR": {"conference": "West", "division": "Northwest"},
    "SAC": {"conference": "West", "division": "Pacific"},
    "SAS": {"conference": "West", "division": "Southwest"},
    "UTA": {"conference": "West", "division": "Northwest"},
}


def _compute_standings(season: str, db: Session) -> List[StandingsEntry]:
    """Compute standings from player_game_logs. No external API needed."""

    # Pull distinct (game_id, matchup, wl, game_date) rows for the season.
    # Multiple players from the same team in the same game share identical values,
    # so distinct() collapses them to one row per (game_id, team_side).
    raw = (
        db.query(
            PlayerGameLog.game_id,
            PlayerGameLog.game_date,
            PlayerGameLog.matchup,
            PlayerGameLog.wl,
        )
        .filter(
            PlayerGameLog.season == season,
            PlayerGameLog.season_type == "Regular Season",
            PlayerGameLog.wl.in_(["W", "L"]),
            PlayerGameLog.matchup.isnot(None),
        )
        .distinct()
        .all()
    )

    # Parse team abbreviation and home/away from matchup.
    # Format: "GSW vs. LAL"  →  team=GSW, home=True
    #         "GSW @ LAL"    →  team=GSW, home=False
    game_results: dict = {}  # (game_id, team_abbr) → result dict
    for row in raw:
        matchup = row.matchup or ""
        if " vs. " in matchup:
            team_abbr = matchup.split(" vs. ")[0].strip()
            is_home = True
        elif " @ " in matchup:
            team_abbr = matchup.split(" @ ")[0].strip()
            is_home = False
        else:
            continue

        key = (row.game_id, team_abbr)
        if key not in game_results:
            game_results[key] = {
                "game_date": row.game_date,
                "team_abbr": team_abbr,
                "wl": row.wl,
                "is_home": is_home,
            }

    # Group by team abbreviation
    team_games: dict = defaultdict(list)
    for g in game_results.values():
        team_games[g["team_abbr"]].append(g)

    # Build a lookup of teams from DB
    teams = {t.abbreviation: t for t in db.query(Team).all()}

    entries: List[dict] = []
    for abbr, games in team_games.items():
        team = teams.get(abbr)
        if not team:
            continue

        wins   = sum(1 for g in games if g["wl"] == "W")
        losses = sum(1 for g in games if g["wl"] == "L")
        gp     = wins + losses
        if gp == 0:
            continue

        home_games = [g for g in games if g["is_home"]]
        road_games = [g for g in games if not g["is_home"]]
        home_w = sum(1 for g in home_games if g["wl"] == "W")
        home_l = sum(1 for g in home_games if g["wl"] == "L")
        road_w = sum(1 for g in road_games if g["wl"] == "W")
        road_l = sum(1 for g in road_games if g["wl"] == "L")

        # Sort games newest-first for L10 + streak
        sorted_games = sorted(
            games,
            key=lambda g: g["game_date"] if g["game_date"] else "0000-00-00",
            reverse=True,
        )
        last10     = sorted_games[:10]
        l10_w      = sum(1 for g in last10 if g["wl"] == "W")
        l10_l      = sum(1 for g in last10 if g["wl"] == "L")

        streak_char: str = ""
        streak_count = 0
        for g in sorted_games:
            if not streak_char:
                streak_char  = g["wl"]
                streak_count = 1
            elif g["wl"] == streak_char:
                streak_count += 1
            else:
                break
        current_streak = f"{streak_char}{streak_count}" if streak_char else ""

        # Normalise conference to "East" / "West"
        fallback = TEAM_METADATA_FALLBACK.get(abbr, {})
        raw_conf = (team.conference or fallback.get("conference") or "").strip()
        if raw_conf.startswith("East"):
            conference = "East"
        elif raw_conf.startswith("West"):
            conference = "West"
        else:
            conference = raw_conf
        division = (team.division or fallback.get("division") or "").strip()

        entries.append({
            "team_id":        team.id,
            "team_city":      team.city or "",
            "team_name":      team.name or "",
            "conference":     conference,
            "division":       division,
            "playoff_rank":   0,      # assigned below
            "wins":           wins,
            "losses":         losses,
            "win_pct":        wins / gp,
            "games_back":     None,   # assigned below
            "l10":            f"{l10_w}-{l10_l}",
            "home_record":    f"{home_w}-{home_l}",
            "road_record":    f"{road_w}-{road_l}",
            "pts_pg":         None,
            "opp_pts_pg":     None,
            "diff_pts_pg":    None,
            "current_streak": current_streak,
            "clinch_indicator": None,
            "abbreviation":   abbr,
        })

    # Assign playoff_rank and games_back within each conference
    for conf in ("East", "West"):
        conf_entries = [e for e in entries if e["conference"] == conf]
        conf_entries.sort(key=lambda e: (-e["wins"], e["losses"]))
        if not conf_entries:
            continue
        leader_w = conf_entries[0]["wins"]
        leader_l = conf_entries[0]["losses"]
        for rank, e in enumerate(conf_entries, start=1):
            e["playoff_rank"] = rank
            if rank == 1:
                e["games_back"] = 0.0
            else:
                e["games_back"] = ((leader_w - e["wins"]) + (e["losses"] - leader_l)) / 2.0

    return [StandingsEntry(**e) for e in entries]


@router.get("", response_model=List[StandingsEntry])
def get_standings(
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    """Return league standings computed from synced player game logs."""
    entries = _compute_standings(season, db)
    entries.sort(key=lambda e: (e.conference, e.playoff_rank))
    return entries
