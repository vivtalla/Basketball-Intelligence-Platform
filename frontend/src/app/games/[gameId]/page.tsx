"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useGameDetail } from "@/hooks/usePlayerStats";

function formatScore(value: number | null) {
  return value == null ? "-" : String(value);
}

function statValue(value: number | null) {
  return value == null ? "-" : value.toFixed(0);
}

export default function GameDetailPage() {
  const params = useParams<{ gameId: string }>();
  const gameId = params.gameId ?? null;
  const { data, error, isLoading } = useGameDetail(gameId);

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
              {data.timeline.length} swings
            </div>
          </div>

          <div className="mt-6 space-y-3">
            {data.timeline.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                No scoring timeline is available for this game yet.
              </div>
            ) : (
              data.timeline.map((point) => (
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
                {data.events.length} events
              </div>
            </div>

            <div className="mt-5 max-h-[42rem] space-y-3 overflow-y-auto pr-1">
              {data.events.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-gray-200 p-6 text-sm text-gray-500 dark:border-gray-700 dark:text-gray-400">
                  No play-by-play events are stored for this game yet.
                </div>
              ) : (
                data.events.map((event) => (
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
                      <div className="mt-1 text-xs uppercase tracking-[0.16em] text-gray-500 dark:text-gray-400">
                        {event.team_abbreviation ?? "NBA"}{event.player_name ? ` · ${event.player_name}` : ""}
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
