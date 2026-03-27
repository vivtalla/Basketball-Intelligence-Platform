"use client";

import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { SeasonStats } from "@/lib/types";

interface StatComparisonBarProps {
  seasons: SeasonStats[];
  statKey?: keyof SeasonStats;
  label?: string;
}

const STAT_GROUPS = [
  {
    label: "Scoring",
    options: [
      { key: "pts_pg",  label: "Points Per Game",  pct: false },
      { key: "fg_pct",  label: "FG%",              pct: true  },
      { key: "fg3_pct", label: "3P%",              pct: true  },
      { key: "ft_pct",  label: "FT%",              pct: true  },
      { key: "ts_pct",  label: "TS%",              pct: true  },
      { key: "efg_pct", label: "eFG%",             pct: true  },
    ],
  },
  {
    label: "Production",
    options: [
      { key: "reb_pg", label: "Rebounds Per Game", pct: false },
      { key: "ast_pg", label: "Assists Per Game",  pct: false },
      { key: "stl_pg", label: "Steals Per Game",   pct: false },
      { key: "blk_pg", label: "Blocks Per Game",   pct: false },
      { key: "min_pg", label: "Minutes Per Game",  pct: false },
    ],
  },
  {
    label: "Advanced",
    options: [
      { key: "per",        label: "PER",             pct: false },
      { key: "bpm",        label: "BPM",             pct: false },
      { key: "ws",         label: "Win Shares",      pct: false },
      { key: "vorp",       label: "VORP",            pct: false },
      { key: "usg_pct",    label: "Usage Rate",      pct: true  },
      { key: "off_rating", label: "Offensive Rating",pct: false },
      { key: "def_rating", label: "Defensive Rating",pct: false },
      { key: "net_rating", label: "Net Rating",      pct: false },
    ],
  },
];

const ALL_OPTIONS = STAT_GROUPS.flatMap((g) => g.options);

export default function StatComparisonBar({
  seasons,
  statKey = "pts_pg",
  label,
}: StatComparisonBarProps) {
  const [selectedKey, setSelectedKey] = useState<string>(statKey as string);

  const option = ALL_OPTIONS.find((o) => o.key === selectedKey) ?? ALL_OPTIONS[0];
  const displayLabel = label ?? option.label;

  const data = seasons.map((s) => {
    const raw = s[selectedKey as keyof SeasonStats];
    const num = typeof raw === "number" ? raw : null;
    const value = num == null ? 0 : option.pct ? parseFloat((num * 100).toFixed(1)) : num;
    return { season: s.season, value };
  });

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between gap-3 mb-4">
        <h2 className="text-lg font-semibold">{displayLabel} by Season</h2>
        <select
          value={selectedKey}
          onChange={(e) => setSelectedKey(e.target.value)}
          className="text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {STAT_GROUPS.map((group) => (
            <optgroup key={group.label} label={group.label}>
              {group.options.map((opt) => (
                <option key={opt.key} value={opt.key}>{opt.label}</option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="season"
            tick={{ fontSize: 11, fill: "#9CA3AF" }}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis tick={{ fontSize: 12, fill: "#9CA3AF" }} />
          <Tooltip formatter={(v) => [`${v}${option.pct ? "%" : ""}`, displayLabel]} />
          <Bar dataKey="value" fill="#3B82F6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
