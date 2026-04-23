"use client";

import { useTeamBenchAnalytics } from "@/hooks/usePlayerStats";
import type { BenchUnitRow } from "@/lib/types";

interface TeamBenchAnalyticsPanelProps {
  teamAbbreviation: string;
  season: string;
}

export default function TeamBenchAnalyticsPanel({
  teamAbbreviation,
  season,
}: TeamBenchAnalyticsPanelProps) {
  const { data, isLoading, error } = useTeamBenchAnalytics(teamAbbreviation, season);

  if (error || data?.data_status === "unavailable") {
    return (
      <div className="p-4 bg-[var(--surface-alt)] rounded border border-[var(--border-color)] text-xs text-[var(--muted)]">
        Bench analytics data unavailable.
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="p-4 bg-[var(--surface-alt)] rounded border border-[var(--border-color)] text-xs text-[var(--muted)]">
        Loading bench analytics...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-[var(--text-secondary)]">Lineup Intelligence</h3>

      <div className="grid grid-cols-3 gap-2">
        <div className="p-3 bg-[var(--surface-alt)] rounded border border-[var(--border-color)]">
          <div className="text-xs text-[var(--muted)] mb-1">Starter Unit NR</div>
          <div className={`text-lg font-bold ${data.starter_net_rating && data.starter_net_rating > 0 ? "text-green-600" : data.starter_net_rating && data.starter_net_rating < 0 ? "text-red-600" : ""}`}>
            {data.starter_net_rating
              ? (data.starter_net_rating > 0 ? "+" : "") + data.starter_net_rating.toFixed(1)
              : "—"}
          </div>
        </div>
        <div className="p-3 bg-[var(--surface-alt)] rounded border border-[var(--border-color)]">
          <div className="text-xs text-[var(--muted)] mb-1">Bench Unit NR</div>
          <div className={`text-lg font-bold ${data.bench_net_rating && data.bench_net_rating > 0 ? "text-green-600" : data.bench_net_rating && data.bench_net_rating < 0 ? "text-red-600" : ""}`}>
            {data.bench_net_rating
              ? (data.bench_net_rating > 0 ? "+" : "") + data.bench_net_rating.toFixed(1)
              : "—"}
          </div>
        </div>
        <div className="p-3 bg-[var(--surface-alt)] rounded border border-[var(--border-color)]">
          <div className="text-xs text-[var(--muted)] mb-1">Gap</div>
          <div className={`text-lg font-bold ${data.net_rating_gap && data.net_rating_gap > 0 ? "text-green-600" : data.net_rating_gap && data.net_rating_gap < 0 ? "text-red-600" : ""}`}>
            {data.net_rating_gap
              ? (data.net_rating_gap > 0 ? "+" : "") + data.net_rating_gap.toFixed(1)
              : "—"}
          </div>
        </div>
      </div>

      {data.bench_anchor_name && (
        <div className="p-3 bg-[var(--surface-alt)] rounded border border-[var(--border-color)] text-xs">
          <div className="text-[var(--muted)] mb-1">Bench Anchor</div>
          <div className="font-semibold">{data.bench_anchor_name}</div>
        </div>
      )}

      {data.best_bench_lineups && data.best_bench_lineups.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-[var(--text-secondary)]">Best Bench Units</h4>
          <div className="space-y-2">
            {data.best_bench_lineups.map((lineup: BenchUnitRow) => (
              <div
                key={lineup.lineup_key}
                className="p-2 bg-[var(--surface-alt)] rounded border border-[var(--border-color)] text-xs"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="font-medium">{lineup.player_names.join(", ")}</div>
                  <div
                    className={`font-bold ${
                      lineup.net_rating && lineup.net_rating > 0
                        ? "text-green-600"
                        : lineup.net_rating && lineup.net_rating < 0
                        ? "text-red-600"
                        : ""
                    }`}
                  >
                    {lineup.net_rating ? (lineup.net_rating > 0 ? "+" : "") + lineup.net_rating.toFixed(1) : "—"}
                  </div>
                </div>
                <div className="text-[var(--muted)] text-xs">
                  {lineup.possessions} poss · {lineup.minutes ? lineup.minutes.toFixed(0) : "—"} min
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
