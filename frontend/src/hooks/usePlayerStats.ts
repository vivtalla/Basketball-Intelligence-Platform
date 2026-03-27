"use client";

import useSWR from "swr";
import type { PlayerProfile, CareerStatsResponse } from "@/lib/types";
import { getPlayerProfile, getPlayerCareerStats } from "@/lib/api";

export function usePlayerProfile(playerId: number) {
  return useSWR<PlayerProfile>(`player-profile-${playerId}`, () =>
    getPlayerProfile(playerId)
  );
}

export function usePlayerCareerStats(playerId: number) {
  return useSWR<CareerStatsResponse>(`player-career-${playerId}`, () =>
    getPlayerCareerStats(playerId)
  );
}
