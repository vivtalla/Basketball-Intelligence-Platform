"use client";

import { useTeamNetRatingSeries } from "@/hooks/usePlayerStats";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";

interface TeamNetRatingChartProps {
  teamAbbreviation: string;
  season: string;
  window?: number;
}

export default function TeamNetRatingChart({
  teamAbbreviation,
  season,
  window = 10,
}: TeamNetRatingChartProps) {
  const { data, isLoading, error } = useTeamNetRatingSeries(teamAbbreviation, season, window);

  if (error || data?.data_status === "unavailable") {
    return (
      <div className="p-4 bg-[var(--surface-alt)] rounded border border-[var(--border-color)] text-xs text-[var(--muted)]">
        Net rating data unavailable.
      </div>
    );
  }

  if (isLoading || !data?.games || data.games.length === 0) {
    return (
      <div className="p-4 bg-[var(--surface-alt)] rounded border border-[var(--border-color)] h-[200px] flex items-center justify-center text-xs text-[var(--muted)]">
        Loading rolling net rating...
      </div>
    );
  }

  const chartData = data.games.map((game) => ({
    date: game.game_date ? game.game_date.split("-").slice(1).join("/") : "—",
    rolling: game.rolling_net_rating,
    opponent: game.opponent_abbr || "—",
    margin: game.margin,
  }));

  return (
    <div className="space-y-2">
      <div>
        <h3 className="text-sm font-semibold text-[var(--text-secondary)]">
          Season Trajectory ({window}-Game Rolling)
        </h3>
        <div className="text-xs text-[var(--muted)]">
          Season avg: {data.season_avg_margin ? (data.season_avg_margin > 0 ? "+" : "") + data.season_avg_margin.toFixed(1) : "—"}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 20, left: -15, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
          <XAxis
            dataKey="date"
            stroke="var(--text-secondary)"
            tick={{ fontSize: 11 }}
            interval={Math.floor(chartData.length / 8)}
          />
          <YAxis
            stroke="var(--text-secondary)"
            tick={{ fontSize: 11 }}
            domain={["dataMin - 2", "dataMax + 2"]}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--surface)",
              border: "1px solid var(--border-color)",
              borderRadius: "4px",
            }}
            cursor={{ stroke: "var(--border-color)", strokeDasharray: "3 3" }}
            labelStyle={{ color: "var(--text-secondary)", fontSize: 12 }}
            formatter={(value: number) => [(value > 0 ? "+" : "") + value.toFixed(1), "Rolling NR"]}
            labelFormatter={(label) => `Date: ${label}`}
          />
          <ReferenceLine
            y={data.season_avg_margin || 0}
            stroke="var(--text-secondary)"
            strokeDasharray="3 3"
            label={{
              value: "Season Avg",
              position: "right",
              fill: "var(--text-secondary)",
              fontSize: 10,
              offset: 5,
            }}
          />
          <Line
            type="monotone"
            dataKey="rolling"
            stroke="rgb(34, 197, 94)"
            dot={false}
            strokeWidth={2}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
