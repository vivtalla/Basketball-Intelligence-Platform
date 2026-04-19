"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { TrajectorySeriesGame } from "@/lib/types";

const METRICS: { key: keyof TrajectorySeriesGame; label: string; color: string }[] = [
  { key: "pts", label: "PTS", color: "#21483b" },
  { key: "ts_pct", label: "TS%", color: "#b45309" },
  { key: "usg_pct", label: "USG%", color: "#7c3aed" },
  { key: "plus_minus", label: "+/-", color: "#0369a1" },
];

interface Props {
  series: TrajectorySeriesGame[];
  lastNGames: number;
}

export function RollingSparklines({ series, lastNGames }: Props) {
  if (!series.length) {
    return (
      <div className="flex h-32 items-center justify-center text-sm text-[var(--muted)]">
        No game data available
      </div>
    );
  }

  // Reverse so oldest is left, newest is right.
  const chartData = [...series].reverse().map((g, i) => ({
    i,
    game_id: g.game_id,
    date: g.date ?? "",
    pts: g.pts,
    ts_pct: g.ts_pct !== null ? +(g.ts_pct * 100).toFixed(1) : null,
    usg_pct: g.usg_pct,
    plus_minus: g.plus_minus,
    is_recent: g.is_recent,
  }));

  const recentStartIndex = chartData.findIndex((d) => d.is_recent);
  const baselinePts =
    chartData
      .filter((d) => !d.is_recent && d.pts !== null)
      .reduce<{ sum: number; count: number }>(
        (acc, d) => ({ sum: acc.sum + (d.pts ?? 0), count: acc.count + 1 }),
        { sum: 0, count: 0 }
      );
  const baselineAvg = baselinePts.count > 0 ? baselinePts.sum / baselinePts.count : null;

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-4 text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
        <span>← Baseline</span>
        <span className="flex-1 border-t border-dashed border-[var(--border)]" />
        <span className="rounded-full bg-[var(--accent-soft)] px-2 py-0.5 text-[var(--accent-strong)]">
          Last {lastNGames} games →
        </span>
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <XAxis dataKey="date" hide />
          <YAxis hide />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload;
              return (
                <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs shadow-lg">
                  <p className="mb-1 font-semibold text-[var(--foreground)]">{d.date || d.game_id}</p>
                  {payload.map((p) => (
                    <p key={p.dataKey as string} style={{ color: p.color }}>
                      {p.name}: {p.value !== null ? p.value : "—"}
                    </p>
                  ))}
                </div>
              );
            }}
          />
          <Legend
            iconType="circle"
            iconSize={6}
            wrapperStyle={{ fontSize: 10, paddingTop: 4 }}
          />
          {recentStartIndex >= 0 && (
            <ReferenceLine
              x={recentStartIndex}
              stroke="var(--border-strong)"
              strokeDasharray="4 2"
            />
          )}
          {baselineAvg !== null && (
            <ReferenceLine
              y={baselineAvg}
              stroke="var(--muted)"
              strokeDasharray="2 2"
              label={{ value: "Base", position: "insideLeft", fontSize: 9, fill: "var(--muted)" }}
            />
          )}
          {METRICS.map((m) => (
            <Line
              key={m.key as string}
              type="monotone"
              dataKey={m.key as string}
              name={m.label}
              stroke={m.color}
              dot={false}
              strokeWidth={1.5}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
