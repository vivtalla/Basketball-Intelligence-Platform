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
