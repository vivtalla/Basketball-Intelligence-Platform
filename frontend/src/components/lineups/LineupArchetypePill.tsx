"use client";

import type { LineupArchetype } from "@/lib/types";

const ARCHETYPE_STYLES: Record<LineupArchetype, { bg: string; text: string; label: string }> = {
  Elite: { bg: "bg-teal-100 dark:bg-teal-900/40", text: "text-teal-700 dark:text-teal-300", label: "Elite" },
  "Offensive Wall": { bg: "bg-amber-100 dark:bg-amber-900/40", text: "text-amber-700 dark:text-amber-300", label: "Offensive Wall" },
  "Defensive Wall": { bg: "bg-indigo-100 dark:bg-indigo-900/40", text: "text-indigo-700 dark:text-indigo-300", label: "Defensive Wall" },
  Balanced: { bg: "bg-gray-100 dark:bg-gray-700", text: "text-gray-600 dark:text-gray-300", label: "Balanced" },
  Negative: { bg: "bg-red-100 dark:bg-red-900/40", text: "text-red-600 dark:text-red-400", label: "Negative" },
  Unclassified: { bg: "bg-gray-100 dark:bg-gray-800", text: "text-gray-400 dark:text-gray-500", label: "—" },
};

interface Props {
  archetype: LineupArchetype;
  size?: "sm" | "md";
}

export default function LineupArchetypePill({ archetype, size = "sm" }: Props) {
  const { bg, text, label } = ARCHETYPE_STYLES[archetype] ?? ARCHETYPE_STYLES.Unclassified;
  const cls = size === "md" ? "px-2.5 py-1 text-xs" : "px-2 py-0.5 text-[10px]";
  return (
    <span className={`inline-flex items-center rounded-full font-semibold ${bg} ${text} ${cls}`}>
      {label}
    </span>
  );
}
