export interface PlayerSearchResult {
  id: number;
  full_name: string;
  is_active: boolean;
}

export interface PlayerProfile {
  id: number;
  full_name: string;
  first_name: string;
  last_name: string;
  team_name: string;
  team_abbreviation: string;
  team_id: number | null;
  jersey: string;
  position: string;
  height: string;
  weight: string;
  birth_date: string;
  country: string;
  school: string | null;
  draft_year: string | null;
  draft_round: string | null;
  draft_number: string | null;
  from_year: number | null;
  to_year: number | null;
  headshot_url: string;
}

export interface SeasonStats {
  season: string;
  team_abbreviation: string;
  gp: number;
  gs: number;
  min_pg: number;
  pts_pg: number;
  reb_pg: number;
  ast_pg: number;
  stl_pg: number;
  blk_pg: number;
  tov_pg: number;
  fg_pct: number;
  fg3_pct: number;
  ft_pct: number;
  pts: number;
  reb: number;
  ast: number;
  fgm: number;
  fga: number;
  fg3m: number;
  fg3a: number;
  ftm: number;
  fta: number;
  oreb: number;
  dreb: number;
  stl: number;
  blk: number;
  tov: number;
  pf: number;
  min_total: number;
  ts_pct: number | null;
  efg_pct: number | null;
  usg_pct: number | null;
  per: number | null;
  bpm: number | null;
  off_rating: number | null;
  def_rating: number | null;
  net_rating: number | null;
  ws: number | null;
  vorp: number | null;
  pie: number | null;
  pace: number | null;
  darko: number | null;
  epm: number | null;
  rapm: number | null;
  lebron: number | null;
  raptor: number | null;
  pipm: number | null;
  obpm: number | null;
  dbpm: number | null;
  ftr: number | null;
  par3: number | null;
  ast_tov: number | null;
  oreb_pct: number | null;
  clutch_pts: number | null;
  clutch_fga: number | null;
  clutch_fg_pct: number | null;
  clutch_plus_minus: number | null;
  second_chance_pts: number | null;
  fast_break_pts: number | null;
  per36: Record<string, number> | null;
  per100: Record<string, number> | null;
}

export interface CareerStatsResponse {
  player_id: number;
  player_name: string;
  seasons: SeasonStats[];
  career_totals: SeasonStats | null;
  playoff_seasons: SeasonStats[];
}

export interface ShotChartShot {
  loc_x: number;
  loc_y: number;
  shot_made: boolean;
  shot_type: string;
  action_type: string;
  zone_basic: string;
  zone_area: string;
  distance: number;
}

export interface TeamRosterPlayer {
  player_id: number;
  full_name: string;
  position: string;
  jersey: string;
  headshot_url: string;
  season: string | null;
  pts_pg: number | null;
  reb_pg: number | null;
  ast_pg: number | null;
  per: number | null;
  bpm: number | null;
}

export interface TeamSummary {
  team_id: number;
  abbreviation: string;
  name: string;
  player_count: number;
}

export interface TeamRosterResponse {
  team_id: number;
  abbreviation: string;
  name: string;
  players: TeamRosterPlayer[];
  synced_count: number;
}

export interface LeaderboardEntry {
  rank: number;
  player_id: number;
  player_name: string;
  team_abbreviation: string;
  headshot_url: string;
  gp: number;
  stat_value: number;
  pts_pg: number | null;
  reb_pg: number | null;
  ast_pg: number | null;
  ts_pct: number | null;
  per: number | null;
  bpm: number | null;
}

export interface LeaderboardResponse {
  stat: string;
  season: string;
  season_type: string;
  entries: LeaderboardEntry[];
}

export interface PercentileResult {
  season: string;
  percentiles: Record<string, number | null>;
}

export interface ShotChartResponse {
  player_id: number;
  season: string;
  season_type: string;
  shots: ShotChartShot[];
  made: number;
  attempted: number;
}

export interface OnOffStats {
  player_id: number;
  season: string;
  on_minutes: number | null;
  off_minutes: number | null;
  on_net_rating: number | null;
  off_net_rating: number | null;
  on_off_net: number | null;
  on_ortg: number | null;
  on_drtg: number | null;
  off_ortg: number | null;
  off_drtg: number | null;
}

export interface PbpCoverage {
  player_id: number;
  season: string;
  eligible_games: number;
  synced_games: number;
  has_on_off: boolean;
  has_scoring_splits: boolean;
  status: "none" | "partial" | "ready";
  last_derived_at: string | null;
}

