"use client";

import Link from "next/link";
import { useState } from "react";
import { useTeams, useUsageEfficiencyReport } from "@/hooks/usePlayerStats";
import UsageLoadBoard from "./UsageLoadBoard";

function pillTone(category: "overused" | "underused") {
  return category === "overused"
    ? "bg-[rgba(140,58,42,0.08)] text-[var(--danger-ink)]"
    : "bg-[rgba(33,72,59,0.08)] text-[var(--accent-strong)]";
}

export default function UsageEfficiencyDashboard() {
  const [season, setSeason] = useState("2024-25");
  const [team, setTeam] = useState("");
  const [minMinutes, setMinMinutes] = useState(20);
  const { data: teams } = useTeams();
  const { data, isLoading } = useUsageEfficiencyReport(season, team || undefined, minMinutes);

  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <section className="rounded-[2rem] border border-[var(--border-strong)] bg-[linear-gradient(135deg,rgba(248,244,232,0.98),rgba(239,232,214,0.96))] p-6 shadow-[0_24px_80px_rgba(47,43,36,0.08)] sm:p-7">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div className="max-w-3xl">
            <p className="bip-kicker mb-2">Coach Workflow</p>
            <h1 className="bip-display text-4xl font-semibold text-[var(--foreground)]">
              Usage vs Efficiency
            </h1>
            <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
              Find where offensive burden may be misallocated by surfacing over-used inefficients and under-used efficient players.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Season</span>
              <select value={season} onChange={(event) => setSeason(event.target.value)} className="bip-input w-full rounded-2xl px-4 py-3 text-sm">
                {["2025-26", "2024-25", "2023-24", "2022-23"].map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Team</span>
              <select value={team} onChange={(event) => setTeam(event.target.value)} className="bip-input w-full rounded-2xl px-4 py-3 text-sm">
                <option value="">All teams</option>
                {(teams ?? []).map((entry) => (
                  <option key={entry.abbreviation} value={entry.abbreviation}>
                    {entry.abbreviation} · {entry.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Min MPG</span>
              <input
                type="number"
                min="0"
                step="1"
                value={minMinutes}
                onChange={(event) => setMinMinutes(Number(event.target.value) || 0)}
                className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
              />
            </label>
          </div>
        </div>
      </section>

      {data?.warnings?.length ? (
        <section className="rounded-[1.5rem] border border-[rgba(181,145,78,0.24)] bg-[rgba(181,145,78,0.08)] px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Warnings</p>
          <ul className="mt-3 space-y-2 text-sm text-[var(--muted-strong)]">
            {data.warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </section>
      ) : null}

      <UsageLoadBoard
        featureMore={data?.underused_efficients ?? []}
        reduceLoad={data?.overused_inefficients ?? []}
      />

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)]">
          <div className="border-b border-[var(--border)] px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Burden Watch</p>
            <h2 className="mt-1 text-2xl font-semibold text-[var(--foreground)]">Over-Used Inefficients</h2>
          </div>
          <div className="space-y-4 p-5">
            {isLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="h-24 animate-pulse rounded-[1.25rem] bg-[var(--surface-alt)]" />
              ))
            ) : data?.overused_inefficients?.length ? (
              data.overused_inefficients.map((row) => (
                <article key={`${row.player_id}-${row.team_abbreviation}-overused`} className="rounded-[1.25rem] border border-[var(--border)] bg-[rgba(255,255,255,0.7)] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-lg font-semibold text-[var(--foreground)]">
                        <Link href={`/players/${row.player_id}`} className="bip-link">
                          {row.player_name}
                        </Link>{" "}
                        <span className="text-sm font-medium text-[var(--muted-strong)]">{row.team_abbreviation}</span>
                      </div>
                      <div className="mt-1 text-sm text-[var(--muted)]">
                        {row.minutes_pg?.toFixed(1) ?? "—"} MPG · ORTG {row.off_rating?.toFixed(1) ?? "—"}
                      </div>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${pillTone("overused")}`}>
                      overused
                    </span>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-3 text-sm text-[var(--muted-strong)]">
                    <div>USG {row.usg_pct?.toFixed(1) ?? "—"}</div>
                    <div>TS {row.ts_pct != null ? `${(row.ts_pct * 100).toFixed(1)}%` : "—"}</div>
                    <div>TOV {row.tov_pg?.toFixed(1) ?? "—"}</div>
                  </div>
                </article>
              ))
            ) : (
              <div className="rounded-[1.25rem] border border-[var(--border)] px-5 py-8 text-sm text-[var(--muted-strong)]">
                No over-used inefficients crossed the current threshold.
              </div>
            )}
          </div>
        </section>

        <section className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)]">
          <div className="border-b border-[var(--border)] px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Opportunity Watch</p>
            <h2 className="mt-1 text-2xl font-semibold text-[var(--foreground)]">Under-Used Efficient Players</h2>
          </div>
          <div className="space-y-4 p-5">
            {isLoading ? (
              Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="h-24 animate-pulse rounded-[1.25rem] bg-[var(--surface-alt)]" />
              ))
            ) : data?.underused_efficients?.length ? (
              data.underused_efficients.map((row) => (
                <article key={`${row.player_id}-${row.team_abbreviation}-underused`} className="rounded-[1.25rem] border border-[var(--border)] bg-[rgba(255,255,255,0.7)] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-lg font-semibold text-[var(--foreground)]">
                        <Link href={`/players/${row.player_id}`} className="bip-link">
                          {row.player_name}
                        </Link>{" "}
                        <span className="text-sm font-medium text-[var(--muted-strong)]">{row.team_abbreviation}</span>
                      </div>
                      <div className="mt-1 text-sm text-[var(--muted)]">
                        {row.minutes_pg?.toFixed(1) ?? "—"} MPG · ORTG {row.off_rating?.toFixed(1) ?? "—"}
                      </div>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${pillTone("underused")}`}>
                      underused
                    </span>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-3 text-sm text-[var(--muted-strong)]">
                    <div>USG {row.usg_pct?.toFixed(1) ?? "—"}</div>
                    <div>TS {row.ts_pct != null ? `${(row.ts_pct * 100).toFixed(1)}%` : "—"}</div>
                    <div>AST {row.ast_pg?.toFixed(1) ?? "—"}</div>
                  </div>
                </article>
              ))
            ) : (
              <div className="rounded-[1.25rem] border border-[var(--border)] px-5 py-8 text-sm text-[var(--muted-strong)]">
                No under-used efficient players crossed the current threshold.
              </div>
            )}
          </div>
        </section>
      </div>

      <section className="rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)] p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Coach Notes</p>
        <div className="mt-4 space-y-3 text-sm leading-6 text-[var(--muted-strong)]">
          {data?.suggestions?.length ? (
            data.suggestions.map((suggestion) => (
              <div key={`${suggestion.player_name}-${suggestion.category}`} className="rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.7)] px-4 py-3">
                {suggestion.suggestion}
              </div>
            ))
          ) : (
            <div>No redistribution suggestions available for the current filter set.</div>
          )}
        </div>
      </section>
    </div>
  );
}
