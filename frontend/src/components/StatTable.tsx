"use client";

import { useState, useMemo } from "react";
import type { SeasonStats } from "@/lib/types";

interface StatTableProps {
  seasons: SeasonStats[];
  careerTotals?: SeasonStats | null;
  playoffSeasons?: SeasonStats[];
}

type ViewMode = "traditional" | "advanced";
type SeasonType = "regular" | "playoffs";
type RateMode = "pg" | "p36" | "p100";

// Which per-game keys map to which counting-stat keys in the per36/per100 dicts
const PG_TO_RATE_KEY: Record<string, string> = {
  pts_pg: "pts",
  reb_pg: "reb",
  ast_pg: "ast",
  stl_pg: "stl",
  blk_pg: "blk",
  tov_pg: "tov",
};

const traditionalColumns = [
  { key: "season", label: "Season" },
  { key: "team_abbreviation", label: "Team" },
  { key: "gp", label: "GP" },
  { key: "gs", label: "GS" },
  { key: "min_pg", label: "MPG" },
  { key: "pts_pg", label: "PTS" },
  { key: "reb_pg", label: "REB" },
  { key: "ast_pg", label: "AST" },
  { key: "stl_pg", label: "STL" },
  { key: "blk_pg", label: "BLK" },
  { key: "tov_pg", label: "TOV" },
  { key: "fg_pct", label: "FG%" },
  { key: "fg3_pct", label: "3P%" },
  { key: "ft_pct", label: "FT%" },
];

const advancedColumns = [
  { key: "season", label: "Season" },
  { key: "team_abbreviation", label: "Team" },
  { key: "gp", label: "GP" },
  { key: "min_pg", label: "MPG" },
  { key: "ts_pct", label: "TS%" },
  { key: "efg_pct", label: "eFG%" },
  { key: "ftr", label: "FTr" },
  { key: "par3", label: "3PAr" },
  { key: "usg_pct", label: "USG%" },
  { key: "ast_tov", label: "AST/TOV" },
  { key: "oreb_pct", label: "OREB%" },
  { key: "per", label: "PER" },
  { key: "obpm", label: "OBPM" },
  { key: "dbpm", label: "DBPM" },
  { key: "bpm", label: "BPM" },
  { key: "off_rating", label: "ORTG" },
  { key: "def_rating", label: "DRTG" },
  { key: "net_rating", label: "NET" },
  { key: "vorp", label: "VORP" },
  { key: "ws", label: "WS" },
  { key: "pie", label: "PIE" },
  { key: "darko", label: "DARKO" },
  { key: "epm", label: "EPM" },
  { key: "rapm", label: "RAPM" },
  { key: "lebron", label: "LEBRON" },
  { key: "raptor", label: "RAPTOR" },
  { key: "pipm", label: "PIPM" },
];

// Stats that show YoY trend indicators. false = lower is better (red when increases).
const TREND_STATS: Record<string, boolean> = {
  pts_pg: true,
  reb_pg: true,
  ast_pg: true,
  stl_pg: true,
  blk_pg: true,
  tov_pg: false,
  fg_pct: true,
  fg3_pct: true,
  ft_pct: true,
  min_pg: true,
  ts_pct: true,
  efg_pct: true,
  usg_pct: true,
  per: true,
  bpm: true,
  obpm: true,
  dbpm: true,
  off_rating: true,
  def_rating: false,
  net_rating: true,
  vorp: true,
  ws: true,
  epm: true,
  rapm: true,
  lebron: true,
  raptor: true,
  pipm: true,
};

// Minimum delta to display (suppress noise for near-identical values)
const TREND_MIN_DELTA: Record<string, number> = {
  fg_pct: 0.005,
  fg3_pct: 0.005,
  ft_pct: 0.005,
  ts_pct: 0.005,
  efg_pct: 0.005,
  usg_pct: 0.005,
  oreb_pct: 0.005,
};

interface TrendInfo {
  delta: number;        // raw delta (current - prior)
  isImprovement: boolean;
}

type TrendMap = Record<string, TrendInfo>;

function formatValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "number") {
    if (key.includes("pct") || key === "pie") return (value * 100).toFixed(1);
    if (key.includes("_pg") || key === "min_pg") return value.toFixed(1);
    if (key === "per" || key === "bpm" || key === "vorp") return value.toFixed(1);
    if (key.includes("rating")) return value.toFixed(1);
    if (key === "darko" || key === "epm" || key === "rapm") return value.toFixed(2);
    if (key === "lebron" || key === "raptor" || key === "pipm") return value.toFixed(2);
    if (key === "obpm" || key === "dbpm") return value.toFixed(1);
    if (key === "ftr" || key === "par3" || key === "oreb_pct") return (value * 100).toFixed(1);
    if (key === "ast_tov") return value.toFixed(2);
    return String(value);
  }
  return String(value);
}

function formatTrendDelta(key: string, delta: number): string {
  const sign = delta > 0 ? "+" : "";
  if (key.includes("pct") || key === "pie" || key === "ftr" || key === "par3" || key === "oreb_pct") {
    return `${sign}${(delta * 100).toFixed(1)}`;
  }
  if (key === "darko" || key === "epm" || key === "rapm" || key === "lebron" || key === "raptor" || key === "pipm" || key === "ast_tov") {
    return `${sign}${delta.toFixed(2)}`;
  }
  return `${sign}${delta.toFixed(1)}`;
}

function getRateValue(
  season: SeasonStats,
  colKey: string,
  rateMode: RateMode
): string {
  // Non-counting columns: always use direct value
  if (!PG_TO_RATE_KEY[colKey]) {
    return formatValue(colKey, season[colKey as keyof SeasonStats]);
  }

  if (rateMode === "pg") {
    return formatValue(colKey, season[colKey as keyof SeasonStats]);
  }

  const rateKey = PG_TO_RATE_KEY[colKey];
  const dict = rateMode === "p36" ? season.per36 : season.per100;
  const val = dict?.[rateKey];
  return val != null ? val.toFixed(1) : "-";
}

/**
 * Compute YoY trends for the most recent season.
 *
 * Strategy:
 * - Group regular-season rows by season string; pick the row with the most GP
 *   (handles mid-season trades where the same player has multiple team rows).
 * - Sort descending by season string. If < 2 distinct seasons, return empty map.
 * - For each TREND_STATS key, compute delta = current - prior and classify.
 */
function computeTrends(seasons: SeasonStats[]): TrendMap {
  if (seasons.length < 2) return {};

  // Group by season, keep highest-GP row
  const bySeason = new Map<string, SeasonStats>();
  for (const s of seasons) {
    const existing = bySeason.get(s.season);
    if (!existing || (s.gp ?? 0) > (existing.gp ?? 0)) {
      bySeason.set(s.season, s);
    }
  }

  if (bySeason.size < 2) return {};

  const sorted = Array.from(bySeason.values()).sort((a, b) =>
    b.season.localeCompare(a.season)
  );
  const current = sorted[0];
  const prior = sorted[1];

  const trends: TrendMap = {};
  for (const [key, higherIsBetter] of Object.entries(TREND_STATS)) {
    const cur = current[key as keyof SeasonStats];
    const prv = prior[key as keyof SeasonStats];
    if (typeof cur !== "number" || typeof prv !== "number") continue;

    const delta = cur - prv;
    const minDelta = TREND_MIN_DELTA[key] ?? 0.05;
    if (Math.abs(delta) < minDelta) continue;

    trends[key] = {
      delta,
      isImprovement: higherIsBetter ? delta > 0 : delta < 0,
    };
  }
  return trends;
}

