"use client";

import {
  Radar,
  RadarChart as RechartsRadar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { SeasonStats } from "@/lib/types";

interface RadarChartProps {
  stats: SeasonStats;
}

function normalizeRadarData(stats: SeasonStats) {
  // Normalize stats to 0-100 scale using rough NBA benchmarks
  const normalize = (val: number | null, max: number) =>
    val !== null ? Math.min(100, Math.round((val / max) * 100)) : 0;

  return [
    { dimension: "Scoring", value: normalize(stats.pts_pg, 35) },
    { dimension: "Playmaking", value: normalize(stats.ast_pg, 12) },
    { dimension: "Rebounding", value: normalize(stats.reb_pg, 15) },
    {
      dimension: "Defense",
      value: normalize((stats.stl_pg || 0) + (stats.blk_pg || 0), 5),
    },
    {
      dimension: "Efficiency",
      value: normalize(stats.ts_pct, 0.7) || normalize(stats.fg_pct, 0.6),
    },
    { dimension: "Usage", value: normalize(stats.usg_pct, 40) },
  ];
}

export default function RadarChart({ stats }: RadarChartProps) {
  const data = normalizeRadarData(stats);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
      <h2 className="text-lg font-semibold mb-4">Player Profile</h2>
      <ResponsiveContainer width="100%" height={300}>
        <RechartsRadar data={data}>
          <PolarGrid stroke="#374151" />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{ fontSize: 12, fill: "#9CA3AF" }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 100]}
            tick={false}
            axisLine={false}
          />
          <Tooltip />
          <Radar
            name="Stats"
            dataKey="value"
            stroke="#3B82F6"
            fill="#3B82F6"
            fillOpacity={0.3}
            strokeWidth={2}
          />
        </RechartsRadar>
      </ResponsiveContainer>
    </div>
  );
}
