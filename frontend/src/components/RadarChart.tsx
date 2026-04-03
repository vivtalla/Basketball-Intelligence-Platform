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
import { chartPalette } from "@/lib/chart-system";

interface RadarChartProps {
  stats: SeasonStats;
}

function normalizeRadarData(stats: SeasonStats) {
  const normalize = (val: number | null, max: number) =>
    val !== null ? Math.min(100, Math.round((val / max) * 100)) : 0;

  return [
    { dimension: "Scoring",    value: normalize(stats.pts_pg, 35) },
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
    <div className="rounded-[2rem] border border-[var(--border)] bg-[linear-gradient(145deg,rgba(247,243,232,0.96),rgba(228,236,232,0.92))] p-6 shadow-[0_18px_48px_rgba(47,43,36,0.07)]">
      <div className="mb-1">
        <p className="bip-kicker">Skill Profile</p>
        <h2 className="mt-0.5 text-lg font-semibold text-[var(--foreground)]">Player Radar</h2>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <RechartsRadar data={data}>
          <defs>
            <radialGradient id="radar-fill-grad" cx="50%" cy="50%" r="50%">
              <stop offset="0%"   stopColor={chartPalette.accent} stopOpacity={0.40} />
              <stop offset="100%" stopColor={chartPalette.accent} stopOpacity={0.06} />
            </radialGradient>
          </defs>
          <PolarGrid stroke={chartPalette.grid} />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{ fontSize: 11, fill: "var(--muted)", fontWeight: 500 }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 100]}
            tick={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              fontSize: 12,
              backgroundColor: "rgba(255,251,246,0.96)",
              border: "1px solid var(--border)",
              borderRadius: 10,
            }}
          />
          <Radar
            name="Stats"
            dataKey="value"
            stroke={chartPalette.accent}
            fill="url(#radar-fill-grad)"
            fillOpacity={1}
            strokeWidth={2.5}
          />
        </RechartsRadar>
      </ResponsiveContainer>
    </div>
  );
}
