"use client";

import useSWR from "swr";
import { getPlayerTeamFit } from "@/lib/api";
import type { TeamFitResponse } from "@/lib/types";

export function usePlayerTeamFit(playerId: number | null, season: string, limit = 5) {
  return useSWR<TeamFitResponse>(
    playerId !== null && season ? `player-team-fit-${playerId}-${season}-${limit}` : null,
    () => getPlayerTeamFit(playerId!, season, limit)
  );
}
