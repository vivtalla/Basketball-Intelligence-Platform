"use client";

import { useState, useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { SeasonStats } from "@/lib/types";

interface PlayerArc {
  name: string;
  seasons: SeasonStats[];
  birthDate?: string | null;
}

interface DualCareerArcChartProps {
  playerA: PlayerArc;
  playerB: PlayerArc;
}

const STAT_OPTIONS = [
  { key: "bpm",    label: "BPM",  pct: false },
  { key: "pts_pg", label: "PPG",  pct: false },
  { key: "per",    label: "PER",  pct: false },
  { key: "ws",     label: "WS",   pct: false },
  { key: "ts_pct", label: "TS%",  pct: true  },
  { key: "vorp",   label: "VORP", pct: false },
];

const COLOR_A = "#3b82f6"; // blue
const COLOR_B = "#f59e0b"; // amber

function parseBirthYear(d: string): number | null {
  const y = parseInt(d.slice(0, 4), 10);
  return isNaN(y) ? null : y;
}

function seasonStartYear(s: string): number {
  return parseInt(s.slice(0, 4), 10);
}

export default function DualCareerArcChart({ playerA, playerB }: DualCareerArcChartProps) {
  const [stat, setStat] = useState("bpm");

  const statMeta = STAT_OPTIONS.find((o) => o.key === stat) ?? STAT_OPTIONS[0];

  // Build a unified season list spanning both careers
  const allSeasons = useMemo(() => {
    const set = new Set<string>();
    playerA.seasons.forEach((s) => set.add(s.season));
    playerB.seasons.forEach((s) => set.add(s.season));
    return Array.from(set).sort();
  }, [playerA.seasons, playerB.seasons]);

  const mapA = useMemo(() => new Map(playerA.seasons.map((s) => [s.season, s])), [playerA.seasons]);
  const mapB = useMemo(() => new Map(playerB.seasons.map((s) => [s.season, s])), [playerB.seasons]);

  const birthYearA = playerA.birthDate ? parseBirthYear(playerA.birthDate) : null;
  const birthYearB = playerB.birthDate ? parseBirthYear(playerB.birthDate) : null;

  const data = useMemo(() => {
    return allSeasons.map((season) => {
      const sA = mapA.get(season);
      const sB = mapB.get(season);
      const rawA = sA ? (sA[stat as keyof SeasonStats] as number | null) : null;
      const rawB = sB ? (sB[stat as keyof SeasonStats] as number | null) : null;
      const valA = rawA != null ? (statMeta.pct ? parseFloat((rawA * 100).toFixed(1)) : rawA) : null;
      const valB = rawB != null ? (statMeta.pct ? parseFloat((rawB * 100).toFixed(1)) : rawB) : null;
      return {
        season,
        [playerA.name]: valA,
        [playerB.name]: valB,
        _ageA: birthYearA ? seasonStartYear(season) - birthYearA : null,
        _ageB: birthYearB ? seasonStartYear(season) - birthYearB : null,
      };
    });
  }, [allSeasons, mapA, mapB, stat, statMeta.pct, playerA.name, playerB.name, birthYearA, birthYearB]);

  if (allSeasons.length === 0) return null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">Career Arc Comparison</h3>
        <div className="flex rounded-xl overflow-hidden border border-gray-200 dark:border-gray-700 text-xs">
          {STAT_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              onClick={() => setStat(opt.key)}
              className={`px-3 py-1.5 transition-colors ${
                stat === opt.key
                  ? "bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 font-medium"
                  : "bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={280}>
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
          {stat === "bpm" && (
            <ReferenceLine y={0} stroke="#9ca3af" strokeDasharray="3 3" strokeWidth={1} />
          )}
          <Tooltip
            contentStyle={{
              fontSize: 12,
              backgroundColor: "var(--tooltip-bg, #fff)",
              border: "1px solid #e5e7eb",
              borderRadius: 8,
            }}
            formatter={(value, name) => [
              `${value}${statMeta.pct ? "%" : ""}`,
              String(name),
            ]}
            labelFormatter={(label, payload) => {
              const p = payload?.[0]?.payload;
              const parts = [label as string];
              if (p?._ageA != null) parts.push(`${playerA.name} age ${p._ageA}`);
              if (p?._ageB != null) parts.push(`${playerB.name} age ${p._ageB}`);
              return parts.join(" · ");
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
          <Line
            type="monotone"
            dataKey={playerA.name}
            stroke={COLOR_A}
            strokeWidth={2}
            dot={{ r: 3, fill: COLOR_A }}
            activeDot={{ r: 5 }}
            connectNulls
          />
          <Line
            type="monotone"
            dataKey={playerB.name}
            stroke={COLOR_B}
            strokeWidth={2}
            dot={{ r: 3, fill: COLOR_B }}
            activeDot={{ r: 5 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>

      <p className="mt-2 text-[10px] text-gray-400 dark:text-gray-500 text-center">
        Age shown in tooltip when birth date is available · gaps indicate seasons without data
      </p>
    </div>
  );
}