export interface PbpCoveragePlayerRow {
  player_id: number;
  player_name: string;
  team_abbreviation: string | null;
  season: string;
  eligible_games: number;
  synced_games: number;
  has_on_off: boolean;
  has_scoring_splits: boolean;
  status: "none" | "partial" | "ready";
  last_derived_at: string | null;
}

export interface PbpCoverageTeamRow {
  team_id: number;
  abbreviation: string;
  name: string;
  season: string;
  player_count: number;
  players_ready: number;
  players_partial: number;
  players_none: number;
  eligible_games: number;
  synced_games: number;
  status: "none" | "partial" | "ready";
}

export interface PbpCoverageDashboard {
  season: string;
  total_teams: number;
  total_players: number;
  teams_ready: number;
  teams_partial: number;
  teams_none: number;
  players_ready: number;
  players_partial: number;
  players_none: number;
  eligible_games: number;
  synced_games: number;
  teams: PbpCoverageTeamRow[];
  players: PbpCoveragePlayerRow[];
}

export interface PbpCoverageSeasonSummary {
  season: string;
  total_teams: number;
  total_players: number;
  teams_ready: number;
  teams_partial: number;
  teams_none: number;
  players_ready: number;
  players_partial: number;
  players_none: number;
  eligible_games: number;
  synced_games: number;
}

export interface ClutchStats {
  player_id: number;
  season: string;
  clutch_pts: number | null;
  clutch_fga: number | null;
  clutch_fg_pct: number | null;
  clutch_plus_minus: number | null;
  second_chance_pts: number | null;
  fast_break_pts: number | null;
}

export interface LineupStatsResponse {
  lineup_key: string;
  player_ids: number[];
  player_names: string[];
  season: string;
  team_id: number | null;
  minutes: number | null;
  net_rating: number | null;
  ortg: number | null;
  drtg: number | null;
  plus_minus: number | null;
  possessions: number | null;
}

export interface LineupsResult {
  season: string;
  lineups: LineupStatsResponse[];
}

export interface OnOffLeaderboardEntry {
  player_id: number;
  player_name: string;
  on_minutes: number | null;
  on_net_rating: number | null;
  off_net_rating: number | null;
  on_off_net: number | null;
}

export interface OnOffLeaderboardResult {
  season: string;
  players: OnOffLeaderboardEntry[];
}

export interface GameLogEntry {
  game_id: string;
  game_date: string;
  matchup: string;
  wl: string;
  min: number | null;
  pts: number | null;
  reb: number | null;
  ast: number | null;
  stl: number | null;
  blk: number | null;
  tov: number | null;
  fgm: number | null;
  fga: number | null;
  fg_pct: number | null;
  fg3m: number | null;
  fg3a: number | null;
  fg3_pct: number | null;
  ftm: number | null;
  fta: number | null;
  ft_pct: number | null;
  oreb: number | null;
  dreb: number | null;
  pf: number | null;
  plus_minus: number | null;
  pts_roll5: number | null;
  reb_roll5: number | null;
  ast_roll5: number | null;
}

export interface GameLogSeasonAverages {
  pts: number | null;
  reb: number | null;
  ast: number | null;
  stl: number | null;
  blk: number | null;
  tov: number | null;
  fg_pct: number | null;
  fg3_pct: number | null;
  ft_pct: number | null;
  min: number | null;
  plus_minus: number | null;
}

export interface GameLogResponse {
  player_id: number;
  season: string;
  season_type: string;
  games: GameLogEntry[];
  season_averages: GameLogSeasonAverages;
  gp: number;
}

export interface GameEvent {
  action_number: number;
  period: number;
  clock: string | null;
  team_id: number | null;
  team_abbreviation: string | null;
  player_id: number | null;
  player_name: string | null;
  event_type: string | null;
  description: string | null;
  home_score: number | null;
  away_score: number | null;
}

export interface GameTimelinePoint {
  action_number: number;
  period: number;
  clock: string | null;
  home_score: number;
  away_score: number;
  scoring_team_id: number | null;
  scoring_team_abbreviation: string | null;
  description: string | null;
}

export interface GamePlayerSummary {
  player_id: number;
  player_name: string;
  team_id: number | null;
  team_abbreviation: string | null;
  pts: number | null;
  reb: number | null;
  ast: number | null;
  stl: number | null;
  blk: number | null;
  tov: number | null;
  min: number | null;
  plus_minus: number | null;
}

