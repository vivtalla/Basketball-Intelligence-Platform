"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { LineupLeaderboardEntry, LineupArchetype } from "@/lib/types";

const ARCHETYPE_COLORS: Record<LineupArchetype, string> = {
  Elite: "#0d9488",
  "Offensive Wall": "#d97706",
  "Defensive Wall": "#6366f1",
  Balanced: "#6b7280",
  Negative: "#ef4444",
  Unclassified: "#9ca3af",
};

interface ScatterPoint {
  x: number;
  y: number;
  r: number;
  label: string;
  archetype: LineupArchetype;
  net_rating: number | null;
  possessions: number | null;
}

interface Props {
  lineups: LineupLeaderboardEntry[];
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: { payload: ScatterPoint }[] }) {
  if (!active || !payload?.[0]) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-2 text-xs shadow-md space-y-0.5">
      <p className="font-semibold text-gray-800 dark:text-gray-200">{d.label}</p>
      <p className="text-gray-500 dark:text-gray-400">ORTG: {d.x.toFixed(1)} · DRTG: {d.y.toFixed(1)}</p>
      <p className="text-gray-500 dark:text-gray-400">Net: {d.net_rating != null ? (d.net_rating >= 0 ? "+" : "") + d.net_rating.toFixed(1) : "—"}</p>
      {d.possessions != null && <p className="text-gray-400 dark:text-gray-500">{d.possessions.toLocaleString()} poss</p>}
    </div>
  );
}

export default function LineupScatterPanel({ lineups }: Props) {
  const points: ScatterPoint[] = lineups
    .filter((l) => l.ortg != null && l.drtg != null)
    .map((l) => ({
      x: l.ortg!,
      y: l.drtg!,
      r: Math.max(4, Math.sqrt((l.minutes ?? 0) / 2)),
      label: l.player_names.join(" / "),
      archetype: l.archetype,
      net_rating: l.net_rating,
      possessions: l.possessions,
    }));

  if (points.length === 0) return null;

  const avgOrtg = points.reduce((s, p) => s + p.x, 0) / points.length;
  const avgDrtg = points.reduce((s, p) => s + p.y, 0) / points.length;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
      <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
        ORTG vs DRTG — bubble size ∝ minutes · Y-axis inverted (lower DRTG = better defense = top)
      </p>
      <ResponsiveContainer width="100%" height={280}>
        <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(107,114,128,0.15)" />
          <XAxis
            dataKey="x"
            type="number"
            name="ORTG"
            domain={["auto", "auto"]}
            tick={{ fontSize: 10 }}
            label={{ value: "ORTG →", position: "insideBottomRight", offset: -4, fontSize: 10 }}
          />
          <YAxis
            dataKey="y"
            type="number"
            name="DRTG"
            reversed
            domain={["auto", "auto"]}
            tick={{ fontSize: 10 }}
            label={{ value: "← Better Defense", angle: -90, position: "insideLeft", offset: 10, fontSize: 10 }}
          />
          <ReferenceLine x={avgOrtg} stroke="rgba(107,114,128,0.4)" strokeDasharray="4 2" />
          <ReferenceLine y={avgDrtg} stroke="rgba(107,114,128,0.4)" strokeDasharray="4 2" />
          <Tooltip content={<CustomTooltip />} />
          <Scatter data={points} isAnimationActive={false}>
            {points.map((p, i) => (
              <Cell
                key={i}
                fill={ARCHETYPE_COLORS[p.archetype] ?? "#9ca3af"}
                fillOpacity={0.75}
                r={p.r}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <div className="mt-2 flex flex-wrap gap-3">
        {(Object.entries(ARCHETYPE_COLORS) as [LineupArchetype, string][])
          .filter(([k]) => k !== "Unclassified")
          .map(([label, color]) => (
            <span key={label} className="flex items-center gap-1 text-[10px] text-gray-500 dark:text-gray-400">
              <span className="inline-block w-2 h-2 rounded-full" style={{ background: color }} />
              {label}
            </span>
          ))}
      </div>
    </div>
  );
}
