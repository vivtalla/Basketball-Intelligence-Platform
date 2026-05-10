"use client";

import type { GameDetailResponse } from "@/lib/types";

/**
 * Sprint 77 (EB4): Scoreboard chrome variant for `/beta/games/[gameId]`.
 *
 * Wraps the StateBanner + ScoreBanner + Headline triplet into a single
 * dark stadium unit. Renders ONLY the top chrome — the 12 module bodies
 * below the score banner are shared with the Broadsheet variant and live
 * outside this component.
 *
 * Visual notes:
 * - Dark slate/charcoal background gradient.
 * - Cream foreground text.
 * - Large mono numerals for the score (text-7xl on md+, text-6xl on sm).
 * - Pulsing red live dot when `state === "live"`.
 * - Cream-on-dark headline (h1) + italic subhead + byline.
 */

export type GameStateLabel = "live" | "halftime" | "final" | "pre";

interface ScoreboardChromeProps {
  data: GameDetailResponse;
  /**
   * Resolved game-state label for the center status pill. Callers compute
   * this from the same is_complete / phase signal that drives the variant
   * pick so the chrome stays in sync with the variant gate.
   */
  state?: GameStateLabel;
  /**
   * Optional period label for live games (e.g. "Q3 4:32"). Falls back to
   * the broad state label when not provided.
   */
  liveDetail?: string | null;
  /**
   * Editorial headline + subhead. Stays identical to the Broadsheet variant —
   * the chrome only changes the typographic frame, not the editorial copy.
   */
  headline?: string | null;
  subhead?: string | null;
  byline?: string;
}

function formatScore(value: number | null): string {
  return value == null ? "—" : String(value);
}

function statusLabel(state: GameStateLabel, liveDetail?: string | null): string {
  if (state === "live") {
    return liveDetail && liveDetail.trim().length > 0 ? `LIVE · ${liveDetail}` : "LIVE";
  }
  if (state === "halftime") {
    return "HALFTIME";
  }
  if (state === "final") {
    return "FINAL";
  }
  return "TIPOFF";
}

function defaultHeadline(data: GameDetailResponse): string {
  const away = data.away_team_abbreviation ?? data.away_team_name ?? "Away";
  const home = data.home_team_abbreviation ?? data.home_team_name ?? "Home";
  if (data.away_score == null || data.home_score == null) {
    return `${away} at ${home}`;
  }
  const margin = Math.abs(data.home_score - data.away_score);
  const winner = data.home_score > data.away_score ? home : away;
  return `${winner} hold on by ${margin}`;
}

function defaultSubhead(data: GameDetailResponse): string {
  const date = data.game_date ?? "";
  const season = data.season ?? "";
  const context = [date, season].filter((value) => value && value.length > 0).join(" · ");
  return context.length > 0 ? `Inside the possessions that decided ${context}` : "Inside the possessions that decided this game";
}

