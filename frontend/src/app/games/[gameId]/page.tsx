"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useDeferredValue, useState } from "react";
import { useGameDetail } from "@/hooks/usePlayerStats";

function formatScore(value: number | null) {
  return value == null ? "-" : String(value);
}

function statValue(value: number | null) {
  return value == null ? "-" : value.toFixed(0);
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
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPeriod, setSelectedPeriod] = useState("all");
  const [selectedTeam, setSelectedTeam] = useState("all");
  const [selectedEventType, setSelectedEventType] = useState("all");
  const [scoringOnly, setScoringOnly] = useState(false);
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
                <div
                  key={`${point.action_number}-${point.clock ?? "na"}`}
                  className="grid gap-3 rounded-3xl border border-gray-200 p-4 dark:border-gray-800 md:grid-cols-[6rem,1fr,7rem]"
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
                </div>
              ))
            )}
          </div>
        </section>

        <section className="space-y-6">
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
                  <div
                    key={`${event.action_number}-${event.period}-${event.clock ?? "na"}`}
                    className="grid gap-3 rounded-3xl border border-gray-200 p-4 dark:border-gray-800 md:grid-cols-[5.25rem,1fr,6rem]"
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
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
