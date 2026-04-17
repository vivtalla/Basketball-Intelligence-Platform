"use client";

import { useState } from "react";
import useSWR, { useSWRConfig } from "swr";
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
  ShotLabFilters,
  ShotLabPeriodBucket,
  ShotLabResultFilter,
  ShotLabShotValueFilter,
  TeamDefenseShotChartResponse,
  TeamDefenseZoneProfileResponse,
  TrendCardsResponse,
  ShotLabSnapshotPayload,
  ShotLabSnapshotResponse,
  WarehouseCompletenessSummary,
  GameVisualizationResponse,
  GameSummaryResponse,
  WarehouseJobSummary,
  WarehouseSeasonHealth,
  IngestionJobResponse,
  StandingsHistoryEntry,
  LineupImpactResponse,
  PlayTypeEVResponse,
  MatchupFlagsResponse,
  FollowThroughResponse,
  TeamSplitsResponse,
  MvpCandidateCaseResponse,
  MvpRaceResponse,
  MvpRaceOptions,
} from "@/lib/types";
import {
  getPlayerProfile,
  getPlayerCareerStats,
  getPlayerTrendReport,
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
  getWarehouseReadinessSummary,
  getTrendCards,
  postWhatIfScenario,
  getStyleXRay,
  getPlayTypeScoutingReport,
  getSituationalPlayerShotChart,
  getSituationalPlayerZoneProfile,
  refreshPlayerShotChart as postRefreshPlayerShotChart,
  getTeamDefenseShotChart,
  getTeamDefenseZoneProfile,
  refreshTeamDefenseShotChart as postRefreshTeamDefenseShotChart,
  createShotLabSnapshot as postCreateShotLabSnapshot,
  getShotLabSnapshot,
  getWarehouseCompletenessSummary,
  getGameVisualization,
  getWarehouseJobSummary,
  getWarehouseSeasonHealth,
  getWarehouseJobs,
  getGameSummary,
  getStandingsHistory,
  getLineupImpactReport,
  getPlayTypeEVReport,
  getMatchupFlagsReport,
  postFollowThroughGames,
  getTeamSplits,
  getMvpCandidateCase,
  getMvpRace,
} from "@/lib/api";

const DEFAULT_SHOT_LAB_FILTERS: ShotLabFilters = {
  startDate: null,
  endDate: null,
  periodBucket: "all",
  result: "all",
  shotValue: "all",
};

function normalizeShotLabFilters(filters?: Partial<ShotLabFilters>): ShotLabFilters {
  return {
    startDate: filters?.startDate ?? null,
    endDate: filters?.endDate ?? null,
    periodBucket: (filters?.periodBucket ?? "all") as ShotLabPeriodBucket,
    result: (filters?.result ?? "all") as ShotLabResultFilter,
    shotValue: (filters?.shotValue ?? "all") as ShotLabShotValueFilter,
  };
}

function buildShotChartKey(
  playerId: number | null,
  season: string | null,
  seasonType = "Regular Season",
  filters?: Partial<ShotLabFilters>
) {
  if (!playerId || !season) return null;
  const normalized = normalizeShotLabFilters(filters);
  return `shot-chart-${playerId}-${season}-${seasonType}-${normalized.startDate ?? "all"}-${normalized.endDate ?? "all"}-${normalized.periodBucket}-${normalized.result}-${normalized.shotValue}`;
}

function buildZoneProfileKey(
  playerId: number | null,
  season: string | null,
  seasonType = "Regular Season",
  filters?: Partial<ShotLabFilters>
) {
  if (!playerId || !season) return null;
  const normalized = normalizeShotLabFilters(filters);
  return `zone-profile-${playerId}-${season}-${seasonType}-${normalized.startDate ?? "all"}-${normalized.endDate ?? "all"}-${normalized.periodBucket}-${normalized.result}-${normalized.shotValue}`;
}

function buildTeamDefenseShotChartKey(
  teamId: number | null,
  season: string | null,
  seasonType = "Regular Season",
  filters?: Partial<ShotLabFilters>
) {
  if (!teamId || !season) return null;
  const normalized = normalizeShotLabFilters(filters);
  return `team-defense-shot-chart-${teamId}-${season}-${seasonType}-${normalized.startDate ?? "all"}-${normalized.endDate ?? "all"}-${normalized.periodBucket}-${normalized.result}-${normalized.shotValue}`;
}

