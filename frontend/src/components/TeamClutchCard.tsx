"use client";

import { useTeamClutch } from "@/hooks/usePlayerStats";

interface TeamClutchCardProps {
  teamAbbreviation: string;
  season: string;
}

export default function TeamClutchCard({ teamAbbreviation, season }: TeamClutchCardProps) {
  const { data, isLoading, error } = useTeamClutch(teamAbbreviation, season);

  if (error || data?.data_status === "unavailable") {
    return (
      <div className="p-4 bg-[var(--surface-alt)] rounded border border-[var(--border-color)] text-xs text-[var(--muted)]">
        Clutch data unavailable.
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="p-4 bg-[var(--surface-alt)] rounded border border-[var(--border-color)] text-xs text-[var(--muted)]">
        Loading clutch statistics...
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-[var(--text-secondary)]">
        Clutch Analytics (Last 5 min, Score within 5)
      </h3>
      <div className="grid grid-cols-4 gap-2">
        <div className="p-3 bg-[var(--surface-alt)] rounded border border-[var(--border-color)]">
          <div className="text-xs text-[var(--muted)] mb-1">W%</div>
          <div className="text-lg font-bold">
            {data.w_pct !== null ? (data.w_pct * 100).toFixed(1) : "—"}%
          </div>
          {data.w_pct_rank && <div className="text-xs text-[var(--muted)] mt-1">#{data.w_pct_rank}</div>}
        </div>
        <div className="p-3 bg-[var(--surface-alt)] rounded border border-[var(--border-color)]">
          <div className="text-xs text-[var(--muted)] mb-1">+/- PG</div>
          <div className={`text-lg font-bold ${data.plus_minus_pg && data.plus_minus_pg > 0 ? "text-green-600" : data.plus_minus_pg && data.plus_minus_pg < 0 ? "text-red-600" : ""}`}>
            {data.plus_minus_pg ? (data.plus_minus_pg > 0 ? "+" : "") + data.plus_minus_pg.toFixed(2) : "—"}
          </div>
          {data.plus_minus_rank && <div className="text-xs text-[var(--muted)] mt-1">#{data.plus_minus_rank}</div>}
        </div>
        <div className="p-3 bg-[var(--surface-alt)] rounded border border-[var(--border-color)]">
          <div className="text-xs text-[var(--muted)] mb-1">FG%</div>
          <div className="text-lg font-bold">
            {data.fg_pct !== null ? (data.fg_pct * 100).toFixed(1) : "—"}%
          </div>
        </div>
        <div className="p-3 bg-[var(--surface-alt)] rounded border border-[var(--border-color)]">
          <div className="text-xs text-[var(--muted)] mb-1">TS%</div>
          <div className="text-lg font-bold">
            {data.ts_pct !== null ? (data.ts_pct * 100).toFixed(1) : "—"}%
          </div>
        </div>
      </div>
    </div>
  );
}
