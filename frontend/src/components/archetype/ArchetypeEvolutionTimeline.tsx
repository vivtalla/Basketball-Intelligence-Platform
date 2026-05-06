"use client";

import { usePlayerArchetypeHistory } from "@/hooks/usePlayerArchetype";
import { humanizeMethodologyVersion } from "@/lib/methodology";
import type { ArchetypeConfidence, ArchetypeHistoryEntry } from "@/lib/types";

interface Props {
  playerId: number;
}

function confidenceDotClass(confidence: ArchetypeConfidence): string {
  if (confidence === "high") return "bg-[var(--accent-strong)]";
  if (confidence === "medium") return "bg-[var(--warning-ink)]";
  return "bg-[var(--muted)]";
}

function Row({ entry, isFirst }: { entry: ArchetypeHistoryEntry; isFirst: boolean }) {
  const transitioned = !isFirst && entry.transitioned_from !== null;
  return (
    <li className="relative flex items-start gap-3 pb-3">
      <div className="flex flex-col items-center">
        <span
          className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${confidenceDotClass(
            entry.confidence
          )}`}
          aria-hidden="true"
        />
        <span className="mt-1 w-px flex-1 bg-[var(--border)]" aria-hidden="true" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-2">
          <div className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
            {entry.season}
          </div>
          {transitioned && (
            <span className="inline-flex items-center rounded-full border border-[var(--warning-border)] bg-[var(--warning-soft)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--warning-ink)]">
              Transition
            </span>
          )}
        </div>
        <div className="mt-0.5 text-sm font-semibold text-[var(--foreground)]">
          {entry.label}
        </div>
        <div className="mt-0.5 text-[11px] text-[var(--muted)]">
          {entry.confidence} confidence
          {transitioned && entry.transitioned_from
            ? ` · previously ${entry.transitioned_from.replace(/_/g, " ")}`
            : ""}
        </div>
      </div>
    </li>
  );
}

export function ArchetypeEvolutionTimeline({ playerId }: Props) {
  const { data, error, isLoading } = usePlayerArchetypeHistory(playerId);

  if (isLoading) {
    return (
      <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 text-sm text-[var(--muted)]">
        Loading archetype history…
      </section>
    );
  }

  if (error || !data || data.entries.length === 0) {
    return null; // Silent — not every player has multi-season history.
  }

  // Single-season history isn't really a "timeline"; hide when only one entry.
  if (data.entries.length < 2) return null;

  const transitionCount = data.entries.filter((e) => e.transitioned_from !== null).length;

  return (
    <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5">
      <header className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-[var(--foreground)]">Archetype history</h3>
        <span className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">
          {data.entries.length} seasons · {transitionCount} transition
          {transitionCount === 1 ? "" : "s"}
        </span>
      </header>
      <ol className="mt-4">
        {data.entries.map((entry, i) => (
          <Row key={entry.season} entry={entry} isFirst={i === 0} />
        ))}
      </ol>
      <p className="mt-2 text-[11px] leading-4 text-[var(--muted)]">
        Each season is classified against its own peer pool. Dot color reflects
        classification confidence (green = high, amber = medium, muted = low).
        {humanizeMethodologyVersion(data.methodology_version)}.
      </p>
    </section>
  );
}
