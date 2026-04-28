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
  metric_values: Record<string, number | null>;
}

export interface LeaderboardResponse {
  stat: string;
  season: string;
  season_type: string;
  entries: LeaderboardEntry[];
}

export interface QueryAskRequest {
  question: string;
  season?: string;
  limit?: number;
}

export interface QueryMetricMetadata {
  key: string;
  label: string;
  description: string;
  format: "number" | "integer" | "percent" | "record";
  category: string;
  aliases: string[];
  entity_types: Array<"player" | "team">;
  higher_is_better: boolean;
  source: string;
}

export interface QueryExample {
  category: string;
  prompt: string;
  description: string;
}

export interface QueryFilter {
  metric_key: string;
  label: string;
  operator: "gte" | "lte";
  value: number;
  formatted_value: string;
}

export interface QueryIntent {
  intent_type: string;
  entity_type: "player" | "team" | null;
  metric_key: string | null;
  metric_label: string | null;
  season: string | null;
  sort_direction: "asc" | "desc" | null;
  limit: number;
  confidence: number;
  normalized_question: string;
  filters: QueryFilter[];
}

export interface QueryResultRow {
  rank: number;
  entity_type: "player" | "team" | "game" | "link";
  entity_id: string | null;
  name: string;
  subtitle: string | null;
  team_abbreviation: string | null;
  abbreviation: string | null;
  value: number | null;
  formatted_value: string | null;
  detail_url: string | null;
  metrics: Record<string, string | number | null>;
}

export interface QueryAnswerCard {
  title: string;
  summary: string;
  primary_label: string | null;
  primary_value: string | null;
  href: string | null;
}

export interface QueryAskResponse {
  question: string;
  status: "ready" | "empty" | "needs_clarification";
  answer: QueryAnswerCard;
  intent: QueryIntent;
  rows: QueryResultRow[];
  metrics: QueryMetricMetadata[];
  warnings: string[];
  suggestions: string[];
  source: string;
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
  gp: number | null;
  pts_pg: number | null;
  opp_pts_pg: number | null;
  diff_pts_pg: number | null;
  reb_pg: number | null;
  ast_pg: number | null;
  tov_pg: number | null;
  stl_pg: number | null;
  blk_pg: number | null;
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
  current_streak: string;
  recent_trend: {
    games: {
      date: string;
      won: boolean;
      margin: number;
      is_home: boolean;
      opponent_abbreviation: string | null;
    }[];
    last_10_record: string;
    avg_margin: number;
    direction: string;
  } | null;
  clinch_indicator: string | null;
}

