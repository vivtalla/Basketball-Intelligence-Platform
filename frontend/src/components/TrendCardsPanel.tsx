"use client";

import Link from "next/link";
import type { TeamAnalytics, TeamIntelligence } from "@/lib/types";
import MomentumRibbon from "./MomentumRibbon";

interface TrendCardsPanelProps {
  teamAbbreviation: string;
  season: string;
  currentAnalytics?: TeamAnalytics | null;
  priorAnalytics?: TeamAnalytics | null;
  intelligence?: TeamIntelligence | null;
}

function fmt(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : value.toFixed(digits);
}

function signed(value: number | null | undefined, digits = 1) {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function pct(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : `${(value * 100).toFixed(digits)}%`;
}

type CardFormat = "number" | "percent" | "signed";

function trendTone(delta: number | null, inverse = false) {
  if (delta == null) return "text-[var(--muted-strong)]";
  const positive = inverse ? delta <= 0 : delta >= 0;
  return positive ? "text-[var(--accent-strong)]" : "text-[var(--danger-ink)]";
}

function cardLabel(delta: number | null, inverse = false) {
  if (delta == null) return "Limited";
  const positive = inverse ? delta <= 0 : delta >= 0;
  return positive ? "Improving" : "Needs attention";
}

export default function TrendCardsPanel({
  teamAbbreviation,
  season,
  currentAnalytics,
  priorAnalytics,
  intelligence,
}: TrendCardsPanelProps) {
  const cards = [
    {
      title: "Net rating drift",
      value: currentAnalytics?.net_rating,
      delta:
        currentAnalytics?.net_rating != null && priorAnalytics?.net_rating != null
          ? currentAnalytics.net_rating - priorAnalytics.net_rating
          : null,
      summary:
        currentAnalytics?.net_rating != null && priorAnalytics?.net_rating != null
          ? "Season efficiency is moving against the prior baseline."
          : "Use this card as a directional season read.",
      inverse: false,
      format: "signed" as CardFormat,
    },
    {
      title: "Pace drift",
      value: currentAnalytics?.pace,
      delta:
        currentAnalytics?.pace != null && priorAnalytics?.pace != null
          ? currentAnalytics.pace - priorAnalytics.pace
          : null,
      summary:
        currentAnalytics?.pace != null && priorAnalytics?.pace != null
          ? "The team tempo has shifted relative to the previous season frame."
          : "Tempo context is available even when prior season data is sparse.",
      inverse: false,
      format: "number" as CardFormat,
    },
    {
      title: "Turnover pressure",
      value: currentAnalytics?.tov_pct,
      delta:
        currentAnalytics?.tov_pct != null && priorAnalytics?.tov_pct != null
          ? currentAnalytics.tov_pct - priorAnalytics.tov_pct
          : null,
      summary:
        currentAnalytics?.tov_pct != null && priorAnalytics?.tov_pct != null
          ? "Ball security is either stabilizing or leaking possessions."
          : "Possession security is still useful even without a clean prior comparison.",
      inverse: true,
      format: "percent" as CardFormat,
    },
    {
      title: "Shot quality",
      value: currentAnalytics?.ts_pct,
      delta:
        currentAnalytics?.ts_pct != null && priorAnalytics?.ts_pct != null
          ? currentAnalytics.ts_pct - priorAnalytics.ts_pct
          : null,
      summary:
        currentAnalytics?.ts_pct != null && priorAnalytics?.ts_pct != null
          ? "Scoring efficiency is drifting against the earlier season baseline."
          : "True shooting gives a usable shot-quality snapshot.",
      inverse: false,
      format: "percent" as CardFormat,
    },
    {
      title: "Glass control",
      value: currentAnalytics?.oreb_pct,
      delta:
        currentAnalytics?.oreb_pct != null && priorAnalytics?.oreb_pct != null
          ? currentAnalytics.oreb_pct - priorAnalytics.oreb_pct
          : null,
      summary:
        currentAnalytics?.oreb_pct != null && priorAnalytics?.oreb_pct != null
          ? "Second-chance profile is drifting relative to baseline."
          : "Offensive rebounding is a useful weekly trend signal.",
      inverse: false,
      format: "percent" as CardFormat,
    },
    {
      title: "Recent form",
      value: intelligence?.recent_avg_margin,
      delta: intelligence?.recent_avg_margin ?? null,
      summary:
        intelligence?.recent_record
          ? `Recent record: ${intelligence.recent_record}.`
          : "Recent form is the cleanest short-window signal on the page.",
      inverse: false,
      format: "signed" as CardFormat,
    },
  ];

  if (!currentAnalytics) {
    return (
      <section className="bip-panel-strong rounded-[2rem] p-6">
        <div className="bip-kicker">Trend Cards</div>
        <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
          Weekly change signals for {teamAbbreviation}
        </h2>
        <div className="bip-empty mt-6 rounded-3xl p-6 text-sm leading-6">
          Select a team on the page to load trend cards for {season}. The cards stay directional even when some season comparisons are missing.
        </div>
      </section>
    );
  }

  return (
    <section className="bip-panel-strong rounded-[2rem] p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="bip-kicker">Trend Cards</div>
          <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
            What is drifting for {teamAbbreviation}?
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
            These cards emphasize direction and relevance over fake precision, then hand the staff back to Game Explorer when a shift needs game-level inspection.
          </p>
        </div>
        <Link
          href={`/teams/${teamAbbreviation}?tab=decision`}
          className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
        >
          Open decision tools
        </Link>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {cards.map((card) => (
          <article
            key={card.title}
            className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-5"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              {cardLabel(card.delta, card.inverse)}
            </p>
            <h3 className="mt-2 text-xl font-semibold text-[var(--foreground)]">
              {card.title}
            </h3>
            <div className="mt-3 rounded-2xl border border-[rgba(25,52,42,0.08)] bg-[rgba(216,228,221,0.16)] px-3 py-2">
              <MomentumRibbon delta={card.delta} inverse={card.inverse} />
            </div>
            <div className={`mt-4 text-3xl font-bold tabular-nums ${trendTone(card.delta, card.inverse)}`}>
              {card.value == null
                ? "—"
                : card.format === "number"
                ? fmt(card.value)
                : card.format === "signed"
                ? signed(card.value)
                : pct(card.value)}
            </div>
            <div className={`mt-1 text-sm font-medium ${trendTone(card.delta, card.inverse)}`}>
              {card.delta == null
                ? "No prior comparison"
                : `${card.delta >= 0 ? "+" : ""}${card.format === "number" ? fmt(card.delta) : card.format === "signed" ? signed(card.delta) : pct(card.delta)} vs prior season`}
            </div>
            <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
              {card.summary}
            </p>
          </article>
        ))}
      </div>

      {intelligence?.recent_games?.length ? (
        <div className="mt-6">
          <div className="flex items-end justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Recent games
              </p>
              <p className="mt-1 text-sm text-[var(--muted-strong)]">
                Use these games as the first drill-down when a trend card changes.
              </p>
            </div>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {intelligence.recent_games.slice(0, 3).map((game) => {
              const params = new URLSearchParams({
                source: "trend-card",
                source_id: `${teamAbbreviation}:${game.game_id}`,
                team: teamAbbreviation,
                season,
                reason: `${game.opponent_abbreviation ?? "Opponent"} on ${game.game_date ?? "recent date"}`,
                return_to: `/insights?tab=trends&team=${teamAbbreviation}&season=${season}`,
              });
              return (
                <Link
                  key={game.game_id}
                  href={`/games/${game.game_id}?${params.toString()}`}
                  className="rounded-[1.25rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4 transition hover:border-[rgba(33,72,59,0.28)] hover:bg-[rgba(216,228,221,0.24)]"
                >
                  <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                    {game.game_date ?? "Date unavailable"}
                  </div>
                  <div className="mt-1 text-lg font-semibold text-[var(--foreground)]">
                    {game.opponent_abbreviation ?? "Opponent TBD"}
                  </div>
                  <div className="mt-2 text-sm text-[var(--muted-strong)]">
                    {game.result} · {game.margin != null ? signed(game.margin) : "—"} margin
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      ) : null}
    </section>
  );
}
