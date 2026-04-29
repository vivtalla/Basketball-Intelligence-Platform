"use client";

import { useState } from "react";
import Link from "next/link";
import useSWR from "swr";
import { getLeaderboard } from "@/lib/api";
import type { LeaderboardEntry, LeaderboardResponse } from "@/lib/types";

/**
 * Top-N leaderboard table for the /leaderboards page. Responds to the
 * Regular Season / Playoffs toggle by re-keying its SWR fetch on
 * `seasonType`. The user can pick a sort stat from the chip row above
 * the table; defaults to PPG.
 */

interface TopLeadersTableProps {
  season: string;
  seasonType: "Regular Season" | "Playoffs";
}

interface StatChoice {
  key: string;
  label: string;
  formatter: (entry: LeaderboardEntry) => string;
  // Where the value lives on the entry. Most are top-level fields, some
  // come from `metric_values`.
  reader: (entry: LeaderboardEntry) => number | null;
}

const STAT_CHOICES: StatChoice[] = [
  {
    key: "pts_pg",
    label: "PPG",
    reader: (e) => e.pts_pg,
    formatter: (e) => (e.pts_pg ?? 0).toFixed(1),
  },
  {
    key: "ast_pg",
    label: "AST",
    reader: (e) => e.ast_pg,
    formatter: (e) => (e.ast_pg ?? 0).toFixed(1),
  },
  {
    key: "reb_pg",
    label: "RPG",
    reader: (e) => e.reb_pg,
    formatter: (e) => (e.reb_pg ?? 0).toFixed(1),
  },
  {
    key: "ts_pct",
    label: "TS%",
    reader: (e) => e.ts_pct,
    formatter: (e) => `${((e.ts_pct ?? 0) * 100).toFixed(1)}%`,
  },
  {
    key: "usg_pct",
    label: "USG%",
    reader: (e) => e.metric_values?.usg_pct ?? null,
    formatter: (e) => {
      const raw = e.metric_values?.usg_pct ?? 0;
      const scaled = raw <= 1.5 ? raw * 100 : raw;
      return `${scaled.toFixed(1)}%`;
    },
  },
  {
    key: "net_rating",
    label: "NET",
    reader: (e) => e.metric_values?.net_rating ?? null,
    formatter: (e) => {
      const v = e.metric_values?.net_rating ?? 0;
      return `${v >= 0 ? "+" : ""}${v.toFixed(1)}`;
    },
  },
];

