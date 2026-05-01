"use client";

import { useState } from "react";
import { usePlayerSplits } from "@/hooks/usePlayerStats";
import type { PlayerSplitRow } from "@/lib/types";

interface Props {
  playerId: number;
  season: string;
}

const FAMILY_ORDER = ["Location", "Win/Loss", "Days Rest", "Month", "Pre/Post All-Star"];

const FAMILY_LABELS: Record<string, string> = {
  "Location": "Home / Away",
  "Win/Loss": "W / L",
  "Days Rest": "Days Rest",
  "Month": "Month",
  "Pre/Post All-Star": "Pre / Post All-Star",
};

function fmt(v: number | null, d = 1): string {
  if (v == null) return "—";
  return v.toFixed(d);
}
function fmtPct(v: number | null): string {
  if (v == null) return "—";
  return (v * 100).toFixed(1) + "%";
}
function fmtPlusMinus(v: number | null): string {
  if (v == null) return "—";
  return (v >= 0 ? "+" : "") + v.toFixed(1);
}
function plusMinusTone(v: number | null): string {
  if (v == null) return "text-[var(--muted)]";
  return v > 0 ? "text-[var(--success-ink)]" : v < 0 ? "text-[var(--danger-ink)]" : "text-[var(--muted)]";
}
function wPctTone(v: number): string {
  if (v >= 0.6) return "text-[var(--success-ink)]";
  if (v >= 0.45) return "text-[var(--foreground)]";
  return "text-[var(--danger-ink)]";
}

function SplitsSkeleton() {
  return (
    <div className="bip-panel-strong rounded-[2rem] p-6 animate-pulse space-y-4">
      <div className="h-4 w-32 rounded bg-[var(--surface-alt)]" />
      <div className="h-6 w-56 rounded bg-[var(--surface-alt)]" />
      <div className="flex gap-2 mt-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-8 w-24 rounded-full bg-[var(--surface-alt)]" />
        ))}
      </div>
      <div className="space-y-2 mt-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-8 rounded bg-[var(--surface-alt)]" />
        ))}
      </div>
    </div>
  );
}

function SplitTable({ rows }: { rows: PlayerSplitRow[] }) {
  const thCls =
    "py-2 px-3 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)] whitespace-nowrap";
  const tdCls =
    "py-2.5 px-3 text-right tabular-nums text-sm text-[var(--muted-strong)] whitespace-nowrap";
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)]">
            <th className={thCls + " text-left pr-4"}>Split</th>
            <th className={thCls}>GP</th>
            <th className={thCls}>W</th>
            <th className={thCls}>L</th>
            <th className={thCls}>W%</th>
            <th className={thCls}>MIN</th>
            <th className={thCls}>PTS</th>
            <th className={thCls}>REB</th>
            <th className={thCls}>AST</th>
            <th className={thCls}>TOV</th>
            <th className={thCls}>STL</th>
            <th className={thCls}>BLK</th>
            <th className={thCls}>FG%</th>
            <th className={thCls}>3P%</th>
            <th className={thCls}>FT%</th>
            <th className={thCls}>TS%</th>
            <th className={thCls}>USG%</th>
            <th className={thCls}>+/-</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border)]">
          {rows.map((row) => (
            <tr key={row.split_value} className="hover:bg-[rgba(255,255,255,0.4)] transition-colors">
              <td className="py-2.5 px-3 text-left text-sm font-medium text-[var(--foreground)] whitespace-nowrap pr-4">
                {row.label}
              </td>
              <td className={tdCls}>{row.gp}</td>
              <td className={tdCls}>{row.w}</td>
              <td className={tdCls}>{row.l}</td>
              <td
                className={
                  "py-2.5 px-3 text-right tabular-nums text-sm whitespace-nowrap font-medium " +
                  wPctTone(row.w_pct)
                }
              >
                {fmtPct(row.w_pct)}
              </td>
              <td className={tdCls}>{fmt(row.min)}</td>
              <td className={tdCls}>{fmt(row.pts)}</td>
              <td className={tdCls}>{fmt(row.reb)}</td>
              <td className={tdCls}>{fmt(row.ast)}</td>
              <td className={tdCls}>{fmt(row.tov)}</td>
              <td className={tdCls}>{fmt(row.stl)}</td>
              <td className={tdCls}>{fmt(row.blk)}</td>
              <td className={tdCls}>{fmtPct(row.fg_pct)}</td>
              <td className={tdCls}>{fmtPct(row.fg3_pct)}</td>
              <td className={tdCls}>{fmtPct(row.ft_pct)}</td>
              <td className={tdCls}>{fmtPct(row.ts_pct)}</td>
              <td className={tdCls}>{fmtPct(row.usg_pct)}</td>
              <td
                className={
                  "py-2.5 px-3 text-right tabular-nums text-sm whitespace-nowrap font-medium " +
                  plusMinusTone(row.plus_minus)
                }
              >
                {fmtPlusMinus(row.plus_minus)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function PlayerSplitsPanel({ playerId, season }: Props) {
  const { data, isLoading, error } = usePlayerSplits(playerId, season);
  const [activeFamily, setActiveFamily] = useState<string>("");

  if (isLoading) return <SplitsSkeleton />;

  if (error) {
    return (
      <div className="bip-panel rounded-[1.8rem] p-6 text-sm text-[var(--muted-strong)]">
        Situational splits unavailable for {season}.
      </div>
    );
  }

  const presentKeys = new Set(data ? Object.keys(data.families) : []);
  const allFamilies = data
    ? [
        ...FAMILY_ORDER.filter((f) => presentKeys.has(f)),
        ...Object.keys(data.families).filter((f) => !FAMILY_ORDER.includes(f)),
      ]
    : [];

  if (!data || allFamilies.length === 0) {
    return (
      <div className="bip-panel rounded-[1.8rem] p-6 text-sm text-[var(--muted-strong)]">
        No situational splits available for {season}.
      </div>
    );
  }

  const displayedFamily =
    activeFamily && presentKeys.has(activeFamily) ? activeFamily : allFamilies[0];
  const rows = data.families[displayedFamily] ?? [];

  return (
    <div className="space-y-6">
      <section className="bip-panel-strong rounded-[2rem] p-6">
        <p className="bip-kicker">Situational Splits</p>
        <h2
          className="bip-display mt-3 font-semibold text-[var(--foreground)]"
          style={{ fontSize: "1.6rem", lineHeight: 1.15, letterSpacing: "-0.02em" }}
        >
          Performance by game context
        </h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--muted-strong)]">
          Official NBA split stats for the {season} regular season. Powered by{" "}
          <span className="font-medium">stats.nba.com</span>.
        </p>

        <div className="mt-5 flex flex-wrap gap-2">
          {allFamilies.map((family) => (
            <button
              key={family}
              onClick={() => setActiveFamily(family)}
              className={
                "bip-toggle rounded-full px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] transition-colors " +
                (displayedFamily === family ? "bip-toggle-active" : "")
              }
            >
              {FAMILY_LABELS[family] ?? family}
            </button>
          ))}
        </div>
      </section>

      <section className="bip-panel rounded-[1.8rem] p-6">
        {rows.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">
            No data for {FAMILY_LABELS[displayedFamily] ?? displayedFamily}.
          </p>
        ) : (
          <SplitTable rows={rows} />
        )}
      </section>
    </div>
  );
}
