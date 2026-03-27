"use client";

import useSWR from "swr";
import type { PlayerProfile, CareerStatsResponse, ShotChartResponse, LeaderboardResponse } from "@/lib/types";
import {
  getPlayerProfile,
  getPlayerCareerStats,
  getPlayerShotChart,
  getLeaderboard,
} from "@/lib/api";

export function usePlayerProfile(playerId: number | null) {
  return useSWR<PlayerProfile>(
    playerId ? `player-profile-${playerId}` : null,
    () => getPlayerProfile(playerId!)
  );
}

export function usePlayerCareerStats(playerId: number | null) {
  return useSWR<CareerStatsResponse>(
    playerId ? `player-career-${playerId}` : null,
    () => getPlayerCareerStats(playerId!)
  );
}

export function usePlayerShotChart(
  playerId: number,
  season: string,
  seasonType = "Regular Season"
) {
  return useSWR<ShotChartResponse>(
    season ? `shot-chart-${playerId}-${season}-${seasonType}` : null,
    () => getPlayerShotChart(playerId, season, seasonType)
  );
}

export function useLeaderboard(
  stat: string,
  season: string,
  seasonType = "Regular Season"
) {
  return useSWR<LeaderboardResponse>(
    season ? `leaderboard-${stat}-${season}-${seasonType}` : null,
    () => getLeaderboard(stat, season, seasonType)
  );
}
