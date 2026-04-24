"use client";

import type { ArchetypeContributor } from "@/lib/types";

interface Props {
  contributors: ArchetypeContributor[];
}

export function ArchetypeContributors({ contributors }: Props) {
  if (!contributors.length) {
    return (
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 text-sm text-[var(--muted)]">
        No dominant role signals detected for this season.
      </div>
    );
  }

  const maxAbsZ = Math.max(...contributors.map((c) => Math.abs(c.z))) || 1;

  return (
    <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5">
      <header className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-[var(--foreground)]">Role Fingerprint</h3>
        <span className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">
          Top features vs league
        </span>
      </header>
      <ul className="mt-4 space-y-3">
        {contributors.map((c) => {
          const pct = Math.max(4, Math.min(100, Math.round((Math.abs(c.z) / maxAbsZ) * 100)));
          const color = c.direction === "above" ? "var(--accent-strong)" : "var(--danger-ink)";
          return (
            <li key={c.feature_key} className="flex items-center gap-3">
              <span className="w-40 shrink-0 text-xs font-medium text-[var(--muted-strong)]">
                {c.label}
              </span>
              <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-[var(--surface-alt)]">
                <div
                  className="absolute inset-y-0 left-0 rounded-full"
                  style={{ width: `${pct}%`, background: color }}
                />
              </div>
              <span className="w-24 shrink-0 text-right text-[11px] font-semibold tabular-nums text-[var(--foreground)]">
                {c.value == null ? "—" : Number(c.value).toFixed(2)}
                <span className="ml-2 text-[var(--muted)]">
                  z={c.z >= 0 ? "+" : ""}{c.z.toFixed(2)}
                </span>
              </span>
            </li>
          );
        })}
      </ul>
      <p className="mt-4 text-[11px] leading-4 text-[var(--muted)]">
        Bar length is |z| relative to the top contributor. Green bars are above-league features,
        red bars are below-league.
      </p>
    </section>
  );
}
