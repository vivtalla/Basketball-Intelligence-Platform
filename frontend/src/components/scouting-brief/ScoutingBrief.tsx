"use client";

import Link from "next/link";
import { usePlayerScoutingBrief } from "@/hooks/usePlayerShotDiagnosis";
import type {
  ScoutingBriefCard,
  ScoutingCardConfidence,
  ScoutingCardType,
} from "@/lib/types";

interface Props {
  playerId: number;
  season: string | null;
}

const CARD_ORDER: ScoutingCardType[] = [
  "role",
  "strengths",
  "usage_efficiency",
  "shot_profile",
  "trajectory",
];

function confidenceBadgeClasses(confidence: ScoutingCardConfidence): string {
  if (confidence === "high") {
    return "border-[var(--accent-strong)] bg-[var(--accent-soft)] text-[var(--accent-strong)]";
  }
  if (confidence === "medium") {
    return "border-[var(--warning-border)] bg-[var(--warning-soft)] text-[var(--warning-ink)]";
  }
  return "border-[var(--border)] bg-[var(--surface-alt)] text-[var(--muted-strong)]";
}

function Card({ card }: { card: ScoutingBriefCard }) {
  return (
    <article className="flex h-full flex-col justify-between rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <header className="flex items-baseline justify-between gap-2">
        <Link
          href={card.deep_link}
          className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)] hover:text-[var(--accent)]"
        >
          {card.title} →
        </Link>
        <span
          className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.1em] ${confidenceBadgeClasses(
            card.confidence
          )}`}
        >
          {card.confidence}
        </span>
      </header>
      <div className="mt-2 text-sm font-semibold leading-5 text-[var(--foreground)]">
        {card.summary}
      </div>
      {card.evidence.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-[11px] leading-4 text-[var(--muted-strong)]">
          {card.evidence.slice(0, 3).map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      )}
    </article>
  );
}

export function ScoutingBrief({ playerId, season }: Props) {
  const { data, error, isLoading } = usePlayerScoutingBrief(playerId, season ?? "");

  if (!season) return null;

  if (isLoading) {
    return (
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="h-28 rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)] animate-pulse"
          />
        ))}
      </section>
    );
  }

  if (error || !data || data.cards.length === 0) {
    return null; // Fail silent — brief is a bonus, not required content.
  }

  // Sort cards into canonical spec order defensively (server returns this order,
  // but don't trust the network).
  const orderIndex: Record<ScoutingCardType, number> = {
    role: 0, strengths: 1, usage_efficiency: 2, shot_profile: 3, trajectory: 4,
  };
  const ordered = [...data.cards].sort(
    (a, b) => orderIndex[a.card_type] - orderIndex[b.card_type]
  );

  return (
    <section>
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="bip-display text-sm font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
          Scouting Brief
        </h2>
        <span className="text-[10px] text-[var(--muted)]">
          {ordered.length} of {CARD_ORDER.length} cards · {data.methodology_version}
        </span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {ordered.map((card) => (
          <Card key={card.card_type} card={card} />
        ))}
      </div>
    </section>
  );
}
