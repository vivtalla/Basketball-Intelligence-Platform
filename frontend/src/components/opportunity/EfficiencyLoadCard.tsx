"use client";

import type { OpportunityPlayerRow } from "@/lib/types";

interface Props {
  row: OpportunityPlayerRow;
}

export function EfficiencyLoadCard({ row }: Props) {
  const usg = row.usg_pct ?? 0;
  const ts = (row.ts_pct ?? 0) * 100;
  // Rough axis bounds for the scatter: USG 10–40, TS% 45–65.
  const xPct = Math.min(100, Math.max(0, ((usg - 10) / 30) * 100));
  const yPct = Math.min(100, Math.max(0, ((ts - 45) / 20) * 100));
  return (
    <section className="rounded-[1.25rem] border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Efficiency vs Load
          </p>
          <h3 className="mt-0.5 text-base font-semibold text-[var(--foreground)]">
            Where he sits on shot-return vs burden
          </h3>
        </div>
        <span
          className="rounded-full bg-[var(--surface-alt)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted-strong)]"
          title="Position cohort against which the scatter is plotted"
        >
          {row.position_bucket} cohort
        </span>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-[auto,1fr] md:items-center">
        <div
          className="relative h-36 w-36 rounded-xl border border-[var(--border)] bg-[linear-gradient(135deg,rgba(248,244,232,0.98),rgba(239,232,214,0.96))]"
          role="img"
          aria-label="Usage vs true-shooting scatter with the player's position marked"
        >
          <div className="absolute inset-x-0 top-1/2 border-t border-dashed border-[rgba(47,43,36,0.12)]" />
          <div className="absolute inset-y-0 left-1/2 border-l border-dashed border-[rgba(47,43,36,0.12)]" />
          <div
            className="absolute h-3 w-3 -translate-x-1/2 translate-y-1/2 rounded-full border-2 border-white bg-[var(--accent-strong)] shadow"
            style={{ left: `${xPct}%`, bottom: `${yPct}%` }}
          />
          <span className="absolute bottom-1 left-1 text-[9px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
            USG→
          </span>
          <span className="absolute left-1 top-1 text-[9px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
            TS↑
          </span>
        </div>
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">USG%</dt>
            <dd className="text-lg font-semibold tabular-nums text-[var(--foreground)]">
              {row.usg_pct != null ? row.usg_pct.toFixed(1) : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">TS%</dt>
            <dd className="text-lg font-semibold tabular-nums text-[var(--foreground)]">
              {row.ts_pct != null ? `${(row.ts_pct * 100).toFixed(1)}%` : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">ORTG</dt>
            <dd className="text-lg font-semibold tabular-nums text-[var(--foreground)]">
              {row.off_rating != null ? row.off_rating.toFixed(1) : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">Net RTG</dt>
            <dd className="text-lg font-semibold tabular-nums text-[var(--foreground)]">
              {row.net_rating != null
                ? `${row.net_rating > 0 ? "+" : ""}${row.net_rating.toFixed(1)}`
                : "—"}
            </dd>
          </div>
        </dl>
      </div>
      <p className="mt-3 text-[11px] leading-5 text-[var(--muted-strong)]">
        Upper-left means high scoring efficiency on a modest load — the signature of an
        under-tapped scorer. Lower-right means heavy load without matching return.
      </p>
    </section>
  );
}
