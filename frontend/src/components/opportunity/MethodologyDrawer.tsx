"use client";

import type { OpportunityMethodology } from "@/lib/types";
import { SIGNAL_DESCRIPTIONS, SIGNAL_LABELS } from "./OpportunityDriverBar";

interface Props {
  methodology: OpportunityMethodology;
}

export function MethodologyDrawer({ methodology }: Props) {
  return (
    <details className="rounded-[1.25rem] border border-[var(--border)] bg-[var(--surface)] p-4 text-sm text-[var(--muted-strong)]">
      <summary className="cursor-pointer list-none font-semibold text-[var(--foreground)]">
        How the Opportunity Score is calculated
      </summary>
      <div className="mt-3 space-y-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Weights (clamped ±{methodology.z_score_cap} per signal)
          </div>
          <ul className="mt-2 grid gap-2 text-xs sm:grid-cols-2">
            {Object.entries(methodology.weights).map(([signal, weight]) => (
              <li
                key={signal}
                className="flex flex-col gap-1 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-[var(--foreground)]">
                    {SIGNAL_LABELS[signal] ?? signal}
                  </span>
                  <span className="tabular-nums text-[var(--muted-strong)]">
                    weight {weight.toFixed(2)}
                  </span>
                </div>
                <p className="text-[11px] leading-4 text-[var(--muted-strong)]">
                  {SIGNAL_DESCRIPTIONS[signal] ?? ""}
                </p>
              </li>
            ))}
          </ul>
        </div>
        <div className="grid gap-2 text-xs sm:grid-cols-2">
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
            <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
              Min. minutes per game
            </div>
            <div className="font-semibold tabular-nums text-[var(--foreground)]">
              {methodology.min_minutes}
            </div>
          </div>
          <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2">
            <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
              Min. possessions per lineup
            </div>
            <div className="font-semibold tabular-nums text-[var(--foreground)]">
              {methodology.min_lineup_possessions}
            </div>
          </div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            Confidence thresholds
          </div>
          <ul className="mt-2 space-y-1 text-xs">
            {Object.entries(methodology.confidence_thresholds).map(([key, bands]) => (
              <li key={key} className="flex items-center justify-between">
                <span className="text-[var(--muted-strong)]">{key}</span>
                <span className="tabular-nums text-[var(--foreground)]">
                  {Object.entries(bands)
                    .map(([band, v]) => `${band} ≥ ${v}`)
                    .join(" · ")}
                </span>
              </li>
            ))}
          </ul>
        </div>
        <ul className="list-disc space-y-1 pl-5 text-xs leading-5">
          {methodology.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
        <p className="text-[10px] text-[var(--muted)]">
          Methodology version: {methodology.version}
        </p>
      </div>
    </details>
  );
}
