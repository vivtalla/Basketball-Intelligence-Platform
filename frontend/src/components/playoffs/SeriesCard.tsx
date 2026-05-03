"use client";

import Link from "next/link";
import type { PlayoffSeriesGame, PlayoffSeriesResponse } from "@/lib/types";

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

// Sprint 86 — when the backend provides parent seed + team abbreviations
// (resolved from the parent PlayoffSeries row), render a richer label like
// "winner of 1v8 (OKC/PHX)" for Round-1 parents. Falls back to the Sprint 85
// round-only label "winner of R{n}" when the seed/abbrs are absent.
function parentLabel(
  parentSeriesId: string | null | undefined,
  parentSeed?: number | null,
  parentAbbrs?: string[] | null,
): string {
  if (!parentSeriesId) return "TBD";

  // Parse the parent's round number from its series_id. R1 parents follow
  // the 1v8 / 2v7 / 3v6 / 4v5 pairing convention (seeds sum to 9), so we
  // can derive the matchup string from a single seed. For R2+ parents the
  // seeds do not follow a fixed pattern, so we only render the abbrs.
  const roundMatch = parentSeriesId.match(/-R(\d+)-/);
  const parentRound = roundMatch ? Number(roundMatch[1]) : null;
  const abbrText =
    parentAbbrs && parentAbbrs.length > 0
      ? parentAbbrs.filter(Boolean).join("/")
      : "";

  if (parentRound === 1 && parentSeed != null && abbrText) {
    return `winner of ${parentSeed}v${9 - parentSeed} (${abbrText})`;
  }
  if (abbrText) {
    return `winner of ${abbrText}`;
  }
  if (parentRound != null) {
    return `winner of R${parentRound}`;
  }
  return `winner of ${parentSeriesId}`;
}

