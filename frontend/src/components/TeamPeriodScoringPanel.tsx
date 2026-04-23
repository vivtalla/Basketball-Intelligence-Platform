"use client";

import { useTeamPeriodScoring } from "@/hooks/usePlayerStats";
import type { TeamPeriodRow } from "@/lib/types";

interface TeamPeriodScoringPanelProps {
  teamAbbreviation: string;
  season: string;
}

export default function TeamPeriodScoringPanel({
  teamAbbreviation,
  season,
}: TeamPeriodScoringPanelProps) {
  const { data, isLoading, error } = useTeamPeriodScoring(teamAbbreviation, season);

  if (error || data?.data_status === "unavailable") {
    return (
      <div className="p-4 bg-[var(--surface-alt)] rounded border border-[var(--border-color)] text-xs text-[var(--muted)]">
        Period scoring data unavailable.
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="p-4 bg-[var(--surface-alt)] rounded border border-[var(--border-color)] text-xs text-[var(--muted)]">
        Loading period scoring...
      </div>
    );
  }

  const renderTable = (rows: TeamPeriodRow[], title: string) => {
    if (!rows || rows.length === 0) return null;

    return (
      <div className="space-y-2">
        <h4 className="text-xs font-semibold text-[var(--text-secondary)]">{title}</h4>
        <div className="bip-table-shell">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-[var(--border-color)]">
                <th className="px-3 py-2 text-left font-semibold">Period</th>
                <th className="px-3 py-2 text-right font-semibold">PTS</th>
                <th className="px-3 py-2 text-right font-semibold">OPP</th>
                <th className="px-3 py-2 text-right font-semibold">+/-</th>
                <th className="px-3 py-2 text-right font-semibold">FG%</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row: TeamPeriodRow) => (
                <tr
                  key={row.period_label}
                  className={`border-b border-[var(--border-color)] hover:bg-[var(--surface-alt)] ${
                    row.period_label === data.best_period ? "bg-green-50 dark:bg-green-950/20" : ""
                  } ${
                    row.period_label === data.worst_period ? "bg-red-50 dark:bg-red-950/20" : ""
                  }`}
                >
                  <td className="px-3 py-2 font-medium">{row.period_label}</td>
                  <td className="px-3 py-2 text-right">{row.pts ? row.pts.toFixed(1) : "—"}</td>
                  <td className="px-3 py-2 text-right">{row.opp_pts ? row.opp_pts.toFixed(1) : "—"}</td>
                  <td
                    className={`px-3 py-2 text-right font-semibold ${
                      row.diff && row.diff > 0
                        ? "text-green-600"
                        : row.diff && row.diff < 0
                        ? "text-red-600"
                        : ""
                    }`}
                  >
                    {row.diff ? (row.diff > 0 ? "+" : "") + row.diff.toFixed(1) : "—"}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {row.fg_pct ? (row.fg_pct * 100).toFixed(1) + "%" : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-[var(--text-secondary)]">Period Scoring Profile</h3>
      {renderTable(data.by_period || [], "By Quarter")}
      {renderTable(data.by_half || [], "By Half")}
    </div>
  );
}
