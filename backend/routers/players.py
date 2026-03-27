from typing import List

from fastapi import APIRouter, HTTPException, Query

from data.cache import CacheManager
from data.nba_client import get_player_info, search_players
from config import CACHE_TTL_PLAYER_BIO
from models.player import PlayerProfile, PlayerSearchResult

router = APIRouter()


@router.get("/search", response_model=List[PlayerSearchResult])
def search(q: str = Query(..., min_length=2, description="Player name to search")):
    results = search_players(q)
    return results


@router.get("/{player_id}", response_model=PlayerProfile)
def get_player(player_id: int):
    cache_key = f"player_info:{player_id}"
    cached = CacheManager.get(cache_key)
    if cached:
        return PlayerProfile(**cached)

    try:
        data = get_player_info(player_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Player not found: {e}")

    CacheManager.set(cache_key, data, CACHE_TTL_PLAYER_BIO)
    return PlayerProfile(**data)