export interface GameDetailResponse {
  game_id: string;
  game_date: string | null;
  season: string | null;
  matchup: string | null;
  home_team_id: number | null;
  home_team_abbreviation: string | null;
  home_team_name: string | null;
  away_team_id: number | null;
  away_team_abbreviation: string | null;
  away_team_name: string | null;
  home_score: number | null;
  away_score: number | null;
  timeline: GameTimelinePoint[];
  top_players: GamePlayerSummary[];
  events: GameEvent[];
}

export interface SimilarPlayerComp {
  player_id: number;
  player_name: string;
  headshot_url: string | null;
  season: string;
  team_abbreviation: string;
  similarity_score: number;
  gp: number;
  pts_pg: number | null;
  reb_pg: number | null;
  ast_pg: number | null;
  ts_pct: number | null;
  usg_pct: number | null;
  per: number | null;
}

export interface SimilarityResponse {
  player_id: number;
  season: string;
  cross_era: boolean;
  comps: SimilarPlayerComp[];
}

export interface BreakoutSeasonStats {
  season: string;
  team_abbreviation: string;
  gp: number;
  pts_pg: number | null;
  reb_pg: number | null;
  ast_pg: number | null;
  ts_pct: number | null;
  per: number | null;
  bpm: number | null;
  usg_pct: number | null;
}

export interface BreakoutEntry {
  player_id: number;
  full_name: string;
  headshot_url: string | null;
  current: BreakoutSeasonStats;
  prior: BreakoutSeasonStats;
  improvement_score: number;
  delta_pts_pg: number | null;
  delta_reb_pg: number | null;
  delta_ast_pg: number | null;
  delta_ts_pct: number | null;
  delta_per: number | null;
  delta_bpm: number | null;
}

export interface BreakoutsResponse {
  season: string;
  prior_season: string;
  improvers: BreakoutEntry[];
  decliners: BreakoutEntry[];
}

export interface StandingsEntry {
  team_id: number;
  abbreviation: string;
  team_city: string;
  team_name: string;
  conference: string;
  division: string;
  playoff_rank: number;
  wins: number;
  losses: number;
  win_pct: number;
  games_back: number | null;
  l10: string;
  home_record: string;
  road_record: string;
  pts_pg: number | null;
  opp_pts_pg: number | null;
  diff_pts_pg: number | null;
  current_streak: string;
  clinch_indicator: string | null;
}

export interface TeamAnalytics {
  team_id: number;
  abbreviation: string;
  name: string;
  season: string;
  gp: number;
  w: number;
  l: number;
  w_pct: number;
  pts_pg: number | null;
  ast_pg: number | null;
  reb_pg: number | null;
  tov_pg: number | null;
  blk_pg: number | null;
  stl_pg: number | null;
  fg_pct: number | null;
  fg3_pct: number | null;
  ft_pct: number | null;
  plus_minus_pg: number | null;
  off_rating: number | null;
  def_rating: number | null;
  net_rating: number | null;
  pace: number | null;
  efg_pct: number | null;
  ts_pct: number | null;
  pie: number | null;
  oreb_pct: number | null;
  dreb_pct: number | null;
  tov_pct: number | null;
  ast_pct: number | null;
  off_rating_rank: number | null;
  def_rating_rank: number | null;
  net_rating_rank: number | null;
  pace_rank: number | null;
  efg_pct_rank: number | null;
  ts_pct_rank: number | null;
  oreb_pct_rank: number | null;
  tov_pct_rank: number | null;
}

export interface TeamRecentGame {
  game_id: string;
  game_date: string | null;
  opponent_abbreviation: string | null;
  is_home: boolean;
  result: string;
  team_score: number | null;
  opponent_score: number | null;
  margin: number | null;
}

export interface TeamPbpCoverage {
  season: string;
  eligible_games: number;
  synced_games: number;
  players_with_on_off: number;
  players_with_scoring_splits: number;
  status: "none" | "partial" | "ready";
}

export interface TeamImpactLeader {
  player_id: number;
  player_name: string;
  team_abbreviation: string | null;
  on_off_net: number | null;
  on_minutes: number | null;
  bpm: number | null;
  pts_pg: number | null;
  clutch_pts: number | null;
}

export interface TeamIntelligence {
  team_id: number;
  abbreviation: string;
  name: string;
  season: string;
  conference: string | null;
  playoff_rank: number | null;
  wins: number | null;
  losses: number | null;
  win_pct: number | null;
  l10: string | null;
  current_streak: string | null;
  pts_pg: number | null;
  opp_pts_pg: number | null;
  diff_pts_pg: number | null;
  recent_record: string | null;
  recent_avg_margin: number | null;
  pbp_coverage: TeamPbpCoverage;
  impact_leaders: TeamImpactLeader[];
  best_lineups: LineupStatsResponse[];
  worst_lineups: LineupStatsResponse[];
  recent_games: TeamRecentGame[];
}