function buildTeamDefenseZoneProfileKey(
  teamId: number | null,
  season: string | null,
  seasonType = "Regular Season",
  filters?: Partial<ShotLabFilters>
) {
  if (!teamId || !season) return null;
  const normalized = normalizeShotLabFilters(filters);
  return `team-defense-zone-profile-${teamId}-${season}-${seasonType}-${normalized.startDate ?? "all"}-${normalized.endDate ?? "all"}-${normalized.periodBucket}-${normalized.result}-${normalized.shotValue}`;
}

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
  filters?: Partial<ShotLabFilters>
) {
  return useSWR<PersistedShotChartResponse>(
    buildShotChartKey(playerId, season, seasonType, filters),
    () =>
      getSituationalPlayerShotChart(
        playerId,
        season,
        seasonType,
        normalizeShotLabFilters(filters)
      )
  );
}

export function useTeamDefenseShotChart(
  teamId: number | null,
  season: string | null,
  seasonType = "Regular Season",
  filters?: Partial<ShotLabFilters>
) {
  return useSWR<TeamDefenseShotChartResponse>(
    buildTeamDefenseShotChartKey(teamId, season, seasonType, filters),
    () => getTeamDefenseShotChart(teamId!, season!, seasonType, normalizeShotLabFilters(filters))
  );
}

