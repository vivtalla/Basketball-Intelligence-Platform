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
}

export interface CareerStatsResponse {
  player_id: number;
  player_name: string;
  seasons: SeasonStats[];
  career_totals: SeasonStats | null;
  playoff_seasons: SeasonStats[];
}
