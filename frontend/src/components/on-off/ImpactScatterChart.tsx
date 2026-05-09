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
import type { EnhancedLeaderboardEntry, ImpactClassification } from "@/lib/types";

interface Props {
  players: EnhancedLeaderboardEntry[];
}

const CLASS_COLORS: Record<ImpactClassification, string> = {
  "Two-Way Elite": "#0d9488",   // teal-600
  "Offensive Engine": "#d97706", // amber-600
  "Defensive Anchor": "#4f46e5", // indigo-600
  "Neutral": "#6b7280",          // gray-500
  "Liability": "#dc2626",        // red-600
};

function dotColor(cls: ImpactClassification | null): string {
  return cls ? (CLASS_COLORS[cls] ?? "#6b7280") : "#6b7280";
}

interface TooltipPayload {
  payload?: EnhancedLeaderboardEntry & { z: number };
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  return (
    <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 text-xs shadow-lg">
      <p className="font-semibold text-gray-900 dark:text-gray-100">{d.player_name}</p>
      {d.team_abbreviation && (
        <p className="text-gray-500 dark:text-gray-400">{d.team_abbreviation}</p>
      )}
      <div className="mt-1 space-y-0.5">
        <p>ORTG Δ: <span className={`font-semibold ${(d.ortg_impact ?? 0) >= 0 ? "text-green-600 dark:text-green-400" : "text-red-500"}`}>{d.ortg_impact != null ? (d.ortg_impact >= 0 ? "+" : "") + d.ortg_impact.toFixed(1) : "—"}</span></p>
        <p>DRTG Δ: <span className={`font-semibold ${(d.drtg_impact ?? 0) >= 0 ? "text-green-600 dark:text-green-400" : "text-red-500"}`}>{d.drtg_impact != null ? (d.drtg_impact >= 0 ? "+" : "") + d.drtg_impact.toFixed(1) : "—"}</span></p>
        <p>On/Off Net: <span className="font-semibold">{d.on_off_net != null ? (d.on_off_net >= 0 ? "+" : "") + d.on_off_net.toFixed(1) : "—"}</span></p>
        {d.impact_classification && (
          <p className="mt-1" style={{ color: dotColor(d.impact_classification) }}>{d.impact_classification}</p>
        )}
      </div>
    </div>
  );
}

export default function ImpactScatterChart({ players }: Props) {
  const data = players
    .filter((p) => p.ortg_impact != null && p.drtg_impact != null)
    .map((p) => ({
      ...p,
      x: p.ortg_impact!,
      y: p.drtg_impact!,
      z: Math.max(6, Math.min(20, (p.on_minutes ?? 400) / 60)),
    }));

  if (data.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-gray-400 dark:text-gray-500">
        No impact data to display
      </div>
    );
  }

  return (
    <div>
      <div className="mb-2 grid grid-cols-2 gap-x-6 gap-y-1 text-[10px] text-gray-500 dark:text-gray-400 sm:flex sm:flex-wrap sm:gap-3">
        {(Object.entries(CLASS_COLORS) as [ImpactClassification, string][]).map(([cls, color]) => (
          <span key={cls} className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
            {cls}
          </span>
        ))}
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(107,114,128,0.2)" />
          <XAxis
            dataKey="x"
            type="number"
            name="ORTG Δ"
            label={{ value: "ORTG Impact (offense)", position: "insideBottom", offset: -15, fontSize: 11 }}
            tick={{ fontSize: 11 }}
          />
          <YAxis
            dataKey="y"
            type="number"
            name="DRTG Δ"
            label={{ value: "DRTG Impact (defense)", angle: -90, position: "insideLeft", offset: 10, fontSize: 11 }}
            tick={{ fontSize: 11 }}
          />
          <ReferenceLine x={0} stroke="rgba(107,114,128,0.5)" strokeDasharray="4 2" />
          <ReferenceLine y={0} stroke="rgba(107,114,128,0.5)" strokeDasharray="4 2" />
          <ReferenceLine x={3} stroke="rgba(13,148,136,0.3)" strokeDasharray="2 4" />
          <ReferenceLine y={3} stroke="rgba(13,148,136,0.3)" strokeDasharray="2 4" />
          <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: "3 3" }} />
          <Scatter data={data} isAnimationActive={false}>
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={dotColor(entry.impact_classification)}
                fillOpacity={0.8}
                r={entry.z}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <p className="mt-1 text-center text-[10px] text-gray-400 dark:text-gray-500">
        Bubble size ∝ on-court minutes · teal lines = Elite threshold (±3)
      </p>
    </div>
  );
}
