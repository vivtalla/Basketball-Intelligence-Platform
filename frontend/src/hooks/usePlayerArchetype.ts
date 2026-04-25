"use client";

import useSWR from "swr";
import {
  getPlayerArchetype,
  getPlayerArchetypeHistory,
  getSimilarPlayersWithArchetype,
} from "@/lib/api";
import type {
  ArchetypeHistoryResponse,
  PlayerArchetype,
  SimilarityMode,
  SimilarityResponseWithArchetype,
} from "@/lib/types";

export function usePlayerArchetype(playerId: number | null, season: string) {
  return useSWR<PlayerArchetype>(
    playerId !== null && season ? `player-archetype-${playerId}-${season}` : null,
    () => getPlayerArchetype(playerId!, season)
  );
}

export function usePlayerSimilarityWithArchetype(
  playerId: number | null,
  season: string,
  mode: SimilarityMode,
  n = 8
) {
  return useSWR<SimilarityResponseWithArchetype>(
    playerId !== null && season
      ? `player-similarity-${playerId}-${season}-${mode}-${n}`
      : null,
    () => getSimilarPlayersWithArchetype(playerId!, season, mode, n)
  );
}

export function usePlayerArchetypeHistory(playerId: number | null) {
  return useSWR<ArchetypeHistoryResponse>(
    playerId !== null ? `player-archetype-history-${playerId}` : null,
    () => getPlayerArchetypeHistory(playerId!)
  );
}