export default function ScoreboardChrome({
  data,
  state = "final",
  liveDetail = null,
  headline = null,
  subhead = null,
  byline = "CourtVue Editorial",
}: ScoreboardChromeProps) {
  const awayAbbr = data.away_team_abbreviation ?? "AWAY";
  const homeAbbr = data.home_team_abbreviation ?? "HOME";
  const awayName = data.away_team_name ?? "Away";
  const homeName = data.home_team_name ?? "Home";
  const isLive = state === "live";
  const status = statusLabel(state, liveDetail);
  const resolvedHeadline = headline && headline.length > 0 ? headline : defaultHeadline(data);
  const resolvedSubhead = subhead && subhead.length > 0 ? subhead : defaultSubhead(data);

  return (
    <section
      data-variant="scoreboard"
      className="overflow-hidden rounded-[2rem] border border-black/40 bg-gradient-to-b from-[#1a1a1a] to-[#252525] text-[#fbf4e9] shadow-[0_30px_70px_rgba(8,6,4,0.45)]"
    >
      {/* Status strip */}
      <div className="flex items-center justify-between border-b border-white/10 px-6 py-3 text-[11px] font-mono uppercase tracking-[0.24em]">
        <span className="flex items-center gap-2 text-white/70">
          {isLive ? (
            <span
              aria-hidden
              className="inline-block h-2 w-2 animate-pulse rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.85)]"
            />
          ) : (
            <span aria-hidden className="inline-block h-2 w-2 rounded-full bg-white/30" />
          )}
          <span>{isLive ? "Live" : state === "halftime" ? "Halftime" : state === "final" ? "Final" : "Pre-Game"}</span>
        </span>
        <span className="text-white/50">
          {data.game_date ?? "Date unavailable"}
          {data.season ? ` · ${data.season}` : ""}
        </span>
      </div>

      {/* Big scoreboard row: away | center status | home */}
      <div className="grid grid-cols-1 items-center gap-6 px-6 py-8 md:grid-cols-[1fr_auto_1fr] md:px-10 md:py-10">
        {/* Away */}
        <div className="flex items-center justify-center gap-5 md:justify-start">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white/5 text-2xl font-bold tracking-[0.08em] text-white/90 ring-1 ring-white/10 md:h-20 md:w-20 md:text-3xl">
            {awayAbbr}
          </div>
          <div className="flex flex-col">
            <span className="text-[10px] font-mono uppercase tracking-[0.24em] text-white/50">
              Away
            </span>
            <span className="bip-display text-sm text-white/80 md:text-base">{awayName}</span>
            <span className="font-mono text-6xl font-bold tabular-nums leading-none text-white md:text-7xl lg:text-8xl">
              {formatScore(data.away_score)}
            </span>
          </div>
        </div>

        {/* Center status */}
        <div className="flex flex-col items-center gap-2 text-center">
          <span
            className={
              "rounded-full px-4 py-1 text-[11px] font-mono font-bold uppercase tracking-[0.28em] " +
              (isLive
                ? "bg-red-500/15 text-red-300 ring-1 ring-red-500/40"
                : state === "halftime"
                ? "bg-amber-500/15 text-amber-200 ring-1 ring-amber-500/40"
                : "bg-white/10 text-white/70 ring-1 ring-white/20")
            }
          >
            {status}
          </span>
          {data.home_score != null && data.away_score != null ? (
            <span className="text-[10px] font-mono uppercase tracking-[0.24em] text-white/50">
              Margin · {Math.abs(data.home_score - data.away_score)}
            </span>
          ) : null}
        </div>

        {/* Home */}
        <div className="flex items-center justify-center gap-5 md:justify-end md:flex-row-reverse">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-white/5 text-2xl font-bold tracking-[0.08em] text-white/90 ring-1 ring-white/10 md:h-20 md:w-20 md:text-3xl">
            {homeAbbr}
          </div>
          <div className="flex flex-col md:items-end">
            <span className="text-[10px] font-mono uppercase tracking-[0.24em] text-white/50">
              Home
            </span>
            <span className="bip-display text-sm text-white/80 md:text-base">{homeName}</span>
            <span className="font-mono text-6xl font-bold tabular-nums leading-none text-white md:text-7xl lg:text-8xl">
              {formatScore(data.home_score)}
            </span>
          </div>
        </div>
      </div>

      {/* Cream-on-dark headline */}
      <div className="border-t border-white/10 px-6 py-7 md:px-10 md:py-9">
        <p className="text-[11px] font-mono uppercase tracking-[0.28em] text-white/50">
          {byline}
        </p>
        <h1 className="bip-display mt-3 text-3xl font-semibold leading-tight text-white md:text-4xl lg:text-5xl">
          {resolvedHeadline}
        </h1>
        <p className="mt-3 max-w-3xl text-base italic leading-relaxed text-white/75 md:text-lg">
          {resolvedSubhead}
        </p>
      </div>
    </section>
  );
}