export interface TeamAnalytics {
  team_id: number;
  abbreviation: string;
  name: string;
  season: string;
  canonical_source?: string | null;
  last_synced_at?: string | null;
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
  data_status: "ready" | "partial" | "limited" | "missing";
  canonical_source: string;
  last_synced_at: string | null;
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

export interface TeamPrepQueueItem {
  game_id: string;
  game_date: string | null;
  status: string;
  prep_urgency: "high" | "medium" | "standard" | string;
  prep_headline: string;
  urgency_rationale: string | null;
  opponent_abbreviation: string | null;
  opponent_name: string | null;
  is_home: boolean;
  opponent_record: string | null;
  opponent_conference: string | null;
  opponent_playoff_rank: number | null;
  availability_summary: string;
  unavailable_count: number;
  questionable_count: number;
  probable_count: number;
  team_rest_days: number | null;
  opponent_rest_days: number | null;
  rest_advantage: number | null;
  schedule_pressure: string;
  best_edge_label: string | null;
  best_edge_summary: string | null;
  best_edge_rationale: string | null;
  best_edge_factor_id: "shooting" | "turnovers" | "rebounding" | "free_throws" | null;
  first_adjustment_label: string | null;
  first_adjustment_summary: string | null;
  first_adjustment_rationale: string | null;
  first_adjustment_factor_id: "shooting" | "turnovers" | "rebounding" | "free_throws" | null;
  pre_read_url: string;
  scouting_url: string;
  compare_url: string;
  follow_through_url: string;
  game_review_url: string;
  latest_snapshot_id: string | null;
  latest_snapshot_share_url: string | null;
}

export interface TeamPrepQueueResponse {
  team_id: number;
  abbreviation: string;
  name: string;
  season: string;
  data_status: "ready" | "partial" | "limited" | "missing";
  canonical_source: string;
  generated_at: string | null;
  items: TeamPrepQueueItem[];
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
  context_flags: string[];
  role_status_reason: string | null;
  injury_context: string | null;
  adjusted_role_status: string | null;
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

export interface TrajectoryDriverContribution {
  signal: string;
  delta: number;
  weighted_contribution: number;
}

export interface TrajectoryEvidenceGame {
  game_id: string;
  date: string | null;
  opponent: string | null;
  result: string | null;
  headline_stat: string;
}

export interface TrajectoryClutchContext {
  clutch_pts: number | null;
  clutch_fg_pct: number | null;
  clutch_fga: number | null;
}

export interface TrajectoryOnOffContext {
  on_off_net: number | null;
  on_minutes: number | null;
  off_minutes: number | null;
  confidence: string;
}

export interface TrajectoryPlayerRow {
  rank: number;
  player_id: number;
  player_name: string;
  team: string;
  position: string | null;
  trajectory_label: string;
  trajectory_score: number;
  position_percentile: number | null;
  key_stat_deltas: Record<string, number>;
  driver_contributions: TrajectoryDriverContribution[];
  narrative: string;
  context_flags: string[];
  evidence_games: TrajectoryEvidenceGame[];
  clutch_context: TrajectoryClutchContext | null;
  on_off_context: TrajectoryOnOffContext | null;
  recent_averages: Record<string, number | null>;
  baseline_averages: Record<string, number | null>;
}

export interface TrajectoryResponse {
  window: string;
  breakout_leaders: TrajectoryPlayerRow[];
  decline_watch: TrajectoryPlayerRow[];
  excluded_players: string[];
  warnings: string[];
}

export interface TrajectorySeriesGame {
  game_id: string;
  date: string | null;
  pts: number | null;
  reb: number | null;
  ast: number | null;
  ts_pct: number | null;
  usg_pct: number | null;
  plus_minus: number | null;
  is_recent: boolean;
}

export interface TrajectorySeriesResponse {
  player_id: number;
  player_name: string;
  season: string;
  series: TrajectorySeriesGame[];
}

export interface TeammateOnOff {
  teammate_id: number;
  teammate_name: string;
  shared_minutes: number | null;
  possessions: number | null;
  net_rating_with: number | null;
  confidence: string;
}

export interface LineupContextResponse {
  player_id: number;
  player_name: string;
  season: string;
  on_off_net: number | null;
  on_minutes: number | null;
  off_minutes: number | null;
  top_teammates: TeammateOnOff[];
  notes: string[];
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
  source_context?: Record<string, string> | null;
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
  rationale: string | null;
  coaching_prompt: string | null;
  projected_impact: string | null;
  opponent_context: string | null;
}

export interface TeamFocusLeversReport {
  team_abbreviation: string;
  team_name: string;
  season: string;
  factor_rows: TeamFactorRow[];
  focus_levers: TeamFocusLever[];
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

export interface WorkflowLaunchLinks {
  pre_read_url: string;
  scouting_url: string;
  compare_url: string;
  prep_url: string;
  follow_through_url: string;
  game_review_url: string;
}

export interface PreReadSnapshotRef {
  snapshot_id: string;
  share_url: string;
  created_at: string;
}

export interface PreReadPrepContext {
  prep_item: TeamPrepQueueItem | null;
  urgency: string | null;
  headline: string | null;
  urgency_rationale: string | null;
  best_edge_label: string | null;
  best_edge_rationale: string | null;
  first_adjustment_label: string | null;
  first_adjustment_rationale: string | null;
}

export interface PreReadDeckResponse {
  season: string;
  team_abbreviation: string;
  opponent_abbreviation: string;
  data_status: "ready" | "partial" | "limited" | "missing";
  canonical_source: string;
  generated_at: string | null;
  focus_levers: TeamFocusLever[];
  matchup_advantages: string[];
  adjustments: PreReadAdjustment[];
  slides: PreReadSlide[];
  launch_links: WorkflowLaunchLinks;
  prep_context: PreReadPrepContext | null;
  snapshot: PreReadSnapshotRef | null;
  warnings: string[];
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
  result: string | null;
  why_this_game: string;
  relevance_score: number;
  supporting_metrics: string[];
  deep_link_url: string;
}

export interface FollowThroughResponse {
  source_type: string;
  source_id: string;
  team_abbreviation: string;
  opponent_abbreviation: string | null;
  season: string;
  window: number;
  games: FollowThroughGame[];
  warnings: string[];
}

export interface LineupImpactFilters {
  season: string;
  opponent_abbreviation: string | null;
  window_games: number;
  min_possessions: number;
}

export interface LineupImpactRow {
  lineup_key: string;
  player_ids: number[];
  player_names: string[];
  minutes: number | null;
  possessions: number | null;
  observed_net_rating: number | null;
  shrunk_net_rating: number | null;
  expected_points_per_100: number | null;
  expected_points_per_game: number | null;
  minute_delta: number | null;
  confidence: "high" | "medium" | "low";
  evidence: string[];
}

export interface LineupImpactResponse {
  team_abbreviation: string;
  season: string;
  filters: LineupImpactFilters;
  current_rotation: LineupImpactRow[];
  recommended_rotation: LineupImpactRow[];
  lineup_rows: LineupImpactRow[];
  impact_summary: string;
  confidence: "high" | "medium" | "low";
  warnings: string[];
}

export interface PlayTypeEvidence {
  label: string;
  value: number | string | null;
}

export interface PlayTypeActionRow {
  action_family: string;
  label: string;
  usage_share: number | null;
  points_per_possession: number | null;
  turnover_rate: number | null;
  foul_rate: number | null;
  offensive_rebound_rate: number | null;
  ev_score: number | null;
  league_percentile: number | null;
  note: string;
}

export interface PlayTypeFlag {
  action_family: string;
  label: string;
  reason: string;
  severity: "high" | "medium" | "low";
  confidence: "high" | "medium" | "low";
  evidence: string[];
}

export interface PlayTypeEVResponse {
  team_abbreviation: string;
  season: string;
  filters: {
    season: string;
    opponent_abbreviation: string | null;
    window_games: number;
  };
  action_rows: PlayTypeActionRow[];
  overused_flags: PlayTypeFlag[];
  underused_flags: PlayTypeFlag[];
  warnings: string[];
}

export interface MatchupFlagEvidence {
  metric_id: string;
  label: string;
  team_value: number | null;
  opponent_value: number | null;
  league_reference: number | null;
  note: string;
}

export interface MatchupFlag {
  flag_id: string;
  title: string;
  summary: string;
  severity: "high" | "medium" | "low";
  confidence: "high" | "medium" | "low";
  evidence: MatchupFlagEvidence[];
  drilldowns: string[];
}

export interface MatchupFlagsResponse {
  team_abbreviation: string;
  opponent_abbreviation: string;
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
  team_name: string;
  archetype: string;
  net_rating: number | null;
  season: string;
  distance: number;
  quality?: "high" | "medium" | "low";
  summary: string;
}

export interface StyleFeatureMovement {
  metric_id: string;
  label: string;
  baseline_z: number | null;
  recent_z: number | null;
  delta_z: number | null;
  direction: "gaining" | "stable" | "fading";
}

export interface StyleMovement {
  narrative: string;
  drift_archetype: string | null;
  window_games: number;
  features: StyleFeatureMovement[];
}

export interface StyleScenarioLink {
  scenario_type: string;
  title: string;
  delta: number;
  rationale: string;
  what_if_payload: Record<string, string>;
}

export interface StyleXRayResponse {
  data_status: "ready" | "partial" | "limited" | "missing";
  canonical_source: string;
  team_abbreviation: string;
  team_name: string;
  season: string;
  window_games: number;
  archetype: string;
  archetype_confidence?: "high" | "medium" | "low";
  label_reason: string;
  stability: string;
  movement?: StyleMovement | null;
  feature_contributors: Array<{
    metric_id: string;
    label: string;
    value: number | null;
    share: number | null;
    note: string;
  }>;
  nearest_neighbors: StyleNeighbor[];
  adjacent_archetypes: StyleNeighbor[];
  scenario_links: StyleScenarioLink[];
  launch_links: {
    prep_url: string | null;
    compare_url: string;
  };
  source_context: Record<string, string> | null;
  warnings: string[];
}

export interface ScenarioDriverFeature {
  metric_id: string;
  label: string;
  value: number | null;
  league_reference: number | null;
  note: string;
}

export interface ScenarioComparablePattern {
  team_abbreviation: string;
  team_name: string | null;
  season: string;
  archetype: string | null;
  summary: string;
  distance: number | null;
}

export interface ReplayLaunchTarget {
  source_surface: string;
  source_label: string;
  reason: string;
  target_game_id: string;
  target_game_date: string | null;
  target_opponent_abbreviation: string | null;
  focus_event_id: string | null;
  focused_action_number: number | null;
  linkage_quality: "exact" | "derived" | "timeline";
  deep_link_url: string;
}

export interface WhatIfScenarioResponse {
  data_status: "ready" | "partial" | "limited" | "missing";
  canonical_source: string;
  context: {
    team: string;
    season: string;
    window: number;
    opponent: string | null;
    source_view: string | null;
    source_snapshot_id: string | null;
  };
  team_abbreviation: string;
  season: string;
  scenario_type: string;
  scenario_label: string;
  delta: number;
  expected_direction: string;
  summary: string;
  directional_note: string | null;
  confidence: "high" | "medium" | "low";
  lower_bound: number | null;
  upper_bound: number | null;
  driver_features: ScenarioDriverFeature[];
  comparable_patterns: ScenarioComparablePattern[];
  style_implication: {
    archetype: string;
    label_reason: string;
    stability: string;
    opposing_tension: string | null;
    relevant_contributors: string[];
  };
  launch_links: {
    prep_url: string | null;
    compare_url: string;
    style_xray_url: string;
    replay_url: string | null;
  };
  replay_target: ReplayLaunchTarget | null;
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

export interface TrendOverview {
  headline: string;
  recent_record: string | null;
  recent_net_rating: number | null;
  baseline_net_rating: number | null;
  recent_ts_pct: number | null;
  baseline_ts_pct: number | null;
  recent_pace: number | null;
  baseline_pace: number | null;
  games_in_window: number;
  player_count: number;
}

export interface TrendCard {
  card_id: string;
  title: string;
  scope: "team" | "player" | "lineup";
  driver_signal: string | null;
  direction: "up" | "down" | "flat";
  magnitude: number | null;
  significance: "high" | "medium" | "low";
  summary: string;
  series: TrendCardPoint[];
  supporting_stats: Record<string, number | null>;
  drilldowns: string[];
  related_player_ids: number[];
  replay_target: ReplayLaunchTarget | null;
}

export interface TrendDriverContribution {
  signal: string;
  label: string;
  value: number | null;
  contribution: number;
  note: string;
}

export interface TrendPlayerRow {
  player_id: number;
  player_name: string;
  team_abbreviation: string;
  position: string | null;
  trend_score: number;
  trend_label: string;
  primary_signal: string;
  confidence: "high" | "medium" | "low";
  recent_games: number;
  recent_pts_pg: number | null;
  baseline_pts_pg: number | null;
  recent_ts_pct: number | null;
  baseline_ts_pct: number | null;
  recent_minutes_pg: number | null;
  baseline_minutes_pg: number | null;
  on_off_net: number | null;
  gravity_score: number | null;
  shot_quality_delta: number | null;
  driver_contributions: TrendDriverContribution[];
  warnings: string[];
}

export interface TrendFoundationSignal {
  signal: string;
  label: string;
  value: number | null;
  context: string;
  status: "ready" | "partial" | "missing";
}

export interface TrendPlayerDetail {
  row: TrendPlayerRow;
  foundation: TrendFoundationSignal[];
  recent_series: TrendCardPoint[];
  drilldowns: string[];
}

export interface TrendMethodology {
  version: string;
  window_games: number;
  scoring_inputs: string[];
  coverage_notes: string[];
}

export interface TrendCardsResponse {
  team_abbreviation: string;
  team_name: string;
  season: string;
  data_status: "ready" | "partial" | "limited" | "missing";
  overview: TrendOverview | null;
  window_games: number;
  cards: TrendCard[];
  player_movers: TrendPlayerRow[];
  pinned_player: TrendPlayerDetail | null;
  methodology: TrendMethodology | null;
  warnings: string[];
}

export interface ClaimInferenceConfidence {
  level: "high" | "medium" | "low";
  reasons: string[];
  anchored_event_count: number;
  opponent_specific_event_count: number;
  evidence_source_diversity: number;
}

export interface ScoutingClaim {
  claim_id: string;
  title: string;
  summary: string;
  evidence: {
    label: string;
    value: number | string | null;
    context?: string | null;
  }[];
  drilldowns: InsightDrilldown[];
  clip_anchor_ids: string[];
  inference_confidence?: ClaimInferenceConfidence | null;
}

export interface ScoutingSection {
  eyebrow: string;
  title: string;
  claims: ScoutingClaim[];
}

export interface ScoutingClipAnchor {
  clip_anchor_id: string;
  claim_id: string;
  game_id: string;
  game_date: string | null;
  opponent_abbreviation: string | null;
  event_id: number | null;
  source_event_id?: string | null;
  action_number: number | null;
  order_index?: number | null;
  period: number | null;
  clock: string | null;
  event_type?: string | null;
  action_family?: string | null;
  title: string;
  reason: string;
  evidence_summary: string;
  event_description?: string | null;
  linkage_quality?: "exact" | "derived" | "timeline";
  source_context?: Record<string, string> | null;
  deep_link_url: string;
  opponent_specific?: boolean;
}

export interface PlayTypeScoutingReportResponse {
  team_abbreviation: string;
  opponent_abbreviation: string;
  season: string;
  data_status: "ready" | "partial" | "limited" | "missing";
  sections: ScoutingSection[];
  clip_anchors: ScoutingClipAnchor[];
  launch_context: {
    pre_read_url: string;
    scouting_url: string;
    compare_url: string;
    export_url: string;
  };
  print_meta: {
    report_title: string;
    season: string;
    format: string;
    generated_from: string;
  };
  warnings: string[];
}

export interface ScoutingClipExportResponse {
  team_abbreviation: string;
  opponent_abbreviation: string;
  season: string;
  data_status: "ready" | "partial" | "limited" | "missing";
  export_title: string;
  clip_count: number;
  clip_anchors: ScoutingClipAnchor[];
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

export interface PreReadSnapshotSummary {
  snapshot_id: string;
  share_url: string;
  created_at: string;
  team_abbreviation: string;
  opponent_abbreviation: string;
  season: string;
  game_id: string | null;
  prep_headline: string | null;
  saved_from: string | null;
}

export interface PreReadSnapshotResponse {
  snapshot_id: string;
  share_url: string;
  created_at: string;
  context: {
    team_abbreviation: string;
    opponent_abbreviation: string;
    season: string;
    game_id: string | null;
    source_view: string | null;
    source_snapshot_id: string | null;
    extras: Record<string, string>;
  };
  deck: PreReadDeckResponse;
}

export interface PreReadSnapshotListResponse {
  items: PreReadSnapshotSummary[];
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

// Sprint 29 — Standings history

export interface StandingsSnapshot {
  date: string;       // ISO "YYYY-MM-DD"
  wins: number;
  losses: number;
  win_pct: number;
}

export interface StandingsHistoryEntry {
  team_id: number;
  team_abbr: string;
  conference: string;
  snapshots: StandingsSnapshot[];
}

// Sprint 29 — Shot zone analytics

export interface ZoneStat {
  zone_basic: string;
  zone_area: string;
  attempts: number;
  made: number;
  fg_pct: number | null;
  pps: number | null;
  freq: number;
}

export interface ZoneProfileResponse {
  player_id: number;
  season: string;
  season_type: string;
  total_attempts: number;
  zones: ZoneStat[];
}

export type ShotChartDataStatus = "ready" | "stale" | "missing";

export interface PersistedShotChartResponse extends ShotChartResponse {
  data_status: ShotChartDataStatus;
  last_synced_at: string | null;
}

export interface PersistedZoneProfileResponse extends ZoneProfileResponse {
  data_status: ShotChartDataStatus;
  last_synced_at: string | null;
}

export interface DbFirstPlayerProfile extends PlayerProfile {
  data_status: ShotChartDataStatus;
  last_synced_at: string | null;
}

export interface DbFirstCareerStatsResponse extends CareerStatsResponse {
  data_status: ShotChartDataStatus;
  last_synced_at: string | null;
}

export interface DbFirstGameLogResponse extends GameLogResponse {
  data_status: ShotChartDataStatus;
  last_synced_at: string | null;
}

export interface WarehouseReadinessDomain {
  domain: string;
  eligible_count: number;
  ready_count: number;
  stale_count: number;
  missing_count: number;
}

export interface WarehouseReadinessSummary {
  season: string;
  domains: WarehouseReadinessDomain[];
}

// Sprint 35 — Shot lab expansion

export interface ShotChartShot {
  game_id?: string | null;
  game_date?: string | null;
}

export interface ShotChartResponse {
  start_date?: string | null;
  end_date?: string | null;
  available_start_date?: string | null;
  available_end_date?: string | null;
  available_game_dates?: string[];
}

export interface ZoneProfileResponse {
  start_date?: string | null;
  end_date?: string | null;
  available_start_date?: string | null;
  available_end_date?: string | null;
}

export interface ShotLabDateRange {
  startDate: string | null;
  endDate: string | null;
}

export type ShotLabWindowPreset =
  | "full"
  | "last-5-games"
  | "last-10-games"
  | "last-30-days"
  | "custom";

// Sprint 37 — Situational shot intelligence

export type ShotLabPeriodBucket = "all" | "q1" | "q2" | "q3" | "q4" | "ot";
export type ShotLabResultFilter = "all" | "made" | "missed";
export type ShotLabShotValueFilter = "all" | "2pt" | "3pt";

export interface ShotLabSituationalFilters {
  periodBucket: ShotLabPeriodBucket;
  result: ShotLabResultFilter;
  shotValue: ShotLabShotValueFilter;
}

export interface ShotLabFilters extends ShotLabDateRange, ShotLabSituationalFilters {}

export interface ShotChartShot {
  period?: number | null;
  clock?: string | null;
  minutes_remaining?: number | null;
  seconds_remaining?: number | null;
  shot_value?: number | null;
  shot_event_id?: string | null;
}

export interface ZoneProfileResponse {
  available_game_dates?: string[];
}

export interface QueueResponse {
  queued: number;
  jobs: IngestionJobResponse[];
}

// Sprint 38 — Platform overhaul

export type ShotCompletenessStatus = "ready" | "partial" | "legacy" | "missing";

export interface ShotCompletenessSummary {
  status: ShotCompletenessStatus;
  total_shots: number;
  contextual_shots: number;
  linked_shots: number;
  exact_linked_shots: number;
  completeness_pct: number;
  linked_pct: number;
  missing_context_fields: string[];
}

export interface ShotChartShot {
  team_id?: number | null;
  team_abbreviation?: string | null;
  opponent_team_id?: number | null;
  opponent_team_abbreviation?: string | null;
  home_score?: number | null;
  away_score?: number | null;
  score_margin?: number | null;
  event_order_index?: number | null;
  action_number?: number | null;
  linkage_mode?: string | null;
}

export interface PersistedShotChartResponse {
  completeness_status?: ShotCompletenessStatus;
  missing_context_fields?: string[];
  exact_event_linked_attempts?: number;
  completeness?: ShotCompletenessSummary | null;
}

export interface PersistedZoneProfileResponse {
  available_game_dates?: string[];
  completeness_status?: ShotCompletenessStatus;
  missing_context_fields?: string[];
  exact_event_linked_attempts?: number;
  completeness?: ShotCompletenessSummary | null;
}

export interface TeamDefenseShotChartResponse {
  team_id: number;
  team_abbreviation?: string | null;
  team_name?: string | null;
  season: string;
  season_type: string;
  shots: ShotChartShot[];
  made: number;
  attempted: number;
  data_status: ShotChartDataStatus;
  last_synced_at?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  available_start_date?: string | null;
  available_end_date?: string | null;
  available_game_dates?: string[];
  completeness_status?: ShotCompletenessStatus;
  missing_context_fields?: string[];
  exact_event_linked_attempts?: number;
  completeness?: ShotCompletenessSummary | null;
}

export interface TeamDefenseZoneProfileResponse {
  team_id: number;
  team_abbreviation?: string | null;
  team_name?: string | null;
  season: string;
  season_type: string;
  total_attempts: number;
  zones: ZoneStat[];
  data_status: ShotChartDataStatus;
  last_synced_at?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  available_start_date?: string | null;
  available_end_date?: string | null;
  available_game_dates?: string[];
  completeness_status?: ShotCompletenessStatus;
  missing_context_fields?: string[];
  exact_event_linked_attempts?: number;
  completeness?: ShotCompletenessSummary | null;
}

export interface ShotLabSnapshotFiltersPayload {
  start_date?: string | null;
  end_date?: string | null;
  period_bucket: ShotLabPeriodBucket;
  result: ShotLabResultFilter;
  shot_value: ShotLabShotValueFilter;
}

export interface ShotLabSnapshotPayload {
  subject_type: "player" | "compare" | "team-defense";
  subject_id?: number | null;
  compare_subject_id?: number | null;
  team_id?: number | null;
  season: string;
  season_type: string;
  active_view: string;
  route_path: string;
  filters: ShotLabSnapshotFiltersPayload;
  metadata?: Record<string, string>;
}

export interface ShotLabSnapshotResponse {
  snapshot_id: string;
  share_url: string;
  created_at?: string | null;
  payload: ShotLabSnapshotPayload;
}

// Sprint 55 — Shot Lab intelligence

export type ShotIntelligenceSubjectType = "player" | "team-defense";
export type ShotIntelligenceCoverageState = "ready" | "partial" | "legacy" | "missing" | "stale";
export type ShotCreationPrecision = "all_shots" | "linked_subset" | "inferred" | "partial";

export interface ShotIntelligenceCoverage {
  state: ShotIntelligenceCoverageState;
  data_status: ShotChartDataStatus;
  total_shots: number;
  contextual_shots: number;
  linked_shots: number;
  exact_linked_shots: number;
  derived_linked_shots: number;
  completeness_pct: number;
  linked_pct: number;
  missing_context_fields: string[];
  note: string;
}

export interface ShotMethodologyNote {
  title: string;
  body: string;
}

export interface ShotLabFilterEcho {
  start_date?: string | null;
  end_date?: string | null;
  period_bucket: ShotLabPeriodBucket;
  result: ShotLabResultFilter;
  shot_value: ShotLabShotValueFilter;
}

export interface ShotQualitySummary {
  shots: number;
  actual_fg_pct?: number | null;
  expected_fg_pct?: number | null;
  fg_pct_delta?: number | null;
  actual_efg_pct?: number | null;
  expected_efg_pct?: number | null;
  efg_pct_delta?: number | null;
  actual_pps?: number | null;
  expected_pps?: number | null;
  pps_delta?: number | null;
  confidence: "high" | "medium" | "low";
}

export interface ShotQualityBin {
  bin_key: string;
  label: string;
  attempts: number;
  made: number;
  frequency: number;
  actual_fg_pct?: number | null;
  expected_fg_pct?: number | null;
  fg_pct_delta?: number | null;
  actual_efg_pct?: number | null;
  expected_efg_pct?: number | null;
  efg_pct_delta?: number | null;
  actual_pps?: number | null;
  expected_pps?: number | null;
  pps_delta?: number | null;
  average_loc_x?: number | null;
  average_loc_y?: number | null;
  sample_confidence: "high" | "medium" | "low";
  coverage_note: string;
  replay_examples?: ShotReplayExample[];
}

export interface ShotReplayExample {
  game_id: string;
  game_date?: string | null;
  opponent_abbreviation?: string | null;
  shot_distance?: number | null;
  shot_made: boolean;
  action_number?: number | null;
  shot_event_id?: string | null;
  period?: number | null;
  clock?: string | null;
  zone_basic?: string | null;
  points_over_expected?: number | null;
  linkage_quality: "exact" | "derived" | "timeline";
  deep_link_url: string;
}

export interface ShotQualityZone {
  zone_basic: string;
  zone_area: string;
  attempts: number;
  made: number;
  frequency: number;
  actual_fg_pct?: number | null;
  expected_fg_pct?: number | null;
  fg_pct_delta?: number | null;
  actual_pps?: number | null;
  expected_pps?: number | null;
  pps_delta?: number | null;
  sample_confidence: "high" | "medium" | "low";
}

export interface ShotQualityResponse {
  subject_type: ShotIntelligenceSubjectType;
  subject_id: number;
  season: string;
  season_type: string;
  filters: ShotLabFilterEcho;
  methodology_version: string;
  coverage_state: ShotIntelligenceCoverageState;
  coverage: ShotIntelligenceCoverage;
  methodology: ShotMethodologyNote[];
  summary: ShotQualitySummary;
  bins: ShotQualityBin[];
  zones: ShotQualityZone[];
}

export interface ShotCreationSplit {
  split_key: string;
  label: string;
  description: string;
  attempts: number;
  made: number;
  frequency: number;
  fg_pct?: number | null;
  efg_pct?: number | null;
  pps?: number | null;
  precision: ShotCreationPrecision;
  coverage_note: string;
  replay_examples?: ShotReplayExample[];
}

export interface ShotCreationResponse {
  subject_type: ShotIntelligenceSubjectType;
  subject_id: number;
  season: string;
  season_type: string;
  filters: ShotLabFilterEcho;
  methodology_version: string;
  coverage_state: ShotIntelligenceCoverageState;
  coverage: ShotIntelligenceCoverage;
  methodology: ShotMethodologyNote[];
  summary: Record<string, number | string>;
  splits: ShotCreationSplit[];
}

export interface ShotIdentityCard {
  identity_key: string;
  label: string;
  tier: "signature" | "strong" | "present" | "low";
  score: number;
  summary: string;
  evidence: string[];
  confidence: "high" | "medium" | "low";
}

export interface ShotIdentityResponse {
  subject_type: ShotIntelligenceSubjectType;
  subject_id: number;
  season: string;
  season_type: string;
  filters: ShotLabFilterEcho;
  methodology_version: string;
  coverage_state: ShotIntelligenceCoverageState;
  coverage: ShotIntelligenceCoverage;
  methodology: ShotMethodologyNote[];
  cards: ShotIdentityCard[];
  takeaways: string[];
}

export interface WarehouseCompletenessDomain {
  domain: string;
  eligible_count?: number;
  ready_count: number;
  partial_count: number;
  legacy_count: number;
  missing_count: number;
  completeness_pct: number;
}

export interface WarehouseCompletenessSummary {
  season: string;
  season_type: string;
  domains: WarehouseCompletenessDomain[];
}

export interface GameEvent {
  source_event_id?: string | null;
  order_index?: number | null;
  action_family?: string | null;
  sub_type?: string | null;
}

export interface GameVisualizationElement {
  kind: string;
  label?: string | null;
  exactness: "exact" | "inferred" | "timeline";
  linkage_mode?: string | null;
  x?: number | null;
  y?: number | null;
  z?: number | null;
  shot_made?: boolean | null;
  shot_value?: number | null;
  team_id?: number | null;
  team_abbreviation?: string | null;
  player_id?: number | null;
  player_name?: string | null;
  event_type?: string | null;
}

export interface GameVisualizationStep {
  action_number: number;
  order_index?: number | null;
  source_event_id?: string | null;
  period?: number | null;
  clock?: string | null;
  event_type?: string | null;
  action_family?: string | null;
  sub_type?: string | null;
  description?: string | null;
  team_id?: number | null;
  team_abbreviation?: string | null;
  player_id?: number | null;
  player_name?: string | null;
  home_score?: number | null;
  away_score?: number | null;
  exact_shot_match: boolean;
  linkage_quality?: "exact" | "derived" | "timeline";
  sequence_role?: "focus" | "neighbor" | null;
  sequence_offset?: number | null;
  elements: GameVisualizationElement[];
}

export interface TeamSplitRow {
  split_family: string;
  split_value: string;
  label: string;
  gp: number;
  w: number;
  l: number;
  w_pct: number;
  min?: number | null;
  pts?: number | null;
  reb?: number | null;
  ast?: number | null;
  tov?: number | null;
  stl?: number | null;
  blk?: number | null;
  fg_pct?: number | null;
  fg3_pct?: number | null;
  ft_pct?: number | null;
  plus_minus?: number | null;
}

export interface TeamSplitsResponse {
  team_id: number;
  abbreviation: string;
  season: string;
  canonical_source?: string | null;
  last_synced_at?: string | null;
  splits: TeamSplitRow[];
}

export interface GameVisualizationResponse {
  game_id: string;
  season: string;
  shot_event_id?: string | null;
  source?: string | null;
  selected_player_id?: number | null;
  selected_period?: number | null;
  selected_event_type?: string | null;
  selected_query?: string | null;
  exact_shot_match: boolean;
  linkage_quality?: "exact" | "derived" | "timeline";
  highlighted_event_id?: string | null;
  highlighted_action_number?: number | null;
  focus_event_id?: string | null;
  focus_action_number?: number | null;
  focus_window?: number;
  focus_steps?: GameVisualizationStep[];
  source_context?: Record<string, string> | null;
  steps: GameVisualizationStep[];
}

// ---------------------------------------------------------------------------
// MVP Award Race — Sprint 48
// ---------------------------------------------------------------------------

export interface MvpCandidate {
  rank: number;
  player_id: number;
  player_name: string;
  team_abbreviation: string;
  headshot_url: string;
  gp: number;
  composite_score: number;
  basketball_value_score?: number | null;
  award_case_score?: number | null;
  basketball_value_rank?: number | null;
  award_case_rank?: number | null;
  ballot_eligible_rank?: number | null;
  context_adjusted_score?: number | null;
  pts_pg: number;
  reb_pg: number;
  ast_pg: number;
  ts_pct: number | null;
  bpm: number | null;
  pts_delta: number | null;
  reb_delta: number | null;
  ast_delta: number | null;
  ts_delta?: number | null;
  momentum: "hot" | "cold" | "steady";
  last_games: number;
  score_pillars?: Record<string, MvpScorePillar>;
  basketball_value_pillars?: Record<string, MvpScorePillar>;
  award_modifiers?: Record<string, MvpAwardModifier>;
  confidence?: MvpCandidateConfidence | null;
  qualitative_lenses?: MvpQualitativeLens[];
  methodology_labels?: MvpMethodologyLabel[];
  case_summary?: string[];
  team_context?: MvpTeamContext | null;
  on_off?: MvpOnOffProfile | null;
  team_impact?: MvpTeamImpactProfile | null;
  advanced_profile?: MvpAdvancedProfile | null;
  clutch_and_pace?: MvpClutchAndPaceProfile | null;
  play_style?: MvpPlayStyleRow[];
  data_coverage?: MvpDataCoverage | null;
  eligibility?: MvpEligibilityProfile | null;
  opponent_context?: MvpOpponentContext | null;
  support_burden?: MvpSupportBurden | null;
  split_profile?: MvpSplitRow[];
  impact_metric_coverage?: MvpImpactMetricCoverage | null;
  visual_coordinates?: MvpVisualCoordinates | null;
  gravity_profile?: MvpGravityProfile | null;
  impact_consensus?: MvpImpactConsensusProfile | null;
  clutch_profile?: MvpClutchProfile | null;
  opponent_adjusted?: MvpOpponentAdjustedProfile | null;
  signature_games?: MvpSignatureGame[];
  rank_by_profile?: Record<string, number>;
}

export type MvpScoringProfile = "box_first" | "balanced" | "impact_consensus";

export interface MvpRaceResponse {
  season: string;
  as_of_date: string;
  candidates: MvpCandidate[];
  weights: Record<string, number>;
  scoring_profile?: string;
  available_profiles?: string[];
}

export interface MvpImpactConsensusMetric {
  name: string;
  value: number | null;
  percentile: number | null;
  source: string | null;
  as_of: string | null;
  note: string | null;
}

export interface MvpImpactConsensusProfile {
  metrics: MvpImpactConsensusMetric[];
  consensus_score: number | null;
  coverage_ratio: string;
  disagreement: number | null;
}

export interface MvpClutchProfile {
  source: string;
  clutch_games: number | null;
  clutch_minutes: number | null;
  clutch_possessions: number | null;
  clutch_pts: number | null;
  clutch_fg_pct: number | null;
  clutch_ts_pct: number | null;
  clutch_ast_to: number | null;
  clutch_plus_minus: number | null;
  clutch_net_rating: number | null;
  clutch_usg_pct: number | null;
  clutch_on_off: number | null;
  close_game_wins: number | null;
  close_game_losses: number | null;
  confidence: "high" | "medium" | "low";
  note: string | null;
}

export interface MvpOpponentAdjustedBucket {
  bucket: "top10_def" | "mid_def" | "bottom_def";
  label: string;
  games: number;
  pts_per_game?: number | null;
  ts_pct?: number | null;
  plus_minus?: number | null;
  confidence: "high" | "medium" | "low";
}

export interface MvpOpponentAdjustedProfile {
  buckets: MvpOpponentAdjustedBucket[];
  ts_gap_top_vs_bottom: number | null;
  pts_gap_top_vs_bottom: number | null;
  confidence: "high" | "medium" | "low";
}

export interface MvpSignatureGame {
  game_id: string;
  date: string | null;
  opponent: string;
  opponent_drtg_rank: number | null;
  opponent_tier: "top10_def" | "mid_def" | "bottom_def";
  result: "W" | "L" | null;
  pts: number;
  reb: number | null;
  ast: number | null;
  ts_pct: number | null;
  plus_minus: number | null;
  leverage_score: number;
}

export interface MvpSensitivityPlayer {
  player_id: number;
  player_name: string;
  team_abbreviation: string;
  headshot_url: string;
  rank_by_profile: Record<string, number>;
  composite_score_default: number | null;
}

export interface MvpSensitivityResponse {
  season: string;
  as_of_date: string;
  default_profile: string;
  profiles: string[];
  profile_labels: Record<string, string>;
  players: MvpSensitivityPlayer[];
}

export interface MvpTimelinePoint {
  date: string;
  rank: number;
  score: number;
  context_adjusted_score?: number | null;
  pts_pg?: number | null;
  reb_pg?: number | null;
  ast_pg?: number | null;
  ts_pct?: number | null;
  wins?: number | null;
  losses?: number | null;
}

export interface MvpTimelinePlayer {
  player_id: number;
  player_name: string;
  team_abbreviation: string;
  current_rank: number;
  previous_rank: number | null;
  rank_delta: number | null;
  current_score: number;
  previous_score: number | null;
  score_delta: number | null;
  current_context_adjusted_score?: number | null;
  momentum: "hot" | "cold" | "steady" | string;
  eligibility_status: string;
  impact_consensus_score?: number | null;
  clutch_confidence?: "high" | "medium" | "low" | null;
  gravity_score?: number | null;
  coverage_warning_count: number;
  reasons: string[];
  series: MvpTimelinePoint[];
}

export interface MvpTimelineMover {
  player_id: number;
  player_name: string;
  team_abbreviation: string;
  current_rank: number;
  previous_rank: number;
  rank_delta: number;
  score_delta: number | null;
  reasons: string[];
}

export interface MvpTimelineResponse {
  season: string;
  profile: string;
  as_of_date: string;
  snapshot_count: number;
  horizon_start?: string | null;
  horizon_end?: string | null;
  timeline_grain: string;
  timeline_mode?: string;
  future_mode?: string;
  methodology: string;
  players: MvpTimelinePlayer[];
  biggest_movers: MvpTimelineMover[];
  coverage_note: string;
}

export interface MvpVoterRoomCandidate {
  player_id: number;
  player_name: string;
  team_abbreviation: string;
  headshot_url: string;
  award_case_rank: number | null;
  basketball_value_rank: number | null;
  ballot_eligible_rank: number | null;
  award_case_score: number | null;
  basketball_value_score: number | null;
  context_adjusted_score: number | null;
  eligibility_status: string;
  confidence?: MvpCandidateConfidence | null;
  team_impact?: MvpTeamImpactProfile | null;
  case_summary: string[];
  evidence: string[];
}

export interface MvpVoterRoomCategory {
  key: string;
  label: string;
  winner_player_id: number | null;
  winner_name: string | null;
  summary: string;
  values: Record<string, number | null>;
}

export interface MvpVoterRoomResponse {
  season: string;
  as_of_date: string;
  mode: string;
  methodology: string;
  selected_player_ids: number[];
  candidates: MvpVoterRoomCandidate[];
  categories: MvpVoterRoomCategory[];
  ballot_summary: string[];
  warnings: string[];
}

export interface MvpSnapshotFreshness {
  status: "ready" | "partial" | "missing" | string;
  latest_snapshot_date: string | null;
  latest_as_of_date: string | null;
  profiles: string[];
  snapshot_count: number;
  note: string;
}

export interface MvpCoverageDomain {
  key: string;
  label: string;
  status: "ready" | "partial" | "missing" | string;
  ready_count: number;
  total_count: number;
  detail: string;
}

export interface MvpCoverageCandidate {
  player_id: number;
  player_name: string;
  team_abbreviation: string;
  rank: number;
  warning_count: number;
  warnings: string[];
}

export interface MvpCoverageResponse {
  season: string;
  as_of_date: string;
  status: "ready" | "partial" | "missing" | string;
  snapshot_freshness: MvpSnapshotFreshness;
  domains: MvpCoverageDomain[];
  candidates: MvpCoverageCandidate[];
  notes: string[];
}

export interface MvpScorePillar {
  label: string;
  weight: number;
  raw_score: number;
  weighted_score: number;
  display_score: number;
  confidence?: "high" | "medium" | "low" | null;
  category?: string | null;
  note?: string | null;
}

export interface MvpAwardModifier {
  key: string;
  label: string;
  raw_score: number;
  modifier: number;
  display_score: number;
  confidence: "high" | "medium" | "low";
  category: string;
  note: string | null;
}

export interface MvpCandidateConfidence {
  overall: "high" | "medium" | "low";
  coverage_score: number;
  sample_stability_score: number;
  signal_agreement_score: number;
  notes: string[];
}

export interface MvpQualitativeLens {
  key: string;
  label: string;
  summary: string;
  confidence: "high" | "medium" | "low";
  evidence: string[];
}

export interface MvpMethodologyLabel {
  key: string;
  label: string;
  category: "core_score_input" | "award_modifier" | "context_signal" | "qualitative_lens";
  description: string;
}

export interface MvpTeamContext {
  team_id: number | null;
  team_name: string | null;
  wins: number | null;
  losses: number | null;
  win_pct: number | null;
  net_rating: number | null;
  off_rating: number | null;
  def_rating: number | null;
  win_pct_rank: number | null;
  net_rating_rank: number | null;
}

export interface MvpOnOffProfile {
  on_minutes: number | null;
  off_minutes: number | null;
  on_net_rating: number | null;
  off_net_rating: number | null;
  on_off_net: number | null;
  on_ortg: number | null;
  on_drtg: number | null;
  off_ortg: number | null;
  off_drtg: number | null;
  confidence: "high" | "medium" | "low";
}

export interface MvpTeammateSwing {
  teammate_id: number;
  teammate_name: string;
  shared_minutes: number | null;
  shared_possessions: number | null;
  both_on_net: number | null;
  candidate_without_teammate_net: number | null;
  swing: number | null;
  confidence: "high" | "medium" | "low";
}

export interface MvpTeamImpactProfile {
  team_abbreviation: string | null;
  team_net_rating: number | null;
  team_net_rating_rank: number | null;
  candidate_game_wins: number | null;
  candidate_game_losses: number | null;
  candidate_game_win_pct: number | null;
  on_minutes: number | null;
  off_minutes: number | null;
  on_off_net: number | null;
  on_net_rating: number | null;
  on_off_rating: number | null;
  on_def_rating: number | null;
  off_net_rating: number | null;
  off_off_rating: number | null;
  off_def_rating: number | null;
  confidence: "high" | "medium" | "low";
  notes: string[];
  teammate_swings?: MvpTeammateSwing[];
}

export interface MvpAdvancedProfile {
  usg_pct: number | null;
  ts_pct: number | null;
  efg_pct: number | null;
  bpm: number | null;
  obpm: number | null;
  dbpm: number | null;
  vorp: number | null;
  ws: number | null;
  win_shares_per_48: number | null;
  pie: number | null;
  net_rating: number | null;
  off_rating: number | null;
  def_rating: number | null;
  epm: number | null;
  raptor: number | null;
  lebron: number | null;
}

export interface MvpClutchAndPaceProfile {
  clutch_pts: number | null;
  clutch_fga: number | null;
  clutch_fg_pct: number | null;
  second_chance_pts: number | null;
  fast_break_pts: number | null;
}

export interface MvpPlayStyleRow {
  action_family: string;
  label: string;
  usage_share: number | null;
  points_per_possession: number | null;
  turnover_rate: number | null;
  ev_score: number | null;
  raw_volume: number;
  confidence: "high" | "medium" | "low";
  note: string;
}

export interface MvpDataCoverage {
  has_season_stats: boolean;
  has_team_context: boolean;
  has_on_off: boolean;
  has_pbp_splits: boolean;
  has_play_style: boolean;
  has_eligibility?: boolean;
  has_opponent_context?: boolean;
  has_support_burden?: boolean;
  has_external_impact?: boolean;
  has_gravity?: boolean;
  warnings: string[];
}

export interface MvpEligibilityProfile {
  eligibility_status: "eligible" | "at_risk" | "ineligible" | "unknown";
  eligible_games: number;
  games_needed: number;
  minutes_qualified_games: number;
  near_miss_games: number;
  games_played: number;
  minutes_played: number | null;
  warning: string | null;
}

export interface MvpSplitRow {
  key: string;
  label: string;
  games: number;
  wins: number | null;
  losses: number | null;
  pts_pg: number | null;
  reb_pg: number | null;
  ast_pg: number | null;
  ts_pct: number | null;
  plus_minus_pg: number | null;
  confidence: "high" | "medium" | "low";
}

export interface MvpOpponentContext {
  rows: MvpSplitRow[];
  best_split: string | null;
  biggest_weakness: string | null;
  note: string;
}

export interface MvpSupportBurden {
  candidate_usage_pct: number | null;
  team_net_without_candidate: number | null;
  top_teammate_name: string | null;
  top_teammate_pts_pg: number | null;
  top_teammate_games: number | null;
  teammate_availability_avg_gp: number | null;
  support_note: string | null;
}

export interface MvpImpactMetricCoverage {
  local_metrics: string[];
  external_metrics_present: string[];
  external_metrics_missing: string[];
  note: string;
}

export interface MvpVisualCoordinates {
  x_team_success: number;
  y_individual_impact: number;
  production: number;
  efficiency: number;
  availability: number;
  momentum: number;
  bubble_size: number;
  color_key: string;
  explanation: string;
}

export interface MvpGravityProfile {
  player_id: number;
  source: string;
  source_label: string;
  overall_gravity: number | null;
  shooting_gravity: number | null;
  rim_gravity: number | null;
  creation_gravity: number | null;
  roll_or_screen_gravity: number | null;
  off_ball_gravity: number | null;
  spacing_lift: number | null;
  gravity_confidence: "high" | "medium" | "low";
  gravity_minutes: number | null;
  source_note: string;
  warnings: string[];
}

export interface MvpNearbyCandidate {
  rank: number;
  player_id: number;
  player_name: string;
  team_abbreviation: string;
  composite_score: number;
}

export interface MvpCandidateCaseResponse {
  season: string;
  as_of_date: string;
  candidate: MvpCandidate;
  nearby: MvpNearbyCandidate[];
  weights: Record<string, number>;
  scoring_profile: string;
  available_profiles?: string[];
}

export interface MvpRaceOptions {
  top?: number;
  minGp?: number;
  position?: string | null;
}

export interface MvpContextMapPoint {
  rank: number;
  player_id: number;
  player_name: string;
  team_abbreviation: string;
  composite_score: number;
  eligibility_status: string;
  momentum: string;
  x_team_success: number;
  y_individual_impact: number;
  production: number;
  efficiency: number;
  availability: number;
  momentum_score: number;
  gravity?: number | null;
  bubble_size: number;
  color_key: string;
  quick_evidence: string[];
  coverage_warnings: string[];
}

export interface MvpContextMapResponse {
  season: string;
  as_of_date: string;
  scoring_profile: string;
  default_x: string;
  default_y: string;
  axis_options: string[];
  points: MvpContextMapPoint[];
  methodology: string;
}

export interface MvpGravityLeaderboardResponse {
  season: string;
  as_of_date: string;
  source_policy: string;
  profiles: MvpGravityProfile[];
}

// ────────────────────────────────────────────────────────────────────────────
// Sprint 58 — Opportunity Workspace contracts
// ────────────────────────────────────────────────────────────────────────────

export type OpportunitySignal =
  | "efficiency_load_gap"
  | "team_impact_swing"
  | "lineup_synergy_lift"
  | "role_fit_gap"
  | "cohort_percentile";

export interface OpportunityDriverContribution {
  signal: OpportunitySignal;
  z_score: number;
  weighted_contribution: number;
}

export interface OpportunityTeammate {
  teammate_id: number;
  teammate_name: string;
  shared_possessions: number;
  net_rating_with: number | null;
}

export interface OpportunityRoleFit {
  par3: number | null;
  par3_bucket_avg: number | null;
  ftr: number | null;
  ftr_bucket_avg: number | null;
  efg_pct: number | null;
  efg_bucket_avg: number | null;
  ast_pg: number | null;
  ast_bucket_avg: number | null;
  tov_pg: number | null;
  tov_bucket_avg: number | null;
}

export interface OpportunityCompareHandoff {
  pinned_player_id: number;
  positional_peers: number[];
  cohort_bucket: string;
}

export interface OpportunityPlayerRow {
  player_id: number;
  player_name: string;
  team_abbreviation: string;
  position: string | null;
  position_bucket: string;
  minutes_pg: number | null;
  gp: number | null;

