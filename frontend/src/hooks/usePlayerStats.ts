"use client";

import useSWR from "swr";
import type {
  PlayerProfile,
  CareerStatsResponse,
  ShotChartResponse,
  LeaderboardResponse,
  PercentileResult,
  OnOffStats,
  ClutchStats,
  LineupsResult,
  OnOffLeaderboardResult,
} from "@/lib/types";
import {
  getPlayerProfile,
  getPlayerCareerStats,
  getPlayerShotChart,
  getLeaderboard,
  getPlayerPercentiles,
  getPlayerOnOff,
  getPlayerClutch,
  getLineups,
  getOnOffLeaderboard,
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

export function usePlayerPercentiles(playerId: number | null, season: string | null) {
  return useSWR<PercentileResult>(
    playerId && season ? `percentiles-${playerId}-${season}` : null,
    () => getPlayerPercentiles(playerId!, season!)
  );
}

export function usePlayerOnOff(playerId: number | null, season: string | null) {
  return useSWR<OnOffStats>(
    playerId && season ? `on-off-${playerId}-${season}` : null,
    () => getPlayerOnOff(playerId!, season!)
  );
}

export function usePlayerClutch(playerId: number | null, season: string | null) {
  return useSWR<ClutchStats>(
    playerId && season ? `clutch-${playerId}-${season}` : null,
    () => getPlayerClutch(playerId!, season!)
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

export function useLineups(
  season: string | null,
  teamId?: number,
  minMinutes = 5,
  limit = 25
) {
  return useSWR<LineupsResult>(
    season ? `lineups-${season}-${teamId ?? "all"}-${minMinutes}-${limit}` : null,
    () => getLineups(season!, teamId, minMinutes, limit)
  );
}

export function useOnOffLeaderboard(
  season: string | null,
  minMinutes = 200,
  limit = 25
) {
  return useSWR<OnOffLeaderboardResult>(
    season ? `on-off-leaderboard-${season}-${minMinutes}-${limit}` : null,
    () => getOnOffLeaderboard(season!, minMinutes, limit)
  );
}
