"use client";

import { useState } from "react";
import Image from "next/image";
import type { PlayerProfile, CareerStatsResponse, SeasonStats } from "@/lib/types";

interface PlayerData {
  profile: PlayerProfile;
  career: CareerStatsResponse;
}

interface ComparisonViewProps {
  playerA: PlayerData;
  playerB: PlayerData;
}

type ViewMode = "career" | "current";

// ─── Stat row definitions ─────────────────────────────────────────────────────

interface StatRow {
  key: keyof SeasonStats;
  label: string;
  higherBetter: boolean;
  pct?: boolean;   // multiply by 100 for display
  decimals?: number;
}

const TRADITIONAL_ROWS: StatRow[] = [
  { key: "pts_pg",  label: "Points Per Game",   higherBetter: true  },
  { key: "reb_pg",  label: "Rebounds Per Game",  higherBetter: true  },
  { key: "ast_pg",  label: "Assists Per Game",   higherBetter: true  },
  { key: "stl_pg",  label: "Steals Per Game",    higherBetter: true  },
  { key: "blk_pg",  label: "Blocks Per Game",    higherBetter: true  },
  { key: "tov_pg",  label: "Turnovers Per Game", higherBetter: false },
  { key: "min_pg",  label: "Minutes Per Game",   higherBetter: true  },
  { key: "fg_pct",  label: "FG%",                higherBetter: true,  pct: true },
  { key: "fg3_pct", label: "3P%",                higherBetter: true,  pct: true },
  { key: "ft_pct",  label: "FT%",                higherBetter: true,  pct: true },
  { key: "gp",      label: "Games Played",       higherBetter: true  },
];

const ADVANCED_ROWS: StatRow[] = [
  { key: "per",         label: "PER",             higherBetter: true              },
  { key: "bpm",         label: "BPM",             higherBetter: true              },
  { key: "ws",          label: "Win Shares",      higherBetter: true              },
  { key: "vorp",        label: "VORP",            higherBetter: true              },
  { key: "ts_pct",      label: "TS%",             higherBetter: true,  pct: true  },
  { key: "efg_pct",     label: "eFG%",            higherBetter: true,  pct: true  },
  { key: "usg_pct",     label: "USG%",            higherBetter: false             },
  { key: "off_rating",  label: "Offensive Rating", higherBetter: true             },
  { key: "def_rating",  label: "Defensive Rating", higherBetter: false            },
  { key: "net_rating",  label: "Net Rating",      higherBetter: true              },
  { key: "pie",         label: "PIE",             higherBetter: true,  pct: true  },
  { key: "darko",       label: "DARKO",           higherBetter: true,  decimals: 2},
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatVal(val: number | null | undefined, row: StatRow): string {
  if (val == null) return "—";
  const v = row.pct ? val * 100 : val;
  const d = row.decimals ?? 1;
  return row.pct ? `${v.toFixed(d)}%` : v.toFixed(d);
}

function winner(
  valA: number | null | undefined,
  valB: number | null | undefined,
  higherBetter: boolean
): "A" | "B" | null {
  if (valA == null || valB == null) return null;
  if (valA === valB) return null;
  return higherBetter ? (valA > valB ? "A" : "B") : (valA < valB ? "A" : "B");
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function PlayerAvatar({ profile, align }: { profile: PlayerProfile; align: "left" | "right" }) {
  return (
    <div className={`flex items-center gap-3 ${align === "right" ? "flex-row-reverse text-right" : ""}`}>
      <div className="relative w-16 h-16 rounded-full overflow-hidden bg-gray-100 dark:bg-gray-700 shrink-0 border-2 border-gray-200 dark:border-gray-600">
        <Image
          src={profile.headshot_url}
          alt={profile.full_name}
          fill
          className="object-cover object-top"
          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
        />
      </div>
      <div>
        <div className="font-bold text-gray-900 dark:text-gray-100 leading-tight">{profile.full_name}</div>
        <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          {profile.team_name || "Free Agent"} · {profile.position || "—"}
        </div>
      </div>
    </div>
  );
}

function StatRowItem({
  row,
  statsA,
  statsB,
}: {
  row: StatRow;
  statsA: SeasonStats | null;
  statsB: SeasonStats | null;
}) {
  const valA = statsA ? (statsA[row.key] as number | null) : null;
  const valB = statsB ? (statsB[row.key] as number | null) : null;
  const w = winner(valA, valB, row.higherBetter);

  return (
    <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 py-2 border-b border-gray-100 dark:border-gray-700/50 last:border-0">
      <span
        className={`text-right font-semibold tabular-nums text-lg ${
          w === "A"
            ? "text-blue-600 dark:text-blue-400"
            : w === "B"
            ? "text-gray-400 dark:text-gray-500"
            : "text-gray-700 dark:text-gray-300"
        }`}
      >
        {formatVal(valA, row)}
      </span>
      <span className="text-xs text-gray-500 dark:text-gray-400 text-center whitespace-nowrap px-2 min-w-[120px]">
        {row.label}
      </span>
      <span
        className={`text-left font-semibold tabular-nums text-lg ${
          w === "B"
            ? "text-blue-600 dark:text-blue-400"
            : w === "A"
            ? "text-gray-400 dark:text-gray-500"
            : "text-gray-700 dark:text-gray-300"
        }`}
      >
        {formatVal(valB, row)}
      </span>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ComparisonView({ playerA, playerB }: ComparisonViewProps) {
  const [mode, setMode] = useState<ViewMode>("career");

  const statsA: SeasonStats | null =
    mode === "career"
      ? playerA.career.career_totals
      : playerA.career.seasons[playerA.career.seasons.length - 1] ?? null;

  const statsB: SeasonStats | null =
    mode === "career"
      ? playerB.career.career_totals
      : playerB.career.seasons[playerB.career.seasons.length - 1] ?? null;

  const seasonLabelA = mode === "current" ? statsA?.season : "Career";
  const seasonLabelB = mode === "current" ? statsB?.season : "Career";

  return (
    <div className="space-y-6">
      {/* Player headers */}
      <div className="grid grid-cols-2 gap-4">
        <PlayerAvatar profile={playerA.profile} align="left" />
        <PlayerAvatar profile={playerB.profile} align="right" />
      </div>

      {/* Mode toggle + season labels */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400 dark:text-gray-500">{seasonLabelA}</span>
        <div className="flex rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 text-xs">
          {(["career", "current"] as ViewMode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-4 py-1.5 capitalize transition-colors ${
                mode === m
                  ? "bg-blue-500 text-white"
                  : "bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-600"
              }`}
            >
              {m === "career" ? "Career" : "Current Season"}
            </button>
          ))}
        </div>
        <span className="text-xs text-gray-400 dark:text-gray-500">{seasonLabelB}</span>
      </div>

      {/* Traditional stats */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-4">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">
          Traditional
        </h4>
        {TRADITIONAL_ROWS.map((row) => (
          <StatRowItem key={row.key} row={row} statsA={statsA} statsB={statsB} />
        ))}
      </div>

      {/* Advanced stats */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-4">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">
          Advanced
        </h4>
        {ADVANCED_ROWS.map((row) => (
          <StatRowItem key={row.key} row={row} statsA={statsA} statsB={statsB} />
        ))}
      </div>

      <p className="text-center text-xs text-blue-500 dark:text-blue-400">
        Blue = better value
      </p>
    </div>
  );
}