  usg_pct: number | null;
  ts_pct: number | null;
  off_rating: number | null;
  def_rating: number | null;
  net_rating: number | null;
  pts_pg: number | null;
  ast_pg: number | null;
  tov_pg: number | null;

  on_off_net: number | null;
  on_minutes: number | null;
  off_minutes: number | null;

  top_teammate: OpportunityTeammate | null;
  role_fit: OpportunityRoleFit | null;

  opportunity_score: number;
  team_opportunity_score: number | null;
  cohort_percentile: number | null;
  confidence: "high" | "medium" | "low";
  driver_contributions: OpportunityDriverContribution[];
  directional_hint: string | null;
  hint_basis: string[];
  top_driver: OpportunitySignal | null;
  compare_handoff: OpportunityCompareHandoff | null;
}

export interface OpportunityMethodology {
  version: string;
  weights: Record<OpportunitySignal, number>;
  z_score_cap: number;
  min_minutes: number;
  min_lineup_possessions: number;
  confidence_thresholds: Record<string, Record<string, number>>;
  notes: string[];
}

export interface OpportunityTeamRollup {
  team_abbreviation: string;
  top_drivers: Record<string, number>;
  sample_size: number;
}

export interface OpportunityResponse {
  season: string;
  team: string | null;
  min_minutes: number;
  position_filter: string | null;
  rows: OpportunityPlayerRow[];
  team_rollup: OpportunityTeamRollup | null;
  methodology: OpportunityMethodology;
  warnings: string[];
}

export interface ShotIntelligenceOpsPlayer {
  player_id: number;
  player_name: string;
  team_id?: number | null;
  team_abbreviation?: string | null;
  state: "ready" | "partial" | "legacy" | "stale" | "missing";
  data_status: string;
  total_shots: number;
  linked_shots: number;
  exact_linked_shots: number;
  missing_context_fields: string[];
  last_synced_at?: string | null;
}

export interface ShotIntelligenceOpsTeam {
  team_id: number;
  team_abbreviation: string;
  team_name?: string | null;
  readiness: "ready" | "partial" | "stale" | "missing";
  roster_size: number;
  ready_count: number;
  partial_count: number;
  legacy_count: number;
  stale_count: number;
  missing_count: number;
}

export interface ShotIntelligenceOpsBaseline {
  season: string;
  season_type: string;
  methodology_version: string;
  status: "ready" | "stale" | "missing";
  sample_n: number;
  computed_at?: string | null;
}

export interface ShotIntelligenceOpsResponse {
  season: string;
  season_type: string;
  methodology_version: string;
  teams: ShotIntelligenceOpsTeam[];
  stale_players: ShotIntelligenceOpsPlayer[];
  missing_context_histogram: Record<string, number>;
  baseline: ShotIntelligenceOpsBaseline;
  totals: Record<string, number>;
}

export interface TeamShootingSplitRow {
  split_family: string;
  split_value: string;
  label: string;
  fgm?: number | null;
  fga?: number | null;
  fg_pct?: number | null;
  fg3m?: number | null;
  fg3a?: number | null;
  fg3_pct?: number | null;
  efg_pct?: number | null;
  blka?: number | null;
  pct_ast_2pm?: number | null;
  pct_uast_2pm?: number | null;
  pct_ast_3pm?: number | null;
  pct_uast_3pm?: number | null;
  pct_ast_fgm?: number | null;
  pct_uast_fgm?: number | null;
}

export interface TeamShootingSplitsResponse {
  team_id: number;
  abbreviation: string;
  season: string;
  canonical_source?: string | null;
  last_synced_at?: string | null;
  splits: TeamShootingSplitRow[];
}

export interface StyleShotProfileDriver {
  split_family: string;
  split_value: string;
  label: string;
  attempt_share?: number | null;
  efg_pct?: number | null;
  league_delta?: number | null;
  summary: string;
}

export interface StyleXRayResponse {
  shot_profile_drivers: StyleShotProfileDriver[];
}

export interface StyleShotProfileDriver {
  family_label?: string | null;
  trust_level?: "strong" | "caution";
  trust_note?: string | null;
  strong_claim?: boolean;
}

export interface StyleNeighbor {
  matchup_label?: string | null;
}

export interface StyleHistoryPoint {
  label: string;
  archetype: string;
  confidence: "high" | "medium" | "low";
  record: string | null;
  shot_profile_note: string | null;
}

export interface StyleXRayResponse {
  history?: StyleHistoryPoint[];
  replay_target?: ReplayLaunchTarget | null;
}

export interface StyleComparisonEntity {
  abbreviation?: string;
  name?: string;
  label_reason?: string;
  current_profile?: Array<{ metric_id?: string; label?: string; team_value?: number | null }>;
  shot_profile_drivers?: StyleShotProfileDriver[];
}

export interface TeamComparisonSnapshot {
  shot_profile_drivers?: StyleShotProfileDriver[];
}

export interface TeamComparisonResponse {
  warnings?: string[];
}

export interface TeamPrepQueueItem {
  xray_url?: string | null;
  replay_url?: string | null;
  shot_profile_driver?: StyleShotProfileDriver | null;
  style_replay_target?: ReplayLaunchTarget | null;
}

export interface WorkflowLaunchLinks {
  style_xray_url?: string | null;
  replay_url?: string | null;
}

export interface PreReadPrepContext {
  shot_profile_driver?: StyleShotProfileDriver | null;
  style_replay_target?: ReplayLaunchTarget | null;
  xray_url?: string | null;
  replay_url?: string | null;
}

export interface OpponentPlayTypeRow {
  play_type: string;
  poss_pct: number | null;
  ppp: number | null;
  percentile: number | null;
  fg_pct: number | null;
  score_pct: number | null;
}

export interface OpponentPlayTypeResponse {
  team_abbr: string;
  season: string;
  plays: OpponentPlayTypeRow[];
  data_status: string;
  source: string;
}

export interface H2HGame {
  game_id: string;
  game_date: string | null;
  season: string;
  is_home: boolean;
  team_score: number | null;
  opponent_score: number | null;
  margin: number | null;
  result: string;
}

export interface H2HResponse {
  team_abbr: string;
  opponent_abbr: string;
  seasons_covered: string[];
  wins: number;
  losses: number;
  series_record: string;
  avg_margin: number | null;
  last_meeting_date: string | null;
  last_meeting_result: string | null;
  games: H2HGame[];
  data_status: string;
}

export interface PaceEdge {
  team_pace: number | null;
  opponent_pace: number | null;
  pace_delta: number | null;
  framing: string;
  edge_label: string;
  magnitude: string;
}

export interface TeamClutchResponse {
  team_abbr: string;
  season: string;
  gp: number | null;
  w: number | null;
  l: number | null;
  w_pct: number | null;
  pts_pg: number | null;
  plus_minus_pg: number | null;
  fg_pct: number | null;
  ft_pct: number | null;
  ts_pct: number | null;
  w_pct_rank: number | null;
  plus_minus_rank: number | null;
  data_status: string;
  source: string;
}

export interface TeamNetRatingGame {
  game_id: string | null;
  game_date: string | null;
  opponent_abbr: string | null;
  pts: number | null;
  opp_pts: number | null;
  margin: number | null;
  rolling_net_rating: number | null;
  wl: string | null;
}

export interface TeamNetRatingSeriesResponse {
  team_abbr: string;
  season: string;
  window: number;
  games: TeamNetRatingGame[];
  season_avg_margin: number | null;
  data_status: string;
}

export interface TeamPeriodRow {
  period_label: string;
  pts: number | null;
  opp_pts: number | null;
  diff: number | null;
  fg_pct: number | null;
  w: number | null;
  l: number | null;
  gp: number | null;
}

export interface TeamPeriodScoringResponse {
  team_abbr: string;
  season: string;
  by_period: TeamPeriodRow[];
  by_half: TeamPeriodRow[];
  best_period: string | null;
  worst_period: string | null;
  data_status: string;
}

export interface BenchUnitRow {
  lineup_key: string;
  player_names: string[];
  starter_count: number;
  net_rating: number | null;
  minutes: number | null;
  possessions: number | null;
}

export interface BenchAnalyticsResponse {
  team_abbr: string;
  season: string;
  starter_net_rating: number | null;
  bench_net_rating: number | null;
  net_rating_gap: number | null;
  bench_anchor_name: string | null;
  bench_anchor_id: number | null;
  best_bench_lineups: BenchUnitRow[];
  worst_bench_lineups: BenchUnitRow[];
  data_status: string;
}

export interface PreReadPacketSelection {
  claim_ids: string[];
  clip_anchor_ids: string[];
}

export interface PreReadPacketSummary {
  claim_count: number;
  clip_count: number;
  claim_titles: string[];
}

export interface PreReadScoutingPacketClaim {
  claim_id: string;
  title: string;
  summary: string;
  evidence: {
    label: string;
    value: number | string | null;
    context?: string | null;
  }[];
  inference_confidence: ClaimInferenceConfidence | null;
  clip_anchors: ScoutingClipAnchor[];
}

export interface PreReadScoutingPacket {
  selection: PreReadPacketSelection;
  claims: PreReadScoutingPacketClaim[];
  generated_at: string | null;
  source_url: string | null;
}

export interface PreReadSnapshotRef {
  title: string | null;
  note: string | null;
  packet_summary: PreReadPacketSummary | null;
}

export interface PreReadPrepContext {
  shot_profile_driver?: StyleShotProfileDriver | null;
  style_replay_target?: ReplayLaunchTarget | null;
  xray_url?: string | null;
  replay_url?: string | null;
}

export interface PreReadDeckResponse {
  runtime_policy?: string | null;
  scouting_packet: PreReadScoutingPacket | null;
}

export interface PreReadSnapshotSummary {
  title: string | null;
  note: string | null;
  packet_summary: PreReadPacketSummary | null;
}

export interface PreReadSnapshotResponse {
  title: string | null;
  note: string | null;
  packet_summary: PreReadPacketSummary | null;
}

// --- Sprint 67 — Player Archetype + Similarity Engine ---------------------

export type ArchetypeKey =
  | "heliocentric_creator"
  | "lead_ball_handler"
  | "iso_scorer"
  | "secondary_playmaker"
  | "movement_shooter"
  | "three_and_d_wing"
  | "rim_pressure_guard"
  | "connective_forward"
  | "defensive_anchor"
  | "interior_finisher"
  | "stretch_big"
  | "switchable_stopper"
  | "rotational_energy"
  | "balanced_role"
  | "developmental";

export type ArchetypeConfidence = "high" | "medium" | "low";

export interface ArchetypeContributor {
  feature_key: string;
  label: string;
  value: number | null;
  z: number;
  direction: "above" | "below";
}

export interface ArchetypeSample {
  gp: number;
  min_pg: number;
  peer_pool_size: number;
}

export interface PlayerArchetype {
  player_id: number;
  season: string;
  archetype_key: ArchetypeKey;
  label: string;
  confidence: ArchetypeConfidence;
  reason: string;
  contributors: ArchetypeContributor[];
  sample: ArchetypeSample;
  methodology_version: string;
}

// Extended similarity comp carrying the archetype label attached by B2.
export interface SimilarPlayerCompWithArchetype extends SimilarPlayerComp {
  archetype_key: ArchetypeKey | null;
  archetype_label: string | null;
  archetype_confidence: ArchetypeConfidence | null;
}

export type SimilarityMode = "season" | "age" | "team_fit";

export interface SimilarityResponseWithArchetype {
  player_id: number;
  season: string;
  mode: SimilarityMode;
  comps: SimilarPlayerCompWithArchetype[];
}

// --- Sprint 67 (Stream B) — Shot Profile Diagnosis ------------------------

export type ShotDiagnosisSentiment = "strength" | "risk" | "neutral";
export type ShotDiagnosisGrade = "green" | "yellow" | "red";
export type ShotSampleConfidence = "high" | "medium" | "low";
export type ShotSustainability =
  | "Sustainable"
  | "Hot Streak"
  | "Cold Streak"
  | "Insufficient Sample";
export type ShotCreationBurden = "Self-Created Heavy" | "Balanced" | "Assisted Heavy";

export interface ShotDiagnosisEvidence {
  metric: string;
  value: number | null;
  delta: number | null;
  zone: string | null;
  note: string | null;
}

export interface ShotDiagnosisTag {
  key: string;
  label: string;
  sentiment: ShotDiagnosisSentiment;
  grade: ShotDiagnosisGrade;
  sample_confidence: ShotSampleConfidence;
  evidence: ShotDiagnosisEvidence[];
}

export interface ShotDiagnosisResponse {
  player_id: number;
  season: string;
  season_type: string;
  methodology_version: string;
  headline: string;
  sustainability: ShotSustainability;
  creation_burden: ShotCreationBurden;
  tags: ShotDiagnosisTag[];
  sample_confidence: ShotSampleConfidence;
  coverage_state: string;
  total_shots: number;
}

// --- Sprint 67 (Stream B) — Scouting Brief --------------------------------

export type ScoutingCardType =
  | "role"
  | "strengths"
  | "usage_efficiency"
  | "shot_profile"
  | "trajectory";

export type ScoutingCardConfidence = "high" | "medium" | "low";

export interface ScoutingBriefCard {
  card_type: ScoutingCardType;
  title: string;
  summary: string;
  evidence: string[];
  confidence: ScoutingCardConfidence;
  deep_link: string;
}

export interface ScoutingBriefResponse {
  player_id: number;
  season: string;
  methodology_version: string;
  cards: ScoutingBriefCard[];
  warnings: string[];
}

// --- Sprint 68 — archetype evolution timeline -----------------------------

export interface ArchetypeHistoryEntry {
  season: string;
  archetype_key: ArchetypeKey;
  label: string;
  confidence: ArchetypeConfidence;
  reason: string;
  transitioned_from: ArchetypeKey | null;
}

export interface ArchetypeHistoryResponse {
  player_id: number;
  player_name: string | null;
  entries: ArchetypeHistoryEntry[];
  methodology_version: string;
}

// --- Sprint 69 — Team-Fit Intelligence -----------------------------------

export interface TeamFitDriver {
  feature_key: string;
  label: string;
  player_z: number;
  team_need_z: number;
  contribution: number;
  summary: string;
}

export interface TeamFitOverlapFlag {
  feature_key: string;
  label: string;
  teammate_id: number;
  teammate_name: string;
  player_z: number;
  teammate_z: number;
  gap: number;
  multiplier: number;
}

export interface TeamFitCurrentTeam {
  team_abbreviation: string;
  fit_score: number;
  value_supplied_score: number;
  teammate_overlap_score: number;
  role_runway_score: number;
  skill_supply_score: number | null;
  roster_need_score: number | null;
  role_competition_score: number | null;
  confidence: string | null;
  confidence_notes: string[];
  summary: string;
  value_drivers: TeamFitDriver[];
  role_runway_drivers: TeamFitDriver[];
  overlap_flags: TeamFitOverlapFlag[];
}

export type TeamFitAlternativeLabel = "better_fit" | "similar_fit" | "different_fit";

export interface TeamFitAlternativeTeam {
  team_abbreviation: string;
  team_name: string | null;
  fit_score: number;
  score_delta_vs_current: number;
  label: TeamFitAlternativeLabel;
  skill_supply_score: number | null;
  roster_need_score: number | null;
  role_competition_score: number | null;
  confidence: string | null;
  confidence_notes: string[];
  summary: string;
  value_drivers: TeamFitDriver[];
  role_runway_drivers: TeamFitDriver[];
  overlap_flags: TeamFitOverlapFlag[];
}

export interface TeamFitMethodology {
  version: string;
  weights: Record<string, number>;
  duplicate_threshold: number;
  duplicate_penalty: number;
  min_games: number;
  min_team_players: number;
  better_fit_delta_threshold: number;
  notes: string[];
}

export interface TeamFitContext {
  team_abbreviation: string | null;
  overlap_flags: TeamFitOverlapFlag[];
  summary: string | null;
}

export interface TeamFitResponse {
  player_id: number;
  player_name: string;
  season: string;
  current_team: TeamFitCurrentTeam | null;
  alternative_teams: TeamFitAlternativeTeam[];
  methodology: TeamFitMethodology;
  warnings: string[];
}

export interface SimilarityResponseWithArchetype {
  team_fit_context?: TeamFitContext | null;
}

export type AnalysisContextType = "injury" | "recovery" | "availability_management" | "manual_note";
export type AnalysisContextSource = "injury_report_auto" | "manual";
export type AnalysisContextSeverity = "low" | "medium" | "high";
export type AnalysisContextFacet = "trend" | "team_fit" | "archetype" | "similarity" | "all";

export interface AnalysisContext {
  id: number | null;
  player_id: number;
  season: string;
  context_type: AnalysisContextType;
  start_date: string | null;
  end_date: string | null;
  severity: AnalysisContextSeverity | null;
  source: AnalysisContextSource;
  note: string | null;
  applies_to: AnalysisContextFacet[];
  created_at: string | null;
  updated_at: string | null;
}

export interface AnalysisContextPayload {
  season: string;
  context_type: AnalysisContextType;
  start_date?: string | null;
  end_date?: string | null;
  severity?: AnalysisContextSeverity | null;
  note?: string | null;
  applies_to?: AnalysisContextFacet[];
}

export interface AnalysisContextListResponse {
  player_id: number;
  season: string;
  contexts: AnalysisContext[];
}

// ── Sprint 72: Leaderboard trend sparklines ──────────────────────────────────
export interface LeaderboardTrendEntry {
  player_id: number;
  player_name: string;
  team_abbreviation: string | null;
  season: string;
  stat: string;
  rolling_values: number[];
  sample_size: number;
  latest_value: number | null;
  delta_vs_baseline: number | null;
}

export interface LeaderboardTrendResponse {
  season: string;
  stat: string;
  window: number;
  entries: LeaderboardTrendEntry[];
}

// ── Sprint 73: Season phase + playoffs bracket ───────────────────────────────
export type SeasonPhase =
  | "regular_season"
  | "playoff_play_in"
  | "playoff_round_1"
  | "playoff_round_2"
  | "conference_finals"
  | "finals"
  | "offseason";

export interface SeasonPhaseResponse {
  phase: SeasonPhase;
  season: string;
  round_label: string | null;
  last_updated_at: string;
}

export type PlayoffSeriesStatus = "scheduled" | "active" | "closed";

export interface PlayoffSeriesGame {
  game_id: string;
  game_date: string | null;
  home_team_id: number | null;
  home_team_abbr: string | null;
  away_team_id: number | null;
  away_team_abbr: string | null;
  home_pts: number | null;
  away_pts: number | null;
  winner_team_id: number | null;
  series_game_num: number | null;
}

export interface PlayoffSeriesResponse {
  season: string;
  round: number;
  series_id: string;
  top_seed_team_id: number | null;
  bottom_seed_team_id: number | null;
  top_seed_team_abbr: string | null;
  bottom_seed_team_abbr: string | null;
  top_seed: number;
  bottom_seed: number;
  top_wins: number;
  bottom_wins: number;
  status: PlayoffSeriesStatus;
  winner_team_id: number | null;
  games: PlayoffSeriesGame[];
}

export interface PlayoffBracketResponse {
  season: string;
  east: PlayoffSeriesResponse[];
  west: PlayoffSeriesResponse[];
  finals: PlayoffSeriesResponse | null;
}

// A playoff game annotated with the series context it belongs to. Mirrors the
// backend `PlayoffSeriesGameWithMatchup` Pydantic schema (Sprint 73).
export interface PlayoffSeriesGameWithMatchup extends PlayoffSeriesGame {
  series_id: string | null;
  season: string | null;
  round: number | null;
  top_seed_team_abbr: string | null;
  bottom_seed_team_abbr: string | null;
  top_wins: number | null;
  bottom_wins: number | null;
  status: PlayoffSeriesStatus | null;
}

export interface PlayoffTodayResponse {
  date: string;
  games: PlayoffSeriesGameWithMatchup[];
}

// ── Sprint 73B — Series simulator. Mirrors `backend/models/playoffs.py`.
export interface SeriesSimulationCurrentState {
  top_seed_team_abbr: string | null;
  bottom_seed_team_abbr: string | null;
  top_wins: number;
  bottom_wins: number;
  games_played: number;
  status: PlayoffSeriesStatus;
}

export interface SeriesProjectionEntry {
  game_num: number;
  home_team_abbr: string | null;
  away_team_abbr: string | null;
  home_win_prob: number;
}

export interface SeriesSimulationResponse {
  series_id: string;
  current_state: SeriesSimulationCurrentState;
  projection: SeriesProjectionEntry[];
  top_seed_series_win_prob: number;
  bottom_seed_series_win_prob: number;
  trials: number;
}

// ── Sprint 74: Shared methodology metadata ──────────────────────────────────
export type MethodologyConfidence = "high" | "medium" | "low";

export interface UncertaintyBand {
  lower: number | null;
  upper: number | null;
  level: number;
  method: string;
}

export interface SampleContext {
  sample_size: number | null;
  effective_sample_size: number | null;
  population_size: number | null;
  minimum_recommended: number | null;
  notes: string[];
}

export interface DriverBreakdown {
  key: string;
  label: string;
  value: number | null;
  weight: number | null;
  contribution: number | null;
  explanation: string;
}

export interface AnalysisMetadata {
  methodology_version: string;
  reliability_score: number | null;
  confidence: MethodologyConfidence | null;
  uncertainty_band: UncertaintyBand | null;
  sample_context: SampleContext | null;
  driver_breakdown: DriverBreakdown[];
  limitations: string[];
  validation_notes: string[];
}

export interface MethodologyDomain {
  domain: string;
  label: string;
  methodology_version: string;
  status: string;
  model_stage: string;
  question_answered: string;
  input_families: string[];
  season_type_support: string[];
  sample_gates: string[];
  confidence_rules: string[];
  reliability_policy: string;
  explainability_policy: string;
  known_limitations: string[];
  validation_notes: string[];
  last_validation_date: string | null;
  docs_path: string;
  implementation_refs: string[];
}

export interface MethodologyRegistryResponse {
  version: string;
  domains: MethodologyDomain[];
}

export interface MethodologyDetailResponse extends MethodologyDomain {
  related_domains: string[];
  recommended_next_steps: string[];
}

export interface MethodologyValidationFixture {
  fixture_key: string;
  domain: string;
  label: string;
  expected_result: string;
  current_result: string;
  passed: boolean;
  notes: string[];
}

export interface MethodologyValidationResponse {
  version: string;
  fixtures: MethodologyValidationFixture[];
}

export interface ShotQualitySummary {
  fg_uncertainty_band?: UncertaintyBand | null;
  pps_delta_uncertainty_band?: UncertaintyBand | null;
  stabilized_fg_pct?: number | null;
  stabilized_pps?: number | null;
  stabilized_pps_delta?: number | null;
  sustainability_label?: string | null;
}

export interface ShotQualityBin {
  stabilized_fg_pct?: number | null;
  stabilized_pps?: number | null;
  stabilized_pps_delta?: number | null;
  sustainability_label?: string | null;
}

export interface ShotQualityZone {
  stabilized_fg_pct?: number | null;
  stabilized_pps?: number | null;
  stabilized_pps_delta?: number | null;
  sustainability_label?: string | null;
}

export interface ShotQualityResponse {
  analysis_metadata?: AnalysisMetadata | null;
}

export interface OpportunityResponse {
  analysis_metadata?: AnalysisMetadata | null;
}

export interface TeamFitCurrentTeam {
  theoretical_usage_score?: number | null;
  fit_gap_vs_theoretical?: number | null;
  fit_interpretation?: string | null;
  reliability_notes?: string[];
}

export interface TeamFitMethodology {
  calibrated_better_fit_thresholds?: Record<string, number>;
}

export interface TeamFitResponse {
  analysis_metadata?: AnalysisMetadata | null;
  low_sample_warning?: string | null;
}
