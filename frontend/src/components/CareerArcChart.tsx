"use client";

import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { SeasonStats } from "@/lib/types";

interface CareerArcChartProps {
  seasons: SeasonStats[];
}

interface StatOption {
  key: keyof SeasonStats;
  label: string;
  color: string;
  pct?: boolean;
}

const STAT_OPTIONS: StatOption[] = [
  { key: "pts_pg", label: "PPG",  color: "#3b82f6" },
  { key: "reb_pg", label: "RPG",  color: "#10b981" },
  { key: "ast_pg", label: "APG",  color: "#f59e0b" },
  { key: "per",    label: "PER",  color: "#8b5cf6" },
  { key: "bpm",    label: "BPM",  color: "#ef4444" },
  { key: "ts_pct", label: "TS%",  color: "#06b6d4", pct: true },
  { key: "ws",     label: "WS",   color: "#ec4899" },
];

const DEFAULT_ACTIVE = new Set(["pts_pg", "per", "bpm"]);

export default function CareerArcChart({ seasons }: CareerArcChartProps) {
  const [active, setActive] = useState<Set<string>>(new Set(DEFAULT_ACTIVE));

  if (seasons.length === 0) return null;

  const data = seasons.map((s) => {
    const point: Record<string, string | number | null> = { season: s.season };
    for (const opt of STAT_OPTIONS) {
      const raw = s[opt.key] as number | null;
      point[opt.key] = raw != null ? (opt.pct ? parseFloat((raw * 100).toFixed(1)) : raw) : null;
    }
    return point;
  });

  function toggleStat(key: string) {
    setActive((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size === 1) return prev; // keep at least one
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Career Arc</h3>

        {/* Stat toggles */}
        <div className="flex flex-wrap gap-2">
          {STAT_OPTIONS.map((opt) => {
            const on = active.has(opt.key as string);
            return (
              <button
                key={opt.key as string}
                onClick={() => toggleStat(opt.key as string)}
                className={`flex items-center gap-1.5 px-3 py-1 text-xs rounded-full border transition-colors ${
                  on
                    ? "text-white border-transparent"
                    : "bg-white dark:bg-gray-800 text-gray-400 border-gray-200 dark:border-gray-600 hover:border-gray-400"
                }`}
                style={on ? { backgroundColor: opt.color, borderColor: opt.color } : undefined}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" className="dark:stroke-gray-700" />
          <XAxis
            dataKey="season"
            tick={{ fontSize: 10, fill: "#9ca3af" }}
            angle={-40}
            textAnchor="end"
            height={52}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} />
          <Tooltip
            contentStyle={{
              fontSize: 12,
              backgroundColor: "var(--tooltip-bg, #fff)",
              border: "1px solid #e5e7eb",
              borderRadius: 8,
            }}
            formatter={(value, name) => {
              const opt = STAT_OPTIONS.find((o) => o.key === name);
              return [`${value}${opt?.pct ? "%" : ""}`, opt?.label ?? name];
            }}
          />
          <Legend
            formatter={(value) => STAT_OPTIONS.find((o) => o.key === value)?.label ?? value}
            wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
          />
          {STAT_OPTIONS.filter((opt) => active.has(opt.key as string)).map((opt) => (
            <Line
              key={opt.key as string}
              type="monotone"
              dataKey={opt.key as string}
              stroke={opt.color}
              strokeWidth={2}
              dot={{ r: 3, fill: opt.color }}
              activeDot={{ r: 5 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
