"use client";

import { useState, useEffect } from "react";
import { useLineupLeaderboard } from "@/hooks/usePlayerStats";
import { getAvailableSeasons, getTeams, postLineupBuilder } from "@/lib/api";
import type { TeamSummary, LineupBuilderResult } from "@/lib/types";
import LineupLeaderboardTable from "@/components/lineups/LineupLeaderboardTable";
import LineupScatterPanel from "@/components/lineups/LineupScatterPanel";
import LineupBuilderPanel from "@/components/lineups/LineupBuilderPanel";
import LineupBuilderResults from "@/components/lineups/LineupBuilderResults";
import LineupMethodologyDrawer from "@/components/lineups/LineupMethodologyDrawer";

type Tab = "leaderboard" | "builder";
type SortKey = "net_rating" | "ortg" | "drtg" | "plus_minus" | "possessions" | "minutes" | "shrunk_net_rating" | "net_vs_baseline";
type SeasonType = "Regular Season" | "Playoffs";

const MIN_POSS_OPTIONS = [50, 100, 200, 500];

export default function LineupsPage() {
  const [tab, setTab] = useState<Tab>("leaderboard");
  const [season, setSeason] = useState("2024-25");
  const [seasonType, setSeasonType] = useState<SeasonType>("Regular Season");
  const [teamId, setTeamId] = useState<number | undefined>(undefined);
  const [minPossessions, setMinPossessions] = useState(100);
  const [sortBy, setSortBy] = useState<SortKey>("net_rating");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [showScatter, setShowScatter] = useState(true);

  const [seasons, setSeasons] = useState<string[]>([]);
  const [teams, setTeams] = useState<TeamSummary[]>([]);

  const [builderResult, setBuilderResult] = useState<LineupBuilderResult | null>(null);
  const [builderLoading, setBuilderLoading] = useState(false);
  const [builderError, setBuilderError] = useState<string | null>(null);

  useEffect(() => {
    getAvailableSeasons().then((s) => {
      setSeasons(s);
      setSeason((prev) => (s.length > 0 && !s.includes(prev) ? s[0] : prev));
    }).catch(() => {});
    getTeams().then(setTeams).catch(() => {});
  }, []);

  const { data: leaderboard, isLoading: lbLoading } = useLineupLeaderboard(
    season,
    seasonType,
    teamId,
    minPossessions,
    sortBy,
    sortDir,
    100
  );

  function handleSort(key: SortKey) {
    if (key === sortBy) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(key);
      setSortDir("desc");
    }
  }

  async function handleBuilderSubmit(playerIds: number[]) {
    setBuilderLoading(true);
    setBuilderError(null);
    setBuilderResult(null);
    try {
      const result = await postLineupBuilder({ player_ids: playerIds, season, season_type: seasonType });
      setBuilderResult(result);
    } catch {
      setBuilderError("Failed to query lineup data. Please try again.");
    } finally {
      setBuilderLoading(false);
    }
  }

  const tabClass = (t: Tab) =>
    `px-4 py-2 text-sm font-semibold transition-colors rounded-t-lg border-b-2 ${
      tab === t
        ? "border-teal-500 text-teal-600 dark:text-teal-400"
        : "border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
    }`;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Lineup Lab</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          League-wide 5-man lineup leaderboard and interactive What-If Studio.
        </p>
      </div>

      {/* Global filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={season}
          onChange={(e) => setSeason(e.target.value)}
          className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-800 dark:text-gray-200"
        >
          {seasons.length === 0 && <option value="2024-25">2024-25</option>}
          {seasons.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>

        <div className="flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden text-sm">
          {(["Regular Season", "Playoffs"] as SeasonType[]).map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => setSeasonType(st)}
              className={`px-3 py-1.5 transition-colors ${
                seasonType === st
                  ? "bg-teal-600 text-white"
                  : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
              }`}
            >
              {st === "Regular Season" ? "Regular" : "Playoffs"}
            </button>
          ))}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700 flex gap-1">
        <button type="button" onClick={() => setTab("leaderboard")} className={tabClass("leaderboard")}>
          Leaderboard
        </button>
        <button type="button" onClick={() => setTab("builder")} className={tabClass("builder")}>
          What-If Studio
        </button>
      </div>

      {tab === "leaderboard" && (
        <div className="space-y-4">
          {/* Leaderboard filters */}
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={teamId ?? ""}
              onChange={(e) => setTeamId(e.target.value ? Number(e.target.value) : undefined)}
              className="rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-1.5 text-sm text-gray-800 dark:text-gray-200"
            >
              <option value="">All Teams</option>
              {teams.map((t) => (
                <option key={t.team_id} value={t.team_id}>{t.abbreviation} — {t.name}</option>
              ))}
            </select>

            <div className="flex items-center gap-1 rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden text-xs">
              {MIN_POSS_OPTIONS.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setMinPossessions(p)}
                  className={`px-3 py-1.5 transition-colors ${
                    minPossessions === p
                      ? "bg-teal-600 text-white font-semibold"
                      : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                  }`}
                >
                  {p}+ poss
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => setShowScatter((v) => !v)}
              className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition-colors ${
                showScatter
                  ? "border-teal-500 bg-teal-50 dark:bg-teal-900/20 text-teal-700 dark:text-teal-400"
                  : "border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300"
              }`}
            >
              Scatter Chart
            </button>
          </div>

          {lbLoading && (
            <div className="space-y-3 animate-pulse">
              <div className="h-64 rounded-xl bg-gray-100 dark:bg-gray-800" />
              <div className="h-48 rounded-xl bg-gray-100 dark:bg-gray-800" />
            </div>
          )}

          {!lbLoading && leaderboard && (
            <>
              {showScatter && leaderboard.lineups.length > 0 && (
                <LineupScatterPanel lineups={leaderboard.lineups} />
              )}
              <div className="flex items-center justify-between">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {leaderboard.total} lineup{leaderboard.total !== 1 ? "s" : ""} · sorted by {sortBy.replace(/_/g, " ")} {sortDir}
                </p>
              </div>
              <LineupLeaderboardTable
                lineups={leaderboard.lineups}
                sortBy={sortBy}
                sortDir={sortDir}
                onSort={handleSort}
              />
            </>
          )}

          {!lbLoading && !leaderboard && (
            <p className="text-sm text-gray-400 dark:text-gray-500 italic py-8 text-center">
              No lineup data available for this filter combination.
            </p>
          )}
        </div>
      )}

      {tab === "builder" && (
        <div className="space-y-4">
          <LineupBuilderPanel
            onSubmit={handleBuilderSubmit}
            isLoading={builderLoading}
          />

          {builderError && (
            <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10 px-3 py-2 text-sm text-red-600 dark:text-red-400">
              {builderError}
            </div>
          )}

          {builderResult && <LineupBuilderResults result={builderResult} />}
        </div>
      )}

      <LineupMethodologyDrawer />
    </div>
  );
}