export function useTeamDefenseZoneProfile(
  teamId: number | null,
  season: string | null,
  seasonType = "Regular Season",
  filters?: Partial<ShotLabFilters>
) {
  return useSWR<TeamDefenseZoneProfileResponse>(
    buildTeamDefenseZoneProfileKey(teamId, season, seasonType, filters),
    () => getTeamDefenseZoneProfile(teamId!, season!, seasonType, normalizeShotLabFilters(filters))
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

export function useTeamSplits(
  teamAbbreviation: string | null,
  season: string | null
) {
  return useSWR<TeamSplitsResponse>(
    teamAbbreviation && season
      ? `team-splits-${teamAbbreviation}-${season}`
      : null,
    () => getTeamSplits(teamAbbreviation!, season!)
  );
}

export function useTeamComparison(
  teamA: string | null,
  teamB: string | null,
  season: string | null,
  options?: {
    sourceType?: string | null;
    sourceId?: string | null;
    reason?: string | null;
  }
) {
  return useSWR<TeamComparisonResponse>(
    teamA && teamB && season
      ? `team-comparison-${teamA}-${teamB}-${season}-${options?.sourceType ?? "none"}-${options?.sourceId ?? "none"}-${options?.reason ?? "none"}`
      : null,
    () => getTeamComparison(teamA!, teamB!, season!, options)
  );
}

export function useTeamFocusLevers(
  teamAbbreviation: string | null,
  season: string | null,
  opponent?: string | null
) {
  return useSWR<TeamFocusLeversReport>(
    teamAbbreviation && season ? `team-focus-levers-${teamAbbreviation}-${season}-${opponent ?? "none"}` : null,
    () => getTeamFocusLevers(teamAbbreviation!, season!, opponent ?? undefined)
  );
}

export function useLineupImpactReport(
  team: string | null,
  season: string | null,
  opponent?: string | null,
  window = 10,
  minPossessions = 25
) {
  return useSWR<LineupImpactResponse>(
    team && season
      ? `lineup-impact-${team}-${season}-${opponent ?? "none"}-${window}-${minPossessions}`
      : null,
    () => getLineupImpactReport(team!, season!, opponent ?? undefined, window, minPossessions)
  );
}

export function usePlayTypeEVReport(
  team: string | null,
  season: string | null,
  opponent?: string | null,
  window = 10
) {
  return useSWR<PlayTypeEVResponse>(
    team && season ? `play-type-ev-${team}-${season}-${opponent ?? "none"}-${window}` : null,
    () => getPlayTypeEVReport(team!, season!, opponent ?? undefined, window)
  );
}

export function useMatchupFlagsReport(
  team: string | null,
  opponent: string | null,
  season: string | null
) {
  return useSWR<MatchupFlagsResponse>(
    team && opponent && season ? `matchup-flags-${team}-${opponent}-${season}` : null,
    () => getMatchupFlagsReport(team!, opponent!, season!)
  );
}

export function useFollowThroughReport(
  payload:
    | {
        source_type: string;
        source_id: string;
        team: string;
        opponent?: string;
        player_ids?: number[];
        lineup_key?: string;
        season: string;
        window?: number;
        context?: Record<string, string>;
      }
    | null
) {
  return useSWR<FollowThroughResponse>(
    payload
      ? `follow-through-${payload.source_type}-${payload.source_id}-${payload.team}-${payload.opponent ?? "none"}-${payload.season}-${payload.window ?? 10}-${(payload.player_ids ?? []).join("-")}-${payload.lineup_key ?? "none"}-${payload.context?.reason ?? "none"}`
      : null,
    () => postFollowThroughGames(payload!)
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

export function useTrendCards(
  team: string | null,
  season: string | null,
  window = 10
) {
  return useSWR<TrendCardsResponse>(
    team && season ? `trend-cards-${team}-${season}-${window}` : null,
    () => getTrendCards(team!, season!, window)
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

export function useGameSummary(gameId: string | null) {
  return useSWR<GameSummaryResponse>(
    gameId ? `game-summary-${gameId}` : null,
    () => getGameSummary(gameId!)
  );
}

export function useGameVisualization(
  gameId: string | null,
  options?: {
    shotEventId?: string | null;
    playerId?: number | null;
    period?: number | null;
    eventType?: string | null;
    query?: string | null;
    source?: string | null;
    sourceSurface?: string | null;
    sourceId?: string | null;
    sourceLabel?: string | null;
    reason?: string | null;
    claimId?: string | null;
    clipAnchorId?: string | null;
    returnTo?: string | null;
    linkageQuality?: string | null;
    focusEventId?: string | null;
    focusActionNumber?: number | null;
    focusWindow?: number | null;
  }
) {
  return useSWR<GameVisualizationResponse>(
    gameId
      ? `game-visualization-${gameId}-${options?.shotEventId ?? "none"}-${options?.playerId ?? "all"}-${options?.period ?? "all"}-${options?.eventType ?? "all"}-${options?.query ?? "none"}-${options?.source ?? "none"}-${options?.sourceSurface ?? "none"}-${options?.sourceId ?? "none"}-${options?.claimId ?? "none"}-${options?.clipAnchorId ?? "none"}-${options?.focusEventId ?? "none"}-${options?.focusActionNumber ?? "none"}-${options?.linkageQuality ?? "none"}-${options?.focusWindow ?? "none"}`
      : null,
    () => getGameVisualization(gameId!, options)
  );
}

export function useWarehouseCompletenessSummary(
  season: string | null,
  seasonType = "Regular Season"
) {
  return useSWR<WarehouseCompletenessSummary>(
    season ? `warehouse-completeness-${season}-${seasonType}` : null,
    () => getWarehouseCompletenessSummary(season!, seasonType)
  );
}

export function useShotLabSnapshot(snapshotId: string | null) {
  return useSWR<ShotLabSnapshotResponse>(
    snapshotId ? `shot-lab-snapshot-${snapshotId}` : null,
    () => getShotLabSnapshot(snapshotId!)
  );
}

export function useCreateShotLabSnapshot() {
  const [isSaving, setIsSaving] = useState(false);
  async function createSnapshot(payload: ShotLabSnapshotPayload) {
    setIsSaving(true);
    try {
      return await postCreateShotLabSnapshot(payload);
    } finally {
      setIsSaving(false);
    }
  }
  return { createSnapshot, isSaving };
}

// ── Sprint 29 hooks ───────────────────────────────────────────────────────────

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
  filters?: Partial<ShotLabFilters>
) {
  return useSWR<PersistedZoneProfileResponse>(
    buildZoneProfileKey(playerId, season, seasonType, filters),
    () =>
      getSituationalPlayerZoneProfile(
        playerId!,
        season!,
        seasonType,
        normalizeShotLabFilters(filters)
      )
  );
}

export function useShotChartRefresh(
  playerId: number | null,
  season: string | null,
  seasonType = "Regular Season",
  filters?: Partial<ShotLabFilters>
) {
  const { mutate, cache } = useSWRConfig();
  const [isRefreshing, setIsRefreshing] = useState(false);

  async function refresh(force = true) {
    if (!playerId || !season || isRefreshing) return null;

    const activeFilters = normalizeShotLabFilters(filters);
    const baseFilters = DEFAULT_SHOT_LAB_FILTERS;
    const activeShotKey = buildShotChartKey(playerId, season, seasonType, activeFilters);
    const activeZoneKey = buildZoneProfileKey(playerId, season, seasonType, activeFilters);
    const baseShotKey = buildShotChartKey(playerId, season, seasonType, baseFilters);
    const baseZoneKey = buildZoneProfileKey(playerId, season, seasonType, baseFilters);
    const previousSyncedAt =
      (activeShotKey ? (cache.get(activeShotKey) as PersistedShotChartResponse | undefined)?.last_synced_at : null) ??
      (baseShotKey ? (cache.get(baseShotKey) as PersistedShotChartResponse | undefined)?.last_synced_at : null) ??
      null;

    setIsRefreshing(true);
    try {
      const queueResult = await postRefreshPlayerShotChart(playerId, season, seasonType, force);
      const pollStart = Date.now();

      while (Date.now() - pollStart <= 60000) {
        const freshBaseShot = baseShotKey ? await mutate(baseShotKey) : null;
        const freshBaseZone = baseZoneKey ? await mutate(baseZoneKey) : null;
        const freshActiveShot =
          activeShotKey && activeShotKey !== baseShotKey ? await mutate(activeShotKey) : freshBaseShot;
        const freshActiveZone =
          activeZoneKey && activeZoneKey !== baseZoneKey ? await mutate(activeZoneKey) : freshBaseZone;

        const latestShot = freshActiveShot ?? freshBaseShot;
        const latestZone = freshActiveZone ?? freshBaseZone;
        const syncedChanged =
          latestShot?.last_synced_at != null && latestShot.last_synced_at !== previousSyncedAt;
        const noLongerBlocked =
          latestShot?.data_status === "ready" &&
          latestZone?.data_status === "ready";

        if (syncedChanged || noLongerBlocked) {
          return queueResult;
        }

        await new Promise((resolve) => window.setTimeout(resolve, 5000));
      }

      return queueResult;
    } finally {
      setIsRefreshing(false);
    }
  }

  return { refresh, isRefreshing };
}

export function useTeamDefenseShotChartRefresh(
  teamId: number | null,
  season: string | null,
  seasonType = "Regular Season",
  filters?: Partial<ShotLabFilters>
) {
  const { mutate, cache } = useSWRConfig();
  const [isRefreshing, setIsRefreshing] = useState(false);

  async function refresh(force = true) {
    if (!teamId || !season || isRefreshing) return null;

    const activeFilters = normalizeShotLabFilters(filters);
    const baseFilters = DEFAULT_SHOT_LAB_FILTERS;
    const activeShotKey = buildTeamDefenseShotChartKey(teamId, season, seasonType, activeFilters);
    const activeZoneKey = buildTeamDefenseZoneProfileKey(teamId, season, seasonType, activeFilters);
    const baseShotKey = buildTeamDefenseShotChartKey(teamId, season, seasonType, baseFilters);
    const baseZoneKey = buildTeamDefenseZoneProfileKey(teamId, season, seasonType, baseFilters);
    const previousSyncedAt =
      (activeShotKey ? (cache.get(activeShotKey) as TeamDefenseShotChartResponse | undefined)?.last_synced_at : null) ??
      (baseShotKey ? (cache.get(baseShotKey) as TeamDefenseShotChartResponse | undefined)?.last_synced_at : null) ??
      null;

    setIsRefreshing(true);
    try {
      const queueResult = await postRefreshTeamDefenseShotChart(teamId, season, seasonType, force);
      const pollStart = Date.now();

      while (Date.now() - pollStart <= 60000) {
        const freshBaseShot = baseShotKey ? await mutate(baseShotKey) : null;
        const freshBaseZone = baseZoneKey ? await mutate(baseZoneKey) : null;
        const freshActiveShot =
          activeShotKey && activeShotKey !== baseShotKey ? await mutate(activeShotKey) : freshBaseShot;
        const freshActiveZone =
          activeZoneKey && activeZoneKey !== baseZoneKey ? await mutate(activeZoneKey) : freshBaseZone;

        const latestShot = freshActiveShot ?? freshBaseShot;
        const latestZone = freshActiveZone ?? freshBaseZone;
        const syncedChanged =
          latestShot?.last_synced_at != null && latestShot.last_synced_at !== previousSyncedAt;
        const noLongerBlocked =
          latestShot?.data_status === "ready" &&
          latestZone?.data_status === "ready";

        if (syncedChanged || noLongerBlocked) {
          return queueResult;
        }

        await new Promise((resolve) => window.setTimeout(resolve, 5000));
      }

      return queueResult;
    } finally {
      setIsRefreshing(false);
    }
  }

  return { refresh, isRefreshing };
}

export function useMvpRace(season: string | null, options?: MvpRaceOptions) {
  const key = season
    ? ["mvp-race", season, options?.top ?? 10, options?.minGp ?? 20, options?.position ?? "all"]
    : null;
  return useSWR<MvpRaceResponse>(
    key,
    () => getMvpRace(season!, options)
  );
}

export function useMvpCandidateCase(
  playerId: number | null,
  season: string | null,
  options?: Pick<MvpRaceOptions, "minGp" | "position">
) {
  const key = playerId && season
    ? ["mvp-candidate-case", playerId, season, options?.minGp ?? 20, options?.position ?? "all"]
    : null;
  return useSWR<MvpCandidateCaseResponse>(
    key,
    () => getMvpCandidateCase(playerId!, season!, options)
  );
}