export default function StatTable({ seasons, careerTotals, playoffSeasons = [] }: StatTableProps) {
  const [view, setView] = useState<ViewMode>("traditional");
  const [seasonType, setSeasonType] = useState<SeasonType>("regular");
  const [rateMode, setRateMode] = useState<RateMode>("pg");

  const columns = view === "traditional" ? traditionalColumns : advancedColumns;
  const displaySeasons = seasonType === "regular" ? seasons : playoffSeasons;
  const hasPlayoffs = playoffSeasons.length > 0;

  // Compute trends once; only show in regular season + per-game mode
  const trends = useMemo(() => computeTrends(seasons), [seasons]);

  // Identify the season string of the most recent regular season row
  const mostRecentSeason = useMemo(() => {
    if (seasons.length === 0) return null;
    return seasons.reduce((best, s) =>
      s.season.localeCompare(best.season) > 0 ? s : best
    ).season;
  }, [seasons]);

  const showTrends = seasonType === "regular" && rateMode === "pg" && Object.keys(trends).length > 0;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold">Season Stats</h2>

          {/* Regular Season / Playoffs toggle */}
          <div className="flex rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 text-xs ml-2">
            <button
              onClick={() => setSeasonType("regular")}
              className={`px-3 py-1.5 transition-colors ${
                seasonType === "regular"
                  ? "bg-blue-500 text-white"
                  : "bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-600"
              }`}
            >
              Regular Season
            </button>
            <button
              onClick={() => hasPlayoffs && setSeasonType("playoffs")}
              disabled={!hasPlayoffs}
              title={!hasPlayoffs ? "No playoff data" : undefined}
              className={`px-3 py-1.5 transition-colors ${
                seasonType === "playoffs"
                  ? "bg-blue-500 text-white"
                  : hasPlayoffs
                  ? "bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-600"
                  : "bg-white dark:bg-gray-700 text-gray-300 dark:text-gray-600 cursor-not-allowed"
              }`}
            >
              Playoffs
            </button>
          </div>

          {/* Per-36 / Per-100 toggle — only on Traditional tab */}
          {view === "traditional" && (
            <div className="flex rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 text-xs ml-2">
              {(["pg", "p36", "p100"] as RateMode[]).map((mode) => {
                const label = mode === "pg" ? "Per Game" : mode === "p36" ? "Per 36" : "Per 100";
                return (
                  <button
                    key={mode}
                    onClick={() => setRateMode(mode)}
                    className={`px-3 py-1.5 transition-colors ${
                      rateMode === mode
                        ? "bg-indigo-500 text-white"
                        : "bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-600"
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Traditional / Advanced toggle */}
        <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
          <button
            onClick={() => setView("traditional")}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              view === "traditional"
                ? "bg-white dark:bg-gray-600 shadow-sm font-medium"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Traditional
          </button>
          <button
            onClick={() => setView("advanced")}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              view === "advanced"
                ? "bg-white dark:bg-gray-600 shadow-sm font-medium"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Advanced
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-750">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap"
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {displaySeasons.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-3 py-8 text-center text-sm text-gray-400 dark:text-gray-500">
                  No {seasonType === "playoffs" ? "playoff" : "regular season"} data available.
                </td>
              </tr>
            ) : (
              displaySeasons.map((season, i) => {
                const isMostRecent = showTrends && season.season === mostRecentSeason;
                return (
                  <tr
                    key={`${season.season}-${season.team_abbreviation}-${i}`}
                    className="hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
                  >
                    {columns.map((col) => {
                      const formattedVal = view === "traditional"
                        ? getRateValue(season, col.key, rateMode)
                        : formatValue(col.key, season[col.key as keyof SeasonStats]);

                      const trend = isMostRecent ? trends[col.key] : undefined;

                      return (
                        <td key={col.key} className="px-3 py-2.5 whitespace-nowrap tabular-nums">
                          {trend ? (
                            <div className="flex flex-col leading-tight">
                              <span>{formattedVal}</span>
                              <span
                                className={`text-[10px] font-medium mt-0.5 ${
                                  trend.isImprovement
                                    ? "text-emerald-500 dark:text-emerald-400"
                                    : "text-red-500 dark:text-red-400"
                                }`}
                              >
                                {trend.isImprovement ? "▲" : "▼"} {formatTrendDelta(col.key, trend.delta)}
                              </span>
                            </div>
                          ) : (
                            formattedVal
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            )}

            {/* Career Totals — only for regular season, only for Per Game */}
            {seasonType === "regular" && careerTotals && (
              <tr className="bg-gray-50 dark:bg-gray-750 font-semibold border-t-2 border-gray-300 dark:border-gray-600">
                {columns.map((col) => (
                  <td key={col.key} className="px-3 py-2.5 whitespace-nowrap tabular-nums">
                    {col.key === "season"
                      ? "Career"
                      : col.key === "team_abbreviation"
                      ? ""
                      : view === "traditional" && rateMode !== "pg"
                      ? "—"
                      : formatValue(col.key, careerTotals[col.key as keyof SeasonStats])}
                  </td>
                ))}
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Trend legend — only shown when trends are active */}
      {showTrends && (
        <div className="px-6 py-2 border-t border-gray-100 dark:border-gray-700 flex items-center gap-3 text-xs text-gray-400 dark:text-gray-500">
          <span>▲ / ▼ vs. prior season</span>
          <span className="text-emerald-500 dark:text-emerald-400">▲ improvement</span>
          <span className="text-red-500 dark:text-red-400">▼ decline</span>
        </div>
      )}
    </div>
  );
}
