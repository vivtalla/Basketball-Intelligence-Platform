"use client";

/**
 * Sprint 77 (Stream B / EB3): Lineup grid for the broadsheet game-detail
 * surface. v1 pulls each team's top-5 season lineups via the existing
 * `useLineups` hook and displays them in one combined table with a "lever"
 * badge derived from net rating. Per-game lineup data is not yet wired —
 * we surface an inline caveat.
 */

import { useLineups } from "@/hooks/usePlayerStats";
import type { LineupStatsResponse } from "@/lib/types";

interface LineupGridProps {
  season: string | null;
  awayTeamId: number | null;
  awayAbbr: string | null;
  homeTeamId: number | null;
  homeAbbr: string | null;
}

interface RowData extends LineupStatsResponse {
  _label: string;
}

function leverFor(netRating: number | null): "high" | "med" | "low" {
  if (netRating == null) return "low";
  if (netRating >= 8) return "high";
  if (netRating >= 0) return "med";
  return "low";
}

function leverStyle(level: "high" | "med" | "low"): React.CSSProperties {
  if (level === "high") {
    return { background: "var(--success-soft)", color: "var(--success-ink)" };
  }
  if (level === "med") {
    return { background: "var(--signal-soft)", color: "var(--signal-ink)" };
  }
  return { background: "var(--danger-soft)", color: "var(--danger-ink)" };
}

function fmt(value: number | null, digits = 1, suffix = ""): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${value.toFixed(digits)}${suffix}`;
}

export default function LineupGrid({
  season,
  awayTeamId,
  awayAbbr,
  homeTeamId,
  homeAbbr,
}: LineupGridProps) {
  const awayQuery = useLineups(season, awayTeamId ?? undefined, 5, 5);
  const homeQuery = useLineups(season, homeTeamId ?? undefined, 5, 5);

  const awayRows: RowData[] = (awayQuery.data?.lineups ?? []).map((row) => ({
    ...row,
    _label: awayAbbr ?? "Away",
  }));
  const homeRows: RowData[] = (homeQuery.data?.lineups ?? []).map((row) => ({
    ...row,
    _label: homeAbbr ?? "Home",
  }));

  const rows = [...awayRows, ...homeRows].sort(
    (a, b) => (b.net_rating ?? -Infinity) - (a.net_rating ?? -Infinity)
  );

  const isLoading = awayQuery.isLoading || homeQuery.isLoading;
  const isEmpty = !isLoading && rows.length === 0;

  return (
    <section
      className="bip-panel rounded-[1.85rem] px-6 py-7"
      style={{ background: "rgba(255,249,241,0.6)" }}
    >
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="bip-kicker">Lineups · five-man combinations</p>
          <h2
            className="bip-display mt-2 font-bold text-[var(--foreground)]"
            style={{ fontSize: "clamp(1.5rem, 2.2vw, 2rem)", letterSpacing: "-0.02em" }}
          >
            Five-man levers
          </h2>
        </div>
        <p
          className="text-xs italic"
          style={{
            fontFamily: "var(--font-display)",
            color: "var(--muted)",
            maxWidth: "26rem",
          }}
        >
          Per-game lineup data not yet wired — showing season top-5 per team.
        </p>
      </div>

      {isLoading ? (
        <div
          className="rounded-[1.4rem] border border-dashed px-5 py-10 text-center"
          style={{ borderColor: "var(--border)", background: "rgba(252,255,253,0.4)" }}
        >
          <p
            className="text-sm italic"
            style={{ fontFamily: "var(--font-display)", color: "var(--muted)" }}
          >
            Loading lineup data…
          </p>
        </div>
      ) : isEmpty ? (
        <div
          className="rounded-[1.4rem] border border-dashed px-5 py-10 text-center"
          style={{ borderColor: "var(--border-strong)", background: "rgba(252,255,253,0.4)" }}
        >
          <p
            className="text-sm italic"
            style={{ fontFamily: "var(--font-display)", color: "var(--muted)" }}
          >
            No lineups available for either team this season.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm tabular-nums">
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
                <th className="pb-2 text-left font-semibold">Team</th>
                <th className="pb-2 text-left font-semibold">Lineup</th>
                <th className="pb-2 text-right font-semibold">Min</th>
                <th className="pb-2 text-right font-semibold">Off</th>
                <th className="pb-2 text-right font-semibold">Def</th>
                <th className="pb-2 text-right font-semibold">Net</th>
                <th className="pb-2 text-right font-semibold">Lever</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => {
                const lever = leverFor(row.net_rating);
                return (
                  <tr
                    key={`${row.team_id ?? "x"}-${row.lineup_key}-${idx}`}
                    className="border-b last:border-0"
                    style={{ borderColor: "var(--border)" }}
                  >
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
                        {row._label}
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-left text-[var(--foreground)]">
                      <span style={{ fontFamily: "var(--font-display)" }}>
                        {row.player_names.join(" · ")}
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-right text-[var(--foreground)]">
                      {fmt(row.minutes, 0)}
                    </td>
                    <td className="py-2 pr-3 text-right text-[var(--foreground)]">
                      {fmt(row.ortg)}
                    </td>
                    <td className="py-2 pr-3 text-right text-[var(--foreground)]">
                      {fmt(row.drtg)}
                    </td>
                    <td className="py-2 pr-3 text-right font-semibold text-[var(--foreground)]">
                      {fmt(row.net_rating)}
                    </td>
                    <td className="py-2 text-right">
                      <span
                        className="rounded-full px-2 py-1 text-[10px] font-semibold uppercase"
                        style={{
                          fontFamily: "var(--font-geist-mono)",
                          letterSpacing: "0.16em",
                          ...leverStyle(lever),
                        }}
                      >
                        {lever}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
