"use client";

import { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { StandingsHistoryEntry } from "@/lib/types";
import { chartPalette } from "@/lib/chart-system";

interface StandingsBumpChartProps {
  historyData: StandingsHistoryEntry[];
  conference: "East" | "West";
  expanded?: boolean;
}

// 15 warm-palette colors, visually distinct on beige background
const TEAM_COLORS = [
  "#21483b", "#b5914e", "#9f3f31", "#3d6b5a", "#7a5c2e",
  "#4a7c6f", "#c27a2c", "#5c3d6b", "#2e6b4a", "#6b3d4a",
  "#3d5c7a", "#7a3d5c", "#5c7a3d", "#3d7a5c", "#7a5c3d",
];

function getTeamColor(idx: number): string {
  return TEAM_COLORS[idx % TEAM_COLORS.length];
}

interface BumpTooltipPayloadItem {
  name?: string;
  value?: number | null;
  color?: string;
}

interface BumpTooltipProps {
  active?: boolean;
  payload?: BumpTooltipPayloadItem[];
  label?: string;
}

function BumpTooltip({ active, payload, label }: BumpTooltipProps) {
  if (!active || !payload?.length) return null;
  const sorted = [...payload]
    .filter((p) => p.value != null)
    .sort((a, b) => (a.value ?? 99) - (b.value ?? 99));
  return (
    <div className="bip-panel rounded-xl px-3 py-2 text-xs shadow-lg max-h-60 overflow-y-auto">
      <p className="bip-kicker mb-1">{label}</p>
      {sorted.map((p, i) => (
        <div key={i} className="flex items-center justify-between gap-4 py-0.5">
          <span style={{ color: p.color }} className="font-medium">{p.name}</span>
          <span className="tabular-nums font-semibold text-[var(--foreground)]">#{p.value}</span>
        </div>
      ))}
    </div>
  );
}

export default function StandingsBumpChart({
  historyData,
  conference,
  expanded = false,
}: StandingsBumpChartProps) {
  const [hoveredTeam, setHoveredTeam] = useState<string | null>(null);

  const teams = useMemo(
    () => historyData.filter((e) => e.conference === conference),
    [historyData, conference]
  );

  // Collect all unique dates across all team snapshots, sorted
  const dates = useMemo(() => {
    const set = new Set<string>();
    teams.forEach((t) => t.snapshots.forEach((s) => set.add(s.date)));
    return Array.from(set).sort();
  }, [teams]);

  // Derive rank per team per date by sorting win_pct descending within conference
  const rankMap = useMemo(() => {
    const map = new Map<string, Map<string, number>>();
    for (const date of dates) {
      const entries = teams
        .map((t) => ({
          abbr: t.team_abbr,
          win_pct: t.snapshots.find((s) => s.date === date)?.win_pct ?? null,
        }))
        .filter((t) => t.win_pct !== null)
        .sort((a, b) => (b.win_pct ?? 0) - (a.win_pct ?? 0));
      entries.forEach(({ abbr }, i) => {
        if (!map.has(abbr)) map.set(abbr, new Map());
        map.get(abbr)!.set(date, i + 1);
      });
    }
    return map;
  }, [teams, dates]);

  // Build Recharts data array: [{date, TeamAbbr: rank, ...}]
  const chartData = useMemo(() => {
    return dates.map((date) => {
      const point: Record<string, string | number | null> = { date };
      for (const t of teams) {
        point[t.team_abbr] = rankMap.get(t.team_abbr)?.get(date) ?? null;
      }
      return point;
    });
  }, [dates, teams, rankMap]);

  if (teams.length === 0 || dates.length < 2) return null;

  const height = expanded ? 420 : 64;

  return (
    <div className={expanded ? "rounded-[2rem] border border-[var(--border)] bg-[linear-gradient(145deg,rgba(247,243,232,0.96),rgba(228,236,232,0.92))] p-6 shadow-[0_18px_48px_rgba(47,43,36,0.07)]" : ""}>
      {expanded && (
        <div className="mb-4">
          <p className="bip-kicker">Conference Rank Trend</p>
          <h3 className="mt-0.5 text-xl font-semibold text-[var(--foreground)]">
            {conference}ern Conference
          </h3>
        </div>
      )}

      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 6, right: expanded ? 56 : 4, left: 0, bottom: 4 }}>
          {expanded && (
            <CartesianGrid strokeDasharray="3 3" stroke={chartPalette.grid} />
          )}
          {expanded && (
            <XAxis
              dataKey="date"
              tick={{ fontSize: 9, fill: "var(--muted)" }}
              tickFormatter={(d: string) => d.slice(5)}
              interval={Math.max(0, Math.floor(dates.length / 8) - 1)}
            />
          )}
          {expanded && (
            <YAxis
              domain={[1, teams.length]}
              reversed
              ticks={[1, 3, 6, 8, 10, teams.length]}
              tick={{ fontSize: 9, fill: "var(--muted)" }}
              width={18}
              tickFormatter={(v: number) => `#${v}`}
            />
          )}
          {expanded && (
            <Tooltip content={<BumpTooltip />} />
          )}

          {teams.map((t, idx) => {
            const color = getTeamColor(idx);
            const isHovered = hoveredTeam === t.team_abbr;
            const dimmed = hoveredTeam !== null && !isHovered;
            return (
              <Line
                key={t.team_abbr}
                type="monotone"
                dataKey={t.team_abbr}
                stroke={color}
                strokeWidth={expanded ? (isHovered ? 3 : 1.5) : 1.5}
                strokeOpacity={dimmed ? 0.2 : 1}
                dot={false}
                activeDot={expanded ? { r: 4, fill: color } : false}
                connectNulls
                name={t.team_abbr}
                onMouseEnter={() => setHoveredTeam(t.team_abbr)}
                onMouseLeave={() => setHoveredTeam(null)}
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>

      {/* Team color legend */}
      {expanded && (
        <div className="flex flex-wrap gap-x-3 gap-y-1.5 mt-4">
          {teams.map((t, idx) => (
            <button
              key={t.team_abbr}
              className="flex items-center gap-1 text-[10px] font-medium transition-opacity"
              style={{ opacity: hoveredTeam !== null && hoveredTeam !== t.team_abbr ? 0.35 : 1 }}
              onMouseEnter={() => setHoveredTeam(t.team_abbr)}
              onMouseLeave={() => setHoveredTeam(null)}
            >
              <span
                className="inline-block w-3 h-0.5 rounded-full shrink-0"
                style={{ backgroundColor: getTeamColor(idx) }}
              />
              <span style={{ color: getTeamColor(idx) }}>{t.team_abbr}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
