"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  useLeaderboard,
  useOnOffLeaderboard,
  useLineups,
} from "@/hooks/usePlayerStats";
import { getAvailableSeasons, syncSeasonPbp } from "@/lib/api";

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

type BoardMode = "players" | "onoff" | "lineups";

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

function formatSigned(value: number | null): string {
  if (value == null) return "-";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}`;
}

export default function LeaderboardsPage() {
  const [mode, setMode] = useState<BoardMode>("players");
  const [stat, setStat] = useState("pts_pg");
  const [season, setSeason] = useState("");
  const [seasonType, setSeasonType] = useState<"Regular Season" | "Playoffs">(
    "Regular Season"
  );
  const [seasons, setSeasons] = useState<string[]>([]);
  const [onOffMinMinutes, setOnOffMinMinutes] = useState(200);
  const [lineupMinMinutes, setLineupMinMinutes] = useState(15);
  const [isSyncingSeason, setIsSyncingSeason] = useState(false);
  const [seasonSyncMessage, setSeasonSyncMessage] = useState<string | null>(null);

  useEffect(() => {
    getAvailableSeasons()
      .then((s) => {
        setSeasons(s);
        if (s.length > 0) setSeason(s[0]);
      })
      .catch(() => {});
  }, []);

  const playersBoard = useLeaderboard(stat, season, seasonType);
  const onOffBoard = useOnOffLeaderboard(
    mode === "onoff" ? season : null,
    onOffMinMinutes,
    25
  );
  const lineupsBoard = useLineups(
    mode === "lineups" ? season : null,
    undefined,
    lineupMinMinutes,
    25
  );

  const statLabel = getStatLabel(stat);
  const statFmt = getStatFmt(stat);

  const isLoading =
    mode === "players"
      ? playersBoard.isLoading
      : mode === "onoff"
      ? onOffBoard.isLoading
      : lineupsBoard.isLoading;

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
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          Leaderboards
        </h1>
        <p className="text-gray-500 dark:text-gray-400">
          Compare players and lineups across box-score and play-by-play metrics.
        </p>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        <button
          onClick={() => setMode("players")}
          className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
            mode === "players"
              ? "bg-blue-500 text-white"
              : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300"
          }`}
        >
          Player Stats
        </button>
        <button
          onClick={() => setMode("onoff")}
          className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
            mode === "onoff"
              ? "bg-blue-500 text-white"
              : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300"
          }`}
        >
          On/Off Impact
        </button>
        <button
          onClick={() => setMode("lineups")}
          className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
            mode === "lineups"
              ? "bg-blue-500 text-white"
              : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300"
          }`}
        >
          Top Lineups
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3 mb-6">
        {mode === "players" && (
          <select
            value={stat}
            onChange={(e) => setStat(e.target.value)}
            className="text-sm border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {STAT_GROUPS.map((group) => (
              <optgroup key={group.label} label={group.label}>
                {group.options.map((opt) => (
                  <option key={opt.key} value={opt.key}>
                    {opt.label}
                  </option>
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
            <option key={s} value={s}>
              {s}
            </option>
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
              type="number"
              min={0}
              step={10}
              value={onOffMinMinutes}
              onChange={(e) => setOnOffMinMinutes(Number(e.target.value) || 0)}
              className="ml-2 w-24 border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800"
            />
          </label>
        )}

        {mode === "lineups" && (
          <label className="text-sm text-gray-600 dark:text-gray-300">
            Min lineup minutes:
            <input
              type="number"
              min={0}
              step={5}
              value={lineupMinMinutes}
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
      </div>

      {seasonSyncMessage ? (
        <div className="mb-6 rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 text-sm text-gray-600 dark:text-gray-300">
          {seasonSyncMessage}
        </div>
      ) : null}

      <div className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {mode === "players" && (
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
                    <td className="px-4 py-3"><div className="h-4 w-40 bg-gray-200 dark:bg-gray-700 rounded" /></td>
                    <td className="px-4 py-3 hidden sm:table-cell"><div className="h-4 w-10 bg-gray-200 dark:bg-gray-700 rounded" /></td>
                    <td className="px-4 py-3 hidden sm:table-cell"><div className="h-4 w-8 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-12 bg-gray-200 dark:bg-gray-700 rounded ml-auto" /></td>
                  </tr>
                ))}

              {!isLoading && playersBoard.data?.entries.length === 0 && (
                <tr>
                  <td colSpan={5} className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">
                    No data available for this combination.
                  </td>
                </tr>
              )}

              {!isLoading &&
                playersBoard.data?.entries.map((entry) => (
                  <tr
                    key={entry.player_id}
                    className="border-b border-gray-100 dark:border-gray-700/50 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
                  >
                    <td className="px-4 py-3 text-sm text-gray-400 dark:text-gray-500 font-mono">{entry.rank}</td>
                    <td className="px-4 py-3">
                      <Link href={`/players/${entry.player_id}`} className="flex items-center gap-3 group">
                        <div className="relative w-8 h-8 rounded-full overflow-hidden bg-gray-100 dark:bg-gray-700 shrink-0">
                          <Image src={entry.headshot_url} alt={entry.player_name} fill className="object-cover object-top" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                        </div>
                        <span className="font-medium text-gray-900 dark:text-gray-100 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors">
                          {entry.player_name}
                        </span>
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 hidden sm:table-cell">{entry.team_abbreviation}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 text-right hidden sm:table-cell">{entry.gp}</td>
                    <td className="px-4 py-3 text-right font-semibold text-blue-600 dark:text-blue-400 tabular-nums">
                      {formatStat(entry.stat_value, statFmt)}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        )}

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
              {!isLoading && onOffBoard.data?.players.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">
                    No on/off data found. Run play-by-play import for this season.
                  </td>
                </tr>
              )}

              {!isLoading &&
                onOffBoard.data?.players.map((entry, idx) => (
                  <tr
                    key={entry.player_id}
                    className="border-b border-gray-100 dark:border-gray-700/50 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
                  >
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
              {!isLoading && lineupsBoard.data?.lineups.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-400 dark:text-gray-500 text-sm">
                    No lineup data found. Run play-by-play import for this season.
                  </td>
                </tr>
              )}

              {!isLoading &&
                lineupsBoard.data?.lineups.map((lineup, idx) => (
                  <tr
                    key={lineup.lineup_key}
                    className="border-b border-gray-100 dark:border-gray-700/50 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors"
                  >
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
          ? 'Min. 15 games played. Use "Regular Season" for current-year comparisons.'
          : mode === "onoff"
          ? "On/Off requires play-by-play import and minimum on-court minutes threshold."
          : "Lineup ratings are possession-based and filtered by minimum lineup minutes."}
      </p>
    </div>
  );
}
