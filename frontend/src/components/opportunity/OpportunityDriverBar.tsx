"use client";

import type { OpportunityDriverContribution } from "@/lib/types";

export const SIGNAL_LABELS: Record<string, string> = {
  efficiency_load_gap: "Eff / Load",
  team_impact_swing: "Team Impact",
  lineup_synergy_lift: "Lineup Fit",
  role_fit_gap: "Role Fit",
  cohort_percentile: "Cohort",
};

interface Props {
  contributions: OpportunityDriverContribution[];
  compact?: boolean;
}

export function OpportunityDriverBar({ contributions, compact = false }: Props) {
  if (!contributions.length) return null;
  const maxAbs = Math.max(
    ...contributions.map((d) => Math.abs(d.weighted_contribution)),
    0.001
  );
  return (
    <div className={compact ? "space-y-1" : "space-y-2"}>
      {contributions.map((d) => {
        const isPositive = d.weighted_contribution >= 0;
        const pct = Math.min(
          100,
          (Math.abs(d.weighted_contribution) / maxAbs) * 100
        );
        return (
          <div key={d.signal} className="flex items-center gap-2">
            <span className="w-[72px] shrink-0 text-right text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
              {SIGNAL_LABELS[d.signal] ?? d.signal}
            </span>
            <div
              className="relative flex-1 overflow-hidden rounded-full bg-[var(--surface-alt)]"
              style={{ height: compact ? 6 : 8 }}
            >
              <div
                className={`absolute inset-y-0 left-0 rounded-full transition-all ${
                  isPositive
                    ? "bg-[var(--accent-strong)]"
                    : "bg-[var(--danger-ink)]"
                }`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span
              className={`w-14 shrink-0 text-right text-[11px] font-semibold tabular-nums ${
                isPositive
                  ? "text-[var(--accent-strong)]"
                  : "text-[var(--danger-ink)]"
              }`}
              title={`z-score ${d.z_score.toFixed(2)}, weighted ${d.weighted_contribution.toFixed(3)}`}
            >
              {d.z_score > 0 ? "+" : ""}
              {d.z_score.toFixed(2)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
