"use client";

import type { ReactNode } from "react";
import {
  CONFIDENCE_LABEL,
  CONFIDENCE_SHORT,
  CONFIDENCE_TONE,
  type ShotConfidenceBand,
} from "@/lib/shotchart-hover";

export interface ShotHoverRow {
  label: string;
  value: string;
  tone?: "positive" | "negative" | "neutral";
}

interface ShotHoverTooltipProps {
  title: string;
  subtitle?: string;
  rows: ShotHoverRow[];
  confidence?: ShotConfidenceBand | null;
  footnote?: ReactNode;
  compact?: boolean;
}

export default function ShotHoverTooltip({
  title,
  subtitle,
  rows,
  confidence,
  footnote,
  compact = false,
}: ShotHoverTooltipProps) {
  return (
    <div
      className={`rounded-lg border border-[rgba(25,52,42,0.14)] bg-white/97 shadow-md backdrop-blur-sm ${
        compact ? "px-2.5 py-1.5 text-[11px]" : "px-3 py-2 text-xs"
      }`}
      role="tooltip"
    >
      <div className="flex items-center justify-between gap-2">
        <p className="font-semibold text-[var(--foreground)]">{title}</p>
        {confidence ? <ConfidencePill band={confidence} /> : null}
      </div>
      {subtitle ? (
        <p className="mt-0.5 text-[10px] uppercase tracking-wide text-[var(--muted)]">
          {subtitle}
        </p>
      ) : null}
      <div className="mt-1.5 space-y-0.5">
        {rows.map((row) => (
          <div
            key={row.label}
            className="flex items-center justify-between gap-3"
          >
            <span className="text-[var(--muted)]">{row.label}</span>
            <span
              className={`tabular-nums font-medium ${toneClass(row.tone)}`}
            >
              {row.value}
            </span>
          </div>
        ))}
      </div>
      {footnote ? (
        <p className="mt-1.5 border-t border-[rgba(25,52,42,0.08)] pt-1 text-[10px] text-[var(--muted)]">
          {footnote}
        </p>
      ) : null}
    </div>
  );
}

function toneClass(tone?: ShotHoverRow["tone"]): string {
  if (tone === "positive") return "text-emerald-600";
  if (tone === "negative") return "text-red-500";
  return "text-[var(--foreground)]";
}

export function ConfidencePill({
  band,
  short = false,
}: {
  band: ShotConfidenceBand;
  short?: boolean;
}) {
  const palette = CONFIDENCE_TONE[band];
  return (
    <span
      className="inline-flex items-center rounded-full px-2 py-0.5 text-[9.5px] font-semibold uppercase tracking-wide"
      style={{ background: palette.bg, color: palette.text }}
      title={CONFIDENCE_LABEL[band]}
    >
      {short ? CONFIDENCE_SHORT[band] : CONFIDENCE_LABEL[band]}
    </span>
  );
}