export interface PbpSyncResult {
  status: string;
  season: string;
  games_requested: number;
  games_processed: number;
  games_fetched: number;
  games_reused: number;
  games_failed: number;
  players_updated: number;
  lineups_updated: number;
}

export interface LeagueContext {
  season: string;
  position_group: string | null;
  league_medians: Record<string, number | null>;
  position_medians: Record<string, number | null>;
}

export interface CareerLeaderboardEntry {
  rank: number;
  player_id: number;
  player_name: string;
  headshot_url: string;
  seasons_played: number;
  career_gp: number;
  stat_value: number;
}

export interface CareerLeaderboardResponse {
  stat: string;
  entries: CareerLeaderboardEntry[];
}

// ── Warehouse pipeline types ─────────────────────────────────────────────────

export interface SourceRunResponse {
  id: number;
  source: string;
  job_type: string;
  entity_type: string;
  entity_id: string;
  status: string;
  attempt_count: number;
  records_written: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  run_metadata: Record<string, unknown> | null;
}

export interface IngestionJobResponse {
  id: number;
  job_type: string;
  job_key: string;
  season: string | null;
  game_id: string | null;
  priority: number;
  status: string;
  attempt_count: number;
  last_error: string | null;
  run_after: string | null;
  leased_until: string | null;
  completed_at: string | null;
}

export interface WarehouseSeasonHealth {
  season: string;
  total_games: number;
  scheduled_games: number;
  completed_games: number;
  games_with_box_score: number;
  games_with_pbp_payload: number;
  games_with_parsed_pbp: number;
  games_materialized: number;
  pending_jobs: number;
  running_jobs: number;
  failed_jobs: number;
  latest_runs: SourceRunResponse[];
}

export interface WarehouseGameHealth {
  game_id: string;
  season: string;
  game_date: string | null;
  status: string;
  home_team_abbreviation: string | null;
  away_team_abbreviation: string | null;
  has_schedule: boolean;
  has_final_box_score: boolean;
  has_pbp_payload: boolean;
  has_parsed_pbp: boolean;
  has_materialized_game_stats: boolean;
  has_materialized_season: boolean;
  pbp_parse_status: string;
  game_player_rows: number;
  game_team_rows: number;
  pbp_event_rows: number;
  raw_payload_types: string[];
  last_box_score_sync_at: string | null;
  last_pbp_sync_at: string | null;
  last_materialized_at: string | null;
}

export interface WarehouseJobTypeSummary {
  job_type: string;
  queued: number;
  running: number;
  complete: number;
  failed: number;
  skipped: number;
}

export interface WarehouseRequestThrottleStatus {
  source: string;
  available_at: string | null;
  last_request_at: string | null;
  seconds_until_available: number;
}

export interface WarehouseJobSummary {
  season: string | null;
  status_counts: Record<string, number>;
  job_types: WarehouseJobTypeSummary[];
  oldest_queued_job: IngestionJobResponse | null;
  stalled_running_count: number;
  stalled_running_jobs: IngestionJobResponse[];
  recent_failed_jobs: IngestionJobResponse[];
  global_request_throttle: WarehouseRequestThrottleStatus | null;
}

// ── Game summary (box score) ──────────────────────────────────────────────────

export interface GameTeamBoxScore {
  team_id: number;
  team_abbreviation: string | null;
  is_home: boolean;
  won: boolean | null;
  pts: number;
  reb: number;
  ast: number;
  stl: number;
  blk: number;
  tov: number;
  fgm: number;
  fga: number;
  fg_pct: number | null;
  fg3m: number;
  fg3a: number;
  fg3_pct: number | null;
  ftm: number;
  fta: number;
  ft_pct: number | null;
  oreb: number;
  dreb: number;
  pf: number;
  plus_minus: number | null;
}

export interface GamePlayerBoxScore {
  player_id: number;
  player_name: string;
  team_id: number | null;
  team_abbreviation: string | null;
  is_starter: boolean;
  min: number | null;
  pts: number;
  reb: number;
  ast: number;
  stl: number;
  blk: number;
  tov: number;
  fgm: number;
  fga: number;
  fg_pct: number | null;
  fg3m: number;
  fg3a: number;
  fg3_pct: number | null;
  ftm: number;
  fta: number;
  ft_pct: number | null;
  oreb: number;
  dreb: number;
  pf: number;
  plus_minus: number | null;
  wl: string | null;
}

