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
const GROUP_START_KEYS = new Set(
  STAT_GROUPS.map((group) => group.options[0]?.key).filter((key): key is string => Boolean(key))
);
const GROUP_ACCENTS: Record<string, { bg: string; border: string; text: string; activeBg: string; activeText: string }> = {
  "Core Per Game": {
    bg: "rgba(33, 72, 59, 0.09)",
    border: "rgba(33, 72, 59, 0.30)",
    text: "#21483b",
    activeBg: "rgba(33, 72, 59, 0.16)",
    activeText: "#17382d",
  },
  Scoring: {
    bg: "rgba(127, 51, 43, 0.08)",
    border: "rgba(127, 51, 43, 0.24)",
    text: "#7f332b",
    activeBg: "rgba(127, 51, 43, 0.14)",
    activeText: "#7f332b",
  },
  "Volume Totals": {
    bg: "rgba(180, 137, 61, 0.12)",
    border: "rgba(180, 137, 61, 0.32)",
    text: "#6c4b16",
    activeBg: "rgba(180, 137, 61, 0.20)",
    activeText: "#4f3810",
  },
  "Shot Profile": {
    bg: "rgba(40, 80, 55, 0.09)",
    border: "rgba(40, 80, 55, 0.28)",
    text: "#285037",
    activeBg: "rgba(40, 80, 55, 0.17)",
    activeText: "#21483b",
  },
  Advanced: {
    bg: "rgba(53, 41, 33, 0.07)",
    border: "rgba(53, 41, 33, 0.20)",
    text: "#4a3a2d",
    activeBg: "rgba(53, 41, 33, 0.13)",
    activeText: "#201a16",
  },
  External: {
    bg: "rgba(111, 101, 90, 0.09)",
    border: "rgba(111, 101, 90, 0.24)",
    text: "#5d5147",
    activeBg: "rgba(111, 101, 90, 0.16)",
    activeText: "#2b2521",
  },
};

// Stats eligible for career aggregation (rate stats that average meaningfully across seasons)
const CAREER_STAT_KEYS = new Set([
  "pts_pg", "reb_pg", "ast_pg", "stl_pg", "blk_pg",
  "bpm", "ws", "vorp", "per", "ts_pct",
]);

const CAREER_OPTIONS = ALL_OPTIONS.filter((o) => CAREER_STAT_KEYS.has(o.key));

function getStatMeta(key: string) {
  return ALL_OPTIONS.find((o) => o.key === key) ?? { key, label: key, fmt: "1f", tooltip: "" };
}

