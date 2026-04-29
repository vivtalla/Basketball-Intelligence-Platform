import type {
  PlayerSearchResult,
  ShotChartResponse,
  LeaderboardResponse,
  QueryAskRequest,
  QueryAskResponse,
  QueryExample,
  QueryMetricMetadata,
  TeamSummary,
  TeamRosterResponse,
  TeamAnalytics,
  TeamIntelligence,
  TeamPrepQueueResponse,
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
  PbpSyncResult,
  GameDetailResponse,
  SimilarityResponse,
  LeagueContext,
  CareerLeaderboardResponse,
  InjuryEntry,
  InjuryReportResponse,
  StandingsHistoryEntry,
  ZoneProfileResponse,
  TrajectorySeriesResponse,
  LineupContextResponse,
  OpportunityResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function searchPlayers(
  query: string
): Promise<PlayerSearchResult[]> {
  return fetchApi<PlayerSearchResult[]>(
    `/api/players/search?q=${encodeURIComponent(query)}`
  );
}

export async function getPlayerProfile(
  playerId: number
): Promise<import("./types").DbFirstPlayerProfile> {
  return fetchApi<import("./types").DbFirstPlayerProfile>(`/api/players/${playerId}`);
}

export async function getPlayerGravity(
  playerId: number,
  season: string,
  seasonType = "Regular Season"
): Promise<import("./types").MvpGravityProfile> {
  const params = new URLSearchParams({ season, season_type: seasonType });
  return fetchApi<import("./types").MvpGravityProfile>(
    `/api/players/${encodeURIComponent(playerId)}/gravity?${params.toString()}`
  );
}

export async function getPlayerCareerStats(
  playerId: number
): Promise<import("./types").DbFirstCareerStatsResponse> {
  return fetchApi<import("./types").DbFirstCareerStatsResponse>(`/api/stats/${playerId}/career`);
}

export async function getAvailableSeasons(): Promise<string[]> {
  return fetchApi<string[]>("/api/leaderboards/seasons");
}

export async function getTeams(): Promise<TeamSummary[]> {
  return fetchApi<TeamSummary[]>("/api/teams");
}

export async function getTeamRoster(
  teamAbbreviation: string
): Promise<TeamRosterResponse> {
  return fetchApi<TeamRosterResponse>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}`
  );
}

export async function getLeaderboard(
  stat: string,
  season: string,
  seasonType = "Regular Season",
  limit = 25,
  team?: string
): Promise<LeaderboardResponse> {
  const params = new URLSearchParams({
    stat,
    season,
    season_type: seasonType,
    limit: String(limit),
  });
  if (team) params.set("team", team);
  return fetchApi<LeaderboardResponse>(`/api/leaderboards?${params.toString()}`);
}

export async function askCourtVue(
  payload: QueryAskRequest
): Promise<QueryAskResponse> {
  return fetchApi<QueryAskResponse>("/api/query/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getQueryExamples(): Promise<QueryExample[]> {
  return fetchApi<QueryExample[]>("/api/query/examples");
}

export async function getQueryMetrics(): Promise<QueryMetricMetadata[]> {
  return fetchApi<QueryMetricMetadata[]>("/api/query/metrics");
}

export async function getPlayerPercentiles(
  playerId: number,
  season: string
): Promise<PercentileResult> {
  return fetchApi<PercentileResult>(
    `/api/stats/${playerId}/percentiles?season=${encodeURIComponent(season)}`
  );
}

export async function getPlayerOnOff(
  playerId: number,
  season: string
): Promise<OnOffStats> {
  return fetchApi<OnOffStats>(
    `/api/advanced/${playerId}/on-off?season=${encodeURIComponent(season)}`
  );
}

export async function getPlayerClutch(
  playerId: number,
  season: string
): Promise<ClutchStats> {
  return fetchApi<ClutchStats>(
    `/api/advanced/${playerId}/clutch?season=${encodeURIComponent(season)}`
  );
}

export async function getPlayerPbpCoverage(
  playerId: number,
  season: string
): Promise<PbpCoverage> {
  return fetchApi<PbpCoverage>(
    `/api/advanced/${playerId}/pbp-coverage?season=${encodeURIComponent(season)}`
  );
}

export async function getPbpCoverageDashboard(
  season: string
): Promise<PbpCoverageDashboard> {
  return fetchApi<PbpCoverageDashboard>(
    `/api/advanced/pbp-dashboard?season=${encodeURIComponent(season)}`
  );
}

export async function getPbpCoverageSeasons(): Promise<PbpCoverageSeasonSummary[]> {
  return fetchApi<PbpCoverageSeasonSummary[]>("/api/advanced/pbp-dashboard-seasons");
}

export async function getLineups(
  season: string,
  teamId?: number,
  minMinutes = 5,
  limit = 25
): Promise<LineupsResult> {
  const params = new URLSearchParams({
    season,
    min_minutes: String(minMinutes),
    limit: String(limit),
  });
  if (teamId != null) params.set("team_id", String(teamId));

  return fetchApi<LineupsResult>(`/api/advanced/lineups?${params.toString()}`);
}

export async function getOnOffLeaderboard(
  season: string,
  minMinutes = 200,
  limit = 25
): Promise<OnOffLeaderboardResult> {
  const params = new URLSearchParams({
    season,
    min_minutes: String(minMinutes),
    limit: String(limit),
  });
  return fetchApi<OnOffLeaderboardResult>(
    `/api/advanced/on-off-leaderboard?${params.toString()}`
  );
}

export async function getPlayerShotChart(
  playerId: number,
  season: string,
  seasonType = "Regular Season"
): Promise<ShotChartResponse> {
  return fetchApi<ShotChartResponse>(
    `/api/shotchart/${playerId}?season=${encodeURIComponent(season)}&season_type=${encodeURIComponent(seasonType)}`
  );
}

export async function syncPlayerPbp(
  playerId: number,
  season: string,
  forceRefresh = false
): Promise<PbpSyncResult> {
  return fetchApi<PbpSyncResult>(
    `/api/advanced/${playerId}/sync-pbp?season=${encodeURIComponent(season)}&force_refresh=${forceRefresh}`,
    { method: "POST" }
  );
}

export async function syncSeasonPbp(
  season: string,
  forceRefresh = false
): Promise<PbpSyncResult> {
  return fetchApi<PbpSyncResult>(
    `/api/advanced/sync-season?season=${encodeURIComponent(season)}&force_refresh=${forceRefresh}`,
    { method: "POST" }
  );
}

export async function getPlayerGameLogs(
  playerId: number,
  season: string,
  seasonType = "Regular Season"
): Promise<import("./types").DbFirstGameLogResponse> {
  return fetchApi<import("./types").DbFirstGameLogResponse>(
    `/api/gamelogs/${playerId}?season=${encodeURIComponent(season)}&season_type=${encodeURIComponent(seasonType)}`
  );
}

export async function getGameDetail(gameId: string): Promise<GameDetailResponse> {
  return fetchApi<GameDetailResponse>(`/api/games/${encodeURIComponent(gameId)}`);
}

export async function getBreakouts(
  season: string,
  minGp = 20,
  limit = 25
): Promise<BreakoutsResponse> {
  return fetchApi<BreakoutsResponse>(
    `/api/insights/breakouts?season=${encodeURIComponent(season)}&min_gp=${minGp}&limit=${limit}`
  );
}

export async function getStandings(season: string): Promise<StandingsEntry[]> {
  return fetchApi<StandingsEntry[]>(
    `/api/standings?season=${encodeURIComponent(season)}`
  );
}

export async function getTeamAnalytics(
  teamAbbreviation: string,
  season: string
): Promise<TeamAnalytics> {
  return fetchApi<TeamAnalytics>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}/analytics?season=${encodeURIComponent(season)}`
  );
}

