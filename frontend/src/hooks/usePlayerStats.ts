"use client";

import useSWR from "swr";
import type {
  PlayerProfile,
  CareerStatsResponse,
  ShotChartResponse,
  LeaderboardResponse,
  TeamSummary,
  TeamRosterResponse,
  TeamAnalytics,
  StandingsEntry,
  PercentileResult,
  OnOffStats,
  ClutchStats,
  LineupsResult,
  OnOffLeaderboardResult,
  GameLogResponse,
  SimilarityResponse,
} from "@/lib/types";
import {
  getPlayerProfile,
  getPlayerCareerStats,
  getPlayerShotChart,
  getLeaderboard,
  getTeams,
  getTeamRoster,
  getTeamAnalytics,
  getStandings,
  getPlayerPercentiles,
  getPlayerOnOff,
  getPlayerClutch,
  getLineups,
  getOnOffLeaderboard,
  getPlayerGameLogs,
  getSimilarPlayers,
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

export function useTeams() {
  return useSWR<TeamSummary[]>("teams", getTeams);
}

export function useTeamRoster(teamAbbreviation: string | null) {
  return useSWR<TeamRosterResponse>(
    teamAbbreviation ? `team-roster-${teamAbbreviation}` : null,
    () => getTeamRoster(teamAbbreviation!)
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

export function usePlayerGameLogs(
  playerId: number | null,
  season: string | null,
  seasonType = "Regular Season"
) {
  return useSWR<GameLogResponse>(
    playerId && season ? `game-logs-${playerId}-${season}-${seasonType}` : null,
    () => getPlayerGameLogs(playerId!, season!, seasonType)
  );
}

export function useStandings(season: string | null) {
  return useSWR<StandingsEntry[]>(
    season ? `standings-${season}` : null,
    () => getStandings(season!)
  );
}

export function useTeamAnalytics(
  teamAbbreviation: string | null,
  season: string | null
) {
  return useSWR<TeamAnalytics>(
    teamAbbreviation && season
      ? `team-analytics-${teamAbbreviation}-${season}`
      : null,
    () => getTeamAnalytics(teamAbbreviation!, season!)
  );
}

export function useSimilarPlayers(
  playerId: number | null,
  season: string | null,
  n = 8,
  crossEra = true
) {
  return useSWR<SimilarityResponse>(
    playerId && season ? `similarity-${playerId}-${season}-${n}-${crossEra}` : null,
    () => getSimilarPlayers(playerId!, season!, n, crossEra)
  );
}