function getGroupAccent(label: string) {
  return GROUP_ACCENTS[label] ?? GROUP_ACCENTS["Core Per Game"];
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

const MODE_META: Record<BoardMode, { label: string; eyebrow: string; description: string }> = {
  players: {
    label: "Player Stats",
    eyebrow: "League-wide leaderboard",
    description: "Sort across the full metric library, stack filters, and scan the current season from one analyst-friendly table.",
  },
  onoff: {
    label: "On/Off Impact",
    eyebrow: "Play-by-play impact board",
    description: "Track which players move team net rating most strongly when they are on versus off the floor.",
  },
  lineups: {
    label: "Top Lineups",
    eyebrow: "Five-man performance board",
    description: "Review the best-performing lineup groups by minutes, possessions, and possession-based efficiency.",
  },
  career: {
    label: "Career Leaders",
    eyebrow: "Multi-season context",
    description: "Compare long-run career production across the seasons currently persisted in the database.",
  },
};

function summarizeScope(parts: Array<string | null | undefined | false>): string {
  return parts.filter(Boolean).join(" • ");
}

function parseFiltersParam(raw: string | null): FilterCondition[] {
  if (!raw) return [];
  return raw
    .split(";")
    .map((part) => {
      const [stat, operator, value] = part.split(",");
      const parsedValue = Number(value);
      if (!stat || (operator !== "gte" && operator !== "lte") || Number.isNaN(parsedValue)) {
        return null;
      }
      return { stat, operator, value: parsedValue } as FilterCondition;
    })
    .filter((item): item is FilterCondition => item !== null)
    .slice(0, MAX_FILTERS);
}

function serializeFiltersParam(filters: FilterCondition[]): string {
  return filters.map((filter) => `${filter.stat},${filter.operator},${filter.value}`).join(";");
}

function parsePositiveIntParam(raw: string | null, fallback: number): number {
  const parsed = Number(raw);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}

// ─── Inner component (uses useSearchParams) ───────────────────────────────────

function PlayerStatsPageContent() {
  const uid = useId();
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialSeasonParam = searchParams.get("season");

  // Initialize state from URL params
  const [mode, setMode] = useState<BoardMode>((searchParams.get("mode") as BoardMode) || "players");
  const [stat, setStat] = useState(searchParams.get("stat") || "pts_pg");
  const [careerStat, setCareerStat] = useState(searchParams.get("careerStat") || "pts_pg");
  const [season, setSeason] = useState(initialSeasonParam || "");
  const [seasonType, setSeasonType] = useState<"Regular Season" | "Playoffs">(
    (searchParams.get("seasonType") as "Regular Season" | "Playoffs") || "Regular Season"
  );
  const [teamFilter, setTeamFilter] = useState(searchParams.get("team") || "");
  const [seasons, setSeasons] = useState<string[]>([]);
  const [teams, setTeams] = useState<string[]>([]);
  const [onOffMinMinutes, setOnOffMinMinutes] = useState(parsePositiveIntParam(searchParams.get("onMin"), 200));
  const [lineupMinMinutes, setLineupMinMinutes] = useState(parsePositiveIntParam(searchParams.get("lineupMin"), 15));
  const [isSyncingSeason, setIsSyncingSeason] = useState(false);
  const [seasonSyncMessage, setSeasonSyncMessage] = useState<string | null>(null);

  // Filter state — up to MAX_FILTERS conditions
  const [filters, setFilters] = useState<FilterCondition[]>(() => parseFiltersParam(searchParams.get("filters")));
  const [showFilterPanel, setShowFilterPanel] = useState(searchParams.get("panel") === "1");

  // New-filter form state
  const [newStat, setNewStat] = useState("ts_pct");
  const [newOp, setNewOp] = useState<Operator>("gte");
  const [newVal, setNewVal] = useState("");

  useEffect(() => {
    getAvailableSeasons()
      .then((s) => {
        setSeasons(s);
        if (s.length > 0 && !initialSeasonParam) setSeason(s[0]);
      })
      .catch(() => {});
  }, [initialSeasonParam]);

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
    if (filters.length > 0) params.set("filters", serializeFiltersParam(filters));
    if (showFilterPanel) params.set("panel", "1");
    if (onOffMinMinutes !== 200) params.set("onMin", String(onOffMinMinutes));
    if (lineupMinMinutes !== 15) params.set("lineupMin", String(lineupMinMinutes));
    router.replace(`?${params.toString()}`, { scroll: false });
  }, [
    mode,
    stat,
    careerStat,
    season,
    seasonType,
    teamFilter,
    filters,
    showFilterPanel,
    onOffMinMinutes,
    lineupMinMinutes,
    router,
  ]);

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
  const activeMetricGroup = GROUP_BY_STAT.get(stat) ?? STAT_GROUPS[0].label;
  const modeMeta = MODE_META[mode];

  const tableMetricGroups = STAT_GROUPS;
  const tableMetricCols = ALL_OPTIONS;
  const playerResultsCount = filteredEntries.length;
  const playerSourceCount = playersBoard.data?.entries.length ?? 0;
  const onOffCount = onOffBoard.data?.players.length ?? 0;
  const lineupCount = lineupsBoard.data?.lineups.length ?? 0;
  const careerCount = careerBoard.data?.entries.length ?? 0;

  const summaryCards =
    mode === "players"
      ? [
          { label: "Board", value: statLabel, detail: activeMetricGroup },
          { label: "Scope", value: summarizeScope([season || "Loading season", seasonType, teamFilter || "All Teams"]), detail: `${playerSourceCount} loaded` },
          { label: "Results", value: `${playerResultsCount}`, detail: filters.length > 0 ? `from top ${playerSourceCount}` : "ranked rows" },
          { label: "Filters", value: filters.length ? `${filters.length} active` : "None", detail: filters.length ? "All conditions must match" : "Optional narrow-downs" },
        ]
      : mode === "career"
      ? [
          { label: "Board", value: careerStatMeta.label, detail: "Career average sort" },
          { label: "Coverage", value: `${careerCount}`, detail: "ranked careers" },
          { label: "Season rule", value: "15+ GP", detail: "per included season" },
          { label: "Lens", value: "All saved seasons", detail: "database-backed only" },
        ]
      : mode === "onoff"
      ? [
          { label: "Season", value: season || "Loading season", detail: `${onOffCount} player rows` },
          { label: "Threshold", value: `${onOffMinMinutes} min`, detail: "minimum on-court sample" },
          { label: "Sort", value: "On/Off Net", detail: "highest impact first" },
          { label: "Source", value: "Local PBP", detail: "derived possession data" },
        ]
      : [
          { label: "Season", value: season || "Loading season", detail: `${lineupCount} lineups` },
          { label: "Threshold", value: `${lineupMinMinutes} min`, detail: "minimum lineup sample" },
          { label: "Sort", value: "Net Rating", detail: "possession-based ranks" },
          { label: "Source", value: "Local PBP", detail: "five-man stint data" },
        ];

  const spotlightCards =
    mode === "players"
      ? filteredEntries.slice(0, 3).map((entry, index) => ({
          key: `player-${entry.player_id}`,
          label: index === 0 ? `Top ${statLabel}` : `Rank ${index + 1}`,
          title: entry.player_name,
          value: formatStat(entry.stat_value, getStatMeta(stat).fmt),
          detail: summarizeScope([entry.team_abbreviation, `${entry.gp} GP`]),
        }))
      : mode === "career"
      ? (careerBoard.data?.entries ?? []).slice(0, 3).map((entry, index) => ({
          key: `career-${entry.player_id}`,
          label: index === 0 ? `Career leader` : `Rank ${index + 1}`,
          title: entry.player_name,
          value: formatStat(entry.stat_value, careerStatMeta.fmt),
          detail: `${entry.seasons_played} seasons • ${entry.career_gp} GP`,
        }))
      : mode === "onoff"
      ? (onOffBoard.data?.players ?? []).slice(0, 3).map((entry, index) => ({
          key: `onoff-${entry.player_id}`,
          label: index === 0 ? "Best on/off swing" : `Rank ${index + 1}`,
          title: entry.player_name,
          value: formatSigned(entry.on_off_net),
          detail: `${entry.on_minutes?.toFixed(1) ?? "-"} on-court min`,
        }))
      : (lineupsBoard.data?.lineups ?? []).slice(0, 3).map((lineup, index) => ({
          key: `lineup-${lineup.lineup_key}`,
          label: index === 0 ? "Best lineup" : `Rank ${index + 1}`,
          title: lineup.player_names.join(" • "),
          value: formatSigned(lineup.net_rating),
          detail: `${lineup.minutes?.toFixed(1) ?? "-"} min • ${lineup.possessions ?? 0} poss`,
        }));
  const stickyRankClass = "sticky left-0 z-10 bg-white dark:bg-gray-800";
  const stickyPlayerClass = "sticky left-10 z-10 bg-white dark:bg-gray-800";
  const rowPaddingClass = "py-3";
  const loadingMessage =
    mode === "players"
      ? "Loading leaderboard rows and filter context..."
      : mode === "career"
      ? "Loading saved career leaderboard..."
      : mode === "onoff"
      ? "Loading play-by-play impact board..."
      : "Loading lineup performance board...";

  return (
    <div className="relative left-1/2 w-screen -translate-x-1/2 px-4 sm:px-6 lg:px-8">
      <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[420px] bg-[linear-gradient(180deg,rgba(255,250,242,0.92),rgba(244,236,222,0)),linear-gradient(90deg,rgba(180,137,61,0.13)_1px,transparent_1px),linear-gradient(180deg,rgba(53,41,33,0.07)_1px,transparent_1px)] bg-[size:100%_100%,84px_84px,84px_84px]" />

      <div className="mb-4">
        <Link
          href="/"
          className="inline-flex items-center gap-1 rounded-md border border-[rgba(53,41,33,0.14)] bg-[rgba(255,251,246,0.86)] px-3 py-1.5 text-sm font-medium text-[var(--muted)] shadow-sm hover:border-[rgba(33,72,59,0.32)] hover:text-[var(--accent)]"
        >
          ← Back to Home
        </Link>
      </div>

      <section className="mb-4 overflow-hidden rounded-lg border border-[rgba(53,41,33,0.16)] bg-[rgba(255,248,237,0.94)] shadow-[0_20px_62px_rgba(46,32,19,0.13)] backdrop-blur">
        <div className="relative border-b border-[rgba(53,41,33,0.14)] bg-[linear-gradient(115deg,rgba(252,244,230,0.98),rgba(234,219,183,0.82)_52%,rgba(216,228,221,0.72))] px-4 py-4 sm:px-5">
          <div className="pointer-events-none absolute inset-y-0 right-0 hidden w-80 opacity-60 lg:block">
            <div className="absolute right-8 top-1/2 h-40 w-40 -translate-y-1/2 rounded-full border border-[rgba(33,72,59,0.24)]" />
            <div className="absolute right-0 top-1/2 h-px w-80 -translate-y-1/2 bg-[rgba(33,72,59,0.18)]" />
            <div className="absolute right-24 top-1/2 h-24 w-28 -translate-y-1/2 border border-[rgba(33,72,59,0.18)]" />
          </div>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--accent)]">
                {modeMeta.eyebrow}
              </p>
              <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
                <h1 className="bip-display text-4xl font-bold tracking-tight text-[var(--foreground)] sm:text-5xl">
                  {modeMeta.label}
                </h1>
                {mode === "players" && (
                  <span className="rounded-md border border-[rgba(33,72,59,0.16)] bg-[rgba(255,251,246,0.76)] px-2 py-1 font-mono text-sm font-semibold text-[var(--accent)]">
                    sorted by {statLabel}
                  </span>
                )}
              </div>
              <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-[var(--muted)]">
                {modeMeta.description}
              </p>
            </div>

            <div className="relative z-10 grid grid-cols-3 overflow-hidden rounded-md border border-[rgba(53,41,33,0.14)] bg-[rgba(255,251,246,0.88)] text-sm shadow-sm">
              {summaryCards.slice(1, 4).map((card) => (
                <div key={card.label} className="min-w-28 border-l border-[rgba(53,41,33,0.12)] px-3 py-2 first:border-l-0">
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted)]">
                    {card.label}
                  </p>
                  <p className="mt-1 whitespace-nowrap font-bold text-[var(--foreground)]">
                    {card.value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Mode tabs ── */}
        <div className="flex flex-wrap gap-1 bg-[rgba(43,37,33,0.92)] px-3 py-2">
          {(["players", "onoff", "lineups", "career"] as BoardMode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                mode === m
                  ? "bg-[var(--signal-soft)] text-[var(--signal-ink)] shadow-sm"
                  : "border border-[rgba(234,219,183,0.24)] bg-[rgba(234,219,183,0.12)] text-[#eadbb7] hover:border-[rgba(234,219,183,0.42)] hover:bg-[rgba(234,219,183,0.20)] hover:text-[#fff7ec]"
              }`}
            >
              {m === "players" ? "Player Stats" : m === "onoff" ? "On/Off Impact" : m === "lineups" ? "Top Lineups" : "Career Leaders"}
            </button>
          ))}
        </div>
      </section>

      {/* ── Controls row ── */}
      <div className="sticky top-[73px] z-30 mb-4 rounded-lg border border-[rgba(53,41,33,0.14)] bg-[rgba(255,251,246,0.94)] p-3 shadow-[0_14px_42px_rgba(46,32,19,0.10)] backdrop-blur">
        <div className="flex flex-wrap items-end gap-3">
          {mode === "players" && (
            <label className="space-y-1.5">
              <span className="block text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--surface-ink)]">
                Primary Sort
              </span>
              <select
                value={stat}
                onChange={(e) => setStat(e.target.value)}
                className="rounded-md border border-[rgba(53,41,33,0.16)] bg-white px-3 py-2 text-sm font-medium text-[var(--foreground)] shadow-sm focus:outline-none focus:ring-2 focus:ring-[rgba(33,72,59,0.22)]"
              >
                {STAT_GROUPS.map((group) => (
                  <optgroup key={group.label} label={group.label}>
                    {group.options.map((opt) => (
                      <option key={opt.key} value={opt.key}>{opt.label}</option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </label>
          )}

          {mode === "career" && (
            <label className="space-y-1.5">
              <span className="block text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--surface-ink)]">
                Career Sort
              </span>
              <select
                value={careerStat}
                onChange={(e) => setCareerStat(e.target.value)}
                className="rounded-md border border-[rgba(53,41,33,0.16)] bg-white px-3 py-2 text-sm font-medium text-[var(--foreground)] shadow-sm focus:outline-none focus:ring-2 focus:ring-[rgba(33,72,59,0.22)]"
              >
                {CAREER_OPTIONS.map((opt) => (
                  <option key={opt.key} value={opt.key}>{opt.label}</option>
                ))}
              </select>
            </label>
          )}

          {mode !== "career" && (
            <label className="space-y-1.5">
              <span className="block text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--surface-ink)]">
                Season
              </span>
              <select
                value={season}
                onChange={(e) => { setSeason(e.target.value); setTeamFilter(""); }}
                disabled={seasons.length === 0}
                className="rounded-md border border-[rgba(53,41,33,0.16)] bg-white px-3 py-2 text-sm font-medium text-[var(--foreground)] shadow-sm focus:outline-none focus:ring-2 focus:ring-[rgba(33,72,59,0.22)] disabled:opacity-50"
              >
                {seasons.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </label>
          )}

          {mode === "players" && (
            <div className="space-y-1.5">
              <span className="block text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--surface-ink)]">
                Season Type
              </span>
              <div className="flex overflow-hidden rounded-md border border-[rgba(53,41,33,0.16)] text-sm shadow-sm">
                {(["Regular Season", "Playoffs"] as const).map((type) => (
                  <button
                    key={type}
                    onClick={() => setSeasonType(type)}
                    className={`px-4 py-2 transition-colors ${
                      seasonType === type
                        ? "bg-[var(--accent)] text-white"
                        : "bg-white text-[var(--muted)] hover:bg-[#fff7ec] hover:text-[var(--foreground)]"
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>
          )}

          {mode === "players" && teams.length > 0 && (
            <label className="space-y-1.5">
              <span className="block text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--surface-ink)]">
                Team
              </span>
              <select
                value={teamFilter}
                onChange={(e) => setTeamFilter(e.target.value)}
                className="rounded-md border border-[rgba(53,41,33,0.16)] bg-white px-3 py-2 text-sm font-medium text-[var(--foreground)] shadow-sm focus:outline-none focus:ring-2 focus:ring-[rgba(33,72,59,0.22)]"
              >
                <option value="">All Teams</option>
                {teams.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </label>
          )}

          {mode === "onoff" && (
            <label className="space-y-1.5">
              <span className="block text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--surface-ink)]">
                Min On-Court Minutes
              </span>
              <input
                type="number" min={0} step={10} value={onOffMinMinutes}
                onChange={(e) => setOnOffMinMinutes(Number(e.target.value) || 0)}
                className="w-32 rounded-md border border-[rgba(53,41,33,0.16)] bg-white px-3 py-2 text-sm font-medium text-[var(--foreground)] shadow-sm focus:outline-none focus:ring-2 focus:ring-[rgba(33,72,59,0.22)]"
              />
            </label>
          )}

          {mode === "lineups" && (
            <label className="space-y-1.5">
              <span className="block text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--surface-ink)]">
                Min Lineup Minutes
              </span>
              <input
                type="number" min={0} step={5} value={lineupMinMinutes}
                onChange={(e) => setLineupMinMinutes(Number(e.target.value) || 0)}
                className="w-32 rounded-md border border-[rgba(53,41,33,0.16)] bg-white px-3 py-2 text-sm font-medium text-[var(--foreground)] shadow-sm focus:outline-none focus:ring-2 focus:ring-[rgba(33,72,59,0.22)]"
              />
            </label>
          )}

          {mode !== "players" && mode !== "career" && season && (
            <button
              onClick={handleSeasonSync}
              disabled={isSyncingSeason}
              className="rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-strong)] disabled:cursor-wait disabled:opacity-60"
            >
              {isSyncingSeason ? "Syncing Season PBP..." : "Sync Season PBP"}
            </button>
          )}

          {mode === "players" && (
            <button
              onClick={() => setShowFilterPanel((v) => !v)}
              className={`relative flex items-center gap-1.5 rounded-md border px-3 py-2 text-sm shadow-sm transition-colors ${
                showFilterPanel || filters.length > 0
                  ? "border-[rgba(33,72,59,0.34)] bg-[var(--accent-soft)] text-[var(--accent)]"
                  : "border-[rgba(53,41,33,0.16)] bg-white text-[var(--muted)] hover:border-[rgba(33,72,59,0.28)] hover:text-[var(--accent)]"
              }`}
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                <path fillRule="evenodd" d="M2.628 1.601C5.028 1.206 7.49 1 10 1s4.973.206 7.372.601a.75.75 0 0 1 .628.74v2.288a2.25 2.25 0 0 1-.659 1.59l-4.682 4.683a2.25 2.25 0 0 0-.659 1.59v3.037c0 .684-.31 1.33-.844 1.757l-1.937 1.55A.75.75 0 0 1 8 18.25v-5.757a2.25 2.25 0 0 0-.659-1.591L2.659 6.22A2.25 2.25 0 0 1 2 4.629V2.34a.75.75 0 0 1 .628-.74Z" clipRule="evenodd" />
              </svg>
              Filters
              {filters.length > 0 && (
                <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-[var(--accent)] text-[10px] font-bold text-white">
                  {filters.length}
                </span>
              )}
            </button>
          )}
        </div>

      </div>

      {/* ── Filter panel ── */}
      {mode === "players" && showFilterPanel && (
        <div className="mb-4 space-y-3 rounded-lg border border-[rgba(33,72,59,0.18)] bg-[rgba(216,228,221,0.72)] p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-wider text-[var(--accent)]">
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
                    className="flex items-center gap-1.5 rounded-md border border-[rgba(33,72,59,0.20)] bg-white px-3 py-1 text-sm font-medium text-[var(--accent)] shadow-sm"
                  >
                    <span className="font-medium">{meta.label}</span>
                    <span className="text-[var(--accent)]">{f.operator === "gte" ? "≥" : "≤"}</span>
                    <span className="tabular-nums">
                      {isPct(f.stat) ? `${displayVal.toFixed(1)}%` : displayVal.toFixed(1)}
                    </span>
                    <button
                      onClick={() => removeFilter(i)}
                      className="ml-0.5 text-[var(--accent)] transition-colors hover:text-red-500"
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
                className="rounded-md border border-[rgba(33,72,59,0.18)] bg-white px-2 py-1.5 text-sm font-medium text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[rgba(33,72,59,0.22)]"
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

              <div className="flex overflow-hidden rounded-md border border-[rgba(33,72,59,0.18)] text-sm">
                {(["gte", "lte"] as Operator[]).map((op) => (
                  <button
                    key={op}
                    onClick={() => setNewOp(op)}
                    className={`px-3 py-1.5 transition-colors ${
                      newOp === op
                        ? "bg-[var(--accent)] text-white"
                        : "bg-white text-[var(--muted)] hover:bg-[#fff7ec]"
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
                className="w-32 rounded-md border border-[rgba(33,72,59,0.18)] bg-white px-2 py-1.5 text-sm font-medium text-[var(--foreground)] focus:outline-none focus:ring-2 focus:ring-[rgba(33,72,59,0.22)]"
              />

              <button
                onClick={addFilter}
                disabled={!newVal || isNaN(parseFloat(newVal))}
                className="rounded-md bg-[var(--accent)] px-4 py-1.5 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-40"
              >
                Add
              </button>

              <span className="text-xs font-medium text-[var(--accent)]">
                {MAX_FILTERS - filters.length} slot{MAX_FILTERS - filters.length !== 1 ? "s" : ""} remaining
              </span>
            </div>
          )}
        </div>
      )}

      {seasonSyncMessage && (
        <div className="mb-4 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm dark:border-slate-700 dark:bg-gray-800 dark:text-gray-300">
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
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white/85 px-4 py-2 text-sm text-slate-600 shadow-sm dark:border-slate-700 dark:bg-slate-950/80 dark:text-slate-300">
          <span>
            Sorted by <span className="font-semibold text-slate-950 dark:text-white">{statLabel}</span>
          </span>
          <span className="font-mono text-xs uppercase tracking-[0.16em]" style={{ color: getGroupAccent(activeMetricGroup).text }}>
            {activeMetricGroup}
          </span>
        </div>
      )}

      {isLoading && (
        <div className="mb-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600 shadow-sm dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-300">
          {loadingMessage}
        </div>
      )}

      {!isLoading && spotlightCards.length > 0 && (
        <div className="mb-4 overflow-hidden rounded-lg border border-[rgba(53,41,33,0.16)] bg-[linear-gradient(115deg,rgba(255,248,237,0.98),rgba(234,219,183,0.72))] text-[var(--foreground)] shadow-[0_20px_55px_rgba(46,32,19,0.12)]">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[rgba(53,41,33,0.12)] px-4 py-2">
            <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--accent)]">
              Top of board
            </p>
            <p className="text-xs font-medium text-[var(--muted)]">
              {mode === "players" ? statLabel : modeMeta.label}
            </p>
          </div>
          <div className="grid divide-y divide-[rgba(53,41,33,0.12)] md:grid-cols-3 md:divide-x md:divide-y-0">
          {spotlightCards.map((card) => (
            <div
              key={card.key}
              className="px-4 py-4"
            >
              <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-[var(--muted)]">
                {card.label}
              </p>
              <p className="mt-2 line-clamp-2 text-sm font-bold text-[var(--foreground)]">
                {card.title}
              </p>
              <p className="mt-3 text-3xl font-bold tracking-tight text-[var(--accent)]">
                {card.value}
              </p>
              <p className="mt-1 text-xs font-medium text-[var(--muted)]">
                {card.detail}
              </p>
            </div>
          ))}
          </div>
        </div>
      )}

      {/* ── Table ── */}
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-[0_22px_70px_rgba(15,23,42,0.12)] dark:border-slate-700 dark:bg-gray-800">

        {/* Players mode */}
        {mode === "players" && (
          <table className="w-full min-w-[5200px]">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th rowSpan={2} className={`${stickyRankClass} text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 w-10`}>#</th>
                <th rowSpan={2} className={`${stickyPlayerClass} text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-4 py-3 min-w-60`}>Player</th>
                <th rowSpan={2} className="text-left text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-3 py-3">Team</th>
                <th rowSpan={2} className="text-right text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 px-3 py-3">GP</th>
                {tableMetricGroups.map((group) => {
                  const accent = getGroupAccent(group.label);
                  return (
                    <th
                      key={group.label}
                      colSpan={group.options.length}
                      className="border-l px-3 py-2 text-center text-[11px] font-semibold uppercase tracking-[0.18em]"
                      style={{
                        background: accent.bg,
                        borderColor: accent.border,
                        color: accent.text,
                      }}
                    >
                      {group.label}
                    </th>
                  );
                })}
                {/* Extra columns for active filter stats */}
                {filters.map((f, i) => (
                  <th
                    key={`${uid}-th-${i}`}
                    rowSpan={2}
                    title={getStatMeta(f.stat).tooltip}
                    className="text-right text-xs font-semibold uppercase tracking-wider text-amber-500 dark:text-amber-400 px-4 py-3"
                  >
                    {getStatMeta(f.stat).label}
                  </th>
                ))}
              </tr>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                {tableMetricCols.map((option) => {
                  const groupLabel = GROUP_BY_STAT.get(option.key) ?? STAT_GROUPS[0].label;
                  const accent = getGroupAccent(groupLabel);
                  return (
                    <th
                      key={option.key}
                      className={`px-2 py-2 text-right text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 ${
                        GROUP_START_KEYS.has(option.key) ? "border-l border-gray-200 dark:border-gray-700" : ""
                      }`}
                      style={{
                        background: option.key === stat ? accent.activeBg : undefined,
                        color: option.key === stat ? accent.activeText : undefined,
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => setStat(option.key)}
                        className={`group relative inline-flex w-full min-w-24 items-center justify-end gap-1 rounded-md px-2 py-1.5 text-right transition-colors hover:bg-white/70 hover:text-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[rgba(33,72,59,0.22)] ${
                          option.key === stat ? "font-bold" : ""
                        }`}
                        aria-label={`Sort player stats by ${option.label}`}
                      >
                        <span>{option.label}</span>
                        <span className={`text-[10px] ${option.key === stat ? "opacity-100" : "opacity-35"}`}>
                          ↓
                        </span>
                        <span className="pointer-events-none absolute right-0 top-full z-30 mt-2 hidden w-64 rounded-md border border-[rgba(53,41,33,0.16)] bg-[rgba(255,251,246,0.98)] px-3 py-2 text-left text-xs font-medium normal-case leading-5 tracking-normal text-[var(--surface-ink)] shadow-[0_16px_38px_rgba(46,32,19,0.16)] group-hover:block group-focus-visible:block">
                          <span className="block font-bold text-[var(--accent)]">{option.label}</span>
                          <span className="mt-1 block">{option.tooltip}</span>
                        </span>
                      </button>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {isLoading &&
                Array.from({ length: 10 }).map((_, i) => (
                  <tr key={i} className="border-b border-gray-100 dark:border-gray-700/50 animate-pulse">
                    <td className={`px-4 ${rowPaddingClass}`}><div className="h-4 w-4 bg-gray-200 dark:bg-gray-700 rounded" /></td>
                    <td className={`px-4 ${rowPaddingClass}`}><div className="h-4 w-40 bg-gray-200 dark:bg-gray-700 rounded" /></td>
                    <td className={`px-4 ${rowPaddingClass}`}><div className="h-4 w-10 bg-gray-200 dark:bg-gray-700 rounded" /></td>
                    <td className={`px-4 ${rowPaddingClass}`}><div className="h-4 w-8 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                    <td className={`px-4 ${rowPaddingClass}`}><div className="h-4 w-12 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                  </tr>
                ))}

              {!isLoading && filteredEntries.length === 0 && (
                <tr>
                  <td colSpan={4 + tableMetricCols.length + filters.length} className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">
                    <div className="mx-auto max-w-md space-y-2">
                      <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">
                        {filters.length > 0 ? "No players match the full filter stack." : "No player rows are available for this selection yet."}
                      </p>
                      <p>
                        {filters.length > 0
                          ? "Try widening a threshold, removing a filter chip, or switching to a broader metric group."
                          : "Change season, season type, or team scope to explore another slice of the leaderboard."}
                      </p>
                    </div>
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
                      <td className={`${stickyRankClass} px-4 ${rowPaddingClass} text-sm text-gray-400 dark:text-gray-500 font-mono`}>
                        <span className="inline-flex min-w-7 items-center justify-center rounded-full bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-500 dark:bg-slate-700/60 dark:text-slate-300">
                          {filters.length > 0 ? displayIdx + 1 : entry.rank}
                        </span>
                      </td>
                      <td className={`${stickyPlayerClass} px-4 ${rowPaddingClass}`}>
                        <Link href={`/players/${entry.player_id}`} className="flex items-center gap-3 group">
                          <div className="relative w-8 h-8 rounded-full overflow-hidden bg-gray-100 dark:bg-gray-700 shrink-0">
                            {entry.headshot_url ? (
                              <Image
                                src={entry.headshot_url}
                                alt={entry.player_name}
                                fill
                                sizes="32px"
                                className="object-cover object-top"
                                onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                              />
                            ) : null}
                          </div>
                          <div className="min-w-0">
                            <span className="block truncate font-medium text-gray-900 transition-colors group-hover:text-teal-700 dark:text-gray-100 dark:group-hover:text-teal-300">
                              {entry.player_name}
                            </span>
                          </div>
                        </Link>
                      </td>
                      <td className={`px-3 ${rowPaddingClass} text-sm text-gray-500 dark:text-gray-400`}>
                        {entry.team_abbreviation}
                      </td>
                      <td className={`px-3 ${rowPaddingClass} text-sm text-gray-500 dark:text-gray-400 text-right`}>
                        {entry.gp}
                      </td>
                      {tableMetricCols.map((option) => {
                        const v = option.key === stat ? entry.stat_value : getEntryMetricValue(entry, option.key);
                        const accent = getGroupAccent(GROUP_BY_STAT.get(option.key) ?? STAT_GROUPS[0].label);
                        return (
                          <td
                            key={option.key}
                            className={`px-3 ${rowPaddingClass} text-right text-sm tabular-nums ${
                              GROUP_START_KEYS.has(option.key) ? "border-l border-gray-100 dark:border-gray-700/70" : ""
                            } ${
                              option.key === stat
                                ? "font-semibold"
                                : "text-gray-900 dark:text-gray-100"
                            }`}
                            style={{
                              background: option.key === stat ? accent.activeBg : undefined,
                              color: option.key === stat ? accent.activeText : undefined,
                            }}
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
                            className={`px-4 ${rowPaddingClass} text-right text-sm tabular-nums font-medium ${
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
                  className="bg-[rgba(216,228,221,0.72)] px-4 py-3 text-right text-xs font-bold uppercase tracking-wider text-[var(--accent)]"
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
                    <div className="mx-auto max-w-md space-y-2">
                      <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">No saved career leaderboard is available yet.</p>
                      <p>Career leaders only appear once qualifying seasons are persisted in the local database.</p>
                    </div>
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
                            sizes="32px"
                            className="object-cover object-top"
                            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                          />
                        ) : null}
                      </div>
                      <span className="font-medium text-gray-900 transition-colors group-hover:text-teal-700 dark:text-gray-100 dark:group-hover:text-teal-300">
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
                  <td className="bg-[rgba(216,228,221,0.62)] px-4 py-3 text-right font-bold tabular-nums text-[var(--accent-strong)]">
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
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-teal-700 dark:text-teal-300">On/Off</th>
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
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">
                    <div className="mx-auto max-w-md space-y-2">
                      <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">No on/off rows are ready for this season.</p>
                      <p>Local play-by-play coverage may still be catching up. Run the season sync if you expect this board to be populated already.</p>
                    </div>
                  </td>
                </tr>
              )}
              {!isLoading && onOffBoard.data?.players.map((entry, idx) => (
                <tr key={entry.player_id} className="border-b border-gray-100 dark:border-gray-700/50 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                  <td className="px-4 py-3 text-sm text-gray-400 dark:text-gray-500 font-mono">{idx + 1}</td>
                  <td className="px-4 py-3">
                    <Link href={`/players/${entry.player_id}`} className="font-medium text-gray-900 transition-colors hover:text-teal-700 dark:text-gray-100 dark:hover:text-teal-300">
                      {entry.player_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-gray-500 dark:text-gray-400 hidden sm:table-cell tabular-nums">{entry.on_minutes?.toFixed(1) ?? "-"}</td>
                  <td className="px-4 py-3 text-right text-sm text-gray-500 dark:text-gray-400 hidden sm:table-cell tabular-nums">{formatSigned(entry.on_net_rating)}</td>
                  <td className="px-4 py-3 text-right text-sm text-gray-500 dark:text-gray-400 hidden sm:table-cell tabular-nums">{formatSigned(entry.off_net_rating)}</td>
                  <td className="px-4 py-3 text-right font-semibold tabular-nums text-teal-700 dark:text-teal-300">{formatSigned(entry.on_off_net)}</td>
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
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-teal-700 dark:text-teal-300">NET</th>
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
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">
                    <div className="mx-auto max-w-md space-y-2">
                      <p className="text-sm font-semibold text-gray-700 dark:text-gray-200">No lineup rows are ready for this season.</p>
                      <p>Lineup ratings depend on the local play-by-play pipeline and the current minimum-minute threshold.</p>
                    </div>
                  </td>
                </tr>
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
                  <td className="px-4 py-3 text-right font-semibold tabular-nums text-teal-700 dark:text-teal-300">{formatSigned(lineup.net_rating)}</td>
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
