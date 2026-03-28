"use client";

import { useState } from "react";
import Image from "next/image";
import type { PlayerProfile, CareerStatsResponse, SeasonStats } from "@/lib/types";
import { usePlayerPercentiles } from "@/hooks/usePlayerStats";

interface PlayerData {
  profile: PlayerProfile;
  career: CareerStatsResponse;
}

interface ComparisonViewProps {
  playerA: PlayerData;
  playerB: PlayerData;
}

type ViewMode = "career" | "current" | "percentile";

// ─── Stat row definitions ─────────────────────────────────────────────────────

interface StatRow {
  key: keyof SeasonStats;
  label: string;
  higherBetter: boolean;
  pct?: boolean;
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

function pctileColor(pct: number): string {
  if (pct >= 80) return "#10b981"; // emerald
  if (pct >= 60) return "#3b82f6"; // blue
  if (pct >= 40) return "#f59e0b"; // amber
  return "#ef4444";                // red
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

function PercentileRowItem({
  row,
  pctA,
  pctB,
  statsA,
  statsB,
}: {
  row: StatRow;
  pctA: number | null;
  pctB: number | null;
  statsA: SeasonStats | null;
  statsB: SeasonStats | null;
}) {
  const valA = statsA ? (statsA[row.key] as number | null) : null;
  const valB = statsB ? (statsB[row.key] as number | null) : null;
  const hasPctA = pctA != null;
  const hasPctB = pctB != null;

  return (
    <div className="py-2.5 border-b border-gray-100 dark:border-gray-700/50 last:border-0">
      <div className="text-xs text-gray-500 dark:text-gray-400 text-center mb-1.5">{row.label}</div>
      <div className="space-y-1">
        {/* Player A bar */}
        <div className="flex items-center gap-2">
          <div className="flex-1 h-5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden relative">
            {hasPctA && (
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${pctA}%`, backgroundColor: pctileColor(pctA) }}
              />
            )}
          </div>
          <span className="text-xs tabular-nums text-gray-500 dark:text-gray-400 w-28 text-right shrink-0">
            {hasPctA
              ? <span style={{ color: pctileColor(pctA!) }}>{Math.round(pctA!)}th pct</span>
              : null}{" "}
            <span className="text-gray-400 dark:text-gray-500">{formatVal(valA, row)}</span>
          </span>
        </div>
        {/* Player B bar */}
        <div className="flex items-center gap-2">
          <div className="flex-1 h-5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden relative">
            {hasPctB && (
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${pctB}%`, backgroundColor: pctileColor(pctB) }}
              />
            )}
          </div>
          <span className="text-xs tabular-nums text-gray-500 dark:text-gray-400 w-28 text-right shrink-0">
            {hasPctB
              ? <span style={{ color: pctileColor(pctB!) }}>{Math.round(pctB!)}th pct</span>
              : null}{" "}
            <span className="text-gray-400 dark:text-gray-500">{formatVal(valB, row)}</span>
          </span>
        </div>
      </div>
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

  const currentSeasonA = playerA.career.seasons[playerA.career.seasons.length - 1]?.season ?? null;
  const currentSeasonB = playerB.career.seasons[playerB.career.seasons.length - 1]?.season ?? null;
  // Use the more recent season for percentile context
  const pctSeason = currentSeasonA && currentSeasonB
    ? currentSeasonA >= currentSeasonB ? currentSeasonA : currentSeasonB
    : currentSeasonA ?? currentSeasonB;

  const { data: percA } = usePlayerPercentiles(
    mode === "percentile" ? playerA.profile.id : null,
    mode === "percentile" ? pctSeason : null
  );
  const { data: percB } = usePlayerPercentiles(
    mode === "percentile" ? playerB.profile.id : null,
    mode === "percentile" ? pctSeason : null
  );

  const pctStatsA = mode === "percentile"
    ? (playerA.career.seasons[playerA.career.seasons.length - 1] ?? null)
    : statsA;
  const pctStatsB = mode === "percentile"
    ? (playerB.career.seasons[playerB.career.seasons.length - 1] ?? null)
    : statsB;

  const seasonLabelA = mode === "career" ? "Career" : mode === "percentile" ? (currentSeasonA ?? "—") : (statsA?.season ?? "—");
  const seasonLabelB = mode === "career" ? "Career" : mode === "percentile" ? (currentSeasonB ?? "—") : (statsB?.season ?? "—");

  const getPct = (percs: typeof percA, key: string): number | null => {
    if (!percs) return null;
    const v = percs.percentiles[key];
    return v != null ? Math.round(v) : null;
  };

  const allRows = [...TRADITIONAL_ROWS, ...ADVANCED_ROWS];

  return (
    <div className="space-y-6">
      {/* Player headers */}
      <div className="grid grid-cols-2 gap-4">
        <PlayerAvatar profile={playerA.profile} align="left" />
        <PlayerAvatar profile={playerB.profile} align="right" />
      </div>

      {/* Mode toggle + season labels */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="text-xs text-gray-400 dark:text-gray-500 min-w-0">{seasonLabelA}</span>
        <div className="flex rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 text-xs shrink-0">
          {([
            { id: "career", label: "Career" },
            { id: "current", label: "Season" },
            { id: "percentile", label: "Percentile" },
          ] as { id: ViewMode; label: string }[]).map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              className={`px-3 py-1.5 transition-colors ${
                mode === m.id
                  ? "bg-blue-500 text-white"
                  : "bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-600"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
        <span className="text-xs text-gray-400 dark:text-gray-500 min-w-0 text-right">{seasonLabelB}</span>
      </div>

      {/* Percentile mode */}
      {mode === "percentile" && (
        <>
          {/* Legend */}
          <div className="flex items-center gap-4 text-xs text-gray-400 dark:text-gray-500 flex-wrap">
            <div className="flex items-center gap-1.5">
              <div className="w-12 h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                <div className="h-full w-1/2 rounded-full" style={{ backgroundColor: "#3b82f6" }} />
              </div>
              <span>{playerA.profile.full_name.split(" ")[1] ?? playerA.profile.full_name} (top bar)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-12 h-2 rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
                <div className="h-full w-1/2 rounded-full" style={{ backgroundColor: "#3b82f6" }} />
              </div>
              <span>{playerB.profile.full_name.split(" ")[1] ?? playerB.profile.full_name} (bottom bar)</span>
            </div>
            <div className="flex items-center gap-3 ml-auto">
              {[["≥80th", "#10b981"], ["60–79th", "#3b82f6"], ["40–59th", "#f59e0b"], ["<40th", "#ef4444"]].map(([label, color]) => (
                <span key={label} className="flex items-center gap-1">
                  <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: color }} />
                  {label}
                </span>
              ))}
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">
              Traditional — {pctSeason}
            </h4>
            {TRADITIONAL_ROWS.filter(r => !["gp", "min_pg"].includes(r.key as string)).map((row) => (
              <PercentileRowItem
                key={row.key}
                row={row}
                pctA={getPct(percA, row.key as string)}
                pctB={getPct(percB, row.key as string)}
                statsA={pctStatsA}
                statsB={pctStatsB}
              />
            ))}
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">
              Advanced — {pctSeason}
            </h4>
            {ADVANCED_ROWS.filter(r => !["darko"].includes(r.key as string)).map((row) => (
              <PercentileRowItem
                key={row.key}
                row={row}
                pctA={getPct(percA, row.key as string)}
                pctB={getPct(percB, row.key as string)}
                statsA={pctStatsA}
                statsB={pctStatsB}
              />
            ))}
          </div>

          <p className="text-center text-xs text-gray-400 dark:text-gray-500">
            Percentiles computed among all players with ≥20 GP in {pctSeason}
          </p>
        </>
      )}

      {/* Career / Current Season mode */}
      {mode !== "percentile" && (
        <>
          <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 p-4">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3">
              Traditional
            </h4>
            {TRADITIONAL_ROWS.map((row) => (
              <StatRowItem key={row.key} row={row} statsA={statsA} statsB={statsB} />
            ))}
          </div>

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
        </>
      )}
    </div>
  );
}
