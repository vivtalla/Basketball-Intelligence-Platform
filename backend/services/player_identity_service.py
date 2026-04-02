from __future__ import annotations

import unicodedata
from collections import defaultdict
from typing import DefaultDict, Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from db.models import InjurySyncUnresolved, Player, PlayerNameAlias, Team

NAME_SUFFIXES = ("Jr.", "Sr.", "II", "III", "IV", "V")


def normalize_lookup_text(value: str = "") -> str:
    normalized = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    normalized = normalized.replace(".", " ").replace("'", "").replace("’", "")
    normalized = normalized.replace("-", " ").replace(",", " ").replace(";", " ")
    return " ".join(normalized.lower().split())


def build_player_alias_rows(player: Player) -> List[Tuple[str, str]]:
    first_name = (player.first_name or "").strip()
    last_name = (player.last_name or "").strip()
    full_name = (player.full_name or "").strip()

    display_candidates: List[str] = []
    if full_name:
        display_candidates.append(full_name)
    if first_name and last_name:
        display_candidates.append("{0} {1}".format(first_name, last_name).strip())
        display_candidates.append("{0}, {1}".format(last_name, first_name).strip())

        for suffix in NAME_SUFFIXES:
            if last_name.endswith(" {0}".format(suffix)):
                base_last = last_name[: -len(" {0}".format(suffix))].strip()
                if base_last:
                    display_candidates.append("{0}, {1} {2}".format(base_last, first_name, suffix).strip())
                    display_candidates.append("{0} {1} {2}".format(first_name, base_last, suffix).strip())
            if full_name.endswith(" {0}".format(suffix)):
                base_full = full_name[: -len(" {0}".format(suffix))].strip()
                if base_full:
                    display_candidates.append("{0}, {1}".format(suffix, base_full).strip())

    if full_name and "," in full_name:
        display_candidates.append(full_name.replace(",", " "))

    rows: List[Tuple[str, str]] = []
    seen: Set[str] = set()
    for display in display_candidates:
        display = " ".join(display.split()).strip()
        if not display:
            continue
        normalized = normalize_lookup_text(display)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        rows.append((normalized, display))
    return rows


def sync_player_aliases(db: Session, player: Player, source: str) -> None:
    if not player.id:
        return

    existing = {
        row.alias_normalized: row
        for row in db.query(PlayerNameAlias).filter(PlayerNameAlias.player_id == player.id).all()
    }
    for normalized, display in build_player_alias_rows(player):
        row = existing.get(normalized)
        if row:
            row.alias_display = display
            row.source = source
            continue
        db.add(
            PlayerNameAlias(
                player_id=player.id,
                alias_normalized=normalized,
                alias_display=display,
                source=source,
            )
        )


def build_team_lookup(db: Session) -> Dict[str, int]:
    lookup: Dict[str, int] = {}
    for team in db.query(Team).all():
        keys = {
            normalize_lookup_text(team.abbreviation or ""),
            normalize_lookup_text(team.name or ""),
        }
        if team.city:
            keys.add(normalize_lookup_text(team.city))
            keys.add(normalize_lookup_text("{0} {1}".format(team.city, team.name or "").strip()))
        for key in keys:
            if key:
                lookup[key] = team.id
    return lookup


def _append_player_id(bucket: DefaultDict[str, Set[int]], key: str, player_id: int) -> None:
    if key:
        bucket[key].add(player_id)