export interface GameSummaryResponse {
  game_id: string;
  season: string;
  game_date: string | null;
  home_team_id: number | null;
  away_team_id: number | null;
  home_team_abbreviation: string | null;
  away_team_abbreviation: string | null;
  home_score: number | null;
  away_score: number | null;
  materialized: boolean;
  home_team_stats: GameTeamBoxScore | null;
  away_team_stats: GameTeamBoxScore | null;
  players: GamePlayerBoxScore[];
}

export interface TeamRotationPlayerRow {
  player_id: number;
  player_name: string;
  team_abbreviation: string | null;
  starts_last_10: number;
  avg_minutes_last_10: number | null;
  avg_minutes_season: number | null;
  minutes_delta: number | null;
  is_primary_starter: boolean;
}

export interface TeamRotationGame {
  game_id: string;
  game_date: string | null;
  opponent_abbreviation: string | null;
  result: string;
  team_score: number | null;
  opponent_score: number | null;
  rotation_note: string;
}

export interface TeamRotationReport {
  team_id: number;
  abbreviation: string;
  season: string;
  status: "ready" | "limited";
  window_games: number;
  starter_stability: "stable" | "mixed" | "volatile";
  recent_starters: TeamRotationPlayerRow[];
  minute_load_leaders: TeamRotationPlayerRow[];
  rotation_risers: TeamRotationPlayerRow[];
  rotation_fallers: TeamRotationPlayerRow[];
  on_off_anchors: TeamImpactLeader[];
  recommended_games: TeamRotationGame[];
}

export interface PlayerTrendForm {
  games: number;
  avg_minutes: number | null;
  avg_points: number | null;
  avg_rebounds: number | null;
  avg_assists: number | null;
  avg_fg_pct: number | null;
  avg_fg3_pct: number | null;
  avg_plus_minus: number | null;
}

export interface PlayerTrendSignals {
  minutes_delta: number | null;
  points_delta: number | null;
  efficiency_delta: number | null;
  starts_last_10: number;
  bench_games_last_10: number;
  games_30_plus_last_10: number;
  games_under_20_last_10: number;
  minute_volatility: number | null;
}

export interface PlayerTrendImpactSnapshot {
  pbp_coverage_status: "ready" | "partial" | "none";
  on_off_net: number | null;
  on_minutes: number | null;
  bpm: number | null;
  per: number | null;
  pts_pg: number | null;
  ts_pct: number | null;
}

export interface PlayerTrendGame {
  game_id: string;
  game_date: string | null;
  matchup: string | null;
  result: string | null;
  minutes: number | null;
  points: number | null;
  plus_minus: number | null;
  is_starter: boolean;
  trend_note: string;
}

export interface PlayerTrendReport {
  player_id: number;
  player_name: string;
  team_abbreviation: string | null;
  season: string;
  status: "ready" | "limited";
  window_games: number;
  role_status:
    | "entrenched_starter"
    | "rising_rotation"
    | "losing_trust"
    | "volatile_role"
    | "stable_rotation";
  recent_form: PlayerTrendForm;
  season_baseline: PlayerTrendForm;
  trust_signals: PlayerTrendSignals;
  impact_snapshot: PlayerTrendImpactSnapshot;
  recommended_games: PlayerTrendGame[];
}

export interface CustomMetricComponent {
  stat_id: string;
  label: string;
  weight: number;
  inverse: boolean;
}

export interface CustomMetricConfig {
  metric_name?: string;
  player_pool: "all" | "position_filter" | "team_filter";
  season: string;
  team_abbreviation?: string;
  position?: string;
  components: CustomMetricComponent[];
}

export interface CustomMetricPlayerRanking {
  rank: number;
  player_name: string;
  team: string;
  composite_score: number;
  component_breakdown: Record<string, number>;
}

export interface CustomMetricNarrative {
  player_name: string;
  narrative: string;
}

export interface CustomMetricAnomaly {
  player_name: string;
  dominant_stat: string;
  contribution_pct: number;
}

export interface CustomMetricResponse {
  metric_label: string;
  metric_interpretation: string;
  player_rankings: CustomMetricPlayerRanking[];
  top_player_narratives: CustomMetricNarrative[];
  anomalies: CustomMetricAnomaly[];
  validation_warnings: string[];
}

