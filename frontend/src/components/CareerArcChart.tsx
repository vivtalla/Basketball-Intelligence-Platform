"use client";

import { useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea,
  ReferenceLine,
} from "recharts";
import type { SeasonStats } from "@/lib/types";
import { chartPalette } from "@/lib/chart-system";

interface CareerArcChartProps {
  seasons: SeasonStats[];
  birthDate?: string | null;
}

interface StatOption {
  key: keyof SeasonStats;
  label: string;
  color: string;
  pct?: boolean;
}

const STAT_OPTIONS: StatOption[] = [
  { key: "pts_pg", label: "PPG",  color: chartPalette.accent },
  { key: "reb_pg", label: "RPG",  color: "#3d6b5a" },
  { key: "ast_pg", label: "APG",  color: chartPalette.signal },
  { key: "per",    label: "PER",  color: "#6b5c8f" },
  { key: "bpm",    label: "BPM",  color: chartPalette.danger },
  { key: "ts_pct", label: "TS%",  color: "#3d7a7a", pct: true },
  { key: "ws",     label: "WS",   color: "#7a5c2e" },
];

const DEFAULT_ACTIVE = new Set(["pts_pg", "per", "bpm"]);

function parseBirthYear(birthDate: string): number | null {
  const year = parseInt(birthDate.slice(0, 4), 10);
  return isNaN(year) ? null : year;
}

/** "2024-25" → 2024 */
function seasonStartYear(season: string): number {
  return parseInt(season.slice(0, 4), 10);
}

/** birth year + age → season string e.g. birthYear=1984, age=26 → "2010-11" */
function seasonForAge(birthYear: number, age: number): string {
  const start = birthYear + age;
  return `${start}-${String(start + 1).slice(-2)}`;
}

export default function CareerArcChart({ seasons, birthDate }: CareerArcChartProps) {
  const [active, setActive] = useState<Set<string>>(new Set(DEFAULT_ACTIVE));
  const [showAging, setShowAging] = useState(false);

  if (seasons.length === 0) return null;

  const birthYear = birthDate ? parseBirthYear(birthDate) : null;
  const canShowAging = birthYear != null;

  // Build chart data — include age when we have birth year
  const data = seasons.map((s) => {
    const point: Record<string, string | number | null> = { season: s.season };
    for (const opt of STAT_OPTIONS) {
      const raw = s[opt.key] as number | null;
      point[opt.key] = raw != null ? (opt.pct ? parseFloat((raw * 100).toFixed(1)) : raw) : null;
    }
    if (birthYear) {
      point._age = seasonStartYear(s.season) - birthYear;
    }
    return point;
  });

  // Aging reference seasons (only relevant if we have birth year)
  const primeStartSeason = birthYear ? seasonForAge(birthYear, 24) : null;
  const primeEndSeason   = birthYear ? seasonForAge(birthYear, 29) : null;
  const peakSeason       = birthYear ? seasonForAge(birthYear, 26) : null;

  // Check if reference seasons fall within the player's career data range
  const seasonSet = new Set(seasons.map(s => s.season));
  const primeOverlaps =
    primeStartSeason && primeEndSeason &&
    seasons.some(s => {
      const y = seasonStartYear(s.season);
      const ps = seasonStartYear(primeStartSeason);
      const pe = seasonStartYear(primeEndSeason);
      return y >= ps && y <= pe;
    });

  function toggleStat(key: string) {
    setActive((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size === 1) return prev;
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  const activeStats = STAT_OPTIONS.filter((opt) => active.has(opt.key as string));

  return (
    <div className="rounded-[2rem] border border-[var(--border)] bg-[linear-gradient(145deg,rgba(247,243,232,0.96),rgba(228,236,232,0.92))] p-6 shadow-[0_18px_48px_rgba(47,43,36,0.07)]">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-3">
          <div>
            <p className="bip-kicker">Career Trajectory</p>
            <h3 className="mt-0.5 font-semibold text-[var(--foreground)]">Career Arc</h3>
          </div>
          {canShowAging && (
            <button
              onClick={() => setShowAging(v => !v)}
              className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                showAging
                  ? "bg-[var(--signal)] border-[var(--signal)] text-white"
                  : "bip-toggle rounded-full"
              }`}
            >
              Aging curve
            </button>
          )}
        </div>

        {/* Stat toggles */}
        <div className="flex flex-wrap gap-2">
          {STAT_OPTIONS.map((opt) => {
            const on = active.has(opt.key as string);
            return (
              <button
                key={opt.key as string}
                onClick={() => toggleStat(opt.key as string)}
                className="flex items-center gap-1.5 px-3 py-1 text-xs rounded-full border transition-all duration-150"
                style={
                  on
                    ? { backgroundColor: opt.color, borderColor: opt.color, color: "#fff" }
                    : { backgroundColor: "rgba(255,251,246,0.9)", borderColor: "var(--border)", color: "var(--muted)" }
                }
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 4 }}>
          <defs>
            {activeStats.map((opt) => (
              <linearGradient key={opt.key as string} id={`arc-grad-${opt.key as string}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={opt.color} stopOpacity={0.18} />
                <stop offset="95%" stopColor={opt.color} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={chartPalette.grid} />
          <XAxis
            dataKey="season"
            tick={{ fontSize: 10, fill: "var(--muted)" }}
            angle={-40}
            textAnchor="end"
            height={52}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fontSize: 11, fill: "var(--muted)" }} />
          <Tooltip
            contentStyle={{
              fontSize: 12,
              backgroundColor: "rgba(255,251,246,0.96)",
              border: "1px solid var(--border)",
              borderRadius: 10,
            }}
            formatter={(value, name) => {
              const opt = STAT_OPTIONS.find((o) => o.key === name);
              return [`${value}${opt?.pct ? "%" : ""}`, opt?.label ?? name];
            }}
            labelFormatter={(label, payload) => {
              const age = payload?.[0]?.payload?._age;
              return age != null ? `${label}  (Age ${age})` : label;
            }}
          />
          <Legend
            formatter={(value) => STAT_OPTIONS.find((o) => o.key === value)?.label ?? value}
            wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
          />

          {/* Aging curve overlays */}
          {showAging && primeOverlaps && primeStartSeason && primeEndSeason && (
            <ReferenceArea
              x1={primeStartSeason}
              x2={primeEndSeason}
              fill={chartPalette.signal}
              fillOpacity={0.07}
              strokeOpacity={0}
            />
          )}
          {showAging && peakSeason && seasonSet.has(peakSeason) && (
            <ReferenceLine
              x={peakSeason}
              stroke={chartPalette.signal}
              strokeDasharray="4 3"
              strokeWidth={1.5}
              label={{ value: "Peak (26)", position: "insideTopRight", fontSize: 9, fill: chartPalette.signal }}
            />
          )}

          {activeStats.map((opt) => (
            <Area
              key={opt.key as string}
              type="monotone"
              dataKey={opt.key as string}
              stroke={opt.color}
              strokeWidth={2}
              fill={`url(#arc-grad-${opt.key as string})`}
              dot={{ r: 3, fill: opt.color }}
              activeDot={{ r: 5 }}
              connectNulls
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>

      {showAging && canShowAging && (
        <p className="mt-2 text-[10px] text-[var(--muted)] text-center">
          Shaded region = typical NBA prime (ages 24–29) · dashed line = expected peak (age 26) · age shown in tooltip
        </p>
      )}
    </div>
  );
}
