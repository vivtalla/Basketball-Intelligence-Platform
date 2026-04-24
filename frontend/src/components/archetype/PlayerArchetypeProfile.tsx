"use client";

import { usePlayerArchetype } from "@/hooks/usePlayerArchetype";
import type { ArchetypeConfidence } from "@/lib/types";
import { ArchetypeContributors } from "./ArchetypeContributors";
import { ArchetypeMethodologyDrawer } from "./ArchetypeMethodologyDrawer";

interface Props {
  playerId: number;
  season: string | null;
}

function confidenceClasses(confidence: ArchetypeConfidence): string {
  if (confidence === "high") {
    return "border-[var(--accent-strong)] bg-[var(--accent-soft)] text-[var(--accent-strong)]";
  }
  if (confidence === "medium") {
    return "border-[var(--warning-border)] bg-[var(--warning-soft)] text-[var(--warning-ink)]";
  }
  return "border-[var(--border)] bg-[var(--surface-alt)] text-[var(--muted-strong)]";
}

export function PlayerArchetypeProfile({ playerId, season }: Props) {
  const { data, error, isLoading } = usePlayerArchetype(playerId, season ?? "");

  if (!season) return null;

  if (isLoading) {
    return (
      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 text-sm text-[var(--muted)]">
        Loading role archetype…
      </section>
    );
  }

  if (error || !data) {
    return (
      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 text-sm text-[var(--muted)]">
        Role archetype unavailable for this season.
      </section>
    );
  }

  const isFallback = data.archetype_key === "developmental" || data.archetype_key === "balanced_role";

  return (
    <section className="space-y-4">
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
              Role archetype · {season}
            </div>
            <h2 className="mt-1 text-2xl font-semibold text-[var(--foreground)]">{data.label}</h2>
          </div>
          <span
            className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${confidenceClasses(
              data.confidence
            )}`}
          >
            {data.confidence} confidence
          </span>
        </div>
        <p className="mt-3 text-sm leading-5 text-[var(--muted-strong)]">{data.reason}</p>
        <p className="mt-3 text-[11px] text-[var(--muted)]">
          Peer pool: {data.sample.peer_pool_size} rotation players · GP {data.sample.gp} ·{" "}
          {data.sample.min_pg.toFixed(1)} min/g · methodology {data.methodology_version}
        </p>
      </div>

      {!isFallback && <ArchetypeContributors contributors={data.contributors} />}

      <ArchetypeMethodologyDrawer />
    </section>
  );
}
