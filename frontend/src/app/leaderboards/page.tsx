"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { useLeaderboard } from "@/hooks/usePlayerStats";
import { getAvailableSeasons } from "@/lib/api";

// ─── Stat options ─────────────────────────────────────────────────────────────

const STAT_GROUPS = [
  {
    label: "Scoring",
    options: [
      { key: "pts_pg",  label: "Points Per Game",       fmt: "1f"  },
      { key: "fg_pct",  label: "Field Goal %",          fmt: "pct" },
      { key: "fg3_pct", label: "3-Point %",             fmt: "pct" },
      { key: "ft_pct",  label: "Free Throw %",          fmt: "pct" },
      { key: "ts_pct",  label: "True Shooting %",       fmt: "pct" },
      { key: "efg_pct", label: "Effective FG %",        fmt: "pct" },
    ],
  },
  {
    label: "Production",
    options: [
      { key: "reb_pg",  label: "Rebounds Per Game",     fmt: "1f"  },
      { key: "ast_pg",  label: "Assists Per Game",      fmt: "1f"  },
      { key: "stl_pg",  label: "Steals Per Game",       fmt: "1f"  },
      { key: "blk_pg",  label: "Blocks Per Game",       fmt: "1f"  },
      { key: "min_pg",  label: "Minutes Per Game",      fmt: "1f"  },
    ],
  },
  {
    label: "Advanced",
    options: [
      { key: "per",         label: "PER",               fmt: "1f"  },
      { key: "bpm",         label: "BPM",               fmt: "1f"  },
      { key: "ws",          label: "Win Shares",        fmt: "1f"  },
      { key: "vorp",        label: "VORP",              fmt: "1f"  },
      { key: "usg_pct",     label: "Usage Rate",        fmt: "pct" },
      { key: "off_rating",  label: "Offensive Rating",  fmt: "1f"  },
      { key: "def_rating",  label: "Defensive Rating",  fmt: "1f"  },
      { key: "net_rating",  label: "Net Rating",        fmt: "1f"  },
      { key: "pie",         label: "PIE",               fmt: "pct" },
      { key: "darko",       label: "DARKO",             fmt: "2f"  },
    ],
  },
];

const ALL_OPTIONS = STAT_GROUPS.flatMap((g) => g.options);

function getStatLabel(key: string) {
  return ALL_OPTIONS.find((o) => o.key === key)?.label ?? key;
}

function getStatFmt(key: string) {
  return ALL_OPTIONS.find((o) => o.key === key)?.fmt ?? "1f";
}

function formatStat(value: number, fmt: string): string {
  if (fmt === "pct") return `${(value * 100).toFixed(1)}%`;
  if (fmt === "2f") return value.toFixed(2);
  return value.toFixed(1);
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LeaderboardsPage() {
  const [stat, setStat] = useState("pts_pg");
  const [season, setSeason] = useState("");
  const [seasonType, setSeasonType] = useState<"Regular Season" | "Playoffs">("Regular Season");
  const [seasons, setSeasons] = useState<string[]>([]);

  useEffect(() => {
    getAvailableSeasons().then((s) => {
      setSeasons(s);
      if (s.length > 0) setSeason(s[0]);
    }).catch(() => {});
  }, []);

  const { data: leaderboard, isLoading } = useLeaderboard(stat, season, seasonType);

  const statLabel = getStatLabel(stat);
  const statFmt = getStatFmt(stat);

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <Link href="/" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors">
          ← Back to Home
        </Link>
      </div>

      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">Leaderboards</h1>
        <p className="text-gray-500 dark:text-gray-400">Top 25 players ranked by any stat for a given season.</p>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        {/* Stat selector */}
        <select
          value={stat}
          onChange={(e) => setStat(e.target.value)}
          className="text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {STAT_GROUPS.map((group) => (
            <optgroup key={group.label} label={group.label}>
              {group.options.map((opt) => (
                <option key={opt.key} value={opt.key}>{opt.label}</option>
              ))}
            </optgroup>
          ))}
        </select>

        {/* Season selector */}
        <select
          value={season}
          onChange={(e) => setSeason(e.target.value)}
          disabled={seasons.length === 0}
          className="text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {seasons.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        {/* Regular Season / Playoffs toggle */}
        <div className="flex rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 text-sm">
          {(["Regular Season", "Playoffs"] as const).map((type) => (
            <button
              key={type}
              onClick={() => setSeasonType(type)}
              className={`px-4 py-2 transition-colors ${
                seasonType === type
                  ? "bg-blue-500 text-white"
                  : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700">
              <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 w-10">#</th>
              <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3">Player</th>
              <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 hidden sm:table-cell">Team</th>
              <th className="text-right text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 hidden sm:table-cell">GP</th>
              <th className="text-right text-xs font-semibold uppercase tracking-wider text-blue-500 dark:text-blue-400 px-4 py-3">{statLabel}</th>
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 10 }).map((_, i) => (
                <tr key={i} className="border-b border-gray-100 dark:border-gray-700/50 animate-pulse">
                  <td className="px-4 py-3"><div className="h-4 w-4 bg-gray-200 dark:bg-gray-700 rounded" /></td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700" />
                      <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
                    </div>
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell"><div className="h-4 w-10 bg-gray-200 dark:bg-gray-700 rounded" /></td>
                  <td className="px-4 py-3 hidden sm:table-cell"><div className="h-4 w-8 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                  <td className="px-4 py-3"><div className="h-4 w-12 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                </tr>
              ))}

            {!isLoading && leaderboard?.entries.length === 0 && (
              <tr>
                <td colSpan={5} className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">
                  No data available for this combination.
                </td>
              </tr>
            )}

            {!isLoading &&
              leaderboard?.entries.map((entry) => (
                <tr
                  key={entry.player_id}
                  className="border-b border-gray-100 dark:border-gray-700/50 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
                >
                  <td className="px-4 py-3 text-sm text-gray-400 dark:text-gray-500 font-mono">
                    {entry.rank}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/players/${entry.player_id}`}
                      className="flex items-center gap-3 group"
                    >
                      <div className="relative w-8 h-8 rounded-full overflow-hidden bg-gray-100 dark:bg-gray-700 shrink-0">
                        <Image
                          src={entry.headshot_url}
                          alt={entry.player_name}
                          fill
                          className="object-cover object-top"
                          onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                        />
                      </div>
                      <span className="font-medium text-gray-900 dark:text-gray-100 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors">
                        {entry.player_name}
                      </span>
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 hidden sm:table-cell">
                    {entry.team_abbreviation}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 text-right hidden sm:table-cell">
                    {entry.gp}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-blue-600 dark:text-blue-400 tabular-nums">
                    {formatStat(entry.stat_value, statFmt)}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-400 dark:text-gray-500 mt-3 text-center">
        Min. 15 games played · Regular season stats only when &quot;Regular Season&quot; is selected
      </p>
    </div>
  );
}