export interface TrajectoryPlayerRow {
  rank: number;
  player_name: string;
  team: string;
  trajectory_label: string;
  trajectory_score: number;
  key_stat_deltas: Record<string, number>;
  narrative: string;
  context_flags: string[];
}

export interface TrajectoryResponse {
  window: string;
  breakout_leaders: TrajectoryPlayerRow[];
  decline_watch: TrajectoryPlayerRow[];
  excluded_players: string[];
  warnings: string[];
}

export interface CourtVueMetricPlayerRanking {
  rank: number;
  player_id: number;
  player_name: string;
  team: string;
  composite_score: number;
  component_breakdown: Record<string, number>;
}

export interface CourtVueMetricResponse {
  metric_label: string;
  metric_interpretation: string;
  player_rankings: CourtVueMetricPlayerRanking[];
  top_player_narratives: CustomMetricNarrative[];
  anomalies: CustomMetricAnomaly[];
  validation_warnings: string[];
}

export interface TeamComparisonSnapshot {
  abbreviation: string;
  name: string;
  season: string;
  recent_record: string | null;
  net_rating: number | null;
  ts_pct: number | null;
  efg_pct: number | null;
  tov_pg: number | null;
  reb_pg: number | null;
  pace: number | null;
}

export interface TeamComparisonRow {
  stat_id: string;
  label: string;
  team_a_value: number | null;
  team_b_value: number | null;
  higher_better: boolean;
  format: "number" | "percent" | "signed";
  edge: "team_a" | "team_b" | "even";
}

export interface TeamComparisonStory {
  label: string;
  summary: string;
  edge: "team_a" | "team_b" | "even";
}

export interface TeamComparisonResponse {
  season: string;
  team_a: TeamComparisonSnapshot;
  team_b: TeamComparisonSnapshot;
  rows: TeamComparisonRow[];
  stories: TeamComparisonStory[];
}

export interface TeamFactorRow {
  factor_id: "shooting" | "turnovers" | "rebounding" | "free_throws";
  label: string;
  team_value: number | null;
  opponent_value: number | null;
  league_reference: number | null;
  margin_signal: number | null;
  note: string;
}

export interface TeamFocusLever {
  title: string;
  summary: string;
  impact_label: string;
  factor_id: "shooting" | "turnovers" | "rebounding" | "free_throws";
}

export interface TeamFocusLeversReport {
  team_abbreviation: string;
  team_name: string;
  season: string;
  factor_rows: TeamFactorRow[];
  focus_levers: TeamFocusLever[];
}

export interface UsageEfficiencyPlayerRow {
  player_id: number;
  player_name: string;
  team_abbreviation: string;
  minutes_pg: number | null;
  usg_pct: number | null;
  ts_pct: number | null;
  off_rating: number | null;
  pts_pg: number | null;
  ast_pg: number | null;
  tov_pg: number | null;
  burden_score: number | null;
  efficiency_score: number | null;
  category: "overused" | "underused";
}

export interface UsageEfficiencySuggestion {
  player_name: string;
  category: "overused" | "underused";
  suggestion: string;
}

export interface UsageEfficiencyResponse {
  season: string;
  team: string | null;
  min_minutes: number;
  overused_inefficients: UsageEfficiencyPlayerRow[];
  underused_efficients: UsageEfficiencyPlayerRow[];
  suggestions: UsageEfficiencySuggestion[];
  warnings: string[];
}

export interface PreReadAdjustment {
  label: string;
  recommendation: string;
}

export interface PreReadSlide {
  title: string;
  eyebrow: string;
  bullets: string[];
}

export interface PreReadDeckResponse {
  season: string;
  team_abbreviation: string;
  opponent_abbreviation: string;
  focus_levers: TeamFocusLever[];
  matchup_advantages: string[];
  adjustments: PreReadAdjustment[];
  slides: PreReadSlide[];
}

export interface ConfidenceSummary {
  level: "high" | "medium" | "low";
  label: string;
  note: string;
}

export interface InsightDrilldown {
  label: string;
  href: string;
  reason: string;
}

export interface FollowThroughSupportingMetric {
  label: string;
  value: number | string | null;
}

export interface FollowThroughGame {
  game_id: string;
  game_date: string | null;
  opponent_abbreviation: string | null;
  why_this_game: string;
  relevance_score: number;
  supporting_metrics: FollowThroughSupportingMetric[];
  deep_link_url: string;
}

export interface FollowThroughResponse {
  source_type: string;
  source_id: string;
  games: FollowThroughGame[];
}

