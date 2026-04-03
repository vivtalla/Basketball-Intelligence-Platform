// Shared shot chart constants and utilities used by ShotChart, ZoneAnnotationCourt, and ZoneProfilePanel

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

// SVG paths for each zone (half-court, basket at cx=250 cy=430, viewport 500×480)
// svgX = locX + 250, svgY = 430 - locY
export const ZONE_PATHS: Record<string, string> = {
  "Restricted Area":
    "M 210,430 A 40,40 0 0 0 290,430 L 250,430 Z",
  "In The Paint (Non-RA)":
    "M 170,240 L 330,240 L 330,430 L 290,430 A 40,40 0 0 1 210,430 L 170,430 Z",
  "Left Corner 3":
    "M 0,341 L 30,341 L 30,480 L 0,480 Z",
  "Right Corner 3":
    "M 470,341 L 500,341 L 500,480 L 470,480 Z",
  "Mid-Range":
    "M 30,341 A 237.5,237.5 0 0 0 470,341 L 470,480 L 330,480 L 330,240 L 170,240 L 170,480 L 30,480 Z",
  "Above the Break 3":
    "M 0,0 L 500,0 L 500,341 L 470,341 A 237.5,237.5 0 0 1 30,341 L 0,341 Z",
  "Backcourt": "",
};

// Green → gray → red gradient based on efficiency delta vs league avg
export function heatColor(diff: number | null, alpha = 0.55): string {
  if (diff === null) return `rgba(156,163,175,${alpha})`;
  if (diff >= 0.08) return `rgba(22,163,74,${alpha})`;
  if (diff >= 0.04) return `rgba(74,222,128,${alpha})`;
  if (diff >= 0) return `rgba(134,239,172,${alpha})`;
  if (diff >= -0.04) return `rgba(252,165,165,${alpha})`;
  if (diff >= -0.08) return `rgba(248,113,113,${alpha})`;
  return `rgba(220,38,38,${alpha})`;
}