export async function getTeamIntelligence(
  teamAbbreviation: string,
  season: string
): Promise<TeamIntelligence> {
  return fetchApi<TeamIntelligence>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}/intelligence?season=${encodeURIComponent(season)}`
  );
}

export async function getTeamPrepQueue(
  teamAbbreviation: string,
  season: string,
  days = 10
): Promise<TeamPrepQueueResponse> {
  return fetchApi<TeamPrepQueueResponse>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}/prep-queue?season=${encodeURIComponent(season)}&days=${days}`
  );
}

export async function getSimilarPlayers(
  playerId: number,
  season: string,
  n = 8,
  crossEra = true
): Promise<SimilarityResponse> {
  return fetchApi<SimilarityResponse>(
    `/api/similarity/${playerId}?season=${encodeURIComponent(season)}&n=${n}&cross_era=${crossEra}`
  );
}

export async function getLeagueContext(
  season: string,
  position?: string
): Promise<LeagueContext> {
  const params = new URLSearchParams({ season });
  if (position) params.set("position", position);
  return fetchApi<LeagueContext>(`/api/stats/context?${params.toString()}`);
}

export async function getCareerLeaderboard(
  stat: string,
  minGp = 15,
  limit = 25
): Promise<CareerLeaderboardResponse> {
  const params = new URLSearchParams({ stat, min_gp: String(minGp), limit: String(limit) });
  return fetchApi<CareerLeaderboardResponse>(`/api/leaderboards/career?${params.toString()}`);
}

export async function getLeaderboardTeams(season: string): Promise<string[]> {
  return fetchApi<string[]>(`/api/leaderboards/teams?season=${encodeURIComponent(season)}`);
}

// ── Warehouse pipeline API ────────────────────────────────────────────────────

import type { WarehouseSeasonHealth, IngestionJobResponse } from "./types";

export async function getWarehouseSeasonHealth(season: string): Promise<WarehouseSeasonHealth> {
  return fetchApi<WarehouseSeasonHealth>(`/api/warehouse/health/${encodeURIComponent(season)}`);
}

export async function getWarehouseJobs(
  status?: string,
  season?: string,
  limit = 50
): Promise<IngestionJobResponse[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (status) params.set("status", status);
  if (season) params.set("season", season);
  return fetchApi<IngestionJobResponse[]>(`/api/warehouse/jobs?${params.toString()}`);
}

export async function queueSeasonBackfill(season: string): Promise<{ queued: number }> {
  return fetchApi<{ queued: number }>(
    `/api/warehouse/queue/season-backfill?season=${encodeURIComponent(season)}`,
    { method: "POST" }
  );
}

export async function queueCurrentSeason(season: string): Promise<{ queued: number }> {
  return fetchApi<{ queued: number }>(
    `/api/warehouse/queue/current-season?season=${encodeURIComponent(season)}`,
    { method: "POST" }
  );
}

export async function queueMvpSnapshot(
  season: string,
  dateKey?: string
): Promise<import("./types").QueueResponse> {
  const params = new URLSearchParams({ season });
  if (dateKey) params.set("date_key", dateKey);
  return fetchApi<import("./types").QueueResponse>(
    `/api/warehouse/queue/mvp-snapshot?${params.toString()}`,
    { method: "POST" }
  );
}

export async function runNextWarehouseJob(
  season?: string
): Promise<{ status: string; result?: Record<string, unknown> }> {
  const params = season ? `?season=${encodeURIComponent(season)}` : "";
  return fetchApi<{ status: string; result?: Record<string, unknown> }>(
    `/api/warehouse/run-next${params}`,
    { method: "POST" }
  );
}

export async function retryFailedJobs(season: string): Promise<{ queued: number }> {
  return fetchApi<{ queued: number }>(
    `/api/warehouse/retry-failed?season=${encodeURIComponent(season)}`,
    { method: "POST" }
  );
}

export async function getWarehouseJobSummary(
  season?: string
): Promise<import("./types").WarehouseJobSummary> {
  const params = season ? `?season=${encodeURIComponent(season)}` : "";
  return fetchApi<import("./types").WarehouseJobSummary>(
    `/api/warehouse/jobs/summary${params}`
  );
}

export async function resetStaleWarehouseJobs(
  season?: string
): Promise<{ queued: number }> {
  const params = season ? `?season=${encodeURIComponent(season)}` : "";
  return fetchApi<{ queued: number }>(
    `/api/warehouse/reset-stale${params}`,
    { method: "POST" }
  );
}

export async function getGameSummary(
  gameId: string
): Promise<import("./types").GameSummaryResponse> {
  return fetchApi<import("./types").GameSummaryResponse>(
    `/api/games/${encodeURIComponent(gameId)}/summary`
  );
}

export async function getTeamRotationReport(
  teamAbbreviation: string,
  season: string
): Promise<import("./types").TeamRotationReport> {
  return fetchApi<import("./types").TeamRotationReport>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}/rotation-report?season=${encodeURIComponent(season)}`
  );
}

export async function getPlayerTrendReport(
  playerId: number,
  season: string
): Promise<import("./types").PlayerTrendReport> {
  return fetchApi<import("./types").PlayerTrendReport>(
    `/api/players/${playerId}/trend-report?season=${encodeURIComponent(season)}`
  );
}

export async function postCustomMetric(
  config: import("./types").CustomMetricConfig
): Promise<import("./types").CustomMetricResponse> {
  return fetchApi<import("./types").CustomMetricResponse>(
    `/api/leaderboards/custom-metric`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    }
  );
}

export async function getTrajectoryReport(
  season: string,
  lastNGames: number,
  playerPool: "all" | "position_filter" | "team_filter",
  minMinutesPerGame: number,
  teamAbbreviation?: string,
  position?: string
): Promise<import("./types").TrajectoryResponse> {
  const params = new URLSearchParams({
    season,
    last_n_games: String(lastNGames),
    player_pool: playerPool,
    min_minutes_per_game: String(minMinutesPerGame),
  });
  if (teamAbbreviation) params.set("team_abbreviation", teamAbbreviation);
  if (position) params.set("position", position);
  return fetchApi<import("./types").TrajectoryResponse>(
    `/api/insights/trajectory?${params.toString()}`
  );
}

export async function postMetricReport(
  config: import("./types").CustomMetricConfig
): Promise<import("./types").CourtVueMetricResponse> {
  return fetchApi<import("./types").CourtVueMetricResponse>(
    `/api/metrics/custom`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    }
  );
}

export async function getTeamComparison(
  teamA: string,
  teamB: string,
  season: string,
  options?: {
    sourceType?: string | null;
    sourceId?: string | null;
    reason?: string | null;
  }
): Promise<import("./types").TeamComparisonResponse> {
  const params = new URLSearchParams({
    team_a: teamA,
    team_b: teamB,
    season,
  });
  if (options?.sourceType) params.set("source_type", options.sourceType);
  if (options?.sourceId) params.set("source_id", options.sourceId);
  if (options?.reason) params.set("reason", options.reason);
  return fetchApi<import("./types").TeamComparisonResponse>(
    `/api/compare/teams?${params.toString()}`
  );
}

export async function getTeamFocusLevers(
  teamAbbreviation: string,
  season: string,
  opponent?: string | null
): Promise<import("./types").TeamFocusLeversReport> {
  const params = new URLSearchParams({ season });
  if (opponent) params.set("opponent", opponent);
  return fetchApi<import("./types").TeamFocusLeversReport>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}/focus-levers?${params.toString()}`
  );
}

