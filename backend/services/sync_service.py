"""Sync service: pulls data from nba_api into PostgreSQL."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from data.nba_client import (
    get_career_stats,
    get_injuries_payload,
    get_league_dash_player_stats,
    get_player_advanced_stats_from_league,
    get_player_info,
    search_players,
)
from db.models import Player, PlayerInjury, SeasonStat, Team
from services.advanced_metrics import enrich_season_with_advanced

logger = logging.getLogger(__name__)


def canonical_player_name(
    full_name: str = "",
    first_name: str = "",
    last_name: str = "",
) -> str:
    """Return the best available full player name.

    Some historical rows were stored with `full_name` equal to only the last
    name. Prefer a composed first+last name whenever both parts exist.
    """
    full_name = (full_name or "").strip()
    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()

    if first_name and last_name:
        combined = "{0} {1}".format(first_name, last_name).strip()
        if not full_name:
            return combined
        if full_name == last_name or first_name not in full_name:
            return combined
        return full_name

    return full_name or first_name or last_name


def _transform_season_row(row: dict) -> dict:
    """Transform a raw nba_api season row into flat dict."""
    gp = row.get("GP", 0) or 1
    return {
        "season": row.get("SEASON_ID", ""),
        "team_abbreviation": row.get("TEAM_ABBREVIATION", ""),
        "gp": row.get("GP", 0),
        "gs": row.get("GS", 0),
        "min_total": row.get("MIN", 0),
        "age": row.get("PLAYER_AGE") or row.get("AGE"),
        "min_pg": round(row.get("MIN", 0) / gp, 1),
        "pts": row.get("PTS", 0),
        "pts_pg": round(row.get("PTS", 0) / gp, 1),
        "reb": row.get("REB", 0),
        "reb_pg": round(row.get("REB", 0) / gp, 1),
        "ast": row.get("AST", 0),
        "ast_pg": round(row.get("AST", 0) / gp, 1),
        "stl": row.get("STL", 0),
        "stl_pg": round(row.get("STL", 0) / gp, 1),
        "blk": row.get("BLK", 0),
        "blk_pg": round(row.get("BLK", 0) / gp, 1),
        "tov": row.get("TOV", 0),
        "tov_pg": round(row.get("TOV", 0) / gp, 1),
        "fgm": row.get("FGM", 0),
        "fga": row.get("FGA", 0),
        "fg_pct": row.get("FG_PCT", 0) or 0,
        "fg3m": row.get("FG3M", 0),
        "fg3a": row.get("FG3A", 0),
        "fg3_pct": row.get("FG3_PCT", 0) or 0,
        "ftm": row.get("FTM", 0),
        "fta": row.get("FTA", 0),
        "ft_pct": row.get("FT_PCT", 0) or 0,
        "oreb": row.get("OREB", 0),
        "dreb": row.get("DREB", 0),
        "pf": row.get("PF", 0),
    }


def sync_player(db: Session, player_id: int) -> Player:
    """Sync a single player's profile and career stats from NBA.com into Postgres.

    Returns the Player ORM object.
    """
    # --- Player profile ---
    logger.info(f"Syncing player {player_id} profile...")
    info = get_player_info(player_id)

    team_abbr = info.get("team_abbreviation", "")
    team_name = info.get("team_name", "")
    team_id = info.get("team_id")

    # Upsert team
    if team_id and team_abbr:
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            team = Team(id=team_id, abbreviation=team_abbr, name=team_name)
            db.add(team)
            db.flush()
        else:
            team.abbreviation = team_abbr
            team.name = team_name

    # Upsert player
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        player = Player(id=player_id)
        db.add(player)

    player.first_name = info.get("first_name", "")
    player.last_name = info.get("last_name", "")
    player.full_name = canonical_player_name(
        info.get("full_name", ""),
        player.first_name,
        player.last_name,
    )
    player.team_id = team_id if team_id else None
    player.jersey = info.get("jersey", "")
    player.position = info.get("position", "")
    player.height = info.get("height", "")
    player.weight = info.get("weight", "")
    player.birth_date = info.get("birth_date", "")
    player.country = info.get("country", "")
    player.school = info.get("school", "")
    player.draft_year = info.get("draft_year")
    player.draft_round = info.get("draft_round")
    player.draft_number = info.get("draft_number")
    player.from_year = info.get("from_year")
    player.to_year = info.get("to_year")
    player.headshot_url = info.get("headshot_url", "")
    player.is_active = True
    db.flush()

    # --- Career stats ---
    logger.info(f"Syncing player {player_id} career stats...")
    raw = get_career_stats(player_id)

    # Cache for league advanced stats by season
    league_advanced_cache = {}

    # Regular season
    for row in raw.get("season_totals", []):
        season_data = _transform_season_row(row)
        season_id = row.get("SEASON_ID", "")

        # Fetch advanced stats
        advanced_data = None
        try:
            if season_id not in league_advanced_cache:
                league_advanced_cache[season_id] = get_league_dash_player_stats(
                    season_id, measure_type="Advanced"
                )
            advanced_data = get_player_advanced_stats_from_league(
                player_id, league_advanced_cache[season_id]
            )
        except Exception:
            pass

        season_data = enrich_season_with_advanced(season_data, advanced_data)
        _upsert_season_stat(db, player_id, season_data, is_playoff=False)

    # Playoff stats
    for row in raw.get("post_season_totals", []):
        season_data = _transform_season_row(row)
        season_data = enrich_season_with_advanced(season_data, None)
        _upsert_season_stat(db, player_id, season_data, is_playoff=True)

    db.commit()
    logger.info(f"Sync complete for player {player_id}")
    return player


def _upsert_season_stat(db: Session, player_id: int, data: dict, is_playoff: bool):
    """Insert or update a season stat row."""
    stat = db.query(SeasonStat).filter(
        SeasonStat.player_id == player_id,
        SeasonStat.season == data["season"],
        SeasonStat.team_abbreviation == data["team_abbreviation"],
        SeasonStat.is_playoff == is_playoff,
    ).first()

    if not stat:
        stat = SeasonStat(
            player_id=player_id,
            season=data["season"],
            team_abbreviation=data["team_abbreviation"],
            is_playoff=is_playoff,
        )
        db.add(stat)

    # Update all stat fields
    for key in [
        "gp", "gs", "min_total", "min_pg", "pts", "pts_pg", "reb", "reb_pg",
        "ast", "ast_pg", "stl", "stl_pg", "blk", "blk_pg", "tov", "tov_pg",
        "fgm", "fga", "fg_pct", "fg3m", "fg3a", "fg3_pct", "ftm", "fta", "ft_pct",
        "oreb", "dreb", "pf", "ts_pct", "efg_pct", "usg_pct", "per", "bpm",
        "off_rating", "def_rating", "net_rating", "ws", "vorp", "pie", "pace",
        "darko", "epm", "rapm",
    ]:
        if key in data:
            setattr(stat, key, data[key])

    db.flush()


def sync_player_if_needed(db: Session, player_id: int) -> Player:
    """Sync a player only if they don't exist in the database yet.

    For re-syncing existing players, use sync_player() directly.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if player and player.season_stats:
        return player
    return sync_player(db, player_id)


