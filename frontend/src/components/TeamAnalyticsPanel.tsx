"use client";

import type { TeamAnalytics } from "@/lib/types";

interface TeamAnalyticsPanelProps {
  analytics: TeamAnalytics;
}

function pct(v: number | null, digits = 1) {
  return v != null ? `${(v * 100).toFixed(digits)}%` : "—";
}

function f1(v: number | null) {
  return v != null ? v.toFixed(1) : "—";
}

function rankBadge(rank: number | null, lowerIsBetter = false) {
  if (rank == null) return null;
  const isGood = lowerIsBetter ? rank <= 10 : rank <= 10;
  const isBad = lowerIsBetter ? rank >= 21 : rank >= 21;
  const color = isGood
    ? "text-emerald-600 dark:text-emerald-400"
    : isBad
    ? "text-red-500 dark:text-red-400"
    : "text-[var(--muted)]";
  return (
    <span className={`text-[10px] font-medium tabular-nums ${color}`}>
      #{rank}
    </span>
  );
}

interface BigMetricProps {
  label: string;
  value: string;
  rank: number | null;
  /** For defensive rating: lower is better */
  lowerIsBetter?: boolean;
  accent?: boolean;
}

function BigMetric({ label, value, rank, lowerIsBetter = false, accent = false }: BigMetricProps) {
  return (
    <div className={`flex flex-col gap-1 rounded-2xl p-4 ${accent ? "bip-accent-card" : "bip-metric"}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">
          {label}
        </span>
        {rankBadge(rank, lowerIsBetter)}
      </div>
      <div className={`text-3xl font-bold tabular-nums ${accent ? "text-[var(--accent)]" : "text-[var(--foreground)]"}`}>
        {value}
      </div>
    </div>
  );
}

interface FactorRowProps {
  label: string;
  value: string;
  rank: number | null;
  lowerIsBetter?: boolean;
  description: string;
}

function FactorRow({ label, value, rank, lowerIsBetter = false, description }: FactorRowProps) {
  const r = rank ?? 30;
  const isGood = lowerIsBetter ? r <= 10 : r <= 10;
  const isBad = lowerIsBetter ? r >= 21 : r >= 21;
  const barColor = isGood
    ? "bg-emerald-500"
    : isBad
    ? "bg-red-400"
    : "bg-[var(--signal)]";
  // Bar width: rank 1 = 100%, rank 30 = 3%
  const barPct = lowerIsBetter
    ? Math.max(3, Math.round(((31 - r) / 30) * 100))
    : Math.max(3, Math.round(((31 - r) / 30) * 100));

  return (
    <div className="flex items-center gap-4 border-b border-[var(--border)] py-3 last:border-0">
      <div className="w-28 shrink-0">
        <div className="text-sm font-medium text-[var(--foreground)]">{label}</div>
        <div className="mt-0.5 text-[10px] text-[var(--muted)]">{description}</div>
      </div>
      <div className="flex-1 flex items-center gap-2">
        <div className="flex-1 h-2 overflow-hidden rounded-full bg-[var(--surface-alt)]">
          <div
            className={`h-full rounded-full transition-all ${barColor}`}
            style={{ width: `${barPct}%` }}
          />
        </div>
        <span className="w-14 text-right text-sm font-semibold tabular-nums text-[var(--foreground)]">
          {value}
        </span>
      </div>
      <div className="w-8 text-right">
        {rankBadge(rank, lowerIsBetter)}
      </div>
    </div>
  );
}

export default function TeamAnalyticsPanel({ analytics: a }: TeamAnalyticsPanelProps) {
  const netColor =
    a.net_rating != null && a.net_rating > 0
      ? "text-emerald-600 dark:text-emerald-400"
      : a.net_rating != null && a.net_rating < 0
      ? "text-red-500 dark:text-red-400"
      : "text-gray-900 dark:text-gray-100";

  return (
    <div className="space-y-6">
      {/* Record + season headline */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="bip-metric flex items-center gap-3 rounded-2xl px-5 py-3">
          <span className="text-2xl font-bold tabular-nums text-[var(--foreground)]">
            {a.w}–{a.l}
          </span>
          <span className="text-sm text-[var(--muted)]">
            ({(a.w_pct * 100).toFixed(0)}% · {a.gp}G)
          </span>
        </div>
        <div className="text-sm text-[var(--muted)]">
          {a.season} Regular Season
        </div>
      </div>

      {/* Four key ratings */}
      <div>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
          Efficiency Ratings
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <BigMetric label="OFF RTG" value={f1(a.off_rating)} rank={a.off_rating_rank} accent />
          <BigMetric label="DEF RTG" value={f1(a.def_rating)} rank={a.def_rating_rank} lowerIsBetter />
          <div className="bip-metric flex flex-col gap-1 rounded-2xl p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-[0.18em] text-[var(--muted)]">
                NET RTG
              </span>
              {rankBadge(a.net_rating_rank)}
            </div>
            <div className={`text-3xl font-bold tabular-nums ${netColor}`}>
              {a.net_rating != null && a.net_rating > 0 ? "+" : ""}{f1(a.net_rating)}
            </div>
          </div>
          <BigMetric label="PACE" value={f1(a.pace)} rank={a.pace_rank} lowerIsBetter={false} />
        </div>
      </div>

      {/* Four Factors */}
      <div>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
          Four Factors
            <span className="ml-2 text-[10px] font-normal normal-case tracking-normal text-[var(--muted)]">
            Bar = league rank (wider = better)
          </span>
        </h3>
        <div className="bip-table-shell rounded-2xl px-4 py-1">
          <FactorRow
            label="eFG%"
            value={pct(a.efg_pct)}
            rank={a.efg_pct_rank}
            description="Shooting efficiency"
          />
          <FactorRow
            label="TOV%"
            value={pct(a.tov_pct)}
            rank={a.tov_pct_rank}
            lowerIsBetter
            description="Turnover rate"
          />
          <FactorRow
            label="OREB%"
            value={pct(a.oreb_pct)}
            rank={a.oreb_pct_rank}
            description="Offensive rebounding"
          />
          <FactorRow
            label="TS%"
            value={pct(a.ts_pct)}
            rank={a.ts_pct_rank}
            description="True shooting %"
          />
        </div>
      </div>

      {/* Per-game averages */}
      <div>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
          Per-Game Averages
        </h3>
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
          {[
            { label: "PTS", value: f1(a.pts_pg) },
            { label: "REB", value: f1(a.reb_pg) },
            { label: "AST", value: f1(a.ast_pg) },
            { label: "STL", value: f1(a.stl_pg) },
            { label: "BLK", value: f1(a.blk_pg) },
            { label: "TOV", value: f1(a.tov_pg) },
          ].map(({ label, value }) => (
            <div key={label} className="bip-metric rounded-2xl p-3 text-center">
              <div className="text-[10px] uppercase tracking-[0.18em] text-[var(--muted)]">
                {label}
              </div>
              <div className="mt-1 text-xl font-semibold tabular-nums text-[var(--foreground)]">
                {value}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Shooting splits */}
      <div>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
          Shooting
        </h3>
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: "FG%", value: pct(a.fg_pct) },
            { label: "3P%", value: pct(a.fg3_pct) },
            { label: "FT%", value: pct(a.ft_pct) },
          ].map(({ label, value }) => (
            <div key={label} className="bip-metric rounded-2xl p-4 text-center">
              <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                {label}
              </div>
              <div className="mt-2 text-2xl font-semibold tabular-nums text-[var(--foreground)]">
                {value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
