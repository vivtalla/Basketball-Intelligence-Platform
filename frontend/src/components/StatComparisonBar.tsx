"use client";

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
  statKey: keyof SeasonStats;
  label: string;
}

export default function StatComparisonBar({
  seasons,
  statKey,
  label,
}: StatComparisonBarProps) {
  const data = seasons.map((s) => ({
    season: s.season,
    value: typeof s[statKey] === "number" ? s[statKey] : 0,
  }));

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
      <h2 className="text-lg font-semibold mb-4">{label} by Season</h2>
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
          <Tooltip />
          <Bar dataKey="value" fill="#3B82F6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
