"use client";

import { Suspense } from "react";
import { useState, useEffect, useMemo, useId } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import {
  useLeaderboard,
  useOnOffLeaderboard,
  useLineups,
  useCareerLeaderboard,
} from "@/hooks/usePlayerStats";
import type { LeaderboardEntry } from "@/lib/types";
import { getAvailableSeasons, syncSeasonPbp, getLeaderboardTeams } from "@/lib/api";

// ─── Stat definitions ────────────────────────────────────────────────────────

const STAT_GROUPS = [
  {
    label: "Core Per Game",
    options: [
      { key: "pts_pg", label: "Points Per Game", fmt: "1f", tooltip: "Average points scored per game." },
      { key: "reb_pg", label: "Rebounds Per Game", fmt: "1f", tooltip: "Average rebounds per game." },
      { key: "ast_pg", label: "Assists Per Game", fmt: "1f", tooltip: "Average assists per game." },
      { key: "stl_pg", label: "Steals Per Game", fmt: "1f", tooltip: "Average steals per game." },
      { key: "blk_pg", label: "Blocks Per Game", fmt: "1f", tooltip: "Average blocks per game." },
      { key: "tov_pg", label: "Turnovers Per Game", fmt: "1f", tooltip: "Average turnovers per game." },
      { key: "min_pg", label: "Minutes Per Game", fmt: "1f", tooltip: "Average minutes played per game." },
    ],
  },
  {
    label: "Scoring",
    options: [
      { key: "fg_pct", label: "Field Goal %", fmt: "pct", tooltip: "Percentage of field goal attempts made." },
      { key: "fg3_pct", label: "3-Point %", fmt: "pct", tooltip: "Percentage of three-point attempts made." },
      { key: "ft_pct", label: "Free Throw %", fmt: "pct", tooltip: "Percentage of free throw attempts made." },
      { key: "ts_pct", label: "True Shooting %", fmt: "pct", tooltip: "Shooting efficiency accounting for 2s, 3s, and free throws." },
      { key: "efg_pct", label: "Effective FG %", fmt: "pct", tooltip: "FG% adjusted for the extra value of three-pointers." },
    ],
  },
  {
    label: "Volume Totals",
    options: [
      { key: "pts", label: "Points", fmt: "int", tooltip: "Total points scored this season." },
      { key: "reb", label: "Rebounds", fmt: "int", tooltip: "Total rebounds this season." },
      { key: "ast", label: "Assists", fmt: "int", tooltip: "Total assists this season." },
      { key: "stl", label: "Steals", fmt: "int", tooltip: "Total steals this season." },
      { key: "blk", label: "Blocks", fmt: "int", tooltip: "Total blocks this season." },
      { key: "tov", label: "Turnovers", fmt: "int", tooltip: "Total turnovers this season." },
      { key: "fgm", label: "Field Goals Made", fmt: "int", tooltip: "Total field goals made this season." },
      { key: "fga", label: "Field Goals Attempted", fmt: "int", tooltip: "Total field goal attempts this season." },
      { key: "fg3m", label: "3s Made", fmt: "int", tooltip: "Total three-pointers made this season." },
      { key: "fg3a", label: "3s Attempted", fmt: "int", tooltip: "Total three-point attempts this season." },
      { key: "ftm", label: "Free Throws Made", fmt: "int", tooltip: "Total free throws made this season." },
      { key: "fta", label: "Free Throws Attempted", fmt: "int", tooltip: "Total free throw attempts this season." },
      { key: "oreb", label: "Offensive Rebounds", fmt: "int", tooltip: "Total offensive rebounds this season." },
      { key: "dreb", label: "Defensive Rebounds", fmt: "int", tooltip: "Total defensive rebounds this season." },
      { key: "pf", label: "Personal Fouls", fmt: "int", tooltip: "Total personal fouls this season." },
      { key: "min_total", label: "Total Minutes", fmt: "1f", tooltip: "Total minutes played this season." },
    ],
  },
  {
    label: "Shot Profile",
    options: [
      { key: "ftr", label: "Free Throw Rate", fmt: "2f", tooltip: "Free throw attempts per field goal attempt — measures drawing fouls." },
      { key: "par3", label: "3-Point Attempt Rate", fmt: "2f", tooltip: "Fraction of field goal attempts that are three-pointers." },
      { key: "ast_tov", label: "Assist / Turnover Ratio", fmt: "2f", tooltip: "Assists divided by turnovers — ball security relative to playmaking." },
      { key: "oreb_pct", label: "Offensive Rebound %", fmt: "pct", tooltip: "Estimated percentage of available offensive rebounds a player grabbed." },
    ],
  },
  {
    label: "Advanced",
    options: [
      { key: "per", label: "PER", fmt: "1f", tooltip: "Player Efficiency Rating — per-minute production normalized to a league average of 15." },
      { key: "obpm", label: "OBPM", fmt: "1f", tooltip: "Offensive Box Plus/Minus — offensive contribution per 100 possessions above average." },
      { key: "dbpm", label: "DBPM", fmt: "1f", tooltip: "Defensive Box Plus/Minus — defensive contribution per 100 possessions above average." },
      { key: "bpm", label: "BPM", fmt: "1f", tooltip: "Box Plus/Minus — overall impact per 100 possessions above league average." },
      { key: "ws", label: "Win Shares", fmt: "1f", tooltip: "Estimated wins contributed based on box score production." },
      { key: "vorp", label: "VORP", fmt: "1f", tooltip: "Value Over Replacement Player — BPM-based value above a replacement-level player." },
      { key: "usg_pct", label: "Usage Rate", fmt: "pct", tooltip: "Percentage of team possessions used while on the floor." },
      { key: "off_rating", label: "Offensive Rating", fmt: "1f", tooltip: "Points scored per 100 possessions while on the floor." },
      { key: "def_rating", label: "Defensive Rating", fmt: "1f", tooltip: "Points allowed per 100 possessions while on the floor." },
      { key: "net_rating", label: "Net Rating", fmt: "1f", tooltip: "Point differential per 100 possessions while on the floor." },
      { key: "pie", label: "PIE", fmt: "pct", tooltip: "Player Impact Estimate — share of game events a player positively contributes to." },
      { key: "darko", label: "DARKO", fmt: "2f", tooltip: "DARKO DPM — probabilistic daily plus/minus estimate." },
    ],
  },
  {
    label: "External",
    options: [
      { key: "epm", label: "EPM", fmt: "2f", tooltip: "Estimated Plus/Minus (Dunks & Threes) — ridge regression impact metric." },
      { key: "rapm", label: "RAPM", fmt: "2f", tooltip: "Regularized Adjusted Plus/Minus — impact estimated from possession data." },
      { key: "lebron", label: "LEBRON", fmt: "2f", tooltip: "Lakers Estimated BRON — BBall Index luck-adjusted impact metric." },
      { key: "raptor", label: "RAPTOR", fmt: "2f", tooltip: "FiveThirtyEight's Robust Algorithm (Predicts True Outcome Rankings) metric." },
      { key: "pipm", label: "PIPM", fmt: "2f", tooltip: "Player Impact Plus/Minus (Krishna) — on/off and box score blended metric." },
    ],
  },
];

