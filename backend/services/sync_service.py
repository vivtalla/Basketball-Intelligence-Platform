"""Sync service: pulls data from nba_api into PostgreSQL."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from data.nba_client import (
    get_career_stats,
    get_injuries_payload,
    get_league_dash_player_stats,
    get_player_advanced_stats_from_league,
    get_player_info,
    get_team_stats,
    search_players,
)
from db.models import Player, PlayerInjury, SeasonStat, Team, TeamSeasonStat
from services.advanced_metrics import enrich_season_with_advanced
from services.player_identity_service import (
    build_player_resolution_indexes,
    persist_unresolved_injury_entry,
    resolve_fallback_player,
    sync_player_aliases,
)

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


def _base_league_dash_to_season_row(row: dict, season: str) -> dict:
    gp = row.get("GP", 0) or 1
    min_total = float(row.get("MIN", 0) or 0.0)
    return {
        "season": season,
        "team_abbreviation": row.get("TEAM_ABBREVIATION", ""),
        "gp": row.get("GP", 0),
        "gs": row.get("GS", 0),
        "age": row.get("AGE"),
        "min_total": round(min_total, 1),
        "min_pg": round(min_total / gp, 1),
        "pts": row.get("PTS", 0),
        "pts_pg": round(float(row.get("PTS", 0) or 0.0) / gp, 1),
        "reb": row.get("REB", 0),
        "reb_pg": round(float(row.get("REB", 0) or 0.0) / gp, 1),
        "ast": row.get("AST", 0),
        "ast_pg": round(float(row.get("AST", 0) or 0.0) / gp, 1),
        "stl": row.get("STL", 0),
        "stl_pg": round(float(row.get("STL", 0) or 0.0) / gp, 1),
        "blk": row.get("BLK", 0),
        "blk_pg": round(float(row.get("BLK", 0) or 0.0) / gp, 1),
        "tov": row.get("TOV", 0),
        "tov_pg": round(float(row.get("TOV", 0) or 0.0) / gp, 1),
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


def _official_team_stats_to_row_payload(team_stats: dict, season: str) -> dict:
    return {
        "season": season,
        "gp": team_stats.get("gp", 0),
        "w": team_stats.get("w", 0),
        "l": team_stats.get("l", 0),
        "w_pct": team_stats.get("w_pct", 0.0),
        "pts_pg": team_stats.get("pts_pg"),
        "ast_pg": team_stats.get("ast_pg"),
        "reb_pg": team_stats.get("reb_pg"),
        "tov_pg": team_stats.get("tov_pg"),
        "blk_pg": team_stats.get("blk_pg"),
        "stl_pg": team_stats.get("stl_pg"),
        "fg_pct": team_stats.get("fg_pct"),
        "fg3_pct": team_stats.get("fg3_pct"),
        "ft_pct": team_stats.get("ft_pct"),
        "plus_minus_pg": team_stats.get("plus_minus_pg"),
        "off_rating": team_stats.get("off_rating"),
        "def_rating": team_stats.get("def_rating"),
        "net_rating": team_stats.get("net_rating"),
        "pace": team_stats.get("pace"),
        "efg_pct": team_stats.get("efg_pct"),
        "ts_pct": team_stats.get("ts_pct"),
        "pie": team_stats.get("pie"),
        "oreb_pct": team_stats.get("oreb_pct"),
        "dreb_pct": team_stats.get("dreb_pct"),
        "tov_pct": team_stats.get("tov_pct"),
        "ast_pct": team_stats.get("ast_pct"),
        "off_rating_rank": team_stats.get("off_rating_rank"),
        "def_rating_rank": team_stats.get("def_rating_rank"),
        "net_rating_rank": team_stats.get("net_rating_rank"),
        "pace_rank": team_stats.get("pace_rank"),
        "efg_pct_rank": team_stats.get("efg_pct_rank"),
        "ts_pct_rank": team_stats.get("ts_pct_rank"),
        "oreb_pct_rank": team_stats.get("oreb_pct_rank"),
        "tov_pct_rank": team_stats.get("tov_pct_rank"),
        "source": "stats.nba.com/team-dashboard",
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
    sync_player_aliases(db, player, source="sync_player")

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
        except Exception as exc:
            logger.debug(
                "Advanced stats unavailable during player sync for %s in %s: %s",
                player_id,
                season_id,
                exc,
            )

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


def sync_official_season_stats(
    db: Session,
    season: str,
    player_ids: Optional[Sequence[int]] = None,
) -> dict:
    logger.info("Syncing official season stats for %s", season)
    official_base_rows = get_league_dash_player_stats(season, measure_type="Base")
    official_advanced_rows = get_league_dash_player_stats(season, measure_type="Advanced")

    player_filter = {int(player_id) for player_id in player_ids} if player_ids else None
    advanced_by_player = {
        int(row.get("PLAYER_ID")): row
        for row in official_advanced_rows
        if row.get("PLAYER_ID") is not None
    }
    base_rows = [
        row for row in official_base_rows
        if row.get("PLAYER_ID") is not None and (player_filter is None or int(row["PLAYER_ID"]) in player_filter)
    ]

    existing_rows = db.query(SeasonStat).filter(
        SeasonStat.season == season,
        SeasonStat.is_playoff == False,  # noqa: E712
    ).all()
    existing_by_key = {(row.player_id, row.team_abbreviation): row for row in existing_rows}

    player_ids_in_scope = {int(row["PLAYER_ID"]) for row in base_rows}
    existing_players = db.query(Player).filter(Player.id.in_(player_ids_in_scope)).all() if player_ids_in_scope else []
    player_lookup = {player.id: player for player in existing_players}

    team_ids_in_scope = {int(row["TEAM_ID"]) for row in base_rows if row.get("TEAM_ID")}
    existing_teams = db.query(Team).filter(Team.id.in_(team_ids_in_scope)).all() if team_ids_in_scope else []
    team_lookup = {team.id: team for team in existing_teams}

    current_team_by_player = {int(row["PLAYER_ID"]): row.get("TEAM_ABBREVIATION", "") for row in base_rows}
    deleted = 0
    for existing in existing_rows:
        if existing.player_id not in current_team_by_player:
            continue
        official_team = current_team_by_player[existing.player_id]
        if existing.team_abbreviation != official_team:
            db.delete(existing)
            existing_by_key.pop((existing.player_id, existing.team_abbreviation), None)
            deleted += 1

    updated = 0
    created_players = 0
    created_teams = 0

    for row in base_rows:
        player_id = int(row["PLAYER_ID"])
        team_id = int(row["TEAM_ID"]) if row.get("TEAM_ID") else None
        team_abbreviation = row.get("TEAM_ABBREVIATION", "")
        player_name = (row.get("PLAYER_NAME") or "").strip()

        if team_id and team_id not in team_lookup:
            team = Team(id=team_id, abbreviation=team_abbreviation, name=team_abbreviation)
            db.add(team)
            db.flush()
            team_lookup[team_id] = team
            created_teams += 1
        elif team_id and team_abbreviation:
            team = team_lookup[team_id]
            team.abbreviation = team_abbreviation

        player = player_lookup.get(player_id)
        if not player:
            player = Player(
                id=player_id,
                full_name=player_name,
                team_id=team_id,
                is_active=True,
                headshot_url=f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png",
            )
            db.add(player)
            db.flush()
            player_lookup[player_id] = player
            created_players += 1
        else:
            if player_name:
                player.full_name = canonical_player_name(player_name, player.first_name or "", player.last_name or "")
            if team_id:
                player.team_id = team_id
            player.is_active = True
            if not player.headshot_url:
                player.headshot_url = f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png"

        season_data = _base_league_dash_to_season_row(row, season)
        season_data = enrich_season_with_advanced(season_data, advanced_by_player.get(player_id))
        stat_row = existing_by_key.get((player_id, team_abbreviation))
        if not stat_row:
            stat_row = SeasonStat(
                player_id=player_id,
                season=season,
                team_abbreviation=team_abbreviation,
                is_playoff=False,
            )
            db.add(stat_row)
            existing_by_key[(player_id, team_abbreviation)] = stat_row

        for key, value in season_data.items():
            if hasattr(stat_row, key):
                setattr(stat_row, key, value)
        updated += 1

    db.commit()
    logger.info(
        "Official season stat sync complete for %s: updated=%s deleted=%s players=%s teams=%s",
        season,
        updated,
        deleted,
        created_players,
        created_teams,
    )
    return {
        "status": "ok",
        "season": season,
        "players_synced": updated,
        "stale_rows_deleted": deleted,
        "players_created": created_players,
        "teams_created": created_teams,
    }


def sync_official_team_season_stats(
    db: Session,
    season: str,
    team_ids: Optional[Sequence[int]] = None,
) -> dict:
    logger.info("Syncing official team season stats for %s", season)
    official_rows_by_abbr = get_team_stats(season)
    team_filter = {int(team_id) for team_id in team_ids} if team_ids else None

    if team_filter is not None:
        official_rows_by_abbr = {
            abbr: row
            for abbr, row in official_rows_by_abbr.items()
            if row.get("team_id") is not None and int(row["team_id"]) in team_filter
        }

    persisted_rows = db.query(TeamSeasonStat).filter(
        TeamSeasonStat.season == season,
        TeamSeasonStat.is_playoff == False,  # noqa: E712
    ).all()
    persisted_by_team = {row.team_id: row for row in persisted_rows}

    created_teams = 0
    updated_rows = 0
    created_rows = 0

    for abbr, team_stats in official_rows_by_abbr.items():
        team_id = int(team_stats["team_id"])
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            team = Team(
                id=team_id,
                abbreviation=abbr,
                name=team_stats.get("name") or abbr,
            )
            db.add(team)
            db.flush()
            created_teams += 1
        else:
            team.abbreviation = abbr
            if team_stats.get("name"):
                team.name = team_stats["name"]

        row = persisted_by_team.get(team_id)
        if not row:
            row = TeamSeasonStat(team_id=team_id, season=season, is_playoff=False)
            db.add(row)
            persisted_by_team[team_id] = row
            created_rows += 1

        payload = _official_team_stats_to_row_payload(team_stats, season)
        for key, value in payload.items():
            setattr(row, key, value)
        updated_rows += 1

    db.commit()
    logger.info(
        "Official team season sync complete for %s: rows=%s teams=%s created=%s",
        season,
        updated_rows,
        created_teams,
        created_rows,
    )
    return {
        "status": "ok",
        "season": season,
        "teams_synced": updated_rows,
        "team_rows_created": created_rows,
        "teams_created": created_teams,
    }


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
    """Fetch the current NBA injury report and persist to player_injuries.

    Upserts one row per (player_id, report_date). Returns a summary dict with
    'fetched', 'upserted', and 'unresolved' counts.
    """
    logger.info("Fetching injuries payload from NBA CDN...")
    try:
        raw = get_injuries_payload(season=season)
    except Exception as exc:
        logger.error(f"Failed to fetch injuries payload: {exc}")
        raise

    payload = raw.get("payload", raw)
    source = (raw.get("source") or "cdn.nba.com/injuries")[:100]
    source_url = raw.get("source_url")
    fallback_reason = raw.get("fallback_reason")
    if fallback_reason:
        logger.warning("Using official injury report fallback after primary feed failure: %s", fallback_reason)

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

    team_lookup, team_alias_lookup, league_alias_lookup, team_last_lookup = build_player_resolution_indexes(db)

    for entry in injury_list:
        try:
            nba_person_id = int(entry.get("PersonID", 0))
        except (ValueError, TypeError):
            nba_person_id = 0

        player_id = player_map.get(nba_person_id)
        resolved_team_id = entry.get("TeamID")
        if not player_id:
            player_id, fallback_team_id = resolve_fallback_player(
                entry,
                team_lookup,
                team_alias_lookup,
                league_alias_lookup,
                team_last_lookup,
            )
            resolved_team_id = fallback_team_id or resolved_team_id
        if not player_id:
            unresolved += 1
            persist_unresolved_injury_entry(
                db,
                season=season,
                report_date=report_date,
                entry=entry,
                source=source,
                source_url=source_url,
            )
            logger.debug("Injury entry could not be resolved in DB, skipping: %s", entry)
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
                    continue

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

        row.team_id = resolved_team_id
        row.return_date = return_date
        row.injury_type = (entry.get("Injury") or "")[:100]
        row.injury_status = (entry.get("Status") or "")[:50]
        row.detail = (entry.get("Detail") or "")[:200]
        row.comment = entry.get("Comment") or ""
        row.season = season
        row.source = source
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
