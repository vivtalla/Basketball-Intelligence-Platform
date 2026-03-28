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

export interface ClutchStats {
  player_id: number;
  season: string;
  clutch_pts: number | null;
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
