"use client";

import type { OpportunityResponse } from "@/lib/types";
import { SIGNAL_DESCRIPTIONS, SIGNAL_LABELS } from "./OpportunityDriverBar";

interface Props {
  report: OpportunityResponse;
}

export function TeamRollup({ report }: Props) {
  const rollup = report.team_rollup;
  if (!rollup || rollup.sample_size === 0) return null;
  const sorted = Object.entries(rollup.top_drivers)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);
  if (!sorted.length) return null;
  return (
    <section className="rounded-[1.5rem] border border-[var(--border)] bg-[linear-gradient(145deg,rgba(247,243,232,0.92),rgba(228,236,232,0.94))] p-5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
        Team Roll-Up
      </p>
      <h2 className="mt-1 text-xl font-semibold text-[var(--foreground)]">
        Where is {rollup.team_abbreviation} leaving opportunity on the table?
      </h2>
      <p className="mt-2 max-w-2xl text-sm text-[var(--muted-strong)]">
        Top drivers across the {rollup.sample_size}-player roster (after filters).
        Each tile counts how many players had that signal as their strongest
        positive contribution.
      </p>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {sorted.map(([signal, count]) => (
          <div
            key={signal}
            title={SIGNAL_DESCRIPTIONS[signal] ?? ""}
            className="cursor-help rounded-xl border border-[rgba(33,72,59,0.12)] bg-[rgba(255,255,255,0.75)] p-4"
          >
            <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
              {SIGNAL_LABELS[signal] ?? signal}
            </div>
            <div className="mt-1 text-2xl font-semibold tabular-nums text-[var(--foreground)]">
              {count}
            </div>
            <div className="text-[11px] text-[var(--muted-strong)]">
              {count === 1 ? "player" : "players"} leading here
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