export interface LineupImpactRow {
  lineup_key: string;
  player_names: string[];
  minutes: number | null;
  possessions: number | null;
  observed_net_rating: number | null;
  shrunk_net_rating: number | null;
  expected_points_delta_per_game: number | null;
  expected_points_delta_per_100: number | null;
  recommended_minute_delta: number | null;
  confidence: ConfidenceSummary;
  top_drivers: string[];
  drilldowns: InsightDrilldown[];
}

export interface LineupImpactRotationSummary {
  current_rotation_note: string;
  recommended_rotation_note: string;
}

export interface LineupImpactResponse {
  team: string;
  opponent: string | null;
  season: string;
  filters: Record<string, string | number | null>;
  current_rotation: LineupImpactRotationSummary;
  recommended_rotation: LineupImpactRotationSummary;
  lineup_rows: LineupImpactRow[];
  impact_summary: string;
  confidence: ConfidenceSummary;
  warnings: string[];
}

export interface PlayTypeEvidence {
  label: string;
  value: number | string | null;
}

export interface PlayTypeActionRow {
  action_family: string;
  usage_rate: number | null;
  efficiency_value: number | null;
  turnover_drag: number | null;
  foul_pressure_bonus: number | null;
  second_chance_bonus: number | null;
  contextual_percentile: number | null;
  confidence: ConfidenceSummary;
  proxy_note: string;
  evidence: PlayTypeEvidence[];
}

export interface PlayTypeFlag {
  action_family: string;
  title: string;
  summary: string;
  severity: "high" | "medium" | "low";
  confidence: ConfidenceSummary;
}

export interface PlayTypeEVResponse {
  team: string;
  opponent: string | null;
  season: string;
  window: number;
  action_rows: PlayTypeActionRow[];
  overused_flags: PlayTypeFlag[];
  underused_flags: PlayTypeFlag[];
  warnings: string[];
}

export interface MatchupFlagEvidence {
  label: string;
  value: number | string | null;
}

export interface MatchupFlag {
  flag_id: string;
  title: string;
  summary: string;
  severity: "high" | "medium" | "low";
  confidence: ConfidenceSummary;
  evidence: MatchupFlagEvidence[];
  drilldowns: InsightDrilldown[];
}

export interface MatchupFlagsResponse {
  team: string;
  opponent: string;
  season: string;
  flags: MatchupFlag[];
  warnings: string[];
}

export interface StyleMetric {
  stat_id: string;
  label: string;
  team_value: number | null;
  league_percentile: number | null;
  trend_delta: number | null;
  note: string;
}

export interface StyleScenarioBin {
  label: string;
  pace_band: string;
  sample_size: number;
  expected_offense_delta: number | null;
  expected_defense_delta: number | null;
  summary: string;
}

export interface TeamStyleProfileResponse {
  team_abbreviation: string;
  season: string;
  window: number;
  current_profile: StyleMetric[];
  recent_drift: StyleMetric[];
  opponent_comparison: StyleMetric[] | null;
  scenario_bins: StyleScenarioBin[];
  warnings: string[];
}

export interface StyleNeighbor {
  team_abbreviation: string;
  season: string;
  distance: number;
  reason: string;
}

export interface StyleXRayResponse {
  team_abbreviation: string;
  season: string;
  window: number;
  archetype: string;
  stability: string;
  feature_contributors: StyleMetric[];
  nearest_neighbors: StyleNeighbor[];
  adjacent_archetypes: string[];
  warnings: string[];
}

export interface ScenarioDriverFeature {
  label: string;
  weight: number | null;
  explanation: string;
}

export interface ScenarioComparablePattern {
  label: string;
  season: string;
  summary: string;
}

export interface WhatIfScenarioResponse {
  team_abbreviation: string;
  season: string;
  scenario_type: string;
  delta: number;
  expected_direction: string;
  confidence: ConfidenceSummary;
  range: {
    low: number | null;
    median: number | null;
    high: number | null;
  };
  driver_features: ScenarioDriverFeature[];
  comparable_patterns: ScenarioComparablePattern[];
  warnings: string[];
}

export interface TrendCardStat {
  label: string;
  value: number | null;
}

export interface TrendCardPoint {
  label: string;
  value: number | null;
}

export interface TrendCard {
  card_id: string;
  title: string;
  direction: "up" | "down" | "flat";
  magnitude: string;
  significance: "high" | "medium" | "low";
  summary: string;
  series: TrendCardPoint[];
  supporting_stats: TrendCardStat[];
  drilldowns: InsightDrilldown[];
}

export interface TrendCardsResponse {
  team_abbreviation: string;
  season: string;
  window: string;
  cards: TrendCard[];
  warnings: string[];
}