export async function getPreReadDeck(
  team: string,
  opponent: string,
  season: string,
  snapshotId?: string
): Promise<import("./types").PreReadDeckResponse> {
  const params = new URLSearchParams();
  if (snapshotId) {
    params.set("snapshot_id", snapshotId);
  } else {
    params.set("team", team);
    params.set("opponent", opponent);
    params.set("season", season);
  }
  return fetchApi<import("./types").PreReadDeckResponse>(
    `/api/pre-read?${params.toString()}`
  );
}

export async function createPreReadSnapshot(payload: {
  team: string;
  opponent: string;
  season: string;
  game_id?: string;
  source_view?: string;
  source_snapshot_id?: string;
  context?: Record<string, string>;
}): Promise<import("./types").PreReadSnapshotResponse> {
  return fetchApi<import("./types").PreReadSnapshotResponse>(`/api/pre-read/snapshots`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getPreReadSnapshots(
  team?: string,
  opponent?: string,
  season?: string,
  limit = 10
): Promise<import("./types").PreReadSnapshotListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (team) params.set("team", team);
  if (opponent) params.set("opponent", opponent);
  if (season) params.set("season", season);
  return fetchApi<import("./types").PreReadSnapshotListResponse>(
    `/api/pre-read/snapshots?${params.toString()}`
  );
}

export async function getPreReadSnapshot(
  snapshotId: string
): Promise<import("./types").PreReadSnapshotResponse> {
  return fetchApi<import("./types").PreReadSnapshotResponse>(
    `/api/pre-read/snapshots/${encodeURIComponent(snapshotId)}`
  );
}

export async function getLineupImpactReport(
  team: string,
  season: string,
  opponent?: string,
  window = 10,
  minPossessions = 25
): Promise<import("./types").LineupImpactResponse> {
  const params = new URLSearchParams({
    team,
    season,
    window: String(window),
    min_possessions: String(minPossessions),
  });
  if (opponent) params.set("opponent", opponent);
  return fetchApi<import("./types").LineupImpactResponse>(
    `/api/decision/lineup-impact?${params.toString()}`
  );
}

export async function getPlayTypeEVReport(
  team: string,
  season: string,
  opponent?: string,
  window = 10
): Promise<import("./types").PlayTypeEVResponse> {
  const params = new URLSearchParams({
    team,
    season,
    window: String(window),
  });
  if (opponent) params.set("opponent", opponent);
  return fetchApi<import("./types").PlayTypeEVResponse>(
    `/api/decision/play-type-ev?${params.toString()}`
  );
}

export async function getMatchupFlagsReport(
  team: string,
  opponent: string,
  season: string
): Promise<import("./types").MatchupFlagsResponse> {
  const params = new URLSearchParams({
    team,
    opponent,
    season,
  });
  return fetchApi<import("./types").MatchupFlagsResponse>(
    `/api/decision/matchup-flags?${params.toString()}`
  );
}

export async function postFollowThroughGames(
  payload: Record<string, unknown>
): Promise<import("./types").FollowThroughResponse> {
  return fetchApi<import("./types").FollowThroughResponse>(
    `/api/follow-through/games`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function getTeamStyleProfile(
  teamAbbreviation: string,
  season: string,
  window = 10,
  opponent?: string
): Promise<import("./types").TeamStyleProfileResponse> {
  const params = new URLSearchParams({
    season,
    window: String(window),
  });
  if (opponent) params.set("opponent", opponent);
  return fetchApi<import("./types").TeamStyleProfileResponse>(
    `/api/styles/teams/${encodeURIComponent(teamAbbreviation)}?${params.toString()}`
  );
}

export async function getStyleXRay(
  team: string,
  season: string,
  window = 10,
  opponent?: string
): Promise<import("./types").StyleXRayResponse> {
  const params = new URLSearchParams({
    team,
    season,
    window: String(window),
  });
  if (opponent) params.set("opponent", opponent);
  return fetchApi<import("./types").StyleXRayResponse>(
    `/api/styles/xray?${params.toString()}`
  );
}

export async function postWhatIfScenario(
  payload: {
    team: string;
    season: string;
    scenario_type: string;
    delta: number;
    window?: number;
    opponent?: string;
    context?: Record<string, string>;
  }
): Promise<import("./types").WhatIfScenarioResponse> {
  return fetchApi<import("./types").WhatIfScenarioResponse>(
    `/api/scenarios/what-if`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function getTrendCards(
  team: string,
  season: string,
  window = 10,
  playerId?: number | null,
  signal?: string | null
): Promise<import("./types").TrendCardsResponse> {
  const params = new URLSearchParams({
    team,
    season,
    window: String(window),
  });
  if (playerId != null) params.set("player_id", String(playerId));
  if (signal) params.set("signal", signal);
  return fetchApi<import("./types").TrendCardsResponse>(
    `/api/trends/cards?${params.toString()}`
  );
}

export async function getPlayTypeScoutingReport(
  team: string,
  opponent: string,
  season: string
): Promise<import("./types").PlayTypeScoutingReportResponse> {
  const params = new URLSearchParams({
    team,
    opponent,
    season,
  });
  return fetchApi<import("./types").PlayTypeScoutingReportResponse>(
    `/api/scouting/play-types?${params.toString()}`
  );
}

export async function postScoutingClipExport(payload: {
  team: string;
  opponent: string;
  season: string;
  claim_ids?: string[];
  clip_anchor_ids?: string[];
  return_to?: string;
}): Promise<import("./types").ScoutingClipExportResponse> {
  return fetchApi<import("./types").ScoutingClipExportResponse>(
    `/api/scouting/clip-export`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function getLineupComparison(
  team: string,
  lineupA: string,
  lineupB: string,
  season: string
): Promise<import("./types").LineupComparisonResponse> {
  const params = new URLSearchParams({
    team,
    lineup_a: lineupA,
    lineup_b: lineupB,
    season,
  });
  return fetchApi<import("./types").LineupComparisonResponse>(
    `/api/compare/lineups?${params.toString()}`
  );
}

export async function getStyleComparison(
  teamA: string,
  teamB: string,
  season: string,
  window = 10
): Promise<import("./types").StyleComparisonResponse> {
  const params = new URLSearchParams({
    team_a: teamA,
    team_b: teamB,
    season,
    window: String(window),
  });
  return fetchApi<import("./types").StyleComparisonResponse>(
    `/api/compare/styles?${params.toString()}`
  );
}

// Sprint 26 — Injuries

export async function getCurrentInjuries(
  season = "2024-25"
): Promise<InjuryReportResponse> {
  return fetchApi<InjuryReportResponse>(
    `/api/injuries/current?season=${encodeURIComponent(season)}`
  );
}

export async function getPlayerInjuries(
  playerId: number,
  season?: string
): Promise<InjuryEntry[]> {
  const params = new URLSearchParams();
  if (season) params.set("season", season);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return fetchApi<InjuryEntry[]>(`/api/injuries/player/${playerId}${qs}`);
}

export async function getTeamAvailability(
  teamAbbreviation: string,
  season: string
): Promise<import("./types").TeamAvailabilityResponse> {
  return fetchApi<import("./types").TeamAvailabilityResponse>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}/availability?season=${encodeURIComponent(season)}`
  );
}

export async function getUpcomingSchedule(
  season: string,
  days = 7,
  team?: string
): Promise<import("./types").UpcomingScheduleGame[]> {
  const params = new URLSearchParams({
    season,
    days: String(days),
  });
  if (team) params.set("team", team);
  return fetchApi<import("./types").UpcomingScheduleGame[]>(
    `/api/schedule/upcoming?${params.toString()}`
  );
}

// Sprint 28 — Compare Availability + Unresolved Injury Ops

export async function fetchCompareAvailability(
  playerAId: number,
  playerBId: number,
  season = "2024-25"
): Promise<import("./types").CompareAvailabilityResponse> {
  const params = new URLSearchParams({
    player_a: String(playerAId),
    player_b: String(playerBId),
    season,
  });
  return fetchApi<import("./types").CompareAvailabilityResponse>(
    `/api/compare/player-availability?${params.toString()}`
  );
}

export async function getUnresolvedInjuries(
  season = "2024-25"
): Promise<import("./types").InjurySyncUnresolvedEntry[]> {
  return fetchApi<import("./types").InjurySyncUnresolvedEntry[]>(
    `/api/injuries/unresolved?season=${encodeURIComponent(season)}`
  );
}

export async function resolveUnresolvedInjury(
  rowId: number,
  playerId: number
): Promise<{ status: string; row_id: number; player_id: number; player_name: string; report_date: string }> {
  return fetchApi(`/api/injuries/unresolved/${rowId}/resolve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ player_id: playerId }),
  });
}

export async function dismissUnresolvedInjury(
  rowId: number
): Promise<{ status: string; row_id: number }> {
  return fetchApi(`/api/injuries/unresolved/${rowId}`, { method: "DELETE" });
}

// Sprint 29 — Standings history
export async function getStandingsHistory(
  season: string,
  days = 30
): Promise<StandingsHistoryEntry[]> {
  return fetchApi<StandingsHistoryEntry[]>(
    `/api/standings/history?season=${encodeURIComponent(season)}&days=${days}`
  );
}

// Sprint 29 — Shot zone analytics
export async function getPlayerZoneProfile(
  playerId: number,
  season: string,
  seasonType = "Regular Season"
): Promise<ZoneProfileResponse> {
  return fetchApi<ZoneProfileResponse>(
    `/api/shotchart/${playerId}/zones?season=${encodeURIComponent(season)}&season_type=${encodeURIComponent(seasonType)}`
  );
}

export async function getPersistedPlayerShotChart(
  playerId: number,
  season: string,
  seasonType = "Regular Season"
): Promise<import("./types").PersistedShotChartResponse> {
  return fetchApi<import("./types").PersistedShotChartResponse>(
    `/api/shotchart/${playerId}?season=${encodeURIComponent(season)}&season_type=${encodeURIComponent(seasonType)}`
  );
}

export async function getPersistedPlayerZoneProfile(
  playerId: number,
  season: string,
  seasonType = "Regular Season"
): Promise<import("./types").PersistedZoneProfileResponse> {
  return fetchApi<import("./types").PersistedZoneProfileResponse>(
    `/api/shotchart/${playerId}/zones?season=${encodeURIComponent(season)}&season_type=${encodeURIComponent(seasonType)}`
  );
}

export async function getWarehouseReadinessSummary(
  season: string
): Promise<import("./types").WarehouseReadinessSummary> {
  return fetchApi<import("./types").WarehouseReadinessSummary>(
    `/api/warehouse/readiness/${encodeURIComponent(season)}`
  );
}

// Sprint 35 — Shot lab expansion

export interface ShotLabFilters {
  startDate?: string | null;
  endDate?: string | null;
}

function buildShotLabQuery(
  playerId: number,
  season: string,
  seasonType: string,
  filters?: ShotLabFilters,
  suffix = ""
): string {
  const params = new URLSearchParams({
    season,
    season_type: seasonType,
  });
  if (filters?.startDate) {
    params.set("start_date", filters.startDate);
  }
  if (filters?.endDate) {
    params.set("end_date", filters.endDate);
  }
  return `/api/shotchart/${playerId}${suffix}?${params.toString()}`;
}

export async function getPersistedPlayerShotChartWindow(
  playerId: number,
  season: string,
  seasonType = "Regular Season",
  filters?: ShotLabFilters
): Promise<import("./types").PersistedShotChartResponse> {
  return fetchApi<import("./types").PersistedShotChartResponse>(
    buildShotLabQuery(playerId, season, seasonType, filters)
  );
}

export async function getPersistedPlayerZoneProfileWindow(
  playerId: number,
  season: string,
  seasonType = "Regular Season",
  filters?: ShotLabFilters
): Promise<import("./types").PersistedZoneProfileResponse> {
  return fetchApi<import("./types").PersistedZoneProfileResponse>(
    buildShotLabQuery(playerId, season, seasonType, filters, "/zones")
  );
}

// Sprint 37 — Situational shot intelligence

function buildSituationalShotLabQuery(
  playerId: number,
  season: string,
  seasonType: string,
  filters?: import("./types").ShotLabFilters,
  suffix = ""
): string {
  const params = new URLSearchParams({
    season,
    season_type: seasonType,
    period_bucket: filters?.periodBucket ?? "all",
    result: filters?.result ?? "all",
    shot_value: filters?.shotValue ?? "all",
  });
  if (filters?.startDate) {
    params.set("start_date", filters.startDate);
  }
  if (filters?.endDate) {
    params.set("end_date", filters.endDate);
  }
  return `/api/shotchart/${playerId}${suffix}?${params.toString()}`;
}

export async function getSituationalPlayerShotChart(
  playerId: number,
  season: string,
  seasonType = "Regular Season",
  filters?: import("./types").ShotLabFilters
): Promise<import("./types").PersistedShotChartResponse> {
  return fetchApi<import("./types").PersistedShotChartResponse>(
    buildSituationalShotLabQuery(playerId, season, seasonType, filters)
  );
}

export async function getSituationalPlayerZoneProfile(
  playerId: number,
  season: string,
  seasonType = "Regular Season",
  filters?: import("./types").ShotLabFilters
): Promise<import("./types").PersistedZoneProfileResponse> {
  return fetchApi<import("./types").PersistedZoneProfileResponse>(
    buildSituationalShotLabQuery(playerId, season, seasonType, filters, "/zones")
  );
}

export async function refreshPlayerShotChart(
  playerId: number,
  season: string,
  seasonType = "Regular Season",
  force = false
): Promise<import("./types").QueueResponse> {
  const params = new URLSearchParams({
    season,
    season_type: seasonType,
    force: String(force),
  });
  return fetchApi<import("./types").QueueResponse>(
    `/api/shotchart/${playerId}/refresh?${params.toString()}`,
    { method: "POST" }
  );
}

export async function getTeamDefenseShotChart(
  teamId: number,
  season: string,
  seasonType = "Regular Season",
  filters?: import("./types").ShotLabFilters
): Promise<import("./types").TeamDefenseShotChartResponse> {
  const params = new URLSearchParams({
    season,
    season_type: seasonType,
    period_bucket: filters?.periodBucket ?? "all",
    result: filters?.result ?? "all",
    shot_value: filters?.shotValue ?? "all",
  });
  if (filters?.startDate) params.set("start_date", filters.startDate);
  if (filters?.endDate) params.set("end_date", filters.endDate);
  return fetchApi<import("./types").TeamDefenseShotChartResponse>(
    `/api/shotchart/team-defense/${teamId}?${params.toString()}`
  );
}

export async function getTeamDefenseZoneProfile(
  teamId: number,
  season: string,
  seasonType = "Regular Season",
  filters?: import("./types").ShotLabFilters
): Promise<import("./types").TeamDefenseZoneProfileResponse> {
  const params = new URLSearchParams({
    season,
    season_type: seasonType,
    period_bucket: filters?.periodBucket ?? "all",
    result: filters?.result ?? "all",
    shot_value: filters?.shotValue ?? "all",
  });
  if (filters?.startDate) params.set("start_date", filters.startDate);
  if (filters?.endDate) params.set("end_date", filters.endDate);
  return fetchApi<import("./types").TeamDefenseZoneProfileResponse>(
    `/api/shotchart/team-defense/${teamId}/zones?${params.toString()}`
  );
}

export async function getPlayerShotQuality(
  playerId: number,
  season: string,
  seasonType = "Regular Season",
  filters?: import("./types").ShotLabFilters
): Promise<import("./types").ShotQualityResponse> {
  return fetchApi<import("./types").ShotQualityResponse>(
    buildSituationalShotLabQuery(playerId, season, seasonType, filters, "/quality")
  );
}

export async function getPlayerShotCreation(
  playerId: number,
  season: string,
  seasonType = "Regular Season",
  filters?: import("./types").ShotLabFilters
): Promise<import("./types").ShotCreationResponse> {
  return fetchApi<import("./types").ShotCreationResponse>(
    buildSituationalShotLabQuery(playerId, season, seasonType, filters, "/creation")
  );
}

export async function getPlayerShotIdentity(
  playerId: number,
  season: string,
  seasonType = "Regular Season",
  filters?: import("./types").ShotLabFilters
): Promise<import("./types").ShotIdentityResponse> {
  return fetchApi<import("./types").ShotIdentityResponse>(
    buildSituationalShotLabQuery(playerId, season, seasonType, filters, "/identity")
  );
}

export async function getPlayerShotCoverage(
  playerId: number,
  season: string,
  seasonType = "Regular Season",
  filters?: import("./types").ShotLabFilters
): Promise<import("./types").ShotIntelligenceCoverage> {
  return fetchApi<import("./types").ShotIntelligenceCoverage>(
    buildSituationalShotLabQuery(playerId, season, seasonType, filters, "/coverage")
  );
}

function buildTeamDefenseShotLabQuery(
  teamId: number,
  season: string,
  seasonType: string,
  filters?: import("./types").ShotLabFilters,
  suffix = ""
): string {
  const params = new URLSearchParams({
    season,
    season_type: seasonType,
    period_bucket: filters?.periodBucket ?? "all",
    result: filters?.result ?? "all",
    shot_value: filters?.shotValue ?? "all",
  });
  if (filters?.startDate) params.set("start_date", filters.startDate);
  if (filters?.endDate) params.set("end_date", filters.endDate);
  return `/api/shotchart/team-defense/${teamId}${suffix}?${params.toString()}`;
}

export async function getTeamDefenseShotQuality(
  teamId: number,
  season: string,
  seasonType = "Regular Season",
  filters?: import("./types").ShotLabFilters
): Promise<import("./types").ShotQualityResponse> {
  return fetchApi<import("./types").ShotQualityResponse>(
    buildTeamDefenseShotLabQuery(teamId, season, seasonType, filters, "/quality")
  );
}

export async function getTeamDefenseShotCreation(
  teamId: number,
  season: string,
  seasonType = "Regular Season",
  filters?: import("./types").ShotLabFilters
): Promise<import("./types").ShotCreationResponse> {
  return fetchApi<import("./types").ShotCreationResponse>(
    buildTeamDefenseShotLabQuery(teamId, season, seasonType, filters, "/creation")
  );
}

export async function getTeamDefenseShotIdentity(
  teamId: number,
  season: string,
  seasonType = "Regular Season",
  filters?: import("./types").ShotLabFilters
): Promise<import("./types").ShotIdentityResponse> {
  return fetchApi<import("./types").ShotIdentityResponse>(
    buildTeamDefenseShotLabQuery(teamId, season, seasonType, filters, "/identity")
  );
}

export async function getTeamDefenseShotCoverage(
  teamId: number,
  season: string,
  seasonType = "Regular Season",
  filters?: import("./types").ShotLabFilters
): Promise<import("./types").ShotIntelligenceCoverage> {
  return fetchApi<import("./types").ShotIntelligenceCoverage>(
    buildTeamDefenseShotLabQuery(teamId, season, seasonType, filters, "/coverage")
  );
}

export async function createShotLabSnapshot(
  payload: import("./types").ShotLabSnapshotPayload
): Promise<import("./types").ShotLabSnapshotResponse> {
  return fetchApi<import("./types").ShotLabSnapshotResponse>("/api/shotchart/snapshots", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getShotLabSnapshot(
  snapshotId: string
): Promise<import("./types").ShotLabSnapshotResponse> {
  return fetchApi<import("./types").ShotLabSnapshotResponse>(
    `/api/shotchart/snapshots/${encodeURIComponent(snapshotId)}`
  );
}

export async function getWarehouseCompletenessSummary(
  season: string,
  seasonType = "Regular Season"
): Promise<import("./types").WarehouseCompletenessSummary> {
  return fetchApi<import("./types").WarehouseCompletenessSummary>(
    `/api/warehouse/completeness/${encodeURIComponent(season)}?season_type=${encodeURIComponent(seasonType)}`
  );
}

export async function getGameVisualization(
  gameId: string,
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
): Promise<import("./types").GameVisualizationResponse> {
  const params = new URLSearchParams();
  if (options?.shotEventId) params.set("shot_event_id", options.shotEventId);
  if (options?.playerId != null) params.set("player_id", String(options.playerId));
  if (options?.period != null) params.set("period", String(options.period));
  if (options?.eventType) params.set("event_type", options.eventType);
  if (options?.query) params.set("query", options.query);
  if (options?.source) params.set("source", options.source);
  if (options?.sourceSurface) params.set("source_surface", options.sourceSurface);
  if (options?.sourceId) params.set("source_id", options.sourceId);
  if (options?.sourceLabel) params.set("source_label", options.sourceLabel);
  if (options?.reason) params.set("reason", options.reason);
  if (options?.claimId) params.set("claim_id", options.claimId);
  if (options?.clipAnchorId) params.set("clip_anchor_id", options.clipAnchorId);
  if (options?.returnTo) params.set("return_to", options.returnTo);
  if (options?.linkageQuality) params.set("linkage_quality", options.linkageQuality);
  if (options?.focusEventId) params.set("focus_event_id", options.focusEventId);
  if (options?.focusActionNumber != null) params.set("focus_action_number", String(options.focusActionNumber));
  if (options?.focusWindow != null) params.set("focus_window", String(options.focusWindow));
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return fetchApi<import("./types").GameVisualizationResponse>(
    `/api/games/${encodeURIComponent(gameId)}/visualization${suffix}`
  );
}

export async function getTeamSplits(
  teamAbbreviation: string,
  season: string
): Promise<import("./types").TeamSplitsResponse> {
  return fetchApi<import("./types").TeamSplitsResponse>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}/splits?season=${encodeURIComponent(season)}`
  );
}

export async function getMvpRace(
  season: string,
  options?: import("./types").MvpRaceOptions & { profile?: string }
): Promise<import("./types").MvpRaceResponse> {
  const params = new URLSearchParams({ season });
  if (options?.top != null) params.set("top", String(options.top));
  if (options?.minGp != null) params.set("min_gp", String(options.minGp));
  if (options?.position) params.set("position", options.position);
  if (options?.profile) params.set("profile", options.profile);
  if (options?.seasonType) params.set("season_type", options.seasonType);
  return fetchApi<import("./types").MvpRaceResponse>(
    `/api/mvp/race?${params.toString()}`
  );
}

export async function getMvpCandidateCase(
  playerId: number,
  season: string,
  options?: Pick<import("./types").MvpRaceOptions, "minGp" | "position"> & { profile?: string }
): Promise<import("./types").MvpCandidateCaseResponse> {
  const params = new URLSearchParams({ season });
  if (options?.minGp != null) params.set("min_gp", String(options.minGp));
  if (options?.position) params.set("position", options.position);
  if (options?.profile) params.set("profile", options.profile);
  return fetchApi<import("./types").MvpCandidateCaseResponse>(
    `/api/mvp/candidates/${encodeURIComponent(playerId)}/case?${params.toString()}`
  );
}

export async function getMvpContextMap(
  season: string,
  options?: import("./types").MvpRaceOptions & { profile?: string }
): Promise<import("./types").MvpContextMapResponse> {
  const params = new URLSearchParams({ season });
  if (options?.top != null) params.set("top", String(options.top));
  if (options?.minGp != null) params.set("min_gp", String(options.minGp));
  if (options?.position) params.set("position", options.position);
  if (options?.profile) params.set("profile", options.profile);
  return fetchApi<import("./types").MvpContextMapResponse>(
    `/api/mvp/context-map?${params.toString()}`
  );
}

export async function getMvpSensitivity(
  season: string,
  options?: import("./types").MvpRaceOptions
): Promise<import("./types").MvpSensitivityResponse> {
  const params = new URLSearchParams({ season });
  if (options?.top != null) params.set("top", String(options.top));
  if (options?.minGp != null) params.set("min_gp", String(options.minGp));
  if (options?.position) params.set("position", options.position);
  return fetchApi<import("./types").MvpSensitivityResponse>(
    `/api/mvp/sensitivity?${params.toString()}`
  );
}

export async function getMvpTimeline(
  season: string,
  options?: Pick<import("./types").MvpRaceOptions, "top" | "minGp"> & { profile?: string; days?: number }
): Promise<import("./types").MvpTimelineResponse> {
  const params = new URLSearchParams({ season });
  if (options?.profile) params.set("profile", options.profile);
  if (options?.days != null) params.set("days", String(options.days));
  if (options?.top != null) params.set("top", String(options.top));
  if (options?.minGp != null) params.set("min_gp", String(options.minGp));
  return fetchApi<import("./types").MvpTimelineResponse>(
    `/api/mvp/timeline?${params.toString()}`
  );
}

export async function getMvpVoterRoom(
  season: string,
  playerIds: number[],
  options?: Pick<import("./types").MvpRaceOptions, "minGp">
): Promise<import("./types").MvpVoterRoomResponse> {
  const params = new URLSearchParams({ season });
  if (playerIds.length) params.set("player_ids", playerIds.join(","));
  if (options?.minGp != null) params.set("min_gp", String(options.minGp));
  return fetchApi<import("./types").MvpVoterRoomResponse>(
    `/api/mvp/voter-room?${params.toString()}`
  );
}

export async function getMvpCoverage(
  season: string,
  options?: Pick<import("./types").MvpRaceOptions, "top" | "minGp">
): Promise<import("./types").MvpCoverageResponse> {
  const params = new URLSearchParams({ season });
  if (options?.top != null) params.set("top", String(options.top));
  if (options?.minGp != null) params.set("min_gp", String(options.minGp));
  return fetchApi<import("./types").MvpCoverageResponse>(
    `/api/mvp/coverage?${params.toString()}`
  );
}

export async function getMvpSnapshotFreshness(
  season: string
): Promise<import("./types").MvpSnapshotFreshness> {
  return fetchApi<import("./types").MvpSnapshotFreshness>(
    `/api/mvp/snapshot-freshness?season=${encodeURIComponent(season)}`
  );
}

export async function getMvpGravity(
  season: string,
  options?: import("./types").MvpRaceOptions
): Promise<import("./types").MvpGravityLeaderboardResponse> {
  const params = new URLSearchParams({ season });
  if (options?.top != null) params.set("top", String(options.top));
  if (options?.minGp != null) params.set("min_gp", String(options.minGp));
  if (options?.position) params.set("position", options.position);
  return fetchApi<import("./types").MvpGravityLeaderboardResponse>(
    `/api/mvp/gravity?${params.toString()}`
  );
}

export async function refreshTeamDefenseShotChart(
  teamId: number,
  season: string,
  seasonType = "Regular Season",
  force = false
): Promise<import("./types").QueueResponse> {
  const params = new URLSearchParams({
    season,
    season_type: seasonType,
    force: String(force),
  });
  return fetchApi<import("./types").QueueResponse>(
    `/api/shotchart/team-defense/${teamId}/refresh?${params.toString()}`,
    { method: "POST" }
  );
}

export function fetchTrajectorySeries(
  playerId: number,
  season: string,
  lastNGames: number
): Promise<TrajectorySeriesResponse> {
  const params = new URLSearchParams({
    season,
    last_n_games: String(lastNGames),
  });
  return fetchApi<TrajectorySeriesResponse>(
    `/api/insights/trajectory/${playerId}/series?${params.toString()}`
  );
}

export function fetchLineupContext(
  playerId: number,
  season: string
): Promise<LineupContextResponse> {
  return fetchApi<LineupContextResponse>(
    `/api/insights/lineup-context/${playerId}?season=${encodeURIComponent(season)}`
  );
}

export function fetchOpportunityReport(
  season: string,
  team?: string | null,
  minMinutes: number = 15,
  position?: string | null
): Promise<OpportunityResponse> {
  const params = new URLSearchParams();
  params.set("season", season);
  if (team) params.set("team", team);
  params.set("min_minutes", String(minMinutes));
  if (position) params.set("position", position);
  return fetchApi<OpportunityResponse>(
    `/api/insights/opportunity?${params.toString()}`
  );
}

export function getShotIntelligenceOps(
  season: string,
  seasonType: string = "Regular Season"
): Promise<import("./types").ShotIntelligenceOpsResponse> {
  const params = new URLSearchParams({ season_type: seasonType });
  return fetchApi<import("./types").ShotIntelligenceOpsResponse>(
    `/shotchart/ops/${season}?${params.toString()}`
  );
}

export function refreshShotQualityBaseline(
  season: string,
  seasonType: string = "Regular Season"
): Promise<import("./types").ShotIntelligenceOpsResponse> {
  const params = new URLSearchParams({ season_type: seasonType });
  return fetchApi<import("./types").ShotIntelligenceOpsResponse>(
    `/shotchart/ops/${season}/refresh-baseline?${params.toString()}`,
    { method: "POST" }
  );
}

export function refreshStaleShotPlayers(
  season: string,
  seasonType: string = "Regular Season",
  limit: number = 40
): Promise<{ queued: number; jobs: unknown[] }> {
  const params = new URLSearchParams({ season_type: seasonType, limit: String(limit) });
  return fetchApi<{ queued: number; jobs: unknown[] }>(
    `/shotchart/ops/${season}/refresh-stale-players?${params.toString()}`,
    { method: "POST" }
  );
}

export async function getTeamShootingSplits(
  teamAbbreviation: string,
  season: string
): Promise<import("./types").TeamShootingSplitsResponse> {
  return fetchApi<import("./types").TeamShootingSplitsResponse>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}/shooting-splits?season=${encodeURIComponent(season)}`
  );
}

export async function getOpponentPlayTypes(
  teamAbbreviation: string,
  season: string
): Promise<import("./types").OpponentPlayTypeResponse> {
  return fetchApi<import("./types").OpponentPlayTypeResponse>(
    `/api/decision/opponent-play-types?team=${encodeURIComponent(teamAbbreviation)}&season=${encodeURIComponent(season)}`
  );
}

export async function getH2HHistory(
  teamAbbreviation: string,
  opponentAbbreviation: string,
  season: string
): Promise<import("./types").H2HResponse> {
  return fetchApi<import("./types").H2HResponse>(
    `/api/decision/h2h?team=${encodeURIComponent(teamAbbreviation)}&opponent=${encodeURIComponent(opponentAbbreviation)}&season=${encodeURIComponent(season)}`
  );
}

export async function getPaceEdge(
  teamAbbreviation: string,
  opponentAbbreviation: string,
  season: string
): Promise<import("./types").PaceEdge> {
  return fetchApi<import("./types").PaceEdge>(
    `/api/decision/pace-edge?team=${encodeURIComponent(teamAbbreviation)}&opponent=${encodeURIComponent(opponentAbbreviation)}&season=${encodeURIComponent(season)}`
  );
}

export async function getTeamClutch(
  teamAbbreviation: string,
  season: string
): Promise<import("./types").TeamClutchResponse> {
  return fetchApi<import("./types").TeamClutchResponse>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}/clutch?season=${encodeURIComponent(season)}`
  );
}

export async function getTeamNetRatingSeries(
  teamAbbreviation: string,
  season: string,
  window: number = 10
): Promise<import("./types").TeamNetRatingSeriesResponse> {
  return fetchApi<import("./types").TeamNetRatingSeriesResponse>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}/net-rating-series?season=${encodeURIComponent(season)}&window=${window}`
  );
}

