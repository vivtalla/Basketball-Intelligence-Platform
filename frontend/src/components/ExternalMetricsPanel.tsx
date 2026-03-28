"use client";

import type { SeasonStats } from "@/lib/types";

interface ExternalMetricsPanelProps {
  seasons: SeasonStats[];
}

const METRICS: { key: keyof SeasonStats; label: string; source: string }[] = [
  { key: "epm",    label: "EPM",    source: "Dunks & Threes" },
  { key: "raptor", label: "RAPTOR", source: "FiveThirtyEight" },
  { key: "pipm",   label: "PIPM",   source: "Basketball Index" },
  { key: "lebron", label: "LEBRON", source: "BBall Index" },
  { key: "rapm",   label: "RAPM",   source: "Public RAPM" },
];

function metricColor(value: number): string {
  if (value >= 4)  return "text-emerald-600 dark:text-emerald-400 font-semibold";
  if (value >= 1)  return "text-green-600 dark:text-green-400";
  if (value > -1)  return "text-gray-600 dark:text-gray-400";
  if (value > -4)  return "text-orange-500 dark:text-orange-400";
  return "text-red-600 dark:text-red-400";
}

export default function ExternalMetricsPanel({ seasons }: ExternalMetricsPanelProps) {
  // Only show seasons that have at least one non-null external metric
  const relevantSeasons = seasons.filter((s) =>
    METRICS.some((m) => s[m.key] != null)
  );

  if (relevantSeasons.length === 0) return null;

  // Only show columns that have any data
  const activeMetrics = METRICS.filter((m) =>
    relevantSeasons.some((s) => s[m.key] != null)
  );

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700/60">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">
          All-In-One Metrics
        </h3>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
          External metrics — imported from public sources, not platform-original
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 dark:border-gray-700/60">
              <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-5 py-3">
                Season
              </th>
              <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-3 py-3 hidden sm:table-cell">
                Team
              </th>
              {activeMetrics.map((m) => (
                <th
                  key={m.key as string}
                  className="text-right text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3"
                  title={`Source: ${m.source}`}
                >
                  {m.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {relevantSeasons.map((s) => (
              <tr
                key={`${s.season}-${s.team_abbreviation}`}
                className="border-b border-gray-100 dark:border-gray-700/50 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
              >
                <td className="px-5 py-2.5 font-medium text-gray-900 dark:text-gray-100 tabular-nums">
                  {s.season}
                </td>
                <td className="px-3 py-2.5 text-gray-500 dark:text-gray-400 hidden sm:table-cell">
                  {s.team_abbreviation}
                </td>
                {activeMetrics.map((m) => {
                  const val = s[m.key] as number | null;
                  return (
                    <td
                      key={m.key as string}
                      className={`px-4 py-2.5 text-right tabular-nums ${
                        val != null ? metricColor(val) : "text-gray-300 dark:text-gray-600"
                      }`}
                    >
                      {val != null ? (val > 0 ? `+${val.toFixed(1)}` : val.toFixed(1)) : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Source legend */}
      <div className="px-5 py-3 border-t border-gray-100 dark:border-gray-700/60 flex flex-wrap gap-x-4 gap-y-1">
        {activeMetrics.map((m) => (
          <span key={m.key as string} className="text-[11px] text-gray-400 dark:text-gray-500">
            <span className="font-medium text-gray-500 dark:text-gray-400">{m.label}:</span> {m.source}
          </span>
        ))}
      </div>
    </div>
  );
}