export interface ScoutingClaim {
  claim_id: string;
  title: string;
  summary: string;
  evidence: MatchupFlagEvidence[];
  drilldowns: InsightDrilldown[];
}

export interface ScoutingSection {
  title: string;
  claims: ScoutingClaim[];
}

export interface PlayTypeScoutingReportResponse {
  team_abbreviation: string;
  opponent_abbreviation: string;
  season: string;
  report: string;
  sections: ScoutingSection[];
  print_meta: {
    title: string;
    subtitle: string;
  };
  warnings: string[];
}

export interface LineupComparisonEntity {
  lineup_key: string;
  player_names: string[];
  team_abbreviation: string;
  minutes: number | null;
  possessions: number | null;
  net_rating: number | null;
}

export interface LineupComparisonRow {
  stat_id: string;
  label: string;
  entity_a_value: number | null;
  entity_b_value: number | null;
  higher_better: boolean;
  format: "number" | "percent" | "signed";
  edge: "entity_a" | "entity_b" | "even";
}

export interface LineupComparisonResponse {
  season: string;
  entity_a: LineupComparisonEntity;
  entity_b: LineupComparisonEntity;
  rows: LineupComparisonRow[];
  stories: TeamComparisonStory[];
  source_context: Record<string, string | null>;
}

export interface StyleComparisonEntity {
  team_abbreviation: string;
  archetype: string;
  season: string;
  window: number;
}

// Sprint 26 — Injuries

export interface InjuryEntry {
  player_id: number;
  player_name: string;
  report_date: string;
  return_date: string | null;
  injury_type: string | null;
  injury_status: string | null;
  detail: string | null;
  comment: string | null;
  season: string | null;
}

export interface InjuryReportResponse {
  report_date: string;
  count: number;
  injuries: InjuryEntry[];
}

export interface StyleComparisonResponse {
  season: string;
  entity_a: StyleComparisonEntity;
  entity_b: StyleComparisonEntity;
  rows: TeamComparisonRow[];
  stories: TeamComparisonStory[];
  source_context: Record<string, string | null>;
}

// Sprint 27 — Availability + upcoming schedule

export interface UpcomingScheduleGame {
  game_id: string;
  season: string;
  game_date: string | null;
  status: string;
  home_team_abbreviation: string | null;
  home_team_name: string | null;
  away_team_abbreviation: string | null;
  away_team_name: string | null;
}

export interface TeamUpcomingGameSummary {
  game_id: string;
  game_date: string | null;
  opponent_abbreviation: string | null;
  opponent_name: string | null;
  is_home: boolean;
  status: string;
}

export interface TeamAvailabilityPlayer {
  player_id: number;
  player_name: string;
  position: string;
  jersey: string;
  headshot_url: string;
  injury_status: string | null;
  injury_type: string | null;
  detail: string | null;
  comment: string | null;
  return_date: string | null;
  pts_pg: number | null;
  bpm: number | null;
  impact_label: string;
}

export interface TeamAvailabilityResponse {
  team_id: number;
  abbreviation: string;
  name: string;
  season: string;
  report_date: string | null;
  overall_status: "healthy" | "monitor" | "shorthanded" | "unknown";
  summary: string;
  available_count: number;
  unavailable_count: number;
  questionable_count: number;
  probable_count: number;
  next_game: TeamUpcomingGameSummary | null;
  key_absences: TeamAvailabilityPlayer[];
  unavailable_players: TeamAvailabilityPlayer[];
  questionable_players: TeamAvailabilityPlayer[];
  probable_players: TeamAvailabilityPlayer[];
}

export interface PreReadDeckResponse {
  team_availability: TeamAvailabilityResponse;
  opponent_availability: TeamAvailabilityResponse;
}

// Sprint 28 — Compare Availability

export interface PlayerAvailabilitySlot {
  player_id: number;
  injury_status: string;
  injury_type: string | null;
  detail: string | null;
  return_date: string | null;
  report_date: string;
}

export interface CompareAvailabilityResponse {
  player_a: PlayerAvailabilitySlot | null;
  player_b: PlayerAvailabilitySlot | null;
}

// Sprint 28 — Unresolved injury identity ops

export interface InjurySyncUnresolvedEntry {
  id: number;
  season: string;
  report_date: string;
  team_abbreviation: string;
  team_name: string;
  player_name: string;
  injury_status: string;
  injury_type: string;
  detail: string;
  source: string;
  source_url: string | null;
  normalized_lookup_key: string;
}
