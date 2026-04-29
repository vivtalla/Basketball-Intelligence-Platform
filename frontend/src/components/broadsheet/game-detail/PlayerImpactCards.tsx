"use client";

/**
 * Sprint 77 (Stream B / EB3): Player impact cards — auto-fit grid of the
 * top-5 players ranked by absolute total +/- across the game, with a
 * per-quarter +/- breakdown derived from `data.player_quarter_impact`.
 */

import type { PlayerQuarterImpact } from "@/lib/types";

interface PlayerImpactCardsProps {
  impacts: PlayerQuarterImpact[] | null | undefined;
}

interface PlayerAggregate {
  player_id: number;
  player_name: string;
  team_abbreviation: string;
  total: number;
  byQuarter: Map<number, { plus_minus: number; minutes: number }>;
}

function aggregate(rows: PlayerQuarterImpact[]): PlayerAggregate[] {
  const acc = new Map<number, PlayerAggregate>();
  for (const row of rows) {
    let entry = acc.get(row.player_id);
    if (!entry) {
      entry = {
        player_id: row.player_id,
        player_name: row.player_name,
        team_abbreviation: row.team_abbreviation,
        total: 0,
        byQuarter: new Map(),
      };
      acc.set(row.player_id, entry);
    }
    entry.total += row.plus_minus;
    entry.byQuarter.set(row.quarter, {
      plus_minus: row.plus_minus,
      minutes: row.minutes,
    });
  }
  return Array.from(acc.values()).sort(
    (a, b) => Math.abs(b.total) - Math.abs(a.total)
  );
}

function pmColor(value: number): string {
  if (value > 0) return "var(--success-ink)";
  if (value < 0) return "var(--danger-ink)";
  return "var(--muted)";
}

function pmLabel(value: number): string {
  if (value > 0) return `+${value}`;
  return String(value);
}

export default function PlayerImpactCards({ impacts }: PlayerImpactCardsProps) {
  const rows = Array.isArray(impacts) ? impacts : [];
  const ready = rows.length > 0;
  const top = ready ? aggregate(rows).slice(0, 5) : [];
  const allQuarters = ready
    ? Array.from(new Set(rows.map((r) => r.quarter))).sort((a, b) => a - b)
    : [1, 2, 3, 4];
  const visibleQuarters = allQuarters.length > 0 ? allQuarters.slice(0, 6) : [1, 2, 3, 4];

  return (
    <section className="space-y-4">
      <div>
        <p className="bip-kicker">Per-quarter impact · top swings</p>
        <h2
          className="bip-display mt-2 font-bold text-[var(--foreground)]"
          style={{ fontSize: "clamp(1.5rem, 2.2vw, 2rem)", letterSpacing: "-0.02em" }}
        >
          Plus-Minus by Quarter
        </h2>
        <p
          className="mt-2 italic text-[var(--muted)]"
          style={{ fontFamily: "var(--font-display)", fontSize: "0.95rem" }}
        >
          Top five players ranked by absolute on-court swing. Each block is
          one quarter of game clock.
        </p>
      </div>

      {ready ? (
        <div
          className="grid gap-4"
          style={{
            gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          }}
        >
          {top.map((player) => (
            <article
              key={player.player_id}
              className="bip-panel rounded-[1.4rem] px-5 py-5"
              style={{ background: "rgba(255,249,241,0.7)" }}
            >
              <header className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <h3
                    className="bip-display text-lg font-semibold text-[var(--foreground)]"
                    style={{ letterSpacing: "-0.01em" }}
                  >
                    {player.player_name}
                  </h3>
                  <p
                    className="mt-1 text-[10px] uppercase"
                    style={{
                      fontFamily: "var(--font-geist-mono)",
                      letterSpacing: "0.18em",
                      color: "var(--muted)",
                    }}
                  >
                    {player.team_abbreviation}
                  </p>
                </div>
                <div
                  className="rounded-full px-3 py-1 text-sm font-semibold tabular-nums"
                  style={{
                    fontFamily: "var(--font-geist-mono)",
                    background:
                      player.total >= 0 ? "var(--success-soft)" : "var(--danger-soft)",
                    color: pmColor(player.total),
                  }}
                >
                  {pmLabel(player.total)}
                </div>
              </header>
              <div
                className="grid gap-2"
                style={{
                  gridTemplateColumns: `repeat(${visibleQuarters.length}, minmax(0,1fr))`,
                }}
              >
                {visibleQuarters.map((q) => {
                  const cell = player.byQuarter.get(q);
                  const value = cell?.plus_minus ?? 0;
                  return (
                    <div
                      key={`q-${player.player_id}-${q}`}
                      className="rounded-[0.9rem] px-2 py-2 text-center"
                      style={{
                        background: "rgba(252,255,253,0.6)",
                        border: "1px solid var(--border)",
                      }}
                    >
                      <div
                        className="text-[10px] uppercase"
                        style={{
                          fontFamily: "var(--font-geist-mono)",
                          letterSpacing: "0.18em",
                          color: "var(--muted)",
                        }}
                      >
                        {q <= 4 ? `Q${q}` : `OT${q - 4}`}
                      </div>
                      <div
                        className="mt-1 font-semibold tabular-nums"
                        style={{
                          fontFamily: "var(--font-geist-mono)",
                          color: pmColor(value),
                        }}
                      >
                        {pmLabel(value)}
                      </div>
                      <div
                        className="text-[10px]"
                        style={{
                          fontFamily: "var(--font-geist-mono)",
                          color: "var(--muted)",
                        }}
                      >
                        {cell ? `${cell.minutes.toFixed(0)}m` : "—"}
                      </div>
                    </div>
                  );
                })}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div
          className="rounded-[1.4rem] border border-dashed px-5 py-10 text-center"
          style={{
            borderColor: "var(--border-strong)",
            background: "rgba(252,255,253,0.4)",
          }}
        >
          <p
            className="text-sm italic"
            style={{ fontFamily: "var(--font-display)", color: "var(--muted)" }}
          >
            Per-quarter +/- not yet available for this game.
          </p>
        </div>
      )}
    </section>
  );
}
