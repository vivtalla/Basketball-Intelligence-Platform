"use client";

import type { LineupConfidence } from "@/lib/types";

const CONF_STYLES: Record<LineupConfidence, { bg: string; text: string; label: string }> = {
  high: { bg: "bg-green-100 dark:bg-green-900/30", text: "text-green-700 dark:text-green-400", label: "High" },
  medium: { bg: "bg-yellow-100 dark:bg-yellow-900/30", text: "text-yellow-700 dark:text-yellow-400", label: "Med" },
  low: { bg: "bg-gray-100 dark:bg-gray-700", text: "text-gray-500 dark:text-gray-400", label: "Low" },
};

interface Props {
  confidence: LineupConfidence;
  possessions?: number | null;
}

export default function LineupConfidenceBadge({ confidence, possessions }: Props) {
  const { bg, text, label } = CONF_STYLES[confidence] ?? CONF_STYLES.low;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${bg} ${text}`}>
      {label}
      {possessions != null && (
        <span className="opacity-70 font-normal">{possessions.toLocaleString()} poss</span>
      )}
    </span>
  );
}
