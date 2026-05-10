"use client";

import Link from "next/link";
import type { TrajectoryPlayerRow } from "@/lib/types";

interface Props {
  row: TrajectoryPlayerRow;
}

export function ShotQualityDeltaCard({ row }: Props) {
  const recentTs = row.recent_averages["ts_pct"] ?? null;
  const baselineTs = row.baseline_averages["ts_pct"] ?? null;

  if (recentTs === null || baselineTs === null) {
    return (
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">Shot Quality</p>
        <p className="mt-1 text-xs text-[var(--muted)]">Insufficient data for this window.</p>
      </div>
    );
  }

  const delta = recentTs - baselineTs;
  const isPositive = delta >= 0;

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">Shot Quality</p>
      <p className="text-[9px] text-[var(--muted)]">True Shooting % — recent vs baseline</p>
      <div className="mt-2 flex items-end gap-6">
        <div className="text-center">
          <p className="text-xl font-bold tabular-nums text-[var(--foreground)]">
            {(recentTs * 100).toFixed(1)}%
          </p>
          <p className="text-[10px] text-[var(--muted)]">Recent</p>
        </div>
        <div className="text-center">
          <p className="text-xl font-bold tabular-nums text-[var(--muted)]">
            {(baselineTs * 100).toFixed(1)}%
          </p>
          <p className="text-[10px] text-[var(--muted)]">Baseline</p>
        </div>
        <div className="text-center">
          <p
            className={`text-xl font-bold tabular-nums ${
              isPositive ? "text-[var(--accent-strong)]" : "text-[var(--danger-ink)]"
            }`}
          >
            {isPositive ? "+" : ""}
            {(delta * 100).toFixed(1)}pp
          </p>
          <p className="text-[10px] text-[var(--muted)]">Δ</p>
        </div>
      </div>
      <Link
        href={`/beta/players/${row.player_id}?tab=shots`}
        className="mt-3 inline-block text-[11px] font-semibold text-[var(--accent-strong)] hover:underline"
      >
        Open Shot Lab →
      </Link>
    </div>
  );
}