export async function getTeamPeriodScoring(
  teamAbbreviation: string,
  season: string
): Promise<import("./types").TeamPeriodScoringResponse> {
  return fetchApi<import("./types").TeamPeriodScoringResponse>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}/period-scoring?season=${encodeURIComponent(season)}`
  );
}

export async function getTeamBenchAnalytics(
  teamAbbreviation: string,
  season: string,
  minPossessions: number = 20
): Promise<import("./types").BenchAnalyticsResponse> {
  return fetchApi<import("./types").BenchAnalyticsResponse>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}/bench-analytics?season=${encodeURIComponent(season)}&min_possessions=${minPossessions}`
  );
}

async function fetchApiText(path: string, init?: RequestInit): Promise<string> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.text();
}

export async function createPreReadPacketSnapshot(payload: {
  team: string;
  opponent: string;
  season: string;
  game_id?: string;
  source_view?: string;
  source_snapshot_id?: string;
  title?: string;
  note?: string;
  packet_selection?: import("./types").PreReadPacketSelection;
  context?: Record<string, string>;
}): Promise<import("./types").PreReadSnapshotResponse> {
  return fetchApi<import("./types").PreReadSnapshotResponse>(`/api/pre-read/snapshots`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updatePreReadPacketSnapshot(
  snapshotId: string,
  payload: {
    title?: string;
    note?: string;
  }
): Promise<import("./types").PreReadSnapshotResponse> {
  return fetchApi<import("./types").PreReadSnapshotResponse>(
    `/api/pre-read/snapshots/${encodeURIComponent(snapshotId)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function getPreReadSnapshotMarkdown(snapshotId: string): Promise<string> {
  return fetchApiText(`/api/pre-read/snapshots/${encodeURIComponent(snapshotId)}/markdown`);
}

// --- Sprint 67 — Player Archetype + Similarity Engine ---------------------

export async function getPlayerArchetype(
  playerId: number,
  season: string
): Promise<import("./types").PlayerArchetype> {
  return fetchApi<import("./types").PlayerArchetype>(
    `/api/archetype/${playerId}?season=${encodeURIComponent(season)}`
  );
}

export async function getSimilarPlayersWithArchetype(
  playerId: number,
  season: string,
  mode: import("./types").SimilarityMode = "season",
  n = 8
): Promise<import("./types").SimilarityResponseWithArchetype> {
  return fetchApi<import("./types").SimilarityResponseWithArchetype>(
    `/api/similarity/${playerId}?season=${encodeURIComponent(season)}&mode=${mode}&n=${n}`
  );
}

// Sprint 67 (Stream B) — Shot diagnosis + scouting brief

export async function getPlayerShotDiagnosis(
  playerId: number,
  season: string,
  seasonType: string = "Regular Season"
): Promise<import("./types").ShotDiagnosisResponse> {
  const params = new URLSearchParams({ season, season_type: seasonType });
  return fetchApi<import("./types").ShotDiagnosisResponse>(
    `/api/shotchart/${playerId}/diagnosis?${params.toString()}`
  );
}

export async function getPlayerScoutingBrief(
  playerId: number,
  season: string
): Promise<import("./types").ScoutingBriefResponse> {
  return fetchApi<import("./types").ScoutingBriefResponse>(
    `/api/players/${playerId}/scouting-brief?season=${encodeURIComponent(season)}`
  );
}

// Sprint 68 — archetype evolution history

export async function getPlayerArchetypeHistory(
  playerId: number
): Promise<import("./types").ArchetypeHistoryResponse> {
  return fetchApi<import("./types").ArchetypeHistoryResponse>(
    `/api/archetype/${playerId}/history`
  );
}

// Sprint 69 — Team-Fit Intelligence

export async function getPlayerTeamFit(
  playerId: number,
  season: string,
  limit = 5,
  seasonType = "Regular Season"
): Promise<import("./types").TeamFitResponse> {
  return fetchApi<import("./types").TeamFitResponse>(
    `/api/team-fit/${playerId}?season=${encodeURIComponent(season)}&limit=${limit}&season_type=${encodeURIComponent(seasonType)}`
  );
}

export async function getPlayerAnalysisContexts(
  playerId: number,
  season: string,
  includeAuto = true
): Promise<import("./types").AnalysisContextListResponse> {
  return fetchApi<import("./types").AnalysisContextListResponse>(
    `/api/players/${playerId}/analysis-contexts?season=${encodeURIComponent(season)}&include_auto=${includeAuto}`
  );
}

export async function createPlayerAnalysisContext(
  playerId: number,
  payload: import("./types").AnalysisContextPayload
): Promise<import("./types").AnalysisContext> {
  return fetchApi<import("./types").AnalysisContext>(
    `/api/players/${playerId}/analysis-contexts`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function updatePlayerAnalysisContext(
  playerId: number,
  contextId: number,
  payload: Partial<import("./types").AnalysisContextPayload>
): Promise<import("./types").AnalysisContext> {
  return fetchApi<import("./types").AnalysisContext>(
    `/api/players/${playerId}/analysis-contexts/${contextId}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function deletePlayerAnalysisContext(
  playerId: number,
  contextId: number
): Promise<{ status: string; context_id: number }> {
  return fetchApi<{ status: string; context_id: number }>(
    `/api/players/${playerId}/analysis-contexts/${contextId}`,
    { method: "DELETE" }
  );
}

// Sprint 74 — shared methodology registry and validation
export async function getMethodologyRegistry(): Promise<import("./types").MethodologyRegistryResponse> {
  return fetchApi<import("./types").MethodologyRegistryResponse>("/api/methodology");
}

export async function getMethodologyDomain(
  domain: string
): Promise<import("./types").MethodologyDetailResponse> {
  return fetchApi<import("./types").MethodologyDetailResponse>(
    `/api/methodology/${encodeURIComponent(domain)}`
  );
}

export async function getMethodologyValidation(): Promise<import("./types").MethodologyValidationResponse> {
  return fetchApi<import("./types").MethodologyValidationResponse>("/api/methodology/validation");
}

// ── Sprint 72: Leaderboard trend sparklines ──────────────────────────────────
export async function getLeaderboardTrends(
  stat: string,
  playerIds: number[],
  season: string,
  window = 10
): Promise<import("./types").LeaderboardTrendResponse> {
  const params = new URLSearchParams({
    player_ids: playerIds.join(","),
    season,
    window: String(window),
  });
  return fetchApi<import("./types").LeaderboardTrendResponse>(
    `/api/leaderboards/${encodeURIComponent(stat)}/trends?${params.toString()}`
  );
}

// ── Sprint 73: Season phase + playoffs bracket ───────────────────────────────
export async function getSeasonPhase(): Promise<import("./types").SeasonPhaseResponse> {
  return fetchApi<import("./types").SeasonPhaseResponse>("/api/season-phase");
}

export async function getBracket(
  season: string
): Promise<import("./types").PlayoffBracketResponse> {
  const params = new URLSearchParams({ season });
  return fetchApi<import("./types").PlayoffBracketResponse>(
    `/api/playoffs/bracket?${params.toString()}`
  );
}

export async function getSeries(
  seriesId: string
): Promise<import("./types").PlayoffSeriesResponse> {
  return fetchApi<import("./types").PlayoffSeriesResponse>(
    `/api/playoffs/series/${encodeURIComponent(seriesId)}`
  );
}

// Sprint 73B — series simulator (Stream A `GET /api/playoffs/series-simulation/{id}`).
export async function getSeriesSimulation(
  seriesId: string
): Promise<import("./types").SeriesSimulationResponse> {
  return fetchApi<import("./types").SeriesSimulationResponse>(
    `/api/playoffs/series-simulation/${encodeURIComponent(seriesId)}`
  );
}

// Sprint 73B — playoff-aware lineups query (`/api/advanced/lineups` already
// accepts `season_type=Playoffs` per Stream A EA3). Distinct from the existing
// `getLineups` so we don't change its signature.
export async function getLineupsForSeasonType(
  season: string,
  seasonType: "Regular Season" | "Playoffs",
  teamId?: number,
  minMinutes = 5,
  limit = 25
): Promise<import("./types").LineupsResult> {
  const params = new URLSearchParams({
    season,
    season_type: seasonType,
    min_minutes: String(minMinutes),
    limit: String(limit),
  });
  if (teamId != null) params.set("team_id", String(teamId));
  return fetchApi<import("./types").LineupsResult>(
    `/api/advanced/lineups?${params.toString()}`
  );
}

// Sprint 73 (EB3): today's playoff slate. `date` is optional; when omitted, the
// backend defaults to "today" in US/Pacific.
export async function getPlayoffsToday(
  date?: string
): Promise<import("./types").PlayoffTodayResponse> {
  const path = date
    ? `/api/playoffs/today?date=${encodeURIComponent(date)}`
    : "/api/playoffs/today";
  return fetchApi<import("./types").PlayoffTodayResponse>(path);
}

// Sprint 75 — Playoff Command Center intelligence payload.
export async function getPlayoffSeriesIntelligence(
  seriesId: string
): Promise<import("./types").PlayoffSeriesIntelligenceResponse> {
  return fetchApi<import("./types").PlayoffSeriesIntelligenceResponse>(
    `/api/playoffs/series/${encodeURIComponent(seriesId)}/intelligence`
  );
}

// Sprint 75 — non-mutating hypothetical simulator state.
export async function getSeriesSimulationWithOverrides(
  seriesId: string,
  overrides?: {
    overrideTopWins?: number | null;
    overrideBottomWins?: number | null;
  }
): Promise<import("./types").SeriesSimulationResponse> {
  const params = new URLSearchParams();
  if (overrides?.overrideTopWins != null) {
    params.set("override_top_wins", String(overrides.overrideTopWins));
  }
  if (overrides?.overrideBottomWins != null) {
    params.set("override_bottom_wins", String(overrides.overrideBottomWins));
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return fetchApi<import("./types").SeriesSimulationResponse>(
    `/api/playoffs/series-simulation/${encodeURIComponent(seriesId)}${suffix}`
  );
}

// ── Sprint 77 (Stream A) — Playoff narrative leaders ─────────────────────────
export async function getPlayoffLeaders(
  season: string,
  limit = 5
): Promise<import("./types").PlayoffLeadersResponse> {
  const params = new URLSearchParams({
    season,
    limit: String(limit),
  });
  return fetchApi<import("./types").PlayoffLeadersResponse>(
    `/api/playoffs/leaders?${params.toString()}`
  );
}

// ── Story Rail — auto-generated story tiles for the broadsheet rail.
// All tiles link to internal routes only.
export async function getPlayoffStoryRail(
  season: string
): Promise<import("./types").PlayoffStoryRailResponse> {
  const params = new URLSearchParams({ season });
  return fetchApi<import("./types").PlayoffStoryRailResponse>(
    `/api/playoffs/story-rail?${params.toString()}`
  );
}

// ── Sprint 77 (Stream B / EB3) — Game-detail enrichment ──────────────────────
// `getGameDetail` already returns the augmented `GameDetailResponse` (see
// `lib/types.ts`) with `win_probability`, `lead_tracker`, `possession_diary`,
// `player_quarter_impact`, and `series_odds_history`. No new endpoints are
// needed for the broadsheet game-detail surface — re-export the existing
// types so component files don't have to dig into `lib/types`.
export type {
  WinProbPoint as GameWinProbPoint,
  LeadPoint as GameLeadPoint,
  PossessionEntry as GamePossessionEntry,
  PlayerQuarterImpact as GamePlayerQuarterImpact,
  SeriesOddsPoint as GameSeriesOddsPoint,
} from "./types";
