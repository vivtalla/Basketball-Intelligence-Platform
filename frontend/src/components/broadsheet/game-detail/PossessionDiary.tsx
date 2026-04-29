"use client";

/**
 * Sprint 77 (Stream B / EB3): Possession Diary table for the broadsheet
 * game-detail surface. Renders the top 24 most lead-impactful possessions
 * from `data.possession_diary`, color-tagging the impact column by
 * `impact_tag` (shot / defense / turnover / transition / clutch).
 */

import type { PossessionEntry } from "@/lib/types";

interface PossessionDiaryProps {
  diary: PossessionEntry[] | null | undefined;
}

function impactColor(tag: string): string {
  // Note: `--signal-strong` falls back to `--signal` if not defined in CSS.
  if (tag === "shot") return "var(--success-ink)";
  if (tag === "defense") return "var(--accent)";
  if (tag === "turnover") return "var(--danger-ink)";
  if (tag === "transition") return "var(--signal)";
  if (tag === "clutch") return "var(--signal-strong, var(--signal))";
  return "var(--muted)";
}

function impactBg(tag: string): string {
  if (tag === "shot") return "var(--success-soft)";
  if (tag === "defense") return "var(--accent-soft)";
  if (tag === "turnover") return "var(--danger-soft)";
  if (tag === "transition") return "var(--signal-soft)";
  if (tag === "clutch") return "var(--signal-soft)";
  return "var(--surface-alt)";
}

function describePossession(entry: PossessionEntry): string {
  const action = entry.primary_action_type
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
  const player = entry.primary_player_name;
  if (entry.points_scored > 0) {
    return `${player} · ${action} (${entry.points_scored} pt${entry.points_scored === 1 ? "" : "s"})`;
  }
  return `${player} · ${action}`;
}

function fmtSwing(value: number): string {
  if (value > 0) return `+${value}`;
  if (value < 0) return String(value);
  return "0";
}

export default function PossessionDiary({ diary }: PossessionDiaryProps) {
  const rows = Array.isArray(diary) ? diary.slice(0, 24) : [];
  const ready = rows.length > 0;

  return (
    <section
      className="bip-panel rounded-[1.85rem] px-6 py-7"
      style={{ background: "rgba(255,249,241,0.6)" }}
    >
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="bip-kicker">Possession diary · biggest swings</p>
          <h2
            className="bip-display mt-2 font-bold text-[var(--foreground)]"
            style={{ fontSize: "clamp(1.5rem, 2.2vw, 2rem)", letterSpacing: "-0.02em" }}
          >
            Possessions That Mattered
          </h2>
        </div>
        {ready && (
          <span
            className="rounded-full px-3 py-1 text-[10px] font-semibold uppercase"
            style={{
              background: "var(--accent-soft)",
              color: "var(--accent-strong)",
              fontFamily: "var(--font-geist-mono)",
              letterSpacing: "0.18em",
            }}
          >
            {rows.length} possessions
          </span>
        )}
      </div>

      {ready ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr
                className="border-b text-[10px] uppercase"
                style={{
                  borderColor: "var(--border-strong)",
                  fontFamily: "var(--font-geist-mono)",
                  letterSpacing: "0.18em",
                  color: "var(--muted)",
                }}
              >
                <th className="pb-2 text-left font-semibold">Q</th>
                <th className="pb-2 text-left font-semibold">Time</th>
                <th className="pb-2 text-left font-semibold">Off.</th>
                <th className="pb-2 text-left font-semibold">Description</th>
                <th className="pb-2 text-right font-semibold">Impact</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr
                  key={`pd-${idx}-${row.quarter}-${row.time_remaining}`}
                  className="border-b last:border-0"
                  style={{ borderColor: "var(--border)" }}
                >
                  <td
                    className="py-2 pr-3 text-left tabular-nums"
                    style={{ fontFamily: "var(--font-geist-mono)", color: "var(--foreground)" }}
                  >
                    {row.quarter <= 4 ? `Q${row.quarter}` : `OT${row.quarter - 4}`}
                  </td>
                  <td
                    className="py-2 pr-3 text-left tabular-nums"
                    style={{ fontFamily: "var(--font-geist-mono)", color: "var(--muted)" }}
                  >
                    {row.time_remaining}
                  </td>
                  <td className="py-2 pr-3 text-left">
                    <span
                      className="rounded-full px-2 py-1 text-[10px] font-semibold uppercase"
                      style={{
                        background: "var(--accent-soft)",
                        color: "var(--accent-strong)",
                        fontFamily: "var(--font-geist-mono)",
                        letterSpacing: "0.16em",
                      }}
                    >
                      {row.offense_team_abbr}
                    </span>
                  </td>
                  <td
                    className="py-2 pr-3 text-left text-[var(--foreground)]"
                    style={{ fontFamily: "var(--font-display)" }}
                  >
                    {describePossession(row)}
                  </td>
                  <td className="py-2 text-right">
                    <span
                      className="rounded-full px-2 py-1 text-[11px] font-semibold uppercase tabular-nums"
                      style={{
                        background: impactBg(row.impact_tag),
                        color: impactColor(row.impact_tag),
                        fontFamily: "var(--font-geist-mono)",
                        letterSpacing: "0.14em",
                      }}
                      title={`${row.impact_tag} · swing ${fmtSwing(row.lead_swing)}`}
                    >
                      {row.impact_tag} · {fmtSwing(row.lead_swing)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
            Possession diary not yet available for this game.
          </p>
        </div>
      )}
    </section>
  );
}
