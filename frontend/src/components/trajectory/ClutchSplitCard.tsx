"use client";

import type { TrajectoryClutchContext } from "@/lib/types";

interface Props {
  clutchContext: TrajectoryClutchContext | null;
}

export function ClutchSplitCard({ clutchContext }: Props) {
  if (!clutchContext) {
    return (
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">Clutch</p>
        <p className="mt-1 text-xs text-[var(--muted)]">No clutch data this season.</p>
      </div>
    );
  }

  const { clutch_pts, clutch_fg_pct, clutch_fga } = clutchContext;
  const hasSample = clutch_fga !== null && clutch_fga >= 5;

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">Clutch</p>
      <p className="text-[9px] text-[var(--muted)]">Last 5 min, score within 5</p>
      <div className="mt-2 flex items-end gap-6">
        {clutch_pts !== null && (
          <div className="text-center">
            <p className="text-xl font-bold tabular-nums text-[var(--foreground)]">
              {clutch_pts.toFixed(1)}
            </p>
            <p className="text-[10px] text-[var(--muted)]">PTS</p>
          </div>
        )}
        {clutch_fg_pct !== null && (
          <div className="text-center">
            <p className="text-xl font-bold tabular-nums text-[var(--foreground)]">
              {(clutch_fg_pct * 100).toFixed(1)}%
            </p>
            <p className="text-[10px] text-[var(--muted)]">FG%</p>
          </div>
        )}
        {clutch_fga !== null && (
          <div className="text-center">
            <p className="text-xl font-bold tabular-nums text-[var(--muted)]">
              {clutch_fga}
            </p>
            <p className="text-[10px] text-[var(--muted)]">FGA</p>
          </div>
        )}
      </div>
      {!hasSample && (
        <p className="mt-2 text-[10px] text-[var(--muted)]">⚠ Small sample — interpret with caution.</p>
      )}
    </div>
  );
}