export default function TopLeadersTable({ season, seasonType }: TopLeadersTableProps) {
  const [statKey, setStatKey] = useState<string>("pts_pg");
  const choice = STAT_CHOICES.find((s) => s.key === statKey) ?? STAT_CHOICES[0];

  const { data, isLoading, error } = useSWR<LeaderboardResponse>(
    [`top-leaders-${seasonType}`, season, statKey],
    () => getLeaderboard(statKey, season, seasonType, 10)
  );

  const entries = data?.entries ?? [];

  return (
    <section className="bip-panel rounded-[1.85rem] overflow-hidden">
      <header className="px-6 py-4 border-b border-[var(--border)] flex items-end justify-between gap-4">
        <div>
          <p className="bip-kicker mb-1">Top Leaders</p>
          <h2
            className="bip-display font-bold text-[var(--foreground)]"
            style={{ fontSize: "1.45rem", letterSpacing: "-0.015em" }}
          >
            {seasonType === "Playoffs"
              ? "The current playoff workload."
              : "The full-season scoreboard."}
          </h2>
        </div>
        <Link
          href={`/player-stats?seasonType=${encodeURIComponent(seasonType)}`}
          className="text-xs bip-link shrink-0 font-medium"
        >
          Full player stats →
        </Link>
      </header>

      {/* Stat picker chips */}
      <div className="px-6 pt-4 flex flex-wrap gap-2">
        {STAT_CHOICES.map((s) => {
          const active = s.key === statKey;
          return (
            <button
              key={s.key}
              type="button"
              onClick={() => setStatKey(s.key)}
              className="rounded-full border px-3 py-1 text-[11px] font-mono font-bold uppercase tracking-[0.14em] transition-colors"
              style={{
                background: active ? "var(--accent)" : "transparent",
                color: active ? "var(--accent-ink)" : "var(--muted)",
                borderColor: active ? "var(--accent)" : "var(--border)",
              }}
            >
              {s.label}
            </button>
          );
        })}
      </div>

      {isLoading && (
        <div className="px-6 py-6 animate-pulse space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-9 rounded bg-[var(--surface-alt)]"
            />
          ))}
        </div>
      )}

      {!isLoading && error && (
        <p
          className="px-6 py-6 text-sm italic text-[var(--muted)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Couldn&rsquo;t load leaders for this season.
        </p>
      )}

      {!isLoading && !error && entries.length === 0 && (
        <p
          className="px-6 py-6 text-sm italic text-[var(--muted)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          No qualifying leaders yet for {seasonType.toLowerCase()}.
        </p>
      )}

      {!isLoading && !error && entries.length > 0 && (
        <div className="px-2 pt-3 pb-2">
          <table className="w-full text-sm">
            <thead>
              <tr
                className="text-[10px] uppercase"
                style={{
                  fontFamily: "var(--font-geist-mono)",
                  letterSpacing: "0.16em",
                  color: "var(--muted)",
                }}
              >
                <th className="text-left px-4 py-2 w-12">#</th>
                <th className="text-left px-2 py-2">Player</th>
                <th className="text-right px-2 py-2 w-14">GP</th>
                <th className="text-right px-2 py-2 w-20">PPG</th>
                <th className="text-right px-2 py-2 w-20">AST</th>
                <th className="text-right px-2 py-2 w-20">RPG</th>
                <th className="text-right px-2 py-2 w-20">TS%</th>
                <th
                  className="text-right px-4 py-2 w-24"
                  style={{ color: "var(--accent)" }}
                >
                  {choice.label}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {entries.map((entry) => (
                <tr
                  key={entry.player_id}
                  className="hover:bg-[rgba(33,72,59,0.05)] transition-colors"
                >
                  <td className="px-4 py-2.5 text-[var(--muted)] tabular-nums">
                    {entry.rank}
                  </td>
                  <td className="px-2 py-2.5">
                    <Link
                      href={`/players/${entry.player_id}`}
                      className="font-semibold text-[var(--foreground)] hover:text-[var(--accent)] transition-colors"
                      style={{
                        fontFamily: "var(--font-display)",
                        letterSpacing: "-0.01em",
                      }}
                    >
                      {entry.player_name}
                    </Link>
                    <span
                      className="ml-2 text-[12px] text-[var(--muted)]"
                      style={{
                        fontFamily: "var(--font-geist-mono)",
                        letterSpacing: "0.06em",
                      }}
                    >
                      {entry.team_abbreviation}
                    </span>
                  </td>
                  <td className="px-2 py-2.5 text-right tabular-nums text-[var(--muted)]">
                    {entry.gp}
                  </td>
                  <td className="px-2 py-2.5 text-right tabular-nums">
                    {(entry.pts_pg ?? 0).toFixed(1)}
                  </td>
                  <td className="px-2 py-2.5 text-right tabular-nums">
                    {(entry.ast_pg ?? 0).toFixed(1)}
                  </td>
                  <td className="px-2 py-2.5 text-right tabular-nums">
                    {(entry.reb_pg ?? 0).toFixed(1)}
                  </td>
                  <td className="px-2 py-2.5 text-right tabular-nums">
                    {((entry.ts_pct ?? 0) * 100).toFixed(1)}
                  </td>
                  <td
                    className="px-4 py-2.5 text-right tabular-nums font-bold"
                    style={{
                      fontFamily: "var(--font-display)",
                      color: "var(--accent)",
                    }}
                  >
                    {choice.formatter(entry)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
