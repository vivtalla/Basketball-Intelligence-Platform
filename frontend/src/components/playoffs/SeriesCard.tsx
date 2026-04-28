"use client";

import Link from "next/link";
import type { PlayoffSeriesResponse } from "@/lib/types";

// Inline brand-color tint map keyed by team abbreviation. Pattern copied from
// frontend/src/app/teams/page.tsx (Sprint 70 TEAM_META). Used to paint the
// left-edge stripe on each SeriesCard. There is no shared TEAM_META export.
const TEAM_TINT: Record<string, string> = {
  ATL: "#e03a3e", BOS: "#007a33", BKN: "#000000", CHA: "#00788c",
  CHI: "#ce1141", CLE: "#6f263d", DET: "#c8102e", IND: "#002d62",
  MIA: "#98002e", MIL: "#00471b", NYK: "#f58426", ORL: "#0077c0",
  PHI: "#006bb6", TOR: "#ce1141", WAS: "#002b5c", DAL: "#00538c",
  DEN: "#0e2240", GSW: "#1d428a", HOU: "#ce1141", LAC: "#c8102e",
  LAL: "#552583", MEM: "#5d76a9", MIN: "#0c2340", NOP: "#0c2340",
  OKC: "#007ac1", PHX: "#1d1160", POR: "#e03a3e", SAC: "#5a2d81",
  SAS: "#c4ced4", UTA: "#002b5c",
};

function tintFor(abbr: string | null | undefined): string {
  if (!abbr) return "var(--accent)";
  return TEAM_TINT[abbr.toUpperCase()] ?? "var(--accent)";
}

function statusLabel(series: PlayoffSeriesResponse): string {
  if (series.status === "closed") {
    const winningWins = Math.max(series.top_wins, series.bottom_wins);
    const losingWins = Math.min(series.top_wins, series.bottom_wins);
    return `Won ${winningWins}-${losingWins}`;
  }
  if (series.status === "scheduled") {
    return "Tipoff TBD";
  }
  // active — figure out the next game number
  const played = series.games.filter(
    (g) => g.home_pts != null && g.away_pts != null
  ).length;
  const nextGame = played + 1;
  return `Game ${nextGame} tonight`;
}

function statusPillClass(status: PlayoffSeriesResponse["status"]): string {
  switch (status) {
    case "active":
      return "bg-[rgba(180,137,61,0.18)] text-[var(--signal)]";
    case "closed":
      return "bg-[rgba(33,72,59,0.12)] text-[var(--accent)]";
    default:
      return "bg-[var(--surface-alt)] text-[var(--muted)]";
  }
}

interface SeriesCardProps {
  series: PlayoffSeriesResponse;
}

export default function SeriesCard({ series }: SeriesCardProps) {
  const topAbbr = series.top_seed_team_abbr ?? "TBD";
  const bottomAbbr = series.bottom_seed_team_abbr ?? "TBD";
  const topColor = tintFor(series.top_seed_team_abbr);
  const bottomColor = tintFor(series.bottom_seed_team_abbr);
  const topIsWinner =
    series.status === "closed" && series.top_wins > series.bottom_wins;
  const bottomIsWinner =
    series.status === "closed" && series.bottom_wins > series.top_wins;

  return (
    <Link
      href={`/pre-read?series_id=${encodeURIComponent(series.series_id)}`}
      className="bip-panel block rounded-2xl overflow-hidden transition-transform hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
      style={{ borderLeft: `4px solid ${topColor}` }}
    >
      <div className="flex items-stretch">
        <div className="flex-1 px-4 py-3 space-y-2">
          {/* Top seed row */}
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="font-mono text-[10px] tracking-wider text-[var(--muted)] w-6 shrink-0"
                style={{ letterSpacing: "0.06em" }}
              >
                #{series.top_seed}
              </span>
              <span
                className="inline-block w-2 h-2 rounded-full shrink-0"
                style={{ background: topColor }}
                aria-hidden
              />
              <span
                className="text-sm font-semibold truncate text-[var(--foreground)]"
                style={{ fontFamily: "var(--font-display)" }}
              >
                {topAbbr}
              </span>
            </div>
            <span
              className={`font-mono text-sm tabular-nums ${
                topIsWinner ? "text-[var(--accent)] font-bold" : "text-[var(--foreground)]"
              }`}
            >
              {series.top_wins}
            </span>
          </div>

          {/* Bottom seed row */}
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="font-mono text-[10px] tracking-wider text-[var(--muted)] w-6 shrink-0"
                style={{ letterSpacing: "0.06em" }}
              >
                #{series.bottom_seed}
              </span>
              <span
                className="inline-block w-2 h-2 rounded-full shrink-0"
                style={{ background: bottomColor }}
                aria-hidden
              />
              <span
                className="text-sm font-semibold truncate text-[var(--foreground)]"
                style={{ fontFamily: "var(--font-display)" }}
              >
                {bottomAbbr}
              </span>
            </div>
            <span
              className={`font-mono text-sm tabular-nums ${
                bottomIsWinner ? "text-[var(--accent)] font-bold" : "text-[var(--foreground)]"
              }`}
            >
              {series.bottom_wins}
            </span>
          </div>

          {/* Status pill */}
          <div className="flex items-center justify-between pt-1">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide ${statusPillClass(
                series.status
              )}`}
              style={{ letterSpacing: "0.06em" }}
            >
              {statusLabel(series)}
            </span>
            <span className="text-[10px] text-[var(--muted)]">
              {series.series_id}
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}