def sync_injuries(db: Session, season: str) -> Dict[str, int]:
    """Fetch the current NBA injury report from CDN and persist to player_injuries.

    Upserts one row per (player_id, report_date). Returns a summary dict with
    'fetched', 'upserted', and 'unresolved' counts.
    """
    logger.info("Fetching injuries payload from NBA CDN...")
    try:
        raw = get_injuries_payload()
    except Exception as exc:
        logger.error(f"Failed to fetch injuries payload: {exc}")
        raise

    payload = raw.get("payload", raw)
    report_date_str = payload.get("date", "")
    try:
        report_date = datetime.strptime(report_date_str, "%Y-%m-%dT%H:%M:%S").date()
    except (ValueError, TypeError):
        report_date = date.today()

    injury_list: List[dict] = payload.get("InjuryList", [])
    fetched = len(injury_list)
    upserted = 0
    unresolved = 0

    # Build a player_id lookup from NBA PersonID strings present in our DB
    # to avoid N+1 queries.
    person_ids = set()
    for entry in injury_list:
        try:
            person_ids.add(int(entry.get("PersonID", 0)))
        except (ValueError, TypeError):
            pass

    player_map: Dict[int, int] = {}
    if person_ids:
        rows = db.query(Player.id).filter(Player.id.in_(list(person_ids))).all()
        player_map = {r[0]: r[0] for r in rows}

    for entry in injury_list:
        try:
            nba_person_id = int(entry.get("PersonID", 0))
        except (ValueError, TypeError):
            unresolved += 1
            continue

        player_id = player_map.get(nba_person_id)
        if not player_id:
            unresolved += 1
            logger.debug(f"Injury: player_id {nba_person_id} not in DB, skipping")
            continue

        # Parse return date if provided
        return_date: Optional[date] = None
        return_str = (entry.get("Return") or "").strip()
        if return_str:
            for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y"):
                try:
                    return_date = datetime.strptime(return_str, fmt).date()
                    break
                except ValueError:
                    pass

        existing = (
            db.query(PlayerInjury)
            .filter(
                PlayerInjury.player_id == player_id,
                PlayerInjury.report_date == report_date,
            )
            .first()
        )
        if existing:
            row = existing
        else:
            row = PlayerInjury(player_id=player_id, report_date=report_date)
            db.add(row)

        row.team_id = None  # team_id resolution would require a team lookup; skip for now
        row.return_date = return_date
        row.injury_type = (entry.get("Injury") or "")[:100]
        row.injury_status = (entry.get("Status") or "")[:50]
        row.detail = (entry.get("Detail") or "")[:200]
        row.comment = entry.get("Comment") or ""
        row.season = season
        row.fetched_at = datetime.utcnow()
        upserted += 1

    db.commit()
    summary = {"fetched": fetched, "upserted": upserted, "unresolved": unresolved}
    logger.info(f"sync_injuries complete: {summary}")
    return summary


def get_or_sync_player_profile(db: Session, player_id: int) -> Player:
    """Return an existing local player row when available.

    This keeps read-heavy UI surfaces like compare from triggering a full
    career sync just to render a profile card. Only missing players are
    fetched from the remote source here.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if player:
        return player
    return sync_player(db, player_id)
