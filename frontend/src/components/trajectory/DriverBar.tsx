"use client";

import type { TrajectoryDriverContribution } from "@/lib/types";

const SIGNAL_LABELS: Record<string, string> = {
  ts_pct: "TS%",
  pts: "PTS",
  usg_pct: "USG%",
  ast: "AST",
  tov_pct: "TOV%",
  reb: "REB",
  stl: "STL",
  blk: "BLK",
  plus_minus: "+/-",
};

export const SIGNAL_DESCRIPTIONS: Record<string, string> = {
  ts_pct:
    "True shooting percentage — scoring efficiency accounting for 2s, 3s, and free throws. Positive delta = more efficient over the recent window.",
  pts:
    "Points per game. Raw scoring volume; positive delta = higher output over the recent window.",
  usg_pct:
    "Usage rate — share of team possessions the player finishes while on the floor. Positive delta = heavier offensive load.",
  ast:
    "Assists per game. Creation volume; positive delta = more setups for teammates.",
  tov_pct:
    "Turnover rate — turnovers per possession used. Note: a positive delta here means MORE turnovers (worse); driver contribution is inverted accordingly.",
  reb:
    "Rebounds per game. Positive delta = more boards in the recent window.",
  stl: "Steals per game. Positive delta = more defensive takeaways.",
  blk: "Blocks per game. Positive delta = more rim protection events.",
  plus_minus:
    "On-court point differential per game. Positive delta = team outscored opponents more while the player was on the floor.",
};

interface Props {
  contributions: TrajectoryDriverContribution[];
  compact?: boolean;
}

export function DriverBar({ contributions, compact = false }: Props) {
  if (!contributions.length) return null;

  const maxAbs = Math.max(...contributions.map((d) => Math.abs(d.weighted_contribution)), 0.001);

  return (
    <div className={compact ? "space-y-1" : "space-y-2"}>
      {contributions.map((d) => {
        const isPositive = d.weighted_contribution >= 0;
        const pct = Math.min(100, (Math.abs(d.weighted_contribution) / maxAbs) * 100);
        const description = SIGNAL_DESCRIPTIONS[d.signal] ?? "";
        return (
          <div
            key={d.signal}
            className="flex items-center gap-2"
            title={description || undefined}
          >
            <span
              className="w-12 shrink-0 cursor-help text-right text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)] underline decoration-dotted decoration-[var(--muted)] underline-offset-2"
              title={description || undefined}
            >
              {SIGNAL_LABELS[d.signal] ?? d.signal}
            </span>
            <div className="relative flex-1 overflow-hidden rounded-full bg-[var(--surface-alt)]" style={{ height: compact ? 6 : 8 }}>
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
                isPositive ? "text-[var(--accent-strong)]" : "text-[var(--danger-ink)]"
              }`}
            >
              {d.delta > 0 ? "+" : ""}
              {d.delta.toFixed(2)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
