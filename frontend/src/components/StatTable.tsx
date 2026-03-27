"use client";

import { useState } from "react";
import type { SeasonStats } from "@/lib/types";

interface StatTableProps {
  seasons: SeasonStats[];
  careerTotals?: SeasonStats | null;
}

type ViewMode = "traditional" | "advanced";

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
  { key: "usg_pct", label: "USG%" },
  { key: "per", label: "PER" },
  { key: "bpm", label: "BPM" },
  { key: "off_rating", label: "ORTG" },
  { key: "def_rating", label: "DRTG" },
  { key: "net_rating", label: "NET" },
  { key: "vorp", label: "VORP" },
  { key: "pie", label: "PIE" },
];

function formatValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "number") {
    if (key.includes("pct") || key === "pie") return (value * 100).toFixed(1);
    if (key.includes("_pg") || key === "min_pg") return value.toFixed(1);
    if (key === "per" || key === "bpm" || key === "vorp") return value.toFixed(1);
    if (key.includes("rating")) return value.toFixed(1);
    return String(value);
  }
  return String(value);
}

export default function StatTable({ seasons, careerTotals }: StatTableProps) {
  const [view, setView] = useState<ViewMode>("traditional");
  const columns = view === "traditional" ? traditionalColumns : advancedColumns;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold">Season Stats</h2>
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
            {seasons.map((season, i) => (
              <tr
                key={`${season.season}-${season.team_abbreviation}-${i}`}
                className="hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className="px-3 py-2.5 whitespace-nowrap tabular-nums"
                  >
                    {formatValue(
                      col.key,
                      season[col.key as keyof SeasonStats]
                    )}
                  </td>
                ))}
              </tr>
            ))}

            {/* Career Totals */}
            {careerTotals && (
              <tr className="bg-gray-50 dark:bg-gray-750 font-semibold border-t-2 border-gray-300 dark:border-gray-600">
                {columns.map((col) => (
                  <td key={col.key} className="px-3 py-2.5 whitespace-nowrap tabular-nums">
                    {col.key === "season"
                      ? "Career"
                      : col.key === "team_abbreviation"
                      ? ""
                      : formatValue(
                          col.key,
                          careerTotals[col.key as keyof SeasonStats]
                        )}
                  </td>
                ))}
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
