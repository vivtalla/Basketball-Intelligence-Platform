"use client";

import type { OpportunityPlayerRow } from "@/lib/types";
import { SIGNAL_LABELS } from "./OpportunityDriverBar";

interface Props {
  row: OpportunityPlayerRow;
}

export function DirectionalHintBanner({ row }: Props) {
  if (!row.directional_hint) return null;
  return (
    <section className="rounded-[1.25rem] border border-[rgba(33,72,59,0.18)] bg-[rgba(33,72,59,0.06)] p-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--accent-strong)]">
        Directional hint · {row.confidence} confidence
      </p>
      <p className="mt-2 text-sm leading-6 text-[var(--foreground)]">
        {row.directional_hint}
      </p>
      {row.hint_basis.length ? (
        <div className="mt-2 flex flex-wrap gap-2">
          {row.hint_basis.map((s) => (
            <span
              key={s}
              className="rounded-full border border-[rgba(33,72,59,0.2)] bg-[rgba(255,255,255,0.7)] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--accent-strong)]"
            >
              {SIGNAL_LABELS[s] ?? s}
            </span>
          ))}
        </div>
      ) : null}
      <p className="mt-2 text-[10px] leading-4 text-[var(--muted)]">
        Hints are directional only. They never imply a specific minute or
        possession reallocation.
      </p>
    </section>
  );
}
