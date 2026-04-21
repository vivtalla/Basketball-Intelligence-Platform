"use client";

import type { ShotIdentityCard } from "@/lib/types";

interface Props {
  cards?: ShotIdentityCard[] | null;
  limit?: number;
  isLoading?: boolean;
  compact?: boolean;
}

const TIER_TONE: Record<ShotIdentityCard["tier"], string> = {
  signature: "border-emerald-400/50 bg-emerald-500/10 text-emerald-300",
  strong: "border-sky-400/40 bg-sky-500/10 text-sky-300",
  present: "border-slate-400/30 bg-slate-500/10 text-[var(--muted-strong)]",
  low: "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)]",
};

const CONFIDENCE_TONE: Record<ShotIdentityCard["confidence"], string> = {
  high: "bg-emerald-500/15 text-emerald-300",
  medium: "bg-amber-500/15 text-amber-300",
  low: "bg-slate-500/20 text-[var(--muted)]",
};

export default function ShotIdentityBadges({ cards, limit = 2, isLoading, compact }: Props) {
  if (isLoading) {
    return (
      <div className="flex gap-2">
        <div className="h-6 w-24 animate-pulse rounded-full bg-[var(--surface)]" />
        <div className="h-6 w-24 animate-pulse rounded-full bg-[var(--surface)]" />
      </div>
    );
  }

  const filtered = (cards ?? []).filter((c) => c.tier !== "low").slice(0, limit);
  if (!filtered.length) return null;

  return (
    <div className={`flex flex-wrap gap-2 ${compact ? "" : "items-center"}`}>
      {filtered.map((card) => (
        <div
          key={card.identity_key}
          className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${TIER_TONE[card.tier]}`}
          title={card.summary}
        >
          <span className="uppercase tracking-wider">{card.label}</span>
          <span className={`rounded-full px-1.5 py-0.5 text-[9px] uppercase tracking-wider ${CONFIDENCE_TONE[card.confidence]}`}>
            {card.confidence}
          </span>
          {!compact && (
            <span className="font-normal normal-case tracking-normal text-[var(--muted-strong)]">
              {card.summary}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}
