"""Standings service: computes and materializes team standings per season."""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from db.models import PlayerGameLog, Team, TeamStanding

logger = logging.getLogger(__name__)

# Static conference/division fallback (same as router, kept in sync)
TEAM_CONF_DIV: Dict[str, Dict[str, str]] = {
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


def _resolve_conf(abbr: str, team: Optional[Team]) -> str:
    raw = (team.conference if team else "") or ""
    raw = raw.strip()
    if raw.startswith("East"):
        return "East"
    if raw.startswith("West"):
        return "West"
    return TEAM_CONF_DIV.get(abbr, {}).get("conference", raw)


def compute_standings_data(season: str, db: Session) -> List[dict]:
    """Compute standings from player_game_logs and return as a list of raw dicts.

    This is the core computation shared by materialize_standings and the
    live-fallback path in the router.
    """
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

    game_results: dict = {}
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

    team_games: dict = defaultdict(list)
    for g in game_results.values():
        team_games[g["team_abbr"]].append(g)

    teams = {t.abbreviation: t for t in db.query(Team).all()}

    entries: List[dict] = []
    for abbr, games in team_games.items():
        team = teams.get(abbr)
        if not team:
            continue

        wins = sum(1 for g in games if g["wl"] == "W")
        losses = sum(1 for g in games if g["wl"] == "L")
        gp = wins + losses
        if gp == 0:
            continue

        home_games = [g for g in games if g["is_home"]]
        road_games = [g for g in games if not g["is_home"]]
        home_w = sum(1 for g in home_games if g["wl"] == "W")
        home_l = sum(1 for g in home_games if g["wl"] == "L")
        road_w = sum(1 for g in road_games if g["wl"] == "W")
        road_l = sum(1 for g in road_games if g["wl"] == "L")

        sorted_games = sorted(
            games,
            key=lambda g: g["game_date"] if g["game_date"] else "0000-00-00",
            reverse=True,
        )
        last10 = sorted_games[:10]
        l10_w = sum(1 for g in last10 if g["wl"] == "W")
        l10_l = sum(1 for g in last10 if g["wl"] == "L")

        streak_char = ""
        streak_count = 0
        for g in sorted_games:
            if not streak_char:
                streak_char = g["wl"]
                streak_count = 1
            elif g["wl"] == streak_char:
                streak_count += 1
            else:
                break

        current_streak = streak_char if streak_char else ""
        streak_num = streak_count if streak_char else 0

        fallback = TEAM_CONF_DIV.get(abbr, {})
        conference = _resolve_conf(abbr, team)
        division = (team.division or fallback.get("division") or "").strip()

        entries.append({
            "team_id": team.id,
            "abbreviation": abbr,
            "team_city": team.city or "",
            "team_name": team.name or "",
            "conference": conference,
            "division": division,
            "wins": wins,
            "losses": losses,
            "win_pct": wins / gp,
            "home_wins": home_w,
            "home_losses": home_l,
            "road_wins": road_w,
            "road_losses": road_l,
            "last_10_wins": l10_w,
            "last_10_losses": l10_l,
            "current_streak": streak_num if current_streak == "W" else -streak_num,
            "streak_type": current_streak,
            "l10": f"{l10_w}-{l10_l}",
            "home_record": f"{home_w}-{home_l}",
            "road_record": f"{road_w}-{road_l}",
            "current_streak_str": f"{current_streak}{streak_count}" if current_streak else "",
            "playoff_rank": 0,
            "games_back": None,
        })

    # Assign playoff_rank and games_back
    for conf in ("East", "West"):
        conf_entries = [e for e in entries if e["conference"] == conf]
        conf_entries.sort(key=lambda e: (-e["wins"], e["losses"]))
        if not conf_entries:
            continue
        leader_w = conf_entries[0]["wins"]
        leader_l = conf_entries[0]["losses"]
        for rank, e in enumerate(conf_entries, start=1):
            e["playoff_rank"] = rank
            e["games_back"] = 0.0 if rank == 1 else ((leader_w - e["wins"]) + (e["losses"] - leader_l)) / 2.0

    return entries


def materialize_standings(season: str, db: Session) -> Dict[str, int]:
    """Compute standings and append today's snapshot to team_standings.

    Inserts one row per team for today if it doesn't exist yet.
    Safe to call multiple times in the same day — second call returns inserted=0.
    """
    logger.info(f"Materializing standings snapshot for {season}...")
    today = date.today()
    entries = compute_standings_data(season, db)
    inserted = 0
    for data in entries:
        exists = (
            db.query(TeamStanding)
            .filter(
                TeamStanding.team_id == data["team_id"],
                TeamStanding.season == season,
                TeamStanding.snapshot_date == today,
            )
            .first()
        )
        if exists:
            continue
        row = TeamStanding(
            team_id=data["team_id"],
            season=season,
            snapshot_date=today,
            wins=data["wins"],
            losses=data["losses"],
            home_wins=data["home_wins"],
            home_losses=data["home_losses"],
            road_wins=data["road_wins"],
            road_losses=data["road_losses"],
            last_10_wins=data["last_10_wins"],
            last_10_losses=data["last_10_losses"],
            current_streak=data["current_streak"],
            streak_type=data["streak_type"],
            conference=data["conference"],
            division=data["division"],
        )
        db.add(row)
        inserted += 1

    db.commit()
    summary = {"season": season, "teams_inserted": inserted}
    logger.info(f"materialize_standings complete: {summary}")
    return summary


def get_standings_history(season: str, days: int, db: Session) -> List[Dict]:
    """Return per-team win-pct time series for the last N days.

    Each entry: {team_id, team_abbr, conference, snapshots: [{date, wins, losses, win_pct}]}
    snapshots sorted ascending by date.
    """
    from datetime import timedelta
    cutoff = date.today() - timedelta(days=days)

    rows = (
        db.query(TeamStanding, Team)
        .join(Team, Team.id == TeamStanding.team_id)
        .filter(
            TeamStanding.season == season,
            TeamStanding.snapshot_date >= cutoff,
        )
        .order_by(TeamStanding.team_id, TeamStanding.snapshot_date)
        .all()
    )

    teams_map: Dict[int, dict] = {}
    for standing, team in rows:
        tid = team.id
        if tid not in teams_map:
            teams_map[tid] = {
                "team_id": tid,
                "team_abbr": team.abbreviation,
                "conference": standing.conference or "",
                "snapshots": [],
            }
        w = standing.wins or 0
        l = standing.losses or 0
        teams_map[tid]["snapshots"].append({
            "date": standing.snapshot_date.isoformat(),
            "wins": w,
            "losses": l,
            "win_pct": round(w / (w + l), 4) if (w + l) > 0 else 0.0,
        })

    return list(teams_map.values())