const ALL_OPTIONS = STAT_GROUPS.flatMap((g) => g.options);
const GROUP_BY_STAT = new Map(ALL_OPTIONS.map((option) => [option.key, STAT_GROUPS.find((group) => group.options.some((candidate) => candidate.key === option.key))?.label ?? "Scoring"]));

// Stats eligible for career aggregation (rate stats that average meaningfully across seasons)
const CAREER_STAT_KEYS = new Set([
  "pts_pg", "reb_pg", "ast_pg", "stl_pg", "blk_pg",
  "bpm", "ws", "vorp", "per", "ts_pct",
]);

const CAREER_OPTIONS = ALL_OPTIONS.filter((o) => CAREER_STAT_KEYS.has(o.key));

function getStatMeta(key: string) {
  return ALL_OPTIONS.find((o) => o.key === key) ?? { key, label: key, fmt: "1f", tooltip: "" };
}

function formatStat(value: number, fmt: string): string {
  if (fmt === "int") return Math.round(value).toLocaleString();
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

function getEntryMetricValue(entry: LeaderboardEntry, key: string): number | null {
  const direct = entry.metric_values?.[key];
  if (direct != null) return direct;
  const fallback = (entry as unknown as Record<string, number | null | undefined>)[key];
  return fallback ?? null;
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

type BoardMode = "players" | "onoff" | "lineups" | "career";

// ─── Inner component (uses useSearchParams) ───────────────────────────────────

function PlayerStatsPageContent() {
  const uid = useId();
  const router = useRouter();
  const searchParams = useSearchParams();

  // Initialize state from URL params
  const [mode, setMode] = useState<BoardMode>((searchParams.get("mode") as BoardMode) || "players");
  const [stat, setStat] = useState(searchParams.get("stat") || "pts_pg");
  const [careerStat, setCareerStat] = useState(searchParams.get("careerStat") || "pts_pg");
  const [season, setSeason] = useState(searchParams.get("season") || "");
  const [seasonType, setSeasonType] = useState<"Regular Season" | "Playoffs">(
    (searchParams.get("seasonType") as "Regular Season" | "Playoffs") || "Regular Season"
  );
  const [teamFilter, setTeamFilter] = useState(searchParams.get("team") || "");
  const [seasons, setSeasons] = useState<string[]>([]);
  const [teams, setTeams] = useState<string[]>([]);
  const [onOffMinMinutes, setOnOffMinMinutes] = useState(200);
  const [lineupMinMinutes, setLineupMinMinutes] = useState(15);
  const [isSyncingSeason, setIsSyncingSeason] = useState(false);
  const [seasonSyncMessage, setSeasonSyncMessage] = useState<string | null>(null);
  const [activeMetricGroup, setActiveMetricGroup] = useState(STAT_GROUPS[0].label);

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
        if (s.length > 0 && !searchParams.get("season")) setSeason(s[0]);
      })
      .catch(() => {});
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch team list when season changes
  useEffect(() => {
    if (!season) return;
    getLeaderboardTeams(season)
      .then(setTeams)
      .catch(() => setTeams([]));
  }, [season]);

  // Sync URL state when key params change
  useEffect(() => {
    if (!season) return;
    const params = new URLSearchParams();
    params.set("mode", mode);
    params.set("stat", stat);
    params.set("careerStat", careerStat);
    params.set("season", season);
    params.set("seasonType", seasonType);
    if (teamFilter) params.set("team", teamFilter);
    router.replace(`?${params.toString()}`, { scroll: false });
  }, [mode, stat, careerStat, season, seasonType, teamFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const nextGroup = GROUP_BY_STAT.get(stat);
    if (nextGroup) {
      setActiveMetricGroup(nextGroup);
    }
  }, [stat]);

  // ── Primary leaderboard — fetch larger set when filters are active
  const primaryLimit = filters.length > 0 ? 200 : 25;
  const playersBoard = useLeaderboard(stat, season, seasonType, primaryLimit, teamFilter);

  // ── Pre-allocated filter stat hooks (3 slots, null key = no fetch)
  const f0 = filters[0] ?? null;
  const f1 = filters[1] ?? null;
  const f2 = filters[2] ?? null;

  const fData0 = useLeaderboard(f0?.stat ?? "", season, seasonType, 200, teamFilter);
  const fData1 = useLeaderboard(f1?.stat ?? "", season, seasonType, 200, teamFilter);
  const fData2 = useLeaderboard(f2?.stat ?? "", season, seasonType, 200, teamFilter);

  const filterDataSources = [fData0, fData1, fData2];

  // ── Career leaderboard (always allocated, null stat = no fetch)
  const careerBoard = useCareerLeaderboard(mode === "career" ? careerStat : null);

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
      : mode === "lineups"
      ? lineupsBoard.isLoading
      : careerBoard.isLoading;

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
  const careerStatMeta = getStatMeta(careerStat);
  const activeMetricOptions = STAT_GROUPS.find((group) => group.label === activeMetricGroup)?.options ?? STAT_GROUPS[0].options;

  const tableMetricCols = activeMetricOptions;

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
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">Player Stats</h1>
        <p className="text-gray-500 dark:text-gray-400">
          Scan player, on/off, lineup, and career leaderboards from one dedicated stats workspace, with the full metric library surfaced directly on the page.
        </p>
      </div>

      {/* ── Mode tabs ── */}
      <div className="flex flex-wrap gap-2 mb-4">
        {(["players", "onoff", "lineups", "career"] as BoardMode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
              mode === m
                ? "bip-toggle-active"
                : "bip-toggle"
            }`}
          >
            {m === "players" ? "Player Stats" : m === "onoff" ? "On/Off Impact" : m === "lineups" ? "Top Lineups" : "Career Leaders"}
          </button>
        ))}
      </div>

      {/* ── Controls row ── */}
      <div className="flex flex-wrap items-center gap-3 mb-3">
        {mode === "players" && (
          <select
            value={activeMetricGroup}
            onChange={(e) => {
              const nextGroup = e.target.value;
              setActiveMetricGroup(nextGroup);
              const nextOptions = STAT_GROUPS.find((group) => group.label === nextGroup)?.options ?? [];
              if (!nextOptions.some((option) => option.key === stat) && nextOptions[0]) {
                setStat(nextOptions[0].key);
              }
            }}
            className="text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {STAT_GROUPS.map((group) => (
              <option key={group.label} value={group.label}>{group.label}</option>
            ))}
          </select>
        )}

        {mode === "players" && (
          <select
            value={stat}
            onChange={(e) => setStat(e.target.value)}
            className="text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {activeMetricOptions.map((opt) => (
              <option key={opt.key} value={opt.key}>{opt.label}</option>
            ))}
          </select>
        )}

        {mode === "career" && (
          <select
            value={careerStat}
            onChange={(e) => setCareerStat(e.target.value)}
            className="text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {CAREER_OPTIONS.map((opt) => (
              <option key={opt.key} value={opt.key}>{opt.label}</option>
            ))}
          </select>
        )}

        {mode !== "career" && (
          <select
            value={season}
            onChange={(e) => { setSeason(e.target.value); setTeamFilter(""); }}
            disabled={seasons.length === 0}
            className="text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {seasons.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        )}

        {mode === "players" && (
          <div className="flex rounded-lg overflow-hidden border border-gray-200 dark:border-gray-600 text-sm">
            {(["Regular Season", "Playoffs"] as const).map((type) => (
              <button
                key={type}
                onClick={() => setSeasonType(type)}
                className={`px-4 py-2 transition-colors ${
                  seasonType === type
                    ? "bip-toggle-active"
                    : "bip-toggle"
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        )}

        {/* Team filter — only in players mode */}
        {mode === "players" && teams.length > 0 && (
          <select
            value={teamFilter}
            onChange={(e) => setTeamFilter(e.target.value)}
            className="text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Teams</option>
            {teams.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
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

        {mode !== "players" && mode !== "career" && season && (
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
                        ? "bip-toggle-active"
                        : "bip-toggle"
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

      {mode === "players" && (
        <div className="mb-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-700 dark:border-blue-900/60 dark:bg-blue-950/20 dark:text-blue-300">
          Showing <span className="font-semibold">{activeMetricGroup}</span> metrics in the table. Rankings are sorted by <span className="font-semibold">{statLabel}</span>.
        </div>
      )}

      {/* ── Table ── */}
      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-x-auto">

        {/* Players mode */}
        {mode === "players" && (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 w-10">#</th>
                <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3">Player</th>
                <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 hidden sm:table-cell">Team</th>
                <th className="text-right text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 hidden sm:table-cell">GP</th>
                {tableMetricCols.map((option) => (
                  <th
                    key={option.key}
                    title={option.tooltip}
                    className={`text-right text-xs font-semibold uppercase tracking-wider px-4 py-3 ${
                      option.key === stat
                        ? "bg-blue-50/50 text-blue-500 dark:bg-blue-950/20 dark:text-blue-400"
                        : "text-gray-400 dark:text-gray-500"
                    }`}
                  >
                    {option.label}
                  </th>
                ))}
                {/* Extra columns for active filter stats */}
                {filters.map((f, i) => (
                  <th
                    key={`${uid}-th-${i}`}
                    title={getStatMeta(f.stat).tooltip}
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
                  <td colSpan={4 + tableMetricCols.length + filters.length} className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">
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
                            {entry.headshot_url ? (
                              <Image
                                src={entry.headshot_url}
                                alt={entry.player_name}
                                fill
                                className="object-cover object-top"
                                onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                              />
                            ) : null}
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
                      {tableMetricCols.map((option) => {
                        const v = option.key === stat ? entry.stat_value : getEntryMetricValue(entry, option.key);
                        return (
                          <td
                            key={option.key}
                            className={`px-4 py-3 text-right text-sm tabular-nums ${
                              option.key === stat
                                ? "font-semibold text-blue-600 bg-blue-50/50 dark:bg-blue-950/20 dark:text-blue-400"
                                : "text-gray-900 dark:text-gray-100"
                            }`}
                          >
                            {v != null ? formatStat(v, option.fmt) : "—"}
                          </td>
                        );
                      })}
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

        {/* Career mode */}
        {mode === "career" && (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 w-10">#</th>
                <th className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3">Player</th>
                <th className="text-right text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 hidden sm:table-cell">Seasons</th>
                <th className="text-right text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 hidden sm:table-cell">GP</th>
                <th
                  title={careerStatMeta.tooltip}
                  className="text-right text-xs font-semibold uppercase tracking-wider text-blue-500 dark:text-blue-400 px-4 py-3 bg-blue-50/50 dark:bg-blue-950/20"
                >
                  {careerStatMeta.label} (Career Avg)
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading && Array.from({ length: 10 }).map((_, i) => (
                <tr key={i} className="border-b border-gray-100 dark:border-gray-700/50 animate-pulse">
                  <td className="px-4 py-3"><div className="h-4 w-4 bg-gray-200 dark:bg-gray-700 rounded" /></td>
                  <td className="px-4 py-3"><div className="h-4 w-40 bg-gray-200 dark:bg-gray-700 rounded" /></td>
                  <td className="px-4 py-3 hidden sm:table-cell"><div className="h-4 w-10 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                  <td className="px-4 py-3 hidden sm:table-cell"><div className="h-4 w-10 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                  <td className="px-4 py-3"><div className="h-4 w-12 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                </tr>
              ))}
              {!isLoading && (careerBoard.data?.entries.length ?? 0) === 0 && (
                <tr>
                  <td colSpan={5} className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">
                    No career data is available for this selection yet.
                  </td>
                </tr>
              )}
              {!isLoading && careerBoard.data?.entries.map((entry, idx) => (
                <tr
                  key={entry.player_id}
                  className="border-b border-gray-100 dark:border-gray-700/50 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
                >
                  <td className="px-4 py-3 text-sm text-gray-400 dark:text-gray-500 font-mono">{idx + 1}</td>
                  <td className="px-4 py-3">
                    <Link href={`/players/${entry.player_id}`} className="flex items-center gap-3 group">
                      <div className="relative w-8 h-8 rounded-full overflow-hidden bg-gray-100 dark:bg-gray-700 shrink-0">
                        {entry.headshot_url ? (
                          <Image
                            src={entry.headshot_url}
                            alt={entry.player_name}
                            fill
                            className="object-cover object-top"
                            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                          />
                        ) : null}
                      </div>
                      <span className="font-medium text-gray-900 dark:text-gray-100 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors">
                        {entry.player_name}
                      </span>
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-500 dark:text-gray-400 hidden sm:table-cell tabular-nums">
                    {entry.seasons_played}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-500 dark:text-gray-400 hidden sm:table-cell tabular-nums">
                    {entry.career_gp}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-blue-600 dark:text-blue-400 tabular-nums bg-blue-50/50 dark:bg-blue-950/20">
                    {formatStat(entry.stat_value, careerStatMeta.fmt)}
                  </td>
                </tr>
              ))}
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
                <tr><td colSpan={6} className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">No on/off data is available for this season yet. Local play-by-play coverage may still be catching up.</td></tr>
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
                <tr><td colSpan={6} className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">No lineup data is available for this season yet. Local play-by-play coverage may still be catching up.</td></tr>
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
          : mode === "career"
          ? "Career averages across all seasons with ≥15 games played. Includes all available seasons in the database."
          : mode === "onoff"
          ? "On/Off depends on local play-by-play-derived coverage and the minimum on-court minutes threshold."
          : "Lineup ratings are possession-based and filtered by minimum lineup minutes."}
      </p>
    </div>
  );
}

export default function PlayerStatsPage() {
  return (
    <Suspense fallback={<div className="max-w-5xl mx-auto p-8 text-gray-400">Loading player stats...</div>}>
      <PlayerStatsPageContent />
    </Suspense>
  );
}
