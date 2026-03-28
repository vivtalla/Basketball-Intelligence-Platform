"use client";

import { useState, useEffect, useMemo, useId } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  useLeaderboard,
  useOnOffLeaderboard,
  useLineups,
} from "@/hooks/usePlayerStats";
import { getAvailableSeasons, syncSeasonPbp } from "@/lib/api";

// ─── Stat definitions ────────────────────────────────────────────────────────

const STAT_GROUPS = [
  {
    label: "Scoring",
    options: [
      { key: "pts_pg", label: "Points Per Game", fmt: "1f" },
      { key: "fg_pct", label: "Field Goal %", fmt: "pct" },
      { key: "fg3_pct", label: "3-Point %", fmt: "pct" },
      { key: "ft_pct", label: "Free Throw %", fmt: "pct" },
      { key: "ts_pct", label: "True Shooting %", fmt: "pct" },
      { key: "efg_pct", label: "Effective FG %", fmt: "pct" },
    ],
  },
  {
    label: "Production",
    options: [
      { key: "reb_pg", label: "Rebounds Per Game", fmt: "1f" },
      { key: "ast_pg", label: "Assists Per Game", fmt: "1f" },
      { key: "stl_pg", label: "Steals Per Game", fmt: "1f" },
      { key: "blk_pg", label: "Blocks Per Game", fmt: "1f" },
      { key: "min_pg", label: "Minutes Per Game", fmt: "1f" },
    ],
  },
  {
    label: "Shot Profile",
    options: [
      { key: "ftr", label: "Free Throw Rate", fmt: "2f" },
      { key: "par3", label: "3-Point Attempt Rate", fmt: "2f" },
      { key: "ast_tov", label: "Assist / Turnover Ratio", fmt: "2f" },
      { key: "oreb_pct", label: "Offensive Rebound %", fmt: "pct" },
    ],
  },
  {
    label: "Advanced",
    options: [
      { key: "per", label: "PER", fmt: "1f" },
      { key: "obpm", label: "OBPM", fmt: "1f" },
      { key: "dbpm", label: "DBPM", fmt: "1f" },
      { key: "bpm", label: "BPM", fmt: "1f" },
      { key: "ws", label: "Win Shares", fmt: "1f" },
      { key: "vorp", label: "VORP", fmt: "1f" },
      { key: "usg_pct", label: "Usage Rate", fmt: "pct" },
      { key: "off_rating", label: "Offensive Rating", fmt: "1f" },
      { key: "def_rating", label: "Defensive Rating", fmt: "1f" },
      { key: "net_rating", label: "Net Rating", fmt: "1f" },
      { key: "pie", label: "PIE", fmt: "pct" },
      { key: "darko", label: "DARKO", fmt: "2f" },
    ],
  },
  {
    label: "External",
    options: [
      { key: "epm", label: "EPM", fmt: "2f" },
      { key: "rapm", label: "RAPM", fmt: "2f" },
      { key: "lebron", label: "LEBRON", fmt: "2f" },
      { key: "raptor", label: "RAPTOR", fmt: "2f" },
      { key: "pipm", label: "PIPM", fmt: "2f" },
    ],
  },
];

const ALL_OPTIONS = STAT_GROUPS.flatMap((g) => g.options);

function getStatMeta(key: string) {
  return ALL_OPTIONS.find((o) => o.key === key) ?? { key, label: key, fmt: "1f" };
}

function formatStat(value: number, fmt: string): string {
  if (fmt === "pct") return `${(value * 100).toFixed(1)}%`;
  if (fmt === "2f") return value.toFixed(2);
  return value.toFixed(1);
}

