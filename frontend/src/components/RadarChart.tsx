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
import type { PercentileResult, SeasonStats } from "@/lib/types";
import { chartPalette } from "@/lib/chart-system";

interface RadarChartProps {
  stats: SeasonStats;
  percentiles?: PercentileResult | null;
  isPercentileLoading?: boolean;
}

const RADAR_DIMENSIONS = [
  {
    dimension: "Scoring",
    stat: "pts_pg",
    label: "Points per game",
    description: "How often this player scores compared with other qualifying players in the same season.",
  },
  {
    dimension: "Playmaking",
    stat: "ast_pg",
    label: "Assists per game",
    description: "How much this player creates made shots for teammates compared with the league.",
  },
  {
    dimension: "Rebounding",
    stat: "reb_pg",
    label: "Rebounds per game",
    description: "How much this player controls missed shots compared with other qualifying players.",
  },
  {
    dimension: "Efficiency",
    stat: "ts_pct",
    label: "True shooting percentage",
    description: "Scoring efficiency that accounts for twos, threes, and free throws.",
  },
  {
    dimension: "Production",
    stat: "per",
    label: "Player Efficiency Rating",
    description: "Box-score production summarized into a per-minute rating.",
  },
  {
    dimension: "Impact",
    stat: "bpm",
    label: "Box Plus/Minus",
    description: "Estimated box-score impact per 100 possessions above or below league average.",
  },
] as const;

function normalizeRadarData(percentiles?: PercentileResult | null) {
  return RADAR_DIMENSIONS.map((item) => {
    const value = percentiles?.percentiles[item.stat] ?? null;
    return {
      ...item,
      value: value != null ? Math.round(value) : 0,
      percentileLabel: value != null ? `${Math.round(value)}th percentile` : "No percentile",
    };
  });
}

function RadarTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: { dimension: string; label: string; description: string; percentileLabel: string } }>;
}) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[rgba(255,251,246,0.98)] px-3 py-2 text-xs shadow-[0_12px_28px_rgba(46,32,19,0.14)]">
      <p className="font-bold text-[var(--foreground)]">{item.dimension}</p>
      <p className="mt-1 text-[var(--muted)]">{item.label}</p>
      <p className="mt-1 text-[var(--surface-ink)]">{item.description}</p>
      <p className="mt-1 font-semibold text-[var(--accent)]">{item.percentileLabel}</p>
    </div>
  );
}

function percentileStatus(percentiles?: PercentileResult | null, isLoading?: boolean) {
  if (isLoading) return "Loading league percentiles...";
  if (!percentiles) return "Percentile context unavailable for this season.";
  return `Percentile rank vs qualifying players in ${percentiles.season}`;
}

function DimensionLegend({ data }: { data: ReturnType<typeof normalizeRadarData> }) {
  return (
    <div className="mt-3 grid grid-cols-2 gap-2 text-xs sm:grid-cols-3">
      {data.map((item) => (
        <div
          key={item.dimension}
          className="group relative rounded-lg border border-[rgba(53,41,33,0.10)] bg-white/58 px-2 py-1.5"
          tabIndex={0}
        >
          <p className="font-bold text-[var(--foreground)]">{item.dimension}</p>
          <p className="text-[var(--muted)]">{item.value > 0 ? item.percentileLabel : "Pending"}</p>
          <div className="pointer-events-none absolute bottom-full left-0 z-20 mb-2 hidden w-64 rounded-md border border-[rgba(53,41,33,0.16)] bg-[rgba(255,251,246,0.98)] px-3 py-2 text-xs font-medium leading-5 text-[var(--surface-ink)] shadow-[0_14px_32px_rgba(46,32,19,0.14)] group-hover:block group-focus:block">
            <p className="font-bold text-[var(--accent)]">{item.label}</p>
            <p className="mt-1">{item.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function RadarChart({
  stats,
  percentiles,
  isPercentileLoading = false,
}: RadarChartProps) {
  const data = normalizeRadarData(percentiles);

  const rawValues = [
    { label: "PTS", value: stats.pts_pg?.toFixed(1) ?? "—" },
    { label: "AST", value: stats.ast_pg?.toFixed(1) ?? "—" },
    { label: "REB", value: stats.reb_pg?.toFixed(1) ?? "—" },
    { label: "TS", value: stats.ts_pct != null ? `${(stats.ts_pct * 100).toFixed(1)}%` : "—" },
  ];

  return (
    <div className="rounded-[2rem] border border-[var(--border)] bg-[linear-gradient(145deg,rgba(247,243,232,0.96),rgba(228,236,232,0.92))] p-6 shadow-[0_18px_48px_rgba(47,43,36,0.07)]">
      <div className="mb-2">
        <p className="bip-kicker">Skill Profile</p>
        <h2 className="mt-0.5 text-lg font-semibold text-[var(--foreground)]">Player Radar</h2>
        <p className="mt-1 text-xs font-medium text-[var(--muted)]">
          {percentileStatus(percentiles, isPercentileLoading)}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {rawValues.map((item) => (
            <span
              key={item.label}
              className="rounded-full border border-[rgba(53,41,33,0.10)] bg-white/62 px-2.5 py-1 text-[11px] font-semibold text-[var(--surface-ink)]"
            >
              {item.label} {item.value}
            </span>
          ))}
        </div>
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
            tick={{ fontSize: 11, fill: "var(--surface-ink)", fontWeight: 700 }}
          />
          <PolarRadiusAxis
            angle={30}
            domain={[0, 100]}
            tick={false}
            axisLine={false}
          />
          <Tooltip
            content={<RadarTooltip />}
          />
          <Radar
            name="Percentile"
            dataKey="value"
            stroke={chartPalette.accent}
            fill="url(#radar-fill-grad)"
            fillOpacity={1}
            strokeWidth={2.5}
          />
        </RechartsRadar>
      </ResponsiveContainer>
      <DimensionLegend data={data} />
    </div>
  );
}
