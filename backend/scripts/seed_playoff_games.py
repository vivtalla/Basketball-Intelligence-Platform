"""One-off: seed 2025-26 playoff GameLog rows from nba_api LeagueGameFinder + build the bracket.

Run with:
    cd backend && PYTHONPATH=. ./venv/bin/python scripts/seed_playoff_games.py
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session
from nba_api.stats.endpoints import LeagueGameFinder

from db.database import SessionLocal
from db.models import GameLog, Team
from services.playoff_bracket_service import build_or_refresh_bracket


def parse_game_date(s: str):
    if not s:
        return None
    # LeagueGameFinder returns "2026-04-27"
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        try:
            return datetime.strptime(s, "%b %d, %Y").date()
        except ValueError:
            return None


def upsert_game(
    db: Session,
    *,
    game_id: str,
    season: str,
    game_date,
    home_team_id: int,
    away_team_id: int,
    home_score: Optional[int],
    away_score: Optional[int],
) -> GameLog:
    row = db.query(GameLog).filter(GameLog.game_id == game_id).one_or_none()
    if row is None:
        row = GameLog(game_id=game_id)
        db.add(row)
    row.season = season
    row.game_date = game_date
    row.home_team_id = home_team_id
    row.away_team_id = away_team_id
    row.home_score = home_score
    row.away_score = away_score
    row.season_type = "Playoffs"
    return row


def seed_playoff_games(season: str = "2025-26") -> int:
    db: Session = SessionLocal()
    try:
        teams = {t.id: t.abbreviation for t in db.query(Team).all()}
        if not teams:
            print("No teams in DB — bailing.")
            return 0

        print(f"  fetching {season} playoff games via LeagueGameFinder ...")
        result = LeagueGameFinder(
            season_nullable=season,
            season_type_nullable="Playoffs",
            league_id_nullable="00",
            timeout=60,
        ).get_normalized_dict()
        rows = result.get("LeagueGameFinderResults", [])
        print(f"  got {len(rows)} rows ({len(rows) // 2} unique games)")

        # gid -> {team_a, team_b, pts_a, pts_b, matchup, date, abbr_a, abbr_b}
        games_seen: Dict[str, Dict] = {}
        for r in rows:
            gid = r.get("GAME_ID")
            if not gid:
                continue
            tid = r.get("TEAM_ID")
            if tid is None:
                continue
            # Only persist scores for completed games. nba_api's LeagueGameFinder
            # returns partial mid-game scores for live games with WL=None; we
            # don't want those polluting the bracket as if they were final.
            wl = r.get("WL")
            game_completed = wl in ("W", "L")
            pts = r.get("PTS") if game_completed else None
            matchup = r.get("MATCHUP", "")
            date = parse_game_date(r.get("GAME_DATE", ""))
            abbr = r.get("TEAM_ABBREVIATION", "") or teams.get(tid, "")

            if gid not in games_seen:
                games_seen[gid] = {
                    "date": date,
                    "team_a": tid,
                    "abbr_a": abbr,
                    "matchup_a": matchup,
                    "pts_a": pts,
                    "team_b": None,
                    "abbr_b": None,
                    "pts_b": None,
                }
            else:
                games_seen[gid]["team_b"] = tid
                games_seen[gid]["abbr_b"] = abbr
                games_seen[gid]["pts_b"] = pts

        inserted = 0
        for gid, info in games_seen.items():
            if info["team_a"] is None or info["team_b"] is None:
                continue
            matchup = info["matchup_a"] or ""
            abbr_a = info["abbr_a"] or ""
            # If team_a's perspective string says "vs.", team_a is home.
            if " vs." in matchup or " VS." in matchup:
                home_id, away_id = info["team_a"], info["team_b"]
                home_pts, away_pts = info["pts_a"], info["pts_b"]
            else:
                home_id, away_id = info["team_b"], info["team_a"]
                home_pts, away_pts = info["pts_b"], info["pts_a"]

            upsert_game(
                db,
                game_id=gid,
                season=season,
                game_date=info["date"],
                home_team_id=home_id,
                away_team_id=away_id,
                home_score=int(home_pts) if home_pts is not None else None,
                away_score=int(away_pts) if away_pts is not None else None,
            )
            inserted += 1

        db.commit()
        print(f"  wrote {inserted} unique playoff games")

        bracket_count = build_or_refresh_bracket(db, season)
        print(f"  bracket: {bracket_count} series refreshed")
        return inserted
    finally:
        db.close()


if __name__ == "__main__":
    n = seed_playoff_games()
    print(f"done. {n} games persisted.")
