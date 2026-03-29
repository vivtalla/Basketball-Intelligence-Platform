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
  TeamIntelligence,
  StandingsEntry,
  BreakoutsResponse,
  PercentileResult,
  OnOffStats,
  PbpCoverage,
  PbpCoverageDashboard,
  PbpCoverageSeasonSummary,
  ClutchStats,
  LineupsResult,
  OnOffLeaderboardResult,
  GameLogResponse,
  GameDetailResponse,
  SimilarityResponse,
  LeagueContext,
  CareerLeaderboardResponse,
} from "@/lib/types";
import {
  getPlayerProfile,
  getPlayerCareerStats,
  getPlayerShotChart,
  getLeaderboard,
  getTeams,
  getTeamRoster,
  getTeamAnalytics,
  getTeamIntelligence,
  getStandings,
  getBreakouts,
  getPlayerPercentiles,
  getPlayerOnOff,
  getPlayerPbpCoverage,
  getPbpCoverageDashboard,
  getPbpCoverageSeasons,
  getPlayerClutch,
  getLineups,
  getOnOffLeaderboard,
  getPlayerGameLogs,
  getGameDetail,
  getSimilarPlayers,
  getLeagueContext,
  getCareerLeaderboard,
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

export function usePlayerPbpCoverage(playerId: number | null, season: string | null) {
  return useSWR<PbpCoverage>(
    playerId && season ? `pbp-coverage-${playerId}-${season}` : null,
    () => getPlayerPbpCoverage(playerId!, season!)
  );
}

export function usePbpCoverageDashboard(season: string | null) {
  return useSWR<PbpCoverageDashboard>(
    season ? `pbp-dashboard-${season}` : null,
    () => getPbpCoverageDashboard(season!)
  );
}

export function usePbpCoverageSeasons() {
  return useSWR<PbpCoverageSeasonSummary[]>("pbp-dashboard-seasons", getPbpCoverageSeasons);
}

export function useLeaderboard(
  stat: string,
  season: string,
  seasonType = "Regular Season",
  limit = 25,
  team = ""
) {
  return useSWR<LeaderboardResponse>(
    stat && season ? `leaderboard-${stat}-${season}-${seasonType}-${limit}-${team}` : null,
    () => getLeaderboard(stat, season, seasonType, limit, team || undefined)
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

export function useGameDetail(gameId: string | null) {
  return useSWR<GameDetailResponse>(
    gameId ? `game-detail-${gameId}` : null,
    () => getGameDetail(gameId!)
  );
}

export function useBreakouts(season: string | null, minGp = 20, limit = 25) {
  return useSWR<BreakoutsResponse>(
    season ? `breakouts-${season}-${minGp}-${limit}` : null,
    () => getBreakouts(season!, minGp, limit)
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

export function useTeamIntelligence(
  teamAbbreviation: string | null,
  season: string | null
) {
  return useSWR<TeamIntelligence>(
    teamAbbreviation && season
      ? `team-intelligence-${teamAbbreviation}-${season}`
      : null,
    () => getTeamIntelligence(teamAbbreviation!, season!)
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

export function useLeagueContext(season: string | null, position?: string) {
  return useSWR<LeagueContext>(
    season ? `league-context-${season}-${position ?? "all"}` : null,
    () => getLeagueContext(season!, position)
  );
}

export function useCareerLeaderboard(
  stat: string | null,
  minGp = 15,
  limit = 25
) {
  return useSWR<CareerLeaderboardResponse>(
    stat ? `career-leaderboard-${stat}-${minGp}-${limit}` : null,
    () => getCareerLeaderboard(stat!, minGp, limit)
  );
}

// ── Warehouse pipeline hooks ──────────────────────────────────────────────────

import type { WarehouseSeasonHealth, IngestionJobResponse } from "@/lib/types";
import { getWarehouseSeasonHealth, getWarehouseJobs } from "@/lib/api";

export function useWarehouseSeasonHealth(season: string | null) {
  return useSWR<WarehouseSeasonHealth>(
    season ? `warehouse-health-${season}` : null,
    () => getWarehouseSeasonHealth(season!)
  );
}

export function useWarehouseJobs(status?: string) {
  return useSWR<IngestionJobResponse[]>(
    `warehouse-jobs-${status ?? "all"}`,
    () => getWarehouseJobs(status)
  );
}
