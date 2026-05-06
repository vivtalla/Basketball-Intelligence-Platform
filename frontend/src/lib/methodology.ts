/**
 * Humanize a backend `methodology_version` string for user-facing display.
 *
 * Backend versions are snake_case identifiers like
 * `playoff_series_intelligence_v1`, `shot_quality_v2`, `uplift_knn_v3`.
 * Rendering them raw leaks the internal naming convention — we ran into
 * this in Sprint 91 when a user asked us to stop writing things "like v_1".
 *
 *   "playoff_series_intelligence_v1" -> "Playoff Series Intelligence (v1)"
 *   "shot_quality_v2"                -> "Shot Quality (v2)"
 *   "uplift_knn_v3"                  -> "Uplift KNN (v3)"
 *   null / "" / undefined            -> "Methodology"
 */
export function humanizeMethodologyVersion(raw: string | null | undefined): string {
  if (!raw) return "Methodology";
  const match = raw.match(/^(.*?)_v(\d+)$/);
  const stem = match ? match[1] : raw;
  const version = match ? match[2] : null;
  // Acronyms we want to preserve in uppercase rather than title-case.
  const acronyms = new Set([
    "knn", "rapm", "epm", "raptor", "lebron", "pipm", "nba",
    "fga", "fta", "ts", "ftr", "mvp",
  ]);
  const words = stem
    .split("_")
    .filter(Boolean)
    .map((w) => (acronyms.has(w.toLowerCase()) ? w.toUpperCase() : w.charAt(0).toUpperCase() + w.slice(1)));
  const title = words.join(" ");
  return version ? `${title} (v${version})` : title;
}
