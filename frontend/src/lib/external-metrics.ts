/**
 * Sprint 82d — Authoritative attribution for proprietary external metrics.
 *
 * Every UI surface that displays these metrics must use EXTERNAL_METRICS
 * to render source attribution. Per CLAUDE.md:
 *
 *   "External metrics (LEBRON, RAPTOR, EPM, PIPM, RAPM) are imported.
 *    Never present as platform-original. Always attribute source."
 */

export interface ExternalMetricMeta {
  key: string;
  label: string;
  fullName: string;
  source: string;
  url: string;
  description: string;
}

export const EXTERNAL_METRICS: Record<string, ExternalMetricMeta> = {
  epm: {
    key: "epm",
    label: "EPM",
    fullName: "Estimated Plus/Minus",
    source: "Dunks & Threes",
    url: "https://dunksandthrees.com/epm",
    description: "Ridge regression impact metric blending box score, play-by-play, and on/off signals.",
  },
  raptor: {
    key: "raptor",
    label: "RAPTOR",
    fullName: "Robust Algorithm using Player Tracking and On/Off Ratings",
    source: "FiveThirtyEight",
    url: "https://github.com/fivethirtyeight/data/tree/master/nba-raptor",
    description: "FiveThirtyEight's all-in-one impact metric. Project archived; historical data only.",
  },
  pipm: {
    key: "pipm",
    label: "PIPM",
    fullName: "Player Impact Plus/Minus",
    source: "Basketball Index",
    url: "https://www.bball-index.com/player-impact-plus-minus/",
    description: "On/off + box-score blended impact metric.",
  },
  lebron: {
    key: "lebron",
    label: "LEBRON",
    fullName: "Luck-adjusted player Estimate using a Box prior Regularized ON-off",
    source: "Basketball Index",
    url: "https://www.bball-index.com/lebron-introduction/",
    description: "Luck-adjusted on/off all-in-one metric. Often regarded as the most trusted public impact metric.",
  },
  rapm: {
    key: "rapm",
    label: "RAPM",
    fullName: "Regularized Adjusted Plus/Minus",
    source: "Public RAPM (nbarapm.com)",
    url: "https://nbarapm.com/",
    description: "Foundational on/off-based impact metric. Many derivatives (EPM, RAPTOR, PIPM, LEBRON) build on RAPM.",
  },
};

export const EXTERNAL_METRIC_KEYS = Object.keys(EXTERNAL_METRICS);

export function isExternalMetric(key: string): boolean {
  return key.toLowerCase() in EXTERNAL_METRICS;
}

export function getMetricMeta(key: string): ExternalMetricMeta | null {
  return EXTERNAL_METRICS[key.toLowerCase()] ?? null;
}

/** Compose a tooltip-ready string for any external metric column. */
export function metricTooltipText(key: string): string {
  const meta = getMetricMeta(key);
  if (!meta) return "";
  return `${meta.fullName} — imported from ${meta.source}. Not platform-original.`;
}

/** Render-ready legend bullets for footer attribution. */
export function legendBullets(keys: string[]): { label: string; source: string; url: string }[] {
  return keys
    .map(getMetricMeta)
    .filter((m): m is ExternalMetricMeta => m !== null)
    .map((m) => ({ label: m.label, source: m.source, url: m.url }));
}
