"use client";

import type { StandingsSnapshot } from "@/lib/types";

interface WinPctSparklineProps {
  snapshots: StandingsSnapshot[];
  width?: number;
  height?: number;
}

export default function WinPctSparkline({
  snapshots,
  width = 80,
  height = 24,
}: WinPctSparklineProps) {
  if (!snapshots || snapshots.length === 0) return null;

  // Single point — render a dot
  if (snapshots.length === 1) {
    return (
      <svg width={width} height={height} className="overflow-visible">
        <circle
          cx={width / 2}
          cy={height / 2}
          r={2.5}
          className="fill-[var(--accent)]"
        />
      </svg>
    );
  }

  const values = snapshots.map((s) => s.win_pct);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 0.01; // avoid div-by-zero for flat lines

  const pad = 2;
  const pts = values.map((v, i) => {
    const x = pad + (i / (values.length - 1)) * (width - 2 * pad);
    const y = pad + (1 - (v - min) / range) * (height - 2 * pad);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const latest = values[values.length - 1];
  const prior = values[values.length - 2];
  const rising = latest >= prior;

  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline
        points={pts.join(" ")}
        fill="none"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={
          rising
            ? "stroke-emerald-500 dark:stroke-emerald-400"
            : "stroke-red-400 dark:stroke-red-500"
        }
      />
    </svg>
  );
}
