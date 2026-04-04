"use client";

import useSWR from "swr";
import type {
  DbFirstPlayerProfile,
  DbFirstCareerStatsResponse,
  PlayerTrendReport,
  PersistedShotChartResponse,
  LeaderboardResponse,
  TeamSummary,
  TeamRosterResponse,
  TeamAnalytics,
  TeamIntelligence,
  TeamPrepQueueResponse,
  TeamRotationReport,
  TeamComparisonResponse,
  TeamFocusLeversReport,
  UsageEfficiencyResponse,
  PreReadDeckResponse,
  PreReadSnapshotListResponse,
  PreReadSnapshotResponse,
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
  DbFirstGameLogResponse,
  GameDetailResponse,
  SimilarityResponse,
  LeagueContext,
  CareerLeaderboardResponse,
  TeamAvailabilityResponse,
  UpcomingScheduleGame,
  PersistedZoneProfileResponse,
  WarehouseReadinessSummary,
  WhatIfScenarioResponse,
  StyleXRayResponse,
  PlayTypeScoutingReportResponse,
  ShotLabDateRange,
} from "@/lib/types";
import {
  getPlayerProfile,
  getPlayerCareerStats,
  getPlayerTrendReport,
  getPersistedPlayerShotChart,
  getPersistedPlayerShotChartWindow,
  getLeaderboard,
  getTeams,
  getTeamRoster,
  getTeamAnalytics,
  getTeamIntelligence,
  getTeamPrepQueue,
  getTeamRotationReport,
  getTeamComparison,
  getTeamFocusLevers,
  getUsageEfficiencyReport,
  getPreReadDeck,
  getPreReadSnapshots,
  getPreReadSnapshot,
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
  getTeamAvailability,
  getUpcomingSchedule,
  getPersistedPlayerZoneProfile,
  getPersistedPlayerZoneProfileWindow,
  getWarehouseReadinessSummary,
  postWhatIfScenario,
  getStyleXRay,
  getPlayTypeScoutingReport,
} from "@/lib/api";

export function usePlayerProfile(playerId: number | null) {
  return useSWR<DbFirstPlayerProfile>(
    playerId ? `player-profile-${playerId}` : null,
    () => getPlayerProfile(playerId!)
  );
}

export function usePlayerCareerStats(playerId: number | null) {
  return useSWR<DbFirstCareerStatsResponse>(
    playerId ? `player-career-${playerId}` : null,
    () => getPlayerCareerStats(playerId!)
  );
}

export function usePlayerTrendReport(playerId: number | null, season: string | null) {
  return useSWR<PlayerTrendReport>(
    playerId && season ? `player-trend-report-${playerId}-${season}` : null,
    () => getPlayerTrendReport(playerId!, season!)
  );
}

