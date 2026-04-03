import type {
  PlayerSearchResult,
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
  PbpSyncResult,
  GameLogResponse,
  GameDetailResponse,
  SimilarityResponse,
  LeagueContext,
  CareerLeaderboardResponse,
  InjuryEntry,
  InjuryReportResponse,
  StandingsHistoryEntry,
  ZoneProfileResponse,
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
): Promise<PlayerProfile> {
  return fetchApi<PlayerProfile>(`/api/players/${playerId}`);
}

export async function getPlayerCareerStats(
  playerId: number
): Promise<CareerStatsResponse> {
  return fetchApi<CareerStatsResponse>(`/api/stats/${playerId}/career`);
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
): Promise<GameLogResponse> {
  return fetchApi<GameLogResponse>(
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
  season: string
): Promise<import("./types").TeamComparisonResponse> {
  const params = new URLSearchParams({
    team_a: teamA,
    team_b: teamB,
    season,
  });
  return fetchApi<import("./types").TeamComparisonResponse>(
    `/api/compare/teams?${params.toString()}`
  );
}

export async function getTeamFocusLevers(
  teamAbbreviation: string,
  season: string
): Promise<import("./types").TeamFocusLeversReport> {
  return fetchApi<import("./types").TeamFocusLeversReport>(
    `/api/teams/${encodeURIComponent(teamAbbreviation)}/focus-levers?season=${encodeURIComponent(season)}`
  );
}

export async function getUsageEfficiencyReport(
  season: string,
  team?: string,
  minMinutes = 20
): Promise<import("./types").UsageEfficiencyResponse> {
  const params = new URLSearchParams({
    season,
    min_minutes: String(minMinutes),
  });
  if (team) params.set("team", team);
  return fetchApi<import("./types").UsageEfficiencyResponse>(
    `/api/insights/usage-efficiency?${params.toString()}`
  );
}

export async function getPreReadDeck(
  team: string,
  opponent: string,
  season: string
): Promise<import("./types").PreReadDeckResponse> {
  const params = new URLSearchParams({
    team,
    opponent,
    season,
  });
  return fetchApi<import("./types").PreReadDeckResponse>(
    `/api/pre-read?${params.toString()}`
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
  window = 10
): Promise<import("./types").StyleXRayResponse> {
  const params = new URLSearchParams({
    team,
    season,
    window: String(window),
  });
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
  window = "4w"
): Promise<import("./types").TrendCardsResponse> {
  const params = new URLSearchParams({
    team,
    season,
    window,
  });
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