def build_player_resolution_indexes(
    db: Session,
) -> Tuple[Dict[str, int], Dict[int, Dict[str, Set[int]]], Dict[str, Set[int]], Dict[int, Dict[str, Set[int]]]]:
    team_lookup = build_team_lookup(db)
    team_alias_lookup: Dict[int, Dict[str, Set[int]]] = defaultdict(lambda: defaultdict(set))
    league_alias_lookup: Dict[str, Set[int]] = defaultdict(set)
    team_last_lookup: Dict[int, Dict[str, Set[int]]] = defaultdict(lambda: defaultdict(set))

    alias_rows = (
        db.query(PlayerNameAlias.player_id, PlayerNameAlias.alias_normalized, Player.team_id)
        .join(Player, Player.id == PlayerNameAlias.player_id)
        .filter(Player.is_active == True, Player.team_id.isnot(None))  # noqa: E712
        .all()
    )
    for player_id, alias_normalized, team_id in alias_rows:
        if not team_id or not alias_normalized:
            continue
        _append_player_id(team_alias_lookup[team_id], alias_normalized, player_id)
        _append_player_id(league_alias_lookup, alias_normalized, player_id)

    players = db.query(Player).filter(Player.is_active == True, Player.team_id.isnot(None)).all()  # noqa: E712
    for player in players:
        for alias_normalized, _display in build_player_alias_rows(player):
            if player.team_id and alias_normalized:
                _append_player_id(team_alias_lookup[player.team_id], alias_normalized, player.id)
                _append_player_id(league_alias_lookup, alias_normalized, player.id)
        last_name = (player.last_name or "").strip()
        if not last_name and player.full_name:
            last_name = player.full_name.split(" ")[-1]
        last_key = normalize_lookup_text(last_name)
        if player.team_id and last_key:
            _append_player_id(team_last_lookup[player.team_id], last_key, player.id)

    return team_lookup, team_alias_lookup, league_alias_lookup, team_last_lookup


def resolve_fallback_player(
    entry: dict,
    team_lookup: Dict[str, int],
    team_alias_lookup: Dict[int, Dict[str, Set[int]]],
    league_alias_lookup: Dict[str, Set[int]],
    team_last_lookup: Dict[int, Dict[str, Set[int]]],
) -> Tuple[Optional[int], Optional[int]]:
    team_key = normalize_lookup_text(
        entry.get("TeamAbbreviation") or entry.get("Team") or entry.get("TeamName") or ""
    )
    team_id = team_lookup.get(team_key)
    if not team_id:
        return None, None

    player_name = (entry.get("PlayerName") or "").strip()
    alias_key = normalize_lookup_text(player_name)
    if not alias_key:
        return None, team_id

    team_matches = team_alias_lookup.get(team_id, {}).get(alias_key, set())
    if len(team_matches) == 1:
        return next(iter(team_matches)), team_id

    league_matches = league_alias_lookup.get(alias_key, set())
    if len(league_matches) == 1:
        return next(iter(league_matches)), team_id

    last_name = player_name.split(",", 1)[0].strip() if "," in player_name else player_name.split(" ")[-1]
    last_key = normalize_lookup_text(last_name)
    last_matches = team_last_lookup.get(team_id, {}).get(last_key, set())
    if len(last_matches) == 1:
        return next(iter(last_matches)), team_id

    return None, team_id


def persist_unresolved_injury_entry(
    db: Session,
    *,
    season: str,
    report_date,
    entry: dict,
    source: str,
    source_url: Optional[str],
) -> None:
    team_abbreviation = (entry.get("TeamAbbreviation") or "").strip()
    team_name = (entry.get("Team") or entry.get("TeamName") or "").strip()
    player_name = (entry.get("PlayerName") or "").strip()
    injury_status = (entry.get("Status") or "").strip()
    injury_type = (entry.get("Injury") or "").strip()
    detail = (entry.get("Detail") or "").strip()

    row = (
        db.query(InjurySyncUnresolved)
        .filter(
            InjurySyncUnresolved.season == season,
            InjurySyncUnresolved.report_date == report_date,
            InjurySyncUnresolved.team_abbreviation == team_abbreviation,
            InjurySyncUnresolved.player_name == player_name,
            InjurySyncUnresolved.injury_status == injury_status,
            InjurySyncUnresolved.detail == detail,
        )
        .first()
    )
    if not row:
        row = InjurySyncUnresolved(
            season=season,
            report_date=report_date,
            team_abbreviation=team_abbreviation,
            player_name=player_name,
            injury_status=injury_status,
            detail=detail,
        )
        db.add(row)

    row.team_name = team_name
    row.injury_type = injury_type
    row.source = source
    row.source_url = source_url
    row.normalized_lookup_key = normalize_lookup_text(
        "{0} {1}".format(team_abbreviation or team_name, player_name).strip()
    )
