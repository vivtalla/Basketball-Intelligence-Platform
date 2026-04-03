"use client";

import type { DataStatus } from "@/lib/chart-system";
import { getDataStatusTone } from "@/lib/chart-system";

interface ChartStatusBadgeProps {
  status: DataStatus;
  compact?: boolean;
}

export default function ChartStatusBadge({
  status,
  compact = false,
}: ChartStatusBadgeProps) {
  const tone = getDataStatusTone(status);

  return (
    <span
      className={`inline-flex items-center rounded-full font-semibold uppercase tracking-[0.12em] ${tone.className} ${
        compact ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-[11px]"
      }`}
    >
      {tone.label}
    </span>
  );
}
