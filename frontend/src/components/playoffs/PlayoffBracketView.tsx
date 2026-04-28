"use client";

import type { PlayoffBracketResponse, PlayoffSeriesResponse } from "@/lib/types";
import SeriesCard from "./SeriesCard";

const ROUND_LABELS: Record<number, string> = {
  1: "First Round",
  2: "Conference Semifinals",
  3: "Conference Finals",
  4: "NBA Finals",
};

function groupByRound(
  series: PlayoffSeriesResponse[]
): Array<{ round: number; series: PlayoffSeriesResponse[] }> {
  const map = new Map<number, PlayoffSeriesResponse[]>();
  for (const s of series) {
    const list = map.get(s.round);
    if (list) {
      list.push(s);
    } else {
      map.set(s.round, [s]);
    }
  }
  return Array.from(map.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([round, list]) => ({ round, series: list }));
}

function ConferenceColumn({
  label,
  series,
}: {
  label: string;
  series: PlayoffSeriesResponse[];
}) {
  const grouped = groupByRound(series);
  return (
    <div className="space-y-5">
      <p className="bip-kicker">{label}</p>
      {grouped.length === 0 && (
        <div className="bip-empty rounded-2xl px-4 py-6 text-sm text-[var(--muted)]">
          No series yet.
        </div>
      )}
      {grouped.map(({ round, series: roundSeries }) => (
        <div key={round} className="space-y-3">
          {grouped.length > 1 && (
            <p
              className="font-mono text-[10px] uppercase tracking-wider text-[var(--muted)]"
              style={{ letterSpacing: "0.08em" }}
            >
              {ROUND_LABELS[round] ?? `Round ${round}`}
            </p>
          )}
          <div className="space-y-4">
            {roundSeries.map((s) => (
              <SeriesCard key={s.series_id} series={s} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

interface PlayoffBracketViewProps {
  bracket: PlayoffBracketResponse;
}

export default function PlayoffBracketView({ bracket }: PlayoffBracketViewProps) {
  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ConferenceColumn label="Eastern Conference" series={bracket.east} />
        <ConferenceColumn label="Western Conference" series={bracket.west} />
      </div>

      {bracket.finals && (
        <div className="space-y-3">
          <p className="bip-kicker text-center">NBA Finals</p>
          <div className="max-w-md mx-auto">
            <SeriesCard series={bracket.finals} />
          </div>
        </div>
      )}
    </div>
  );
}
