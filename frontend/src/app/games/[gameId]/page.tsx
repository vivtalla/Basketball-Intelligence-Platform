"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useDeferredValue, useState } from "react";
import { useGameDetail, useGameSummary } from "@/hooks/usePlayerStats";
import type { GameTeamBoxScore, GamePlayerBoxScore } from "@/lib/types";

function formatScore(value: number | null) {
  return value == null ? "-" : String(value);
}

function statValue(value: number | null) {
  return value == null ? "-" : value.toFixed(0);
}

function pct(made: number, attempted: number): string {
  if (attempted === 0) return "-";
  return (made / attempted * 100).toFixed(1) + "%";
}

function fmtMin(value: number | null): string {
  if (value == null) return "-";
  const m = Math.floor(value);
  const s = Math.round((value - m) * 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function fmtPlusMinus(value: number | null): string {
  if (value == null) return "-";
  return value > 0 ? `+${value.toFixed(0)}` : value.toFixed(0);
}

function TeamBoxRow({ label, away, home }: { label: string; away: string; home: string }) {
  return (
    <div className="grid grid-cols-3 gap-2 py-2 text-sm border-b border-gray-100 dark:border-gray-800 last:border-0">
      <div className="tabular-nums text-right text-gray-900 dark:text-gray-100 font-medium">{away}</div>
      <div className="text-center text-xs uppercase tracking-[0.16em] text-gray-400 dark:text-gray-500">{label}</div>
      <div className="tabular-nums text-left text-gray-900 dark:text-gray-100 font-medium">{home}</div>
    </div>
  );
}

function PlayerBoxTable({
  players,
  title,
}: {
  players: import("@/lib/types").GamePlayerBoxScore[];
  title: string;
}) {
  const starters = players.filter((p) => p.is_starter);
  const bench = players.filter((p) => !p.is_starter);
  const rows = [...starters, ...bench];
  if (rows.length === 0) return null;

  return (
    <div>
      <div className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
        {title}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs tabular-nums">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700 text-[10px] uppercase tracking-[0.16em] text-gray-400 dark:text-gray-500">
              <th className="pb-2 text-left font-medium w-36">Player</th>
              <th className="pb-2 text-right font-medium px-2">MIN</th>
              <th className="pb-2 text-right font-medium px-2">PTS</th>
              <th className="pb-2 text-right font-medium px-2">REB</th>
              <th className="pb-2 text-right font-medium px-2">AST</th>
              <th className="pb-2 text-right font-medium px-2">STL</th>
              <th className="pb-2 text-right font-medium px-2">BLK</th>
              <th className="pb-2 text-right font-medium px-2">TOV</th>
              <th className="pb-2 text-right font-medium px-2">FG</th>
              <th className="pb-2 text-right font-medium px-2">3P</th>
              <th className="pb-2 text-right font-medium px-2">FT</th>
              <th className="pb-2 text-right font-medium px-2">+/-</th>
            </tr>
          </thead>
          <tbody>
            {starters.length > 0 && bench.length > 0 && (
              <>
                {starters.map((p, i) => (
                  <PlayerBoxRow key={`s-${p.player_id}-${i}`} player={p} />
                ))}
                <tr>
                  <td colSpan={12} className="py-1 text-[10px] uppercase tracking-[0.16em] text-gray-400 dark:text-gray-500 pt-3">
                    Bench
                  </td>
                </tr>
                {bench.map((p, i) => (
                  <PlayerBoxRow key={`b-${p.player_id}-${i}`} player={p} />
                ))}
              </>
            )}
            {(starters.length === 0 || bench.length === 0) && rows.map((p, i) => (
              <PlayerBoxRow key={`r-${p.player_id}-${i}`} player={p} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PlayerBoxRow({ player }: { player: import("@/lib/types").GamePlayerBoxScore }) {
  const pm = fmtPlusMinus(player.plus_minus);
  return (
    <tr className="border-b border-gray-100 dark:border-gray-800 last:border-0 hover:bg-gray-50 dark:hover:bg-gray-800/40">
      <td className="py-2 pr-2">
        <Link
          href={`/players/${player.player_id}`}
          className="font-medium text-gray-900 dark:text-gray-100 hover:text-blue-500 dark:hover:text-blue-400 transition-colors"
        >
          {player.player_name}
        </Link>
      </td>
      <td className="py-2 px-2 text-right text-gray-600 dark:text-gray-300">{fmtMin(player.min)}</td>
      <td className="py-2 px-2 text-right font-semibold text-gray-900 dark:text-gray-100">{player.pts}</td>
      <td className="py-2 px-2 text-right text-gray-600 dark:text-gray-300">{player.reb}</td>
      <td className="py-2 px-2 text-right text-gray-600 dark:text-gray-300">{player.ast}</td>
      <td className="py-2 px-2 text-right text-gray-600 dark:text-gray-300">{player.stl}</td>
      <td className="py-2 px-2 text-right text-gray-600 dark:text-gray-300">{player.blk}</td>
      <td className="py-2 px-2 text-right text-gray-600 dark:text-gray-300">{player.tov}</td>
      <td className="py-2 px-2 text-right text-gray-500 dark:text-gray-400">{player.fgm}-{player.fga}</td>
      <td className="py-2 px-2 text-right text-gray-500 dark:text-gray-400">{player.fg3m}-{player.fg3a}</td>
      <td className="py-2 px-2 text-right text-gray-500 dark:text-gray-400">{player.ftm}-{player.fta}</td>
      <td className={`py-2 px-2 text-right font-medium ${
        player.plus_minus != null && player.plus_minus > 0
          ? "text-green-600 dark:text-green-400"
          : player.plus_minus != null && player.plus_minus < 0
          ? "text-red-500 dark:text-red-400"
          : "text-gray-400 dark:text-gray-500"
      }`}>{pm}</td>
    </tr>
  );
}

function formatEventType(value: string | null | undefined) {
  if (!value) {
    return "Unclassified";
  }

  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function GameDetailPage() {
  const params = useParams<{ gameId: string }>();
  const gameId = params.gameId ?? null;
  const { data, error, isLoading } = useGameDetail(gameId);
  const { data: summary } = useGameSummary(gameId);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPeriod, setSelectedPeriod] = useState("all");
  const [selectedTeam, setSelectedTeam] = useState("all");
  const [selectedEventType, setSelectedEventType] = useState("all");
  const [scoringOnly, setScoringOnly] = useState(false);
  const [selectedActionNumber, setSelectedActionNumber] = useState<number | null>(null);
  const deferredSearchQuery = useDeferredValue(searchQuery);

  if (!gameId) {
    return (
      <div className="py-20 text-center">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
          Invalid game
        </h1>
        <p className="mt-3 text-gray-500 dark:text-gray-400">
          A valid game ID is required to open the explorer.
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="h-5 w-28 animate-pulse rounded-full bg-gray-200 dark:bg-gray-800" />
        <div className="rounded-[2rem] border border-gray-200 bg-white p-8 dark:border-gray-800 dark:bg-gray-900">
          <div className="space-y-4 animate-pulse">
            <div className="h-5 w-36 rounded-full bg-gray-200 dark:bg-gray-800" />
            <div className="h-12 w-72 rounded-2xl bg-gray-200 dark:bg-gray-800" />
            <div className="grid gap-4 md:grid-cols-3">
              {[1, 2, 3].map((item) => (
                <div key={item} className="h-24 rounded-3xl bg-gray-100 dark:bg-gray-800" />
              ))}
            </div>
          </div>
        </div>
        <div className="grid gap-6 xl:grid-cols-[1.05fr,0.95fr]">
          {[1, 2].map((item) => (
            <div
              key={item}
              className="h-[28rem] animate-pulse rounded-[2rem] border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-3xl py-16 text-center">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
          Game detail unavailable
        </h1>
        <p className="mt-4 text-gray-500 dark:text-gray-400">
          The platform could not load this game yet. Try opening it from a synced
          player game log or refresh after a play-by-play sync.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex rounded-full bg-blue-500 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-600"
        >
          Back to home
        </Link>
      </div>
    );
  }

  const title =
    data.away_team_abbreviation && data.home_team_abbreviation
      ? `${data.away_team_abbreviation} at ${data.home_team_abbreviation}`
      : data.matchup ?? data.game_id;
  const normalizedSearch = deferredSearchQuery.trim().toLowerCase();
  const availablePeriods = Array.from(
    new Set(
      data.events
        .map((event) => event.period)
        .filter((period): period is number => period != null)
    )
  ).sort((a, b) => a - b);
  const availableTeams = Array.from(
    new Set(
      data.events
        .map((event) => event.team_abbreviation)
        .filter((team): team is string => Boolean(team))
    )
  ).sort();
  const availableEventTypes = Array.from(
    new Set(
      data.events
        .map((event) => event.event_type)
        .filter((eventType): eventType is string => Boolean(eventType))
    )
  ).sort();
  const filteredEvents = data.events.filter((event) => {
    const matchesPeriod =
      selectedPeriod === "all" || String(event.period ?? "") === selectedPeriod;
    const matchesTeam =
      selectedTeam === "all" || event.team_abbreviation === selectedTeam;
    const matchesEventType =
      selectedEventType === "all" || event.event_type === selectedEventType;
    const isScoringPlay =
      event.away_score != null &&
      event.home_score != null &&
      ["2pt", "3pt", "freethrow"].includes(event.event_type ?? "");
    const matchesScoring = !scoringOnly || isScoringPlay;
    const haystack = [
      event.description,
      event.event_type,
      event.player_name,
      event.team_abbreviation,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    const matchesSearch =
      normalizedSearch.length === 0 || haystack.includes(normalizedSearch);

    return matchesPeriod && matchesTeam && matchesEventType && matchesScoring && matchesSearch;
  });
  const filteredActionNumbers = new Set(filteredEvents.map((event) => event.action_number));
  const filteredTimeline = data.timeline.filter((point) => {
    const matchesPeriod =
      selectedPeriod === "all" || String(point.period ?? "") === selectedPeriod;
    const matchesTeam =
      selectedTeam === "all" || point.scoring_team_abbreviation === selectedTeam;
    const haystack = [
      point.description,
      point.scoring_team_abbreviation,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    const matchesSearch =
      normalizedSearch.length === 0 || haystack.includes(normalizedSearch);

    return matchesPeriod && matchesTeam && matchesSearch && filteredActionNumbers.has(point.action_number);
  });
  const visibleScoringPlays = filteredEvents.filter(
    (event) =>
      event.away_score != null &&
      event.home_score != null &&
      ["2pt", "3pt", "freethrow"].includes(event.event_type ?? "")
  ).length;
  const visibleTurnovers = filteredEvents.filter(
    (event) => event.event_type === "turnover"
  ).length;
  const activeFilterCount = [
    selectedPeriod !== "all",
    selectedTeam !== "all",
    selectedEventType !== "all",
    scoringOnly,
    normalizedSearch.length > 0,
  ].filter(Boolean).length;
  const selectedEvent =
    filteredEvents.length === 0
      ? null
      : selectedActionNumber == null
      ? filteredEvents[0]
      : filteredEvents.find((event) => event.action_number === selectedActionNumber) ?? filteredEvents[0];
  const selectedEventIndex = selectedEvent
    ? filteredEvents.findIndex((event) => event.action_number === selectedEvent.action_number)
    : -1;
  const selectedEventNeighbors =
    selectedEventIndex >= 0
      ? filteredEvents.slice(
          Math.max(0, selectedEventIndex - 1),
          Math.min(filteredEvents.length, selectedEventIndex + 2)
        )
      : [];

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <div>
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-gray-500 transition-colors hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400"
        >
          ← Back to Home
        </Link>
      </div>

      <section className="rounded-[2rem] border border-gray-200 bg-white p-8 dark:border-gray-800 dark:bg-gray-900">
        <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.24em] text-blue-500">
              Game Explorer
            </p>
            <h1 className="mt-3 text-4xl font-bold text-gray-900 dark:text-gray-100">
              {title}
            </h1>
            <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">
              {data.game_date ?? "Date unavailable"} · {data.season ?? "Season unavailable"} · {data.game_id}
            </p>
          </div>

          <div className="grid min-w-full gap-3 sm:grid-cols-3 lg:min-w-[25rem]">
            <div className="rounded-3xl bg-gray-50 p-5 dark:bg-gray-800">
              <div className="text-xs uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
                Away
              </div>
              <div className="mt-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
                {data.away_team_abbreviation ?? "Away"}
              </div>
              <div className="mt-3 text-4xl font-bold text-gray-900 dark:text-gray-100">
                {formatScore(data.away_score)}
              </div>
            </div>
            <div className="rounded-3xl bg-blue-50 p-5 dark:bg-blue-950/40">
              <div className="text-xs uppercase tracking-[0.18em] text-blue-600 dark:text-blue-300">
                Final
              </div>
              <div className="mt-2 text-lg font-semibold text-blue-700 dark:text-blue-200">
                Margin
              </div>
              <div className="mt-3 text-4xl font-bold text-blue-700 dark:text-blue-200">
                {data.home_score != null && data.away_score != null
                  ? Math.abs(data.home_score - data.away_score)
                  : "-"}
              </div>
            </div>
            <div className="rounded-3xl bg-gray-50 p-5 dark:bg-gray-800">
              <div className="text-xs uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
                Home
              </div>
              <div className="mt-2 text-lg font-semibold text-gray-900 dark:text-gray-100">
                {data.home_team_abbreviation ?? "Home"}
              </div>
              <div className="mt-3 text-4xl font-bold text-gray-900 dark:text-gray-100">
                {formatScore(data.home_score)}
              </div>
            </div>
          </div>
        </div>
      </section>

      {summary && (summary.home_team_box_score || summary.away_team_box_score || summary.player_box_scores.length > 0) && (
        <section className="rounded-[2rem] border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
          <div className="mb-6 flex items-end justify-between gap-4">
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.24em] text-blue-500">Box Score</p>
              <h2 className="mt-2 text-2xl font-semibold text-gray-900 dark:text-gray-100">Team Stats</h2>
            </div>
          </div>

          {(summary.home_team_box_score || summary.away_team_box_score) && (() => {
            const away = summary.away_team_box_score;
            const home = summary.home_team_box_score;
            const awayAbbr = summary.away_team_abbreviation ?? "Away";
            const homeAbbr = summary.home_team_abbreviation ?? "Home";
            return (
              <div className="mb-8">
                <div className="grid grid-cols-3 gap-2 mb-3 text-[11px] font-semibold uppercase tracking-[0.18em]">
                  <div className="text-right text-gray-700 dark:text-gray-200">{awayAbbr}</div>
                  <div className="text-center text-gray-400 dark:text-gray-500">Stat</div>
                  <div className="text-left text-gray-700 dark:text-gray-200">{homeAbbr}</div>
                </div>
                <TeamBoxRow label="PTS" away={String(away?.pts ?? "-")} home={String(home?.pts ?? "-")} />
                <TeamBoxRow label="FG%" away={away ? pct(away.fgm, away.fga) : "-"} home={home ? pct(home.fgm, home.fga) : "-"} />
                <TeamBoxRow label="3P%" away={away ? pct(away.fg3m, away.fg3a) : "-"} home={home ? pct(home.fg3m, home.fg3a) : "-"} />
                <TeamBoxRow label="FT%" away={away ? pct(away.ftm, away.fta) : "-"} home={home ? pct(home.ftm, home.fta) : "-"} />
                <TeamBoxRow label="REB" away={String(away?.reb ?? "-")} home={String(home?.reb ?? "-")} />
                <TeamBoxRow label="OREB" away={String(away?.oreb ?? "-")} home={String(home?.oreb ?? "-")} />
                <TeamBoxRow label="AST" away={String(away?.ast ?? "-")} home={String(home?.ast ?? "-")} />
                <TeamBoxRow label="TOV" away={String(away?.tov ?? "-")} home={String(home?.tov ?? "-")} />
                <TeamBoxRow label="STL" away={String(away?.stl ?? "-")} home={String(home?.stl ?? "-")} />
                <TeamBoxRow label="BLK" away={String(away?.blk ?? "-")} home={String(home?.blk ?? "-")} />
                <TeamBoxRow label="PF" away={String(away?.pf ?? "-")} home={String(home?.pf ?? "-")} />
              </div>
            );
          })()}

          {summary.player_box_scores.length > 0 && (() => {
            const awayPlayers = summary.player_box_scores.filter(
              (p) => p.team_abbreviation === summary.away_team_abbreviation
            );
            const homePlayers = summary.player_box_scores.filter(
              (p) => p.team_abbreviation === summary.home_team_abbreviation
            );
            return (
              <div className="grid gap-8 lg:grid-cols-2">
                {awayPlayers.length > 0 && (
                  <PlayerBoxTable
                    players={awayPlayers}
                    title={summary.away_team_abbreviation ?? "Away"}
                  />
                )}
                {homePlayers.length > 0 && (
                  <PlayerBoxTable
                    players={homePlayers}
                    title={summary.home_team_abbreviation ?? "Home"}
                  />
                )}
              </div>
            );
          })()}
        </section>
      )}

      <section className="overflow-hidden rounded-[2rem] border border-sky-200 bg-gradient-to-br from-sky-50 via-white to-cyan-50 dark:border-sky-900/70 dark:from-slate-900 dark:via-slate-950 dark:to-cyan-950/40">
        <div className="grid gap-6 p-6 lg:grid-cols-[1.1fr,0.9fr] lg:p-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-600 dark:text-sky-300">
              Explorer Controls
            </p>
            <h2 className="mt-3 text-2xl font-semibold text-slate-900 dark:text-slate-100">
              Slice the possession log without leaving the page
            </h2>
            <p className="mt-2 max-w-2xl text-sm text-slate-600 dark:text-slate-300">
              Narrow the feed by quarter, team, event type, scoring plays, or a text search
              for players and descriptions.
            </p>

            <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <label className="space-y-2">
                <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                  Search
                </span>
                <input
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="Player, team, or event"
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:border-sky-500"
                />
              </label>

              <label className="space-y-2">
                <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                  Period
                </span>
                <select
                  value={selectedPeriod}
                  onChange={(event) => setSelectedPeriod(event.target.value)}
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:border-sky-500"
                >
                  <option value="all">All periods</option>
                  {availablePeriods.map((period) => (
                    <option key={period} value={String(period)}>
                      Q{period}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-2">
                <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                  Team
                </span>
                <select
                  value={selectedTeam}
                  onChange={(event) => setSelectedTeam(event.target.value)}
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:border-sky-500"
                >
                  <option value="all">Both teams</option>
                  {availableTeams.map((team) => (
                    <option key={team} value={team}>
                      {team}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-2">
                <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                  Event Type
                </span>
                <select
                  value={selectedEventType}
                  onChange={(event) => setSelectedEventType(event.target.value)}
                  className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-sky-400 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:border-sky-500"
                >
                  <option value="all">All event types</option>
                  {availableEventTypes.map((eventType) => (
                    <option key={eventType} value={eventType}>
                      {formatEventType(eventType)}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => setScoringOnly((value) => !value)}
                className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition ${
                  scoringOnly
                    ? "bg-sky-600 text-white hover:bg-sky-700"
                    : "bg-white text-slate-600 hover:bg-slate-100 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800"
                }`}
              >
                {scoringOnly ? "Scoring Plays Only" : "Show All Plays"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("");
                  setSelectedPeriod("all");
                  setSelectedTeam("all");
                  setSelectedEventType("all");
                  setScoringOnly(false);
                }}
                className="rounded-full border border-slate-200 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-600 transition hover:bg-white dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-900"
              >
                Reset Filters
              </button>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-3xl bg-white/80 p-5 shadow-sm ring-1 ring-sky-100 backdrop-blur dark:bg-slate-900/80 dark:ring-sky-900/50">
              <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                Visible Events
              </div>
              <div className="mt-2 text-4xl font-bold text-slate-900 dark:text-slate-100">
                {filteredEvents.length}
              </div>
              <div className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                {data.events.length} stored total
              </div>
            </div>
            <div className="rounded-3xl bg-white/80 p-5 shadow-sm ring-1 ring-sky-100 backdrop-blur dark:bg-slate-900/80 dark:ring-sky-900/50">
              <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                Scoring Plays
              </div>
              <div className="mt-2 text-4xl font-bold text-slate-900 dark:text-slate-100">
                {visibleScoringPlays}
              </div>
              <div className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                {filteredTimeline.length} timeline updates
              </div>
            </div>
            <div className="rounded-3xl bg-white/80 p-5 shadow-sm ring-1 ring-sky-100 backdrop-blur dark:bg-slate-900/80 dark:ring-sky-900/50">
              <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                Turnovers
              </div>
              <div className="mt-2 text-4xl font-bold text-slate-900 dark:text-slate-100">
                {visibleTurnovers}
              </div>
              <div className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                In current filtered view
              </div>
            </div>
            <div className="rounded-3xl bg-white/80 p-5 shadow-sm ring-1 ring-sky-100 backdrop-blur dark:bg-slate-900/80 dark:ring-sky-900/50">
              <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
                Active Filters
              </div>
              <div className="mt-2 text-4xl font-bold text-slate-900 dark:text-slate-100">
                {activeFilterCount}
              </div>
              <div className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                Zero means full game view
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.05fr,0.95fr]">
        <section className="rounded-[2rem] border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
          <div className="flex items-end justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                Score Timeline
              </h2>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Every recorded scoring update from the synced play-by-play feed.
              </p>
            </div>
            <div className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-gray-500 dark:bg-gray-800 dark:text-gray-400">
              {filteredTimeline.length} swings
            </div>
          </div>

          <div className="mt-6 space-y-3">
            {filteredTimeline.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                No scoring timeline matches the current filter set.
              </div>
            ) : (
              filteredTimeline.map((point) => (
                <button
                  key={`${point.action_number}-${point.clock ?? "na"}`}
                  type="button"
                  onClick={() => setSelectedActionNumber(point.action_number)}
                  className={`grid w-full gap-3 rounded-3xl border p-4 text-left transition-colors md:grid-cols-[6rem,1fr,7rem] ${
                    selectedEvent?.action_number === point.action_number
                      ? "border-blue-300 bg-blue-50 dark:border-blue-700 dark:bg-blue-950/20"
                      : "border-gray-200 dark:border-gray-800"
                  }`}
                >
                  <div className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    Q{point.period} {point.clock ?? ""}
                  </div>
                  <div className="text-sm text-gray-700 dark:text-gray-300">
                    {point.description ?? "Score update"}
                  </div>
                  <div className="text-right text-lg font-semibold tabular-nums text-gray-900 dark:text-gray-100">
                    {point.away_score}-{point.home_score}
                  </div>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="space-y-6">
          <div className="rounded-[2rem] border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
            <div className="flex items-end justify-between gap-4">
              <div>
                <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                  Event Drill-Down
                </h2>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Click any timeline row or feed event to pin the possession context here.
                </p>
              </div>
              <div className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                {selectedEvent ? `Play ${selectedEvent.action_number}` : "No event selected"}
              </div>
            </div>

            {selectedEvent ? (
              <div className="mt-5 grid gap-4 lg:grid-cols-[0.95fr,1.05fr]">
                <div className="rounded-3xl bg-blue-50 p-5 dark:bg-blue-950/30">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-blue-600 dark:text-blue-300">
                    Selected event
                  </div>
                  <div className="mt-3 text-xl font-semibold text-gray-900 dark:text-gray-100">
                    {selectedEvent.description ?? formatEventType(selectedEvent.event_type)}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs uppercase tracking-[0.16em] text-gray-500 dark:text-gray-400">
                    <span>Q{selectedEvent.period ?? "—"} {selectedEvent.clock ?? ""}</span>
                    <span>{selectedEvent.team_abbreviation ?? "NBA"}</span>
                    <span>{selectedEvent.player_name ?? "Team event"}</span>
                    <span>{formatEventType(selectedEvent.event_type)}</span>
                  </div>
                  <div className="mt-4 text-3xl font-bold tabular-nums text-blue-700 dark:text-blue-200">
                    {selectedEvent.away_score != null && selectedEvent.home_score != null
                      ? `${selectedEvent.away_score}-${selectedEvent.home_score}`
                      : "No score change"}
                  </div>
                </div>

                <div className="rounded-3xl border border-gray-200 p-5 dark:border-gray-800">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
                    Nearby sequence
                  </div>
                  <div className="mt-3 space-y-3">
                    {selectedEventNeighbors.map((event) => (
                      <button
                        key={`neighbor-${event.action_number}`}
                        type="button"
                        onClick={() => setSelectedActionNumber(event.action_number)}
                        className={`w-full rounded-2xl border px-4 py-3 text-left transition-colors ${
                          event.action_number === selectedEvent.action_number
                            ? "border-blue-300 bg-blue-50 dark:border-blue-700 dark:bg-blue-950/30"
                            : "border-gray-200 hover:border-blue-200 hover:bg-gray-50 dark:border-gray-800 dark:hover:border-blue-900 dark:hover:bg-gray-900"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-3 text-xs uppercase tracking-[0.16em] text-gray-500 dark:text-gray-400">
                          <span>Play {event.action_number}</span>
                          <span>Q{event.period ?? "—"} {event.clock ?? ""}</span>
                        </div>
                        <div className="mt-2 text-sm font-medium text-gray-900 dark:text-gray-100">
                          {event.description ?? formatEventType(event.event_type)}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-5 rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                No event matches the current filters. Reset filters to inspect a specific play.
              </div>
            )}
          </div>

          <div className="rounded-[2rem] border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
            <div className="flex items-end justify-between gap-4">
              <div>
                <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                  Top Players
                </h2>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Quick box-score leaders derived from the synced game events.
                </p>
              </div>
              <div className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                Top {data.top_players.length}
              </div>
            </div>

            <div className="mt-5 space-y-3">
              {data.top_players.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                  No player summaries are available yet.
                </div>
              ) : (
                data.top_players.map((player) => (
                  <Link
                    key={player.player_id}
                    href={`/players/${player.player_id}`}
                    className="flex items-center justify-between gap-4 rounded-3xl border border-gray-200 p-4 transition-colors hover:border-blue-300 hover:bg-blue-50/60 dark:border-gray-800 dark:hover:border-blue-800 dark:hover:bg-blue-950/20"
                  >
                    <div>
                      <div className="text-base font-semibold text-gray-900 dark:text-gray-100">
                        {player.player_name}
                      </div>
                      <div className="mt-1 text-xs uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
                        {player.team_abbreviation ?? "Team unavailable"}
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-3 text-right text-sm tabular-nums text-gray-600 dark:text-gray-300">
                      <div>
                        <div className="text-[11px] uppercase tracking-[0.18em] text-gray-400 dark:text-gray-500">
                          PTS
                        </div>
                        <div className="mt-1 font-semibold text-gray-900 dark:text-gray-100">
                          {statValue(player.pts)}
                        </div>
                      </div>
                      <div>
                        <div className="text-[11px] uppercase tracking-[0.18em] text-gray-400 dark:text-gray-500">
                          REB
                        </div>
                        <div className="mt-1 font-semibold text-gray-900 dark:text-gray-100">
                          {statValue(player.reb)}
                        </div>
                      </div>
                      <div>
                        <div className="text-[11px] uppercase tracking-[0.18em] text-gray-400 dark:text-gray-500">
                          TOV
                        </div>
                        <div className="mt-1 font-semibold text-gray-900 dark:text-gray-100">
                          {statValue(player.tov)}
                        </div>
                      </div>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>

          <div className="rounded-[2rem] border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
            <div className="flex items-end justify-between gap-4">
              <div>
                <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                  Play-by-Play Feed
                </h2>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Full event stream for this game, ordered exactly as stored.
              </p>
            </div>
            <div className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium uppercase tracking-[0.18em] text-gray-500 dark:bg-gray-800 dark:text-gray-400">
              {filteredEvents.length} events
            </div>
          </div>

            <div className="mt-5 max-h-[42rem] space-y-3 overflow-y-auto pr-1">
              {filteredEvents.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                  No play-by-play events match the current filter set.
                </div>
              ) : (
                filteredEvents.map((event) => (
                  <button
                    key={`${event.action_number}-${event.period}-${event.clock ?? "na"}`}
                    type="button"
                    onClick={() => setSelectedActionNumber(event.action_number)}
                    className={`grid w-full gap-3 rounded-3xl border p-4 text-left transition-colors md:grid-cols-[5.25rem,1fr,6rem] ${
                      selectedEvent?.action_number === event.action_number
                        ? "border-blue-300 bg-blue-50 dark:border-blue-700 dark:bg-blue-950/20"
                        : "border-gray-200 dark:border-gray-800"
                    }`}
                  >
                    <div className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Q{event.period} {event.clock ?? ""}
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                        {event.description ?? event.event_type ?? "Event"}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.16em] text-gray-500 dark:text-gray-400">
                        <span>
                          {event.team_abbreviation ?? "NBA"}{event.player_name ? ` · ${event.player_name}` : ""}
                        </span>
                        <span className="rounded-full bg-gray-100 px-2 py-1 text-[10px] font-semibold tracking-[0.18em] text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                          {formatEventType(event.event_type)}
                        </span>
                      </div>
                    </div>
                    <div className="text-right text-sm font-semibold tabular-nums text-gray-900 dark:text-gray-100">
                      {event.away_score != null && event.home_score != null
                        ? `${event.away_score}-${event.home_score}`
                        : "-"}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
