"use client";

import useSWR from "swr";
import Link from "next/link";
import { getBracket } from "@/lib/api";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import type {
  PlayoffBracketResponse,
  PlayoffSeriesResponse,
} from "@/lib/types";

/**
 * Sprint 77 (Stream B / EB1): Bracket Strip — compact East/West mini bracket
 * for the broadsheet home. Renders QF / SF / CF columns side-by-side, then a
 * shared Finals chip below. Closed series go forest-on-cream with the winner
 * bolded; active series hold a thin signal-gold rule; scheduled series are
 * muted.
 */

const ACTIVE_SEASON_FALLBACK = "2024-25";

const ROUND_LABELS: Record<number, string> = {
  1: "First Round",
  2: "Conference Semis",
  3: "Conference Finals",
};

function groupByRound(
  series: PlayoffSeriesResponse[]
): Map<number, PlayoffSeriesResponse[]> {
  const map = new Map<number, PlayoffSeriesResponse[]>();
  for (const s of series) {
    const list = map.get(s.round);
    if (list) list.push(s);
    else map.set(s.round, [s]);
  }
  return map;
}

function MiniSeriesRow({ series }: { series: PlayoffSeriesResponse }) {
  const top = series.top_seed_team_abbr ?? "TBD";
  const bot = series.bottom_seed_team_abbr ?? "TBD";
  const closed = series.status === "closed";
  const active = series.status === "active";
  const topWinner = closed && series.top_wins > series.bottom_wins;
  const botWinner = closed && series.bottom_wins > series.top_wins;

  return (
    <Link
      href={`/pre-read?series_id=${encodeURIComponent(series.series_id)}`}
      className="block rounded-md border px-2 py-1.5 hover:-translate-y-0.5 transition-transform"
      style={{
        background: "rgba(255,249,241,0.7)",
        borderColor: active
          ? "rgba(180,137,61,0.45)"
          : closed
            ? "rgba(33,72,59,0.16)"
            : "var(--border)",
        opacity: series.status === "scheduled" ? 0.6 : 1,
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span
          className={topWinner ? "font-bold" : "font-medium"}
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 12,
            color: topWinner ? "var(--accent)" : "var(--foreground)",
          }}
        >
          <span
            className="text-[var(--muted)] font-mono mr-1"
            style={{ fontSize: 9 }}
          >
            {series.top_seed}
          </span>
          {top}
        </span>
        <span
          className="tabular-nums font-mono"
          style={{
            fontSize: 11,
            color: topWinner ? "var(--accent)" : "var(--muted)",
            fontWeight: topWinner ? 700 : 500,
          }}
        >
          {series.top_wins}
        </span>
      </div>
      <div className="flex items-center justify-between gap-2 mt-0.5">
        <span
          className={botWinner ? "font-bold" : "font-medium"}
          style={{
            fontFamily: "var(--font-display)",
            fontSize: 12,
            color: botWinner ? "var(--accent)" : "var(--foreground)",
          }}
        >
          <span
            className="text-[var(--muted)] font-mono mr-1"
            style={{ fontSize: 9 }}
          >
            {series.bottom_seed}
          </span>
          {bot}
        </span>
        <span
          className="tabular-nums font-mono"
          style={{
            fontSize: 11,
            color: botWinner ? "var(--accent)" : "var(--muted)",
            fontWeight: botWinner ? 700 : 500,
          }}
        >
          {series.bottom_wins}
        </span>
      </div>
    </Link>
  );
}

function ConferenceColumn({
  label,
  series,
}: {
  label: string;
  series: PlayoffSeriesResponse[];
}) {
  const grouped = groupByRound(series);
  // Render rounds 1, 2, 3 as side-by-side mini columns. If a round has no
  // series yet, render an "—" placeholder so the geometry stays stable.
  const rounds: number[] = [1, 2, 3];
  return (
    <div>
      <p className="bip-kicker text-center mb-3">{label}</p>
      <div className="grid grid-cols-3 gap-2">
        {rounds.map((round) => {
          const list = grouped.get(round) ?? [];
          return (
            <div key={round} className="space-y-1.5">
              <p
                className="text-center"
                style={{
                  fontFamily: "var(--font-geist-mono)",
                  fontSize: 9,
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  color: "var(--muted)",
                }}
              >
                {ROUND_LABELS[round] ?? `Round ${round}`}
              </p>
              {list.length > 0 ? (
                list.map((s) => (
                  <MiniSeriesRow key={s.series_id} series={s} />
                ))
              ) : (
                <p
                  className="text-center text-xs italic text-[var(--muted)] py-3"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  —
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function BracketStrip() {
  const { season } = useSeasonPhase();
  const seasonKey = season ?? ACTIVE_SEASON_FALLBACK;

  const { data, isLoading, error } = useSWR<PlayoffBracketResponse>(
    ["broadsheet-bracket-strip", seasonKey],
    () => getBracket(seasonKey),
    {
      refreshInterval: 5 * 60_000,
      revalidateOnFocus: false,
    }
  );

  return (
    <section className="bip-panel rounded-[1.85rem] overflow-hidden">
      <header className="px-6 py-4 border-b border-[var(--border)] flex items-end justify-between gap-4">
        <div>
          <p className="bip-kicker mb-1">Bracket</p>
          <h3
            className="bip-display font-bold text-[var(--foreground)]"
            style={{
              fontSize: "1.4rem",
              letterSpacing: "-0.015em",
            }}
          >
            The path to the trophy.
          </h3>
        </div>
        <Link
          href="/bracket"
          className="text-xs bip-link shrink-0 font-medium"
        >
          Full bracket →
        </Link>
      </header>
      <div className="p-5">
        {isLoading && (
          <div
            className="rounded-2xl animate-pulse"
            style={{
              height: 200,
              background: "rgba(255,249,241,0.5)",
              border: "1px solid var(--border)",
            }}
          />
        )}
        {!isLoading && error && (
          <p
            className="text-sm italic text-[var(--muted)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Bracket is on the press.
          </p>
        )}
        {!isLoading && !error && data && (
          <div className="space-y-5">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <ConferenceColumn
                label="Eastern Conference"
                series={data.east}
              />
              <ConferenceColumn
                label="Western Conference"
                series={data.west}
              />
            </div>
            {data.finals && (
              <div className="pt-4 border-t border-[var(--border)]">
                <p className="bip-kicker text-center mb-2">NBA Finals</p>
                <div className="max-w-xs mx-auto">
                  <MiniSeriesRow series={data.finals} />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
