"use client";

import useSWR from "swr";
import Link from "next/link";
import { getPlayoffsToday } from "@/lib/api";
import type { PlayoffTodayResponse } from "@/lib/types";
import BroadsheetGameCard from "./BroadsheetGameCard";

/**
 * Sprint 77 (Stream B / EB1): Today's playoff slate, broadsheet edition.
 *
 * Vertical column of <BroadsheetGameCard> rows. Replaces the Sprint 73
 * <DailyPlayoffSlate> list-style layout when the broadsheet home is
 * active.
 */

const DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  weekday: "long",
  month: "long",
  day: "numeric",
});

export default function TodaysSlate() {
  const { data, isLoading, error } = useSWR<PlayoffTodayResponse>(
    ["broadsheet-todays-slate"],
    () => getPlayoffsToday(),
    { refreshInterval: 60_000, revalidateOnFocus: true }
  );

  const games = data?.games ?? [];
  const dateLabel = data?.date
    ? DATE_FORMATTER.format(new Date(`${data.date}T00:00:00`))
    : DATE_FORMATTER.format(new Date());

  return (
    <section className="bip-panel rounded-[1.85rem] overflow-hidden">
      <header className="px-6 py-5 border-b border-[var(--border)] flex items-end justify-between gap-4">
        <div>
          <p className="bip-kicker mb-1.5">Today&rsquo;s Slate</p>
          <h2
            className="bip-display font-bold text-[var(--foreground)]"
            style={{
              fontSize: "clamp(1.5rem, 2.4vw, 2.1rem)",
              letterSpacing: "-0.015em",
            }}
          >
            Tonight on the boards.
          </h2>
          <p
            className="mt-1 text-xs"
            style={{
              fontFamily: "var(--font-geist-mono)",
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "var(--muted)",
            }}
          >
            {dateLabel}
          </p>
        </div>
        <Link
          href="/bracket"
          className="text-sm bip-link shrink-0 font-medium"
        >
          Bracket →
        </Link>
      </header>

      <div className="p-5 space-y-4">
        {isLoading && (
          <div className="space-y-4 animate-pulse">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="rounded-2xl border border-[var(--border)]"
                style={{
                  height: 132,
                  background: "rgba(255,249,241,0.4)",
                }}
              />
            ))}
          </div>
        )}

        {!isLoading && error && (
          <p
            className="px-2 py-6 text-sm italic text-[var(--muted)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Couldn&rsquo;t load today&rsquo;s slate. The presses will roll
            again at the next refresh.
          </p>
        )}

        {!isLoading && !error && games.length === 0 && (
          <p
            className="px-2 py-6 text-sm italic text-[var(--muted)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            No playoff games tonight. The bracket{" "}
            <Link href="/bracket" className="bip-link not-italic">
              is here
            </Link>
            .
          </p>
        )}

        {!isLoading && !error && games.length > 0 && (
          <div className="space-y-4">
            {games.map((game) => (
              <BroadsheetGameCard key={game.game_id} game={game} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
