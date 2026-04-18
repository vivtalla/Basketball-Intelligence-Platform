"use client";

import type { MvpClutchProfile } from "@/lib/types";

interface Props {
  clutch: MvpClutchProfile | null | undefined;
}

function fmt(value: number | null | undefined, digits = 1, suffix = ""): string {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(digits)}${suffix}`;
}

function pct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

const confidenceClass: Record<string, string> = {
  high: "text-[var(--success-ink)]",
  medium: "text-[var(--foreground)]",
  low: "text-[var(--warning-ink)]",
};

export default function MvpClutchCard({ clutch }: Props) {
  if (!clutch) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4 text-xs text-[var(--muted)]">
        Clutch data unavailable.
      </div>
    );
  }

  const dimmed = clutch.confidence === "low";

  return (
    <div className={`rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4 ${dimmed ? "opacity-70" : ""}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--accent)]">Clutch &amp; Leverage</p>
          <p className="mt-1 text-xs text-[var(--muted)]">Last 5 min, margin ≤ 5.</p>
        </div>
        <div className="text-right text-[10px] text-[var(--muted)]">
          <p className={`font-semibold ${confidenceClass[clutch.confidence] ?? ""}`}>
            {clutch.confidence.toUpperCase()} confidence
          </p>
          <p>{clutch.source}</p>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
        <Cell label="Games" value={fmt(clutch.clutch_games, 0)} />
        <Cell label="Minutes" value={fmt(clutch.clutch_minutes, 0)} />
        <Cell label="Poss." value={fmt(clutch.clutch_possessions, 0)} />
        <Cell label="TS%" value={pct(clutch.clutch_ts_pct)} />
        <Cell label="Net Rtg" value={fmt(clutch.clutch_net_rating, 1)} />
        <Cell label="+/-" value={fmt(clutch.clutch_plus_minus, 1)} />
        <Cell label="On/Off" value={fmt(clutch.clutch_on_off, 1)} />
        <Cell
          label="Close W-L"
          value={`${clutch.close_game_wins ?? 0}-${clutch.close_game_losses ?? 0}`}
        />
      </div>

      {clutch.note ? <p className="mt-2 text-[10px] text-[var(--muted)]">{clutch.note}</p> : null}
    </div>
  );
}

function Cell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-[var(--border)] bg-[var(--surface)] p-2">
      <p className="text-[10px] uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className="mt-1 text-sm font-semibold text-[var(--foreground)]">{value}</p>
    </div>
  );
}
