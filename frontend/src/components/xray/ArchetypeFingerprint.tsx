"use client";

import type { StyleXRayResponse } from "@/lib/types";

interface Props {
  data: StyleXRayResponse;
}

export function ArchetypeFingerprint({ data }: Props) {
  const contributors = data.feature_contributors ?? [];
  if (!contributors.length) {
    return (
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 text-sm text-[var(--muted)]">
        No dominant style signals detected for this window.
      </div>
    );
  }
  return (
    <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5">
      <header className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-[var(--foreground)]">Style Fingerprint</h3>
        <span className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">
          Top contributors vs league
        </span>
      </header>
      <ul className="mt-4 space-y-3">
        {contributors.map((c) => {
          const share = c.share ?? 0;
          const pct = Math.max(4, Math.min(100, Math.round(share * 100)));
          return (
            <li key={c.metric_id} className="flex items-center gap-3">
              <span className="w-36 shrink-0 text-xs font-medium text-[var(--muted-strong)]">
                {c.label}
              </span>
              <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-[var(--surface-alt)]">
                <div
                  className="absolute inset-y-0 left-0 rounded-full bg-[var(--accent-strong)]"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="w-16 shrink-0 text-right text-[11px] font-semibold tabular-nums text-[var(--foreground)]">
                {c.value == null ? "—" : Number(c.value).toFixed(2)}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="mt-4 text-[11px] leading-4 text-[var(--muted)]">
        Share reflects how much each feature drives the archetype label relative to the other top
        contributors (|z|-weighted).
      </p>
    </section>
  );
}