export function usePlayerShotChart(
  playerId: number,
  season: string,
  seasonType = "Regular Season",
  filters?: ShotLabDateRange
) {
  return useSWR<PersistedShotChartResponse>(
    season
      ? `shot-chart-${playerId}-${season}-${seasonType}-${filters?.startDate ?? "all"}-${filters?.endDate ?? "all"}`
      : null,
    () =>
      filters?.startDate || filters?.endDate
        ? getPersistedPlayerShotChartWindow(playerId, season, seasonType, filters)
        : getPersistedPlayerShotChart(playerId, season, seasonType)
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

export function useTeamAvailability(
  teamAbbreviation: string | null,
  season: string | null
) {
  return useSWR<TeamAvailabilityResponse>(
    teamAbbreviation && season ? `team-availability-${teamAbbreviation}-${season}` : null,
    () => getTeamAvailability(teamAbbreviation!, season!)
  );
}

export function useUpcomingSchedule(
  season: string | null,
  days = 7,
  team?: string | null
) {
  return useSWR<UpcomingScheduleGame[]>(
    season ? `upcoming-schedule-${season}-${days}-${team ?? "all"}` : null,
    () => getUpcomingSchedule(season!, days, team ?? undefined)
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
  return useSWR<DbFirstGameLogResponse>(
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

export function useTeamPrepQueue(
  teamAbbreviation: string | null,
  season: string | null,
  days = 10
) {
  return useSWR<TeamPrepQueueResponse>(
    teamAbbreviation && season
      ? `team-prep-queue-${teamAbbreviation}-${season}-${days}`
      : null,
    () => getTeamPrepQueue(teamAbbreviation!, season!, days)
  );
}

export function useTeamRotationReport(
  teamAbbreviation: string | null,
  season: string | null
) {
  return useSWR<TeamRotationReport>(
    teamAbbreviation && season
      ? `team-rotation-report-${teamAbbreviation}-${season}`
      : null,
    () => getTeamRotationReport(teamAbbreviation!, season!)
  );
}

export function useTeamComparison(
  teamA: string | null,
  teamB: string | null,
  season: string | null
) {
  return useSWR<TeamComparisonResponse>(
    teamA && teamB && season ? `team-comparison-${teamA}-${teamB}-${season}` : null,
    () => getTeamComparison(teamA!, teamB!, season!)
  );
}

export function useTeamFocusLevers(
  teamAbbreviation: string | null,
  season: string | null
) {
  return useSWR<TeamFocusLeversReport>(
    teamAbbreviation && season ? `team-focus-levers-${teamAbbreviation}-${season}` : null,
    () => getTeamFocusLevers(teamAbbreviation!, season!)
  );
}

export function useUsageEfficiencyReport(
  season: string | null,
  team?: string,
  minMinutes = 20
) {
  return useSWR<UsageEfficiencyResponse>(
    season ? `usage-efficiency-${season}-${team ?? "all"}-${minMinutes}` : null,
    () => getUsageEfficiencyReport(season!, team, minMinutes)
  );
}

export function usePreReadDeck(
  team: string | null,
  opponent: string | null,
  season: string | null,
  snapshotId?: string | null
) {
  return useSWR<PreReadDeckResponse>(
    snapshotId || (team && opponent && season)
      ? `pre-read-${snapshotId ?? `${team}-${opponent}-${season}`}`
      : null,
    () => getPreReadDeck(team ?? "", opponent ?? "", season ?? "", snapshotId ?? undefined)
  );
}

export function usePreReadSnapshots(
  team: string | null,
  opponent: string | null,
  season: string | null,
  limit = 8
) {
  return useSWR<PreReadSnapshotListResponse>(
    team && opponent && season ? `pre-read-snapshots-${team}-${opponent}-${season}-${limit}` : null,
    () => getPreReadSnapshots(team!, opponent!, season!, limit)
  );
}

export function usePreReadSnapshot(snapshotId: string | null) {
  return useSWR<PreReadSnapshotResponse>(
    snapshotId ? `pre-read-snapshot-${snapshotId}` : null,
    () => getPreReadSnapshot(snapshotId!)
  );
}

export function useWhatIfScenario(
  payload:
    | {
        team: string;
        season: string;
        scenario_type: string;
        delta: number;
        window?: number;
        opponent?: string;
        context?: Record<string, string>;
      }
    | null
) {
  return useSWR<WhatIfScenarioResponse>(
    payload
      ? `what-if-${payload.team}-${payload.season}-${payload.scenario_type}-${payload.delta}-${payload.window ?? 10}-${payload.opponent ?? "none"}-${payload.context?.source_view ?? "none"}-${payload.context?.snapshot_id ?? "none"}`
      : null,
    () => postWhatIfScenario(payload!)
  );
}

export function useStyleXRay(
  team: string | null,
  season: string | null,
  window = 10,
  opponent?: string | null
) {
  return useSWR<StyleXRayResponse>(
    team && season ? `style-xray-${team}-${season}-${window}-${opponent ?? "none"}` : null,
    () => getStyleXRay(team!, season!, window, opponent ?? undefined)
  );
}

export function usePlayTypeScoutingReport(
  team: string | null,
  opponent: string | null,
  season: string | null
) {
  return useSWR<PlayTypeScoutingReportResponse>(
    team && opponent && season ? `scouting-play-types-${team}-${opponent}-${season}` : null,
    () => getPlayTypeScoutingReport(team!, opponent!, season!)
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

import type {
  WarehouseJobSummary,
  WarehouseSeasonHealth,
  IngestionJobResponse,
} from "@/lib/types";
import {
  getWarehouseJobSummary,
  getWarehouseSeasonHealth,
  getWarehouseJobs,
} from "@/lib/api";

export function useWarehouseSeasonHealth(season: string | null) {
  return useSWR<WarehouseSeasonHealth>(
    season ? `warehouse-health-${season}` : null,
    () => getWarehouseSeasonHealth(season!)
  );
}

export function useWarehouseJobs(status?: string, season?: string) {
  return useSWR<IngestionJobResponse[]>(
    `warehouse-jobs-${status ?? "all"}${season ? `-${season}` : ""}`,
    () => getWarehouseJobs(status, season)
  );
}

export function useWarehouseJobSummary(season?: string | null) {
  return useSWR<WarehouseJobSummary>(
    `warehouse-job-summary-${season ?? "all"}`,
    () => getWarehouseJobSummary(season ?? undefined)
  );
}

export function useWarehouseReadiness(season?: string | null) {
  return useSWR<WarehouseReadinessSummary>(
    season ? `warehouse-readiness-${season}` : null,
    () => getWarehouseReadinessSummary(season!)
  );
}

// ── Game summary hook ─────────────────────────────────────────────────────────

import type { GameSummaryResponse } from "@/lib/types";
import { getGameSummary } from "@/lib/api";

export function useGameSummary(gameId: string | null) {
  return useSWR<GameSummaryResponse>(
    gameId ? `game-summary-${gameId}` : null,
    () => getGameSummary(gameId!)
  );
}

// ── Sprint 29 hooks ───────────────────────────────────────────────────────────

import type { StandingsHistoryEntry } from "@/lib/types";
import { getStandingsHistory } from "@/lib/api";

export function useStandingsHistory(season: string | null, days = 30) {
  return useSWR<StandingsHistoryEntry[]>(
    season ? `standings-history-${season}-${days}` : null,
    () => getStandingsHistory(season!, days)
  );
}

export function usePlayerZoneProfile(
  playerId: number | null,
  season: string | null,
  seasonType = "Regular Season",
  filters?: ShotLabDateRange
) {
  return useSWR<PersistedZoneProfileResponse>(
    playerId && season
      ? `zone-profile-${playerId}-${season}-${seasonType}-${filters?.startDate ?? "all"}-${filters?.endDate ?? "all"}`
      : null,
    () =>
      filters?.startDate || filters?.endDate
        ? getPersistedPlayerZoneProfileWindow(playerId!, season!, seasonType, filters)
        : getPersistedPlayerZoneProfile(playerId!, season!, seasonType)
  );
}
