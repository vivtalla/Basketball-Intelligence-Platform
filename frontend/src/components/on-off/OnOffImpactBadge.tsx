"use client";

import type { ImpactClassification, ConfidenceTier } from "@/lib/types";

interface Props {
  classification: ImpactClassification | null;
  confidenceTier: ConfidenceTier;
  size?: "sm" | "md";
}

const CLASS_STYLES: Record<ImpactClassification, { bg: string; text: string }> = {
  "Two-Way Elite": { bg: "bg-teal-100 dark:bg-teal-900/40", text: "text-teal-700 dark:text-teal-300" },
  "Offensive Engine": { bg: "bg-amber-100 dark:bg-amber-900/40", text: "text-amber-700 dark:text-amber-300" },
  "Defensive Anchor": { bg: "bg-indigo-100 dark:bg-indigo-900/40", text: "text-indigo-700 dark:text-indigo-300" },
  "Neutral": { bg: "bg-gray-100 dark:bg-gray-700", text: "text-gray-600 dark:text-gray-300" },
  "Liability": { bg: "bg-red-100 dark:bg-red-900/40", text: "text-red-700 dark:text-red-400" },
};

const TIER_BORDER: Record<ConfidenceTier, string> = {
  high: "border-solid border-2",
  medium: "border-dashed border-2",
  low: "border-dotted border-2",
  insufficient: "border border-dashed opacity-60",
};

export default function OnOffImpactBadge({ classification, confidenceTier, size = "md" }: Props) {
  if (!classification) return null;
  const { bg, text } = CLASS_STYLES[classification];
  const border = TIER_BORDER[confidenceTier];
  const px = size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs";
  return (
    <span className={`inline-flex items-center rounded-full font-semibold ${px} ${bg} ${text} ${border} border-current`}>
      {classification}
    </span>
  );
}
