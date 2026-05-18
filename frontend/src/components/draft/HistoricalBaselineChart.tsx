// Sprint 101 (Stream B) — historical baseline distribution chart.
//
// Single horizontal stacked bar showing the comp-neighbourhood's outcome
// distribution: star_pct + starter_pct + role_player_pct + bust_pct = 1.0.
// "Of N historical comps with NBA outcomes" caption below. When the analysis
// service flags `insufficient: true` (fewer than 3 comps with outcomes),
// renders a caveat panel instead.

import type { HistoricalBaseline } from "@/lib/types";
import { TIER_PALETTE } from "./TierBadge";

interface Props {
  baseline: HistoricalBaseline | null | undefined;
}

interface Segment {
  key: string;
  label: string;
  pct: number;
  color: string;
}

function buildSegments(baseline: HistoricalBaseline): Segment[] {
  return [
    { key: "star",        label: "Star+",       pct: baseline.star_pct,        color: TIER_PALETTE.star.text },
    { key: "starter",     label: "Starter",     pct: baseline.starter_pct,     color: TIER_PALETTE.starter.text },
    { key: "role_player", label: "Role Player", pct: baseline.role_player_pct, color: TIER_PALETTE.role_player.text },
    { key: "bust",        label: "Bust",        pct: baseline.bust_pct,        color: TIER_PALETTE.bust.text },
  ];
}

export default function HistoricalBaselineChart({ baseline }: Props) {
  if (!baseline) return null;

  // Insufficient data → render the caveat instead of a misleading bar.
  if (baseline.insufficient) {
    return (
      <section className="bip-panel rounded-[1.85rem] p-5 sm:p-6">
        <p className="bip-kicker">Historical baseline</p>
        <h2 className="bip-display mt-1 text-xl font-bold text-[var(--foreground)]">
          Outcome distribution
        </h2>
        <p className="mt-3 text-sm text-[var(--muted-strong)]">
          Insufficient comp data — only{" "}
          <span className="tabular-nums font-semibold">{baseline.n_with_outcome}</span>{" "}
          of {baseline.n_comps} comps have NBA career outcomes recorded yet. Need at
          least 3 for a reliable distribution.
        </p>
      </section>
    );
  }

  const segments = buildSegments(baseline);

  return (
    <section className="bip-panel rounded-[1.85rem] p-5 sm:p-6">
      <p className="bip-kicker">Historical baseline</p>
      <h2 className="bip-display mt-1 text-xl font-bold text-[var(--foreground)]">
        Comp-neighbourhood outcome distribution
      </h2>

      {/* Stacked bar */}
      <div className="mt-4 flex h-6 w-full overflow-hidden rounded-md border border-[var(--border)]">
        {segments.map((seg) => {
          if (seg.pct <= 0) return null;
          return (
            <div
              key={seg.key}
              className="flex items-center justify-center text-[10px] font-semibold text-white"
              style={{ width: `${seg.pct * 100}%`, backgroundColor: seg.color }}
              title={`${seg.label}: ${(seg.pct * 100).toFixed(0)}%`}
            >
              {seg.pct >= 0.12 ? `${(seg.pct * 100).toFixed(0)}%` : null}
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
        {segments.map((seg) => (
          <span key={seg.key} className="inline-flex items-center gap-1.5 text-[11px]">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: seg.color }} />
            <span className="text-[var(--muted-strong)]">{seg.label}</span>
            <span className="tabular-nums font-semibold text-[var(--foreground)]">
              {(seg.pct * 100).toFixed(0)}%
            </span>
          </span>
        ))}
      </div>

      <p className="mt-3 text-[11px] text-[var(--muted)]">
        Based on{" "}
        <span className="tabular-nums font-semibold">{baseline.n_with_outcome}</span>{" "}
        historical comps with NBA outcomes (out of {baseline.n_comps} total).
      </p>
    </section>
  );
}
