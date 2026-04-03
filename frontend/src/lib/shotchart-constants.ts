// Shared shot chart constants used by ShotChart and ZoneProfilePanel

// League-average FG% by zone (approximate, current era)
export const LEAGUE_AVG_FG: Record<string, number> = {
  "Restricted Area": 0.64,
  "In The Paint (Non-RA)": 0.40,
  "Mid-Range": 0.41,
  "Left Corner 3": 0.38,
  "Right Corner 3": 0.38,
  "Above the Break 3": 0.36,
  "Backcourt": 0.02,
};

// Point value per zone (2 or 3)
export const ZONE_POINTS: Record<string, number> = {
  "Restricted Area": 2,
  "In The Paint (Non-RA)": 2,
  "Mid-Range": 2,
  "Left Corner 3": 3,
  "Right Corner 3": 3,
  "Above the Break 3": 3,
  "Backcourt": 3,
};

export const ZONE_ORDER = [
  "Restricted Area",
  "In The Paint (Non-RA)",
  "Mid-Range",
  "Left Corner 3",
  "Right Corner 3",
  "Above the Break 3",
  "Backcourt",
];