function formatSigned(value: number | null): string {
  if (value == null) return "-";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}`;
}

// For pct-format stats, the stored value is 0–1 but users type 0–100.
function isPct(key: string) {
  return getStatMeta(key).fmt === "pct";
}

// Convert user-entered threshold to stored value
function toStoredValue(key: string, displayValue: number): number {
  return isPct(key) ? displayValue / 100 : displayValue;
}

// Convert stored value to display value for chips/labels
function toDisplayValue(key: string, storedValue: number): number {
  return isPct(key) ? storedValue * 100 : storedValue;
}

// ─── Filter types ─────────────────────────────────────────────────────────────

type Operator = "gte" | "lte";

interface FilterCondition {
  stat: string;
  operator: Operator;
  value: number; // stored value (pct stats = 0–1)
}

// Max 3 filter slots so we can pre-allocate hooks (React rules)
const MAX_FILTERS = 3;

// ─── Mode ────────────────────────────────────────────────────────────────────

type BoardMode = "players" | "onoff" | "lineups";

// ─── Main component ───────────────────────────────────────────────────────────

export default function LeaderboardsPage() {
  const uid = useId();

  const [mode, setMode] = useState<BoardMode>("players");
  const [stat, setStat] = useState("pts_pg");
  const [season, setSeason] = useState("");
  const [seasonType, setSeasonType] = useState<"Regular Season" | "Playoffs">("Regular Season");
  const [seasons, setSeasons] = useState<string[]>([]);
  const [onOffMinMinutes, setOnOffMinMinutes] = useState(200);
  const [lineupMinMinutes, setLineupMinMinutes] = useState(15);
  const [isSyncingSeason, setIsSyncingSeason] = useState(false);
  const [seasonSyncMessage, setSeasonSyncMessage] = useState<string | null>(null);

  // Filter state — up to MAX_FILTERS conditions
  const [filters, setFilters] = useState<FilterCondition[]>([]);
  const [showFilterPanel, setShowFilterPanel] = useState(false);

  // New-filter form state
  const [newStat, setNewStat] = useState("ts_pct");
  const [newOp, setNewOp] = useState<Operator>("gte");
  const [newVal, setNewVal] = useState("");

  useEffect(() => {
    getAvailableSeasons()
      .then((s) => {
        setSeasons(s);
        if (s.length > 0) setSeason(s[0]);
      })
      .catch(() => {});
  }, []);

  // ── Primary leaderboard — fetch larger set when filters are active
  const primaryLimit = filters.length > 0 ? 200 : 25;
  const playersBoard = useLeaderboard(stat, season, seasonType, primaryLimit);

  // ── Pre-allocated filter stat hooks (3 slots, null key = no fetch)
  const f0 = filters[0] ?? null;
  const f1 = filters[1] ?? null;
  const f2 = filters[2] ?? null;

  const fData0 = useLeaderboard(f0?.stat ?? "", season, seasonType, 200);
  const fData1 = useLeaderboard(f1?.stat ?? "", season, seasonType, 200);
  const fData2 = useLeaderboard(f2?.stat ?? "", season, seasonType, 200);

  const filterDataSources = [fData0, fData1, fData2];

  // ── On/off and lineup boards
  const onOffBoard = useOnOffLeaderboard(mode === "onoff" ? season : null, onOffMinMinutes, 25);
  const lineupsBoard = useLineups(mode === "lineups" ? season : null, undefined, lineupMinMinutes, 25);

  // ── Build per-player stat lookup from filter fetches
  // playerFilterValues[playerId][stat] = value
  const playerFilterValues = useMemo(() => {
    const map = new Map<number, Record<string, number>>();
    filters.forEach((f, i) => {
      const data = filterDataSources[i]?.data;
      if (!data) return;
      for (const entry of data.entries) {
        if (!map.has(entry.player_id)) map.set(entry.player_id, {});
        map.get(entry.player_id)![f.stat] = entry.stat_value;
      }
    });
    return map;
  }, [filters, fData0.data, fData1.data, fData2.data]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Apply filters to primary leaderboard
  const filteredEntries = useMemo(() => {
    const entries = playersBoard.data?.entries ?? [];
    if (filters.length === 0) return entries;
    return entries.filter((entry) => {
      const vals = playerFilterValues.get(entry.player_id);
      return filters.every((f) => {
        const v = vals?.[f.stat];
        if (v == null) return false; // player not in top 200 for this stat → exclude
        return f.operator === "gte" ? v >= f.value : v <= f.value;
      });
    });
  }, [playersBoard.data, filters, playerFilterValues]);

  const isLoading =
    mode === "players"
      ? playersBoard.isLoading
      : mode === "onoff"
      ? onOffBoard.isLoading
      : lineupsBoard.isLoading;

  // ── Filter actions
  function addFilter() {
    const numVal = parseFloat(newVal);
    if (isNaN(numVal) || filters.length >= MAX_FILTERS) return;
    // Don't add duplicate stat
    if (filters.some((f) => f.stat === newStat)) return;
    setFilters((prev) => [
      ...prev,
      { stat: newStat, operator: newOp, value: toStoredValue(newStat, numVal) },
    ]);
    setNewVal("");
  }

  function removeFilter(index: number) {
    setFilters((prev) => prev.filter((_, i) => i !== index));
  }

  function clearFilters() {
    setFilters([]);
  }

  async function handleSeasonSync() {
    setIsSyncingSeason(true);
    setSeasonSyncMessage(null);
    try {
      const result = await syncSeasonPbp(season);
      await Promise.all([onOffBoard.mutate(), lineupsBoard.mutate()]);
      setSeasonSyncMessage(
        `Synced ${result.games_processed} games, updated ${result.players_updated} players, and rebuilt ${result.lineups_updated} lineups.`
      );
    } catch (error) {
      setSeasonSyncMessage(error instanceof Error ? error.message : "Season PBP sync failed.");
    } finally {
      setIsSyncingSeason(false);
    }
  }

  const statLabel = getStatMeta(stat).label;
  const statFmt = getStatMeta(stat).fmt;

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
        >
          ← Back to Home
        </Link>
      </div>

      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">Leaderboards</h1>
        <p className="text-gray-500 dark:text-gray-400">
          Compare players and lineups across box-score and play-by-play metrics.
        </p>
      </div>

      {/* ── Mode tabs ── */}
      <div className="flex flex-wrap gap-2 mb-4">
        {(["players", "onoff", "lineups"] as BoardMode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
              mode === m
                ? "bg-blue-500 text-white"
                : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300"
            }`}
          >
            {m === "players" ? "Player Stats" : m === "onoff" ? "On/Off Impact" : "Top Lineups"}
          </button>
        ))}
      </div>

      {/* ── Controls row ── */}
      <div className="flex flex-wrap items-center gap-3 mb-3">
        {mode === "players" && (
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
        )}

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

        {mode === "players" && (
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
        )}

        {mode === "onoff" && (
          <label className="text-sm text-gray-600 dark:text-gray-300">
            Min on-court minutes:
            <input
              type="number" min={0} step={10} value={onOffMinMinutes}
              onChange={(e) => setOnOffMinMinutes(Number(e.target.value) || 0)}
              className="ml-2 w-24 border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800"
            />
          </label>
        )}

        {mode === "lineups" && (
          <label className="text-sm text-gray-600 dark:text-gray-300">
            Min lineup minutes:
            <input
              type="number" min={0} step={5} value={lineupMinMinutes}
              onChange={(e) => setLineupMinMinutes(Number(e.target.value) || 0)}
              className="ml-2 w-24 border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800"
            />
          </label>
        )}

        {mode !== "players" && season && (
          <button
            onClick={handleSeasonSync}
            disabled={isSyncingSeason}
            className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-wait disabled:opacity-60"
          >
            {isSyncingSeason ? "Syncing Season PBP..." : "Sync Season PBP"}
          </button>
        )}

        {/* Filter toggle — only in players mode */}
        {mode === "players" && (
          <button
            onClick={() => setShowFilterPanel((v) => !v)}
            className={`relative flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm transition-colors ${
              showFilterPanel || filters.length > 0
                ? "border-blue-400 bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-300"
                : "border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300"
            }`}
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
              <path fillRule="evenodd" d="M2.628 1.601C5.028 1.206 7.49 1 10 1s4.973.206 7.372.601a.75.75 0 0 1 .628.74v2.288a2.25 2.25 0 0 1-.659 1.59l-4.682 4.683a2.25 2.25 0 0 0-.659 1.59v3.037c0 .684-.31 1.33-.844 1.757l-1.937 1.55A.75.75 0 0 1 8 18.25v-5.757a2.25 2.25 0 0 0-.659-1.591L2.659 6.22A2.25 2.25 0 0 1 2 4.629V2.34a.75.75 0 0 1 .628-.74Z" clipRule="evenodd" />
            </svg>
            Filters
            {filters.length > 0 && (
              <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-blue-500 text-white text-[10px] font-bold">
                {filters.length}
              </span>
            )}
          </button>
        )}
      </div>

      {/* ── Filter panel ── */}
      {mode === "players" && showFilterPanel && (
        <div className="mb-4 rounded-2xl border border-blue-200 dark:border-blue-900/60 bg-blue-50 dark:bg-blue-950/20 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-blue-600 dark:text-blue-400">
              Add Conditions — results must match ALL filters
            </p>
            {filters.length > 0 && (
              <button
                onClick={clearFilters}
                className="text-xs text-red-500 hover:text-red-600 dark:text-red-400 dark:hover:text-red-300 transition-colors"
              >
                Clear all
              </button>
            )}
          </div>

          {/* Active filter chips */}
          {filters.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {filters.map((f, i) => {
                const meta = getStatMeta(f.stat);
                const displayVal = toDisplayValue(f.stat, f.value);
                return (
                  <div
                    key={`${uid}-chip-${i}`}
                    className="flex items-center gap-1.5 rounded-full bg-blue-100 dark:bg-blue-900/50 border border-blue-300 dark:border-blue-700 px-3 py-1 text-sm text-blue-800 dark:text-blue-200"
                  >
                    <span className="font-medium">{meta.label}</span>
                    <span className="text-blue-500 dark:text-blue-400">{f.operator === "gte" ? "≥" : "≤"}</span>
                    <span className="tabular-nums">
                      {isPct(f.stat) ? `${displayVal.toFixed(1)}%` : displayVal.toFixed(1)}
                    </span>
                    <button
                      onClick={() => removeFilter(i)}
                      className="ml-0.5 text-blue-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
                    >
                      ×
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {/* Add filter form */}
          {filters.length < MAX_FILTERS && (
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={newStat}
                onChange={(e) => setNewStat(e.target.value)}
                className="text-sm border border-blue-200 dark:border-blue-800 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {STAT_GROUPS.map((group) => (
                  <optgroup key={group.label} label={group.label}>
                    {group.options
                      .filter((opt) => opt.key !== stat && !filters.some((f) => f.stat === opt.key))
                      .map((opt) => (
                        <option key={opt.key} value={opt.key}>{opt.label}</option>
                      ))}
                  </optgroup>
                ))}
              </select>

              <div className="flex rounded-lg overflow-hidden border border-blue-200 dark:border-blue-800 text-sm">
                {(["gte", "lte"] as Operator[]).map((op) => (
                  <button
                    key={op}
                    onClick={() => setNewOp(op)}
                    className={`px-3 py-1.5 transition-colors ${
                      newOp === op
                        ? "bg-blue-500 text-white"
                        : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400"
                    }`}
                  >
                    {op === "gte" ? "≥" : "≤"}
                  </button>
                ))}
              </div>

              <input
                type="number"
                placeholder={isPct(newStat) ? "e.g. 58 (%)" : "e.g. 20"}
                value={newVal}
                onChange={(e) => setNewVal(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addFilter()}
                className="w-32 text-sm border border-blue-200 dark:border-blue-800 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />

              <button
                onClick={addFilter}
                disabled={!newVal || isNaN(parseFloat(newVal))}
                className="rounded-lg bg-blue-500 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Add
              </button>

              <span className="text-xs text-blue-500 dark:text-blue-400">
                {MAX_FILTERS - filters.length} slot{MAX_FILTERS - filters.length !== 1 ? "s" : ""} remaining
              </span>
            </div>
          )}
        </div>
      )}

      {seasonSyncMessage && (
        <div className="mb-4 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
          {seasonSyncMessage}
        </div>
      )}

      {/* ── Results summary ── */}
      {mode === "players" && filters.length > 0 && !isLoading && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
          <span className="font-semibold text-gray-900 dark:text-gray-100">{filteredEntries.length}</span>
          {" "}of{" "}
          <span className="font-semibold">{playersBoard.data?.entries.length ?? 0}</span>
          {" "}players match all conditions
        </p>
      )}

      {/* ── Table ── */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">

        {/* Players mode */}
        {mode === "players" && (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 w-10">#</th>
                <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3">Player</th>
                <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 hidden sm:table-cell">Team</th>
                <th className="text-right text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 hidden sm:table-cell">GP</th>
                {/* Primary sort stat */}
                <th className="text-right text-xs font-semibold uppercase tracking-wider text-blue-500 dark:text-blue-400 px-4 py-3">
                  {statLabel}
                </th>
                {/* Extra columns for active filter stats */}
                {filters.map((f, i) => (
                  <th
                    key={`${uid}-th-${i}`}
                    className="text-right text-xs font-semibold uppercase tracking-wider text-amber-500 dark:text-amber-400 px-4 py-3 hidden md:table-cell"
                  >
                    {getStatMeta(f.stat).label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading &&
                Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i} className="border-b border-gray-100 dark:border-gray-700/50 animate-pulse">
                    <td className="px-4 py-3"><div className="h-4 w-4 bg-gray-200 dark:bg-gray-700 rounded" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-40 bg-gray-200 dark:bg-gray-700 rounded" /></td>
                    <td className="px-4 py-3 hidden sm:table-cell"><div className="h-4 w-10 bg-gray-200 dark:bg-gray-700 rounded" /></td>
                    <td className="px-4 py-3 hidden sm:table-cell"><div className="h-4 w-8 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-12 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                  </tr>
                ))}

              {!isLoading && filteredEntries.length === 0 && (
                <tr>
                  <td colSpan={5 + filters.length} className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">
                    {filters.length > 0
                      ? "No players match all filter conditions. Try relaxing a threshold."
                      : "No data available for this combination."}
                  </td>
                </tr>
              )}

              {!isLoading &&
                filteredEntries.map((entry, displayIdx) => {
                  const filterVals = playerFilterValues.get(entry.player_id);
                  return (
                    <tr
                      key={entry.player_id}
                      className="border-b border-gray-100 dark:border-gray-700/50 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
                    >
                      <td className="px-4 py-3 text-sm text-gray-400 dark:text-gray-500 font-mono">
                        {filters.length > 0 ? displayIdx + 1 : entry.rank}
                      </td>
                      <td className="px-4 py-3">
                        <Link href={`/players/${entry.player_id}`} className="flex items-center gap-3 group">
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
                      {/* Filter stat values as extra columns */}
                      {filters.map((f, i) => {
                        const v = filterVals?.[f.stat];
                        const meta = getStatMeta(f.stat);
                        const passes = v != null && (f.operator === "gte" ? v >= f.value : v <= f.value);
                        return (
                          <td
                            key={`${uid}-td-${i}`}
                            className={`px-4 py-3 text-right text-sm tabular-nums hidden md:table-cell font-medium ${
                              passes
                                ? "text-amber-600 dark:text-amber-400"
                                : "text-gray-400 dark:text-gray-500"
                            }`}
                          >
                            {v != null ? formatStat(v, meta.fmt) : "—"}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
            </tbody>
          </table>
        )}

        {/* On/Off mode */}
        {mode === "onoff" && (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 w-10">#</th>
                <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3">Player</th>
                <th className="text-right text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 hidden sm:table-cell">On Min</th>
                <th className="text-right text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 hidden sm:table-cell">On Net</th>
                <th className="text-right text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 hidden sm:table-cell">Off Net</th>
                <th className="text-right text-xs font-semibold uppercase tracking-wider text-blue-500 dark:text-blue-400 px-4 py-3">On/Off</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && Array.from({ length: 10 }).map((_, i) => (
                <tr key={i} className="border-b border-gray-100 dark:border-gray-700/50 animate-pulse">
                  <td className="px-4 py-3"><div className="h-4 w-4 bg-gray-200 dark:bg-gray-700 rounded" /></td>
                  <td className="px-4 py-3"><div className="h-4 w-40 bg-gray-200 dark:bg-gray-700 rounded" /></td>
                  <td className="px-4 py-3 hidden sm:table-cell"><div className="h-4 w-16 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                  <td className="px-4 py-3 hidden sm:table-cell"><div className="h-4 w-12 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                  <td className="px-4 py-3 hidden sm:table-cell"><div className="h-4 w-12 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                  <td className="px-4 py-3"><div className="h-4 w-12 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                </tr>
              ))}
              {!isLoading && onOffBoard.data?.players.length === 0 && (
                <tr><td colSpan={6} className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">No on/off data found. Run play-by-play import for this season.</td></tr>
              )}
              {!isLoading && onOffBoard.data?.players.map((entry, idx) => (
                <tr key={entry.player_id} className="border-b border-gray-100 dark:border-gray-700/50 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                  <td className="px-4 py-3 text-sm text-gray-400 dark:text-gray-500 font-mono">{idx + 1}</td>
                  <td className="px-4 py-3">
                    <Link href={`/players/${entry.player_id}`} className="font-medium text-gray-900 dark:text-gray-100 hover:text-blue-500 dark:hover:text-blue-400 transition-colors">
                      {entry.player_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-500 dark:text-gray-400 hidden sm:table-cell tabular-nums">{entry.on_minutes?.toFixed(1) ?? "-"}</td>
                  <td className="px-4 py-3 text-right text-sm text-gray-500 dark:text-gray-400 hidden sm:table-cell tabular-nums">{formatSigned(entry.on_net_rating)}</td>
                  <td className="px-4 py-3 text-right text-sm text-gray-500 dark:text-gray-400 hidden sm:table-cell tabular-nums">{formatSigned(entry.off_net_rating)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-blue-600 dark:text-blue-400 tabular-nums">{formatSigned(entry.on_off_net)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Lineups mode */}
        {mode === "lineups" && (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 w-10">#</th>
                <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3">Lineup</th>
                <th className="text-right text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 hidden sm:table-cell">Min</th>
                <th className="text-right text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 hidden sm:table-cell">ORTG</th>
                <th className="text-right text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 hidden sm:table-cell">DRTG</th>
                <th className="text-right text-xs font-semibold uppercase tracking-wider text-blue-500 dark:text-blue-400 px-4 py-3">NET</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && Array.from({ length: 10 }).map((_, i) => (
                <tr key={i} className="border-b border-gray-100 dark:border-gray-700/50 animate-pulse">
                  <td className="px-4 py-3"><div className="h-4 w-4 bg-gray-200 dark:bg-gray-700 rounded" /></td>
                  <td className="px-4 py-3"><div className="h-4 w-64 bg-gray-200 dark:bg-gray-700 rounded mb-1.5" /></td>
                  <td className="px-4 py-3 hidden sm:table-cell"><div className="h-4 w-10 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                  <td className="px-4 py-3 hidden sm:table-cell"><div className="h-4 w-10 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                  <td className="px-4 py-3 hidden sm:table-cell"><div className="h-4 w-10 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                  <td className="px-4 py-3"><div className="h-4 w-12 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                </tr>
              ))}
              {!isLoading && lineupsBoard.data?.lineups.length === 0 && (
                <tr><td colSpan={6} className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">No lineup data found. Run play-by-play import for this season.</td></tr>
              )}
              {!isLoading && lineupsBoard.data?.lineups.map((lineup, idx) => (
                <tr key={lineup.lineup_key} className="border-b border-gray-100 dark:border-gray-700/50 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                  <td className="px-4 py-3 text-sm text-gray-400 dark:text-gray-500 font-mono">{idx + 1}</td>
                  <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                    <div className="font-medium">{lineup.player_names.join(" • ")}</div>
                    <div className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{lineup.possessions ?? 0} possessions</div>
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-500 dark:text-gray-400 hidden sm:table-cell tabular-nums">{lineup.minutes?.toFixed(1) ?? "-"}</td>
                  <td className="px-4 py-3 text-right text-sm text-gray-500 dark:text-gray-400 hidden sm:table-cell tabular-nums">{lineup.ortg?.toFixed(1) ?? "-"}</td>
                  <td className="px-4 py-3 text-right text-sm text-gray-500 dark:text-gray-400 hidden sm:table-cell tabular-nums">{lineup.drtg?.toFixed(1) ?? "-"}</td>
                  <td className="px-4 py-3 text-right font-semibold text-blue-600 dark:text-blue-400 tabular-nums">{formatSigned(lineup.net_rating)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <p className="text-xs text-gray-400 dark:text-gray-500 mt-3 text-center">
        {mode === "players"
          ? filters.length > 0
            ? "Filtered from top 200 by primary stat. Players outside top 200 in any filter stat are excluded."
            : 'Min. 15 games played. Use "Regular Season" for current-year comparisons.'
          : mode === "onoff"
          ? "On/Off requires play-by-play import and minimum on-court minutes threshold."
          : "Lineup ratings are possession-based and filtered by minimum lineup minutes."}
      </p>
    </div>
  );
}
