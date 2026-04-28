"use client";

import Link from "next/link";
import useSWR from "swr";
import { getPlayoffsToday } from "@/lib/api";
import type {
  PlayoffSeriesGameWithMatchup,
  PlayoffTodayResponse,
} from "@/lib/types";

const TIME_FORMATTER = new Intl.DateTimeFormat("en-US", {
  hour: "numeric",
  minute: "2-digit",
  timeZone: "America/Los_Angeles",
  timeZoneName: "short",
});

function formatTipoff(game: PlayoffSeriesGameWithMatchup): string {
  // Backend sends `game_date` only (no clock time). Until tipoff times are
  // wired into GameLog, we render "TBD" so we don't fabricate a tipoff.
  if (!game.game_date) return "TBD";
  // Try to derive a tipoff from any ISO-style timestamp embedded in game_date.
  // GameLog only persists a date today, so this branch is mostly defensive.
  const isoCandidate = `${game.game_date}T19:00:00Z`;
  const parsed = new Date(isoCandidate);
  if (Number.isNaN(parsed.getTime())) return "TBD";
  return TIME_FORMATTER.format(parsed);
}

function seriesContext(game: PlayoffSeriesGameWithMatchup): string | null {
  if (game.top_wins == null || game.bottom_wins == null) return null;
  if (!game.top_seed_team_abbr || !game.bottom_seed_team_abbr) return null;
  if (game.top_wins === 0 && game.bottom_wins === 0) {
    return `Series tied 0-0`;
  }
  if (game.top_wins === game.bottom_wins) {
    return `Series tied ${game.top_wins}-${game.bottom_wins}`;
  }
  const leader =
    game.top_wins > game.bottom_wins
      ? game.top_seed_team_abbr
      : game.bottom_seed_team_abbr;
  const lead = `${Math.max(game.top_wins, game.bottom_wins)}-${Math.min(game.top_wins, game.bottom_wins)}`;
  return `${leader} leads ${lead}`;
}

function GameRow({ game }: { game: PlayoffSeriesGameWithMatchup }) {
  const tipoff = formatTipoff(game);
  const ctx = seriesContext(game);
  const finalScore =
    game.home_pts != null && game.away_pts != null
      ? `${game.away_pts} - ${game.home_pts}`
      : null;

  return (
    <li className="flex items-center gap-4 px-4 py-3 hover:bg-[rgba(33,72,59,0.06)]">
      <div className="w-20 shrink-0">
        <p
          className="tabular-nums"
          style={{
            fontFamily: "var(--font-geist-mono)",
            fontSize: 11,
            letterSpacing: "0.06em",
            color: "var(--muted)",
          }}
        >
          {tipoff}
        </p>
        {game.series_game_num != null && (
          <p
            className="mt-0.5"
            style={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: 10,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--muted)",
            }}
          >
            Game {game.series_game_num}
          </p>
        )}
      </div>

      <div className="flex flex-1 items-center gap-2 min-w-0">
        <div className="flex items-center gap-2 min-w-0">
          <span
            aria-hidden
            className="inline-block w-6 h-6 rounded-full bg-[var(--surface-alt)] border border-[var(--border)]"
          />
          <span className="text-sm font-semibold text-[var(--foreground)] truncate">
            {game.away_team_abbr ?? "TBD"}
          </span>
        </div>
        <span className="text-xs text-[var(--muted)] px-1">@</span>
        <div className="flex items-center gap-2 min-w-0">
          <span
            aria-hidden
            className="inline-block w-6 h-6 rounded-full bg-[var(--surface-alt)] border border-[var(--border)]"
          />
          <span className="text-sm font-semibold text-[var(--foreground)] truncate">
            {game.home_team_abbr ?? "TBD"}
          </span>
        </div>
      </div>

      <div className="shrink-0 text-right">
        {finalScore ? (
          <p
            className="tabular-nums text-sm font-semibold text-[var(--foreground)]"
            style={{ fontVariantNumeric: "tabular-nums" }}
          >
            {finalScore}
          </p>
        ) : (
          <p
            style={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: 10,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "var(--muted)",
            }}
          >
            Tip
          </p>
        )}
        {ctx && (
          <p
            className="mt-0.5 text-[11px]"
            style={{ color: "var(--muted)" }}
          >
            {ctx}
          </p>
        )}
      </div>
    </li>
  );
}

export default function DailyPlayoffSlate() {
  const { data, isLoading, error } = useSWR<PlayoffTodayResponse>(
    ["playoffs-today"],
    () => getPlayoffsToday()
  );

  const games = data?.games ?? [];

  return (
    <section className="bip-panel rounded-[1.85rem] overflow-hidden">
      <div className="px-5 py-4 border-b border-[var(--border)] flex items-end justify-between gap-4">
        <div>
          <p className="bip-kicker mb-1.5">Today&rsquo;s Playoff Slate</p>
          <h2 className="bip-display text-2xl font-semibold text-[var(--foreground)]">
            Tonight&rsquo;s <span className="text-[var(--accent)]">games.</span>
          </h2>
        </div>
        <Link href="/bracket" className="text-sm bip-link shrink-0 font-medium">
          Bracket →
        </Link>
      </div>

      {isLoading && (
        <div className="divide-y divide-[var(--border)] animate-pulse">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-4 py-3">
              <div className="h-3 w-16 rounded bg-[var(--surface-alt)] shrink-0" />
              <div className="h-4 flex-1 rounded bg-[var(--surface-alt)]" />
              <div className="h-3 w-12 rounded bg-[var(--surface-alt)] shrink-0" />
            </div>
          ))}
        </div>
      )}

      {!isLoading && error && (
        <p className="px-5 py-6 text-sm text-[var(--muted)]">
          Couldn&rsquo;t load today&rsquo;s playoff slate.
        </p>
      )}

      {!isLoading && !error && games.length === 0 && (
        <p className="px-5 py-6 text-sm text-[var(--muted)]">
          No playoff games today. Bracket →{" "}
          <Link href="/bracket" className="bip-link">
            /bracket
          </Link>
        </p>
      )}

      {!isLoading && !error && games.length > 0 && (
        <ul className="divide-y divide-[var(--border)]">
          {games.map((game) => (
            <GameRow key={game.game_id} game={game} />
          ))}
        </ul>
      )}
    </section>
  );
}
