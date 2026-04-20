"use client";

import type { StyleNeighbor } from "@/lib/types";

interface Props {
  archetypes: StyleNeighbor[];
}

export function AdjacentArchetypes({ archetypes }: Props) {
  if (!archetypes.length) return null;
  return (
    <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5">
      <header className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-[var(--foreground)]">Adjacent identities</h3>
        <span className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">
          Nearest different archetypes
        </span>
      </header>
      <ul className="mt-3 space-y-2">
        {archetypes.map((n) => (
          <li
            key={n.team_abbreviation + n.archetype}
            className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-[var(--foreground)]">{n.archetype}</span>
              <span className="text-[11px] text-[var(--muted)]">
                via {n.team_abbreviation}
              </span>
            </div>
            <p className="mt-1 text-[11px] leading-4 text-[var(--muted-strong)]">{n.summary}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
