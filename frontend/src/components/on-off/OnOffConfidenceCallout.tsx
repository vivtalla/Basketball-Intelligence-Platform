"use client";

import type { ConfidenceTier } from "@/lib/types";

interface Props {
  confidenceTier: ConfidenceTier;
  onMinutes: number | null;
}

const TIER_CONFIG: Record<ConfidenceTier, { label: string; style: string }> = {
  high: { label: "Reliable · 800+ min", style: "bg-teal-50 dark:bg-teal-900/30 text-teal-700 dark:text-teal-300 border-teal-200 dark:border-teal-700" },
  medium: { label: "Moderate · 400–800 min", style: "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-700" },
  low: { label: "Limited · 200–400 min", style: "bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-700" },
  insufficient: { label: "Too few minutes", style: "bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400 border-gray-200 dark:border-gray-600" },
};

export default function OnOffConfidenceCallout({ confidenceTier, onMinutes }: Props) {
  const { label, style } = TIER_CONFIG[confidenceTier];
  const minLabel = onMinutes != null ? `${onMinutes.toFixed(0)} on-court min recorded` : null;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style}`}>
      {label}
      {minLabel && <span className="font-normal normal-case opacity-70">· {minLabel}</span>}
    </span>
  );
}