function statusLabel(series: PlayoffSeriesResponse): string {
  const topMissing = series.top_seed_team_id == null;
  const bottomMissing = series.bottom_seed_team_id == null;
  if (topMissing || bottomMissing) {
    if (topMissing && bottomMissing) {
      return "Awaiting both arms";
    }
    if (topMissing) {
      return `Awaiting ${parentLabel(
        series.parent_top_series_id,
        series.parent_top_seed,
        series.parent_top_team_abbrs,
      )}`;
    }
    return `Awaiting ${parentLabel(
      series.parent_bottom_series_id,
      series.parent_bottom_seed,
      series.parent_bottom_team_abbrs,
    )}`;
  }
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

// Sprint 83c — compact per-game W/L chip for the SeriesCard score strip.
// Coloring is from the top seed's perspective so a row of chips reads as the
// favorite's series story (green = top seed won, red = top seed lost).
function GameChip({
  game,
  topSeedTeamId,
}: {
  game: PlayoffSeriesGame;
  topSeedTeamId: number | null;
}) {
  const played = game.home_pts != null && game.away_pts != null;
  const topWon =
    played && game.winner_team_id != null && game.winner_team_id === topSeedTeamId;
  const isAway = topSeedTeamId != null && game.away_team_id === topSeedTeamId;
  const topScore = isAway ? game.away_pts : game.home_pts;
  const oppScore = isAway ? game.home_pts : game.away_pts;

  const className =
    "rounded-md border px-2 py-1 text-[10px] font-mono leading-tight " +
    (played
      ? topWon
        ? "border-[var(--success-ink)] bg-[rgba(33,72,59,0.06)] text-[var(--foreground)]"
        : "border-[var(--danger-ink)] bg-[rgba(180,30,30,0.06)] text-[var(--foreground)]"
      : "border-[var(--border)] bg-[var(--surface-alt)] text-[var(--muted)]");

  const title = played
    ? `Game ${game.series_game_num ?? "?"}: ${game.home_team_abbr ?? "TBD"} ${game.home_pts ?? "-"} – ${
        game.away_team_abbr ?? "TBD"
      } ${game.away_pts ?? "-"}`
    : `Game ${game.series_game_num ?? "?"}: not yet played`;

  return (
    <div className={className} title={title}>
      <div className="text-[9px] uppercase tracking-wider opacity-70">
        G{game.series_game_num ?? "?"}
      </div>
      {played ? (
        <>
          <div className="font-semibold tabular-nums">{topScore}</div>
          <div className="opacity-60 tabular-nums">{oppScore}</div>
        </>
      ) : (
        <div className="opacity-40">—</div>
      )}
    </div>
  );
}

interface SeriesCardProps {
  series: PlayoffSeriesResponse;
}

export default function SeriesCard({ series }: SeriesCardProps) {
  // Sprint 85 — auto-advance slots can have one or both seats waiting on a
  // parent series. Treat null team_id as the canonical "TBD" signal so the
  // row renders the muted placeholder regardless of what the abbr field says.
  const topMissing = series.top_seed_team_id == null;
  const bottomMissing = series.bottom_seed_team_id == null;
  const topAbbr = topMissing ? "TBD" : series.top_seed_team_abbr ?? "TBD";
  const bottomAbbr = bottomMissing ? "TBD" : series.bottom_seed_team_abbr ?? "TBD";
  const topColor = topMissing
    ? "var(--border)"
    : tintFor(series.top_seed_team_abbr);
  const bottomColor = bottomMissing
    ? "var(--border)"
    : tintFor(series.bottom_seed_team_abbr);
  const topIsWinner =
    series.status === "closed" && series.top_wins > series.bottom_wins;
  const bottomIsWinner =
    series.status === "closed" && series.bottom_wins > series.top_wins;
  const topParentLabel = topMissing
    ? parentLabel(
        series.parent_top_series_id,
        series.parent_top_seed,
        series.parent_top_team_abbrs,
      )
    : null;
  const bottomParentLabel = bottomMissing
    ? parentLabel(
        series.parent_bottom_series_id,
        series.parent_bottom_seed,
        series.parent_bottom_team_abbrs,
      )
    : null;

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
                {series.top_seed != null ? `#${series.top_seed}` : "—"}
              </span>
              <span
                className="inline-block w-2 h-2 rounded-full shrink-0"
                style={{ background: topColor }}
                aria-hidden
              />
              {topMissing ? (
                <span
                  className="bip-empty inline-flex items-center px-2 py-0.5 rounded-md border border-dashed border-[var(--border)] text-[11px] uppercase tracking-wider text-[var(--muted)]"
                  title={`Awaiting ${topParentLabel}`}
                >
                  TBD · {topParentLabel}
                </span>
              ) : (
                <span
                  className="text-sm font-semibold truncate text-[var(--foreground)]"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {topAbbr}
                </span>
              )}
            </div>
            <span
              className={`font-mono text-sm tabular-nums ${
                topIsWinner ? "text-[var(--accent)] font-bold" : "text-[var(--foreground)]"
              }`}
            >
              {topMissing ? "—" : series.top_wins}
            </span>
          </div>

          {/* Bottom seed row */}
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="font-mono text-[10px] tracking-wider text-[var(--muted)] w-6 shrink-0"
                style={{ letterSpacing: "0.06em" }}
              >
                {series.bottom_seed != null ? `#${series.bottom_seed}` : "—"}
              </span>
              <span
                className="inline-block w-2 h-2 rounded-full shrink-0"
                style={{ background: bottomColor }}
                aria-hidden
              />
              {bottomMissing ? (
                <span
                  className="bip-empty inline-flex items-center px-2 py-0.5 rounded-md border border-dashed border-[var(--border)] text-[11px] uppercase tracking-wider text-[var(--muted)]"
                  title={`Awaiting ${bottomParentLabel}`}
                >
                  TBD · {bottomParentLabel}
                </span>
              ) : (
                <span
                  className="text-sm font-semibold truncate text-[var(--foreground)]"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {bottomAbbr}
                </span>
              )}
            </div>
            <span
              className={`font-mono text-sm tabular-nums ${
                bottomIsWinner ? "text-[var(--accent)] font-bold" : "text-[var(--foreground)]"
              }`}
            >
              {bottomMissing ? "—" : series.bottom_wins}
            </span>
          </div>

          {/* Per-game score chips (Sprint 83c) */}
          {series.games && series.games.length > 0 ? (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {series.games.map((game) => (
                <GameChip
                  key={game.game_id}
                  game={game}
                  topSeedTeamId={series.top_seed_team_id}
                />
              ))}
            </div>
          ) : null}

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
