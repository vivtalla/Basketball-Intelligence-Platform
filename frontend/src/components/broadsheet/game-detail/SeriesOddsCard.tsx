"use client";

/**
 * Sprint 77 (Stream B / EB3): Series odds card. Renders a 5-card
 * horizontal row of post-game series-odds snapshots. Returns `null` when
 * the underlying `series_odds_history` is missing or empty (i.e., not a
 * playoff game).
 */

import type { SeriesOddsPoint } from "@/lib/types";

interface SeriesOddsCardProps {
  history: SeriesOddsPoint[] | null | undefined;
}

function fmtPct(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

function fmtSwing(swing: number): string {
  const pp = swing * 100;
  if (pp > 0) return `+${pp.toFixed(0)}pp`;
  if (pp < 0) return `${pp.toFixed(0)}pp`;
  return "0pp";
}

function swingArrow(swing: number): string {
  if (swing > 0.005) return "▲";
  if (swing < -0.005) return "▼";
  return "→";
}

function swingColor(swing: number): string {
  if (swing > 0.005) return "var(--success-ink)";
  if (swing < -0.005) return "var(--danger-ink)";
  return "var(--muted)";
}

export default function SeriesOddsCard({ history }: SeriesOddsCardProps) {
  if (!Array.isArray(history) || history.length === 0) {
    return null;
  }

  const cards = history.slice(0, 7);

  return (
    <section
      className="bip-panel rounded-[1.85rem] px-6 py-7"
      style={{ background: "rgba(255,249,241,0.6)" }}
    >
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="bip-kicker">Series odds · post-game snapshots</p>
          <h2
            className="bip-display mt-2 font-bold text-[var(--foreground)]"
            style={{ fontSize: "clamp(1.5rem, 2.2vw, 2rem)", letterSpacing: "-0.02em" }}
          >
            How the math moved
          </h2>
        </div>
      </div>

      <div
        className="grid gap-3"
        style={{
          gridTemplateColumns: `repeat(${Math.min(5, cards.length)}, minmax(0,1fr))`,
        }}
      >
        {cards.map((card) => (
          <article
            key={`odds-${card.game_num}`}
            className="rounded-[1.2rem] border px-4 py-4"
            style={{
              borderColor: "var(--border-strong)",
              background: "rgba(252,255,253,0.65)",
            }}
          >
            <header
              className="text-[10px] uppercase"
              style={{
                fontFamily: "var(--font-geist-mono)",
                letterSpacing: "0.2em",
                color: "var(--muted)",
              }}
            >
              Game {card.game_num}
            </header>
            <div
              className="mt-2 inline-flex rounded-full px-2 py-1 text-[10px] font-semibold uppercase"
              style={{
                background: "var(--accent-soft)",
                color: "var(--accent-strong)",
                fontFamily: "var(--font-geist-mono)",
                letterSpacing: "0.16em",
              }}
            >
              {card.winner_team_abbr}
            </div>
            <div
              className="mt-3 tabular-nums"
              style={{
                fontFamily: "var(--font-geist-mono)",
                fontSize: "1.6rem",
                fontWeight: 700,
                color: "var(--foreground)",
              }}
            >
              {fmtPct(card.top_seed_post_game_odds)}
            </div>
            <div
              className="mt-1 flex items-center gap-1 text-[11px] font-semibold tabular-nums"
              style={{
                fontFamily: "var(--font-geist-mono)",
                color: swingColor(card.swing_pp),
              }}
            >
              <span aria-hidden>{swingArrow(card.swing_pp)}</span>
              <span>{fmtSwing(card.swing_pp)}</span>
            </div>
            <div
              className="mt-2 text-[10px]"
              style={{
                fontFamily: "var(--font-geist-mono)",
                letterSpacing: "0.16em",
                color: "var(--muted)",
              }}
            >
              {card.date}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
