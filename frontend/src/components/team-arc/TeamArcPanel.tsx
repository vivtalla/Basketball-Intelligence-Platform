"use client";

import { useEffect, useMemo, useState } from "react";
import { getTeamArc, getTeamArcWithLevers } from "@/lib/api";
import { humanizeMethodologyVersion } from "@/lib/methodology";
import type {
  TeamArcIncomingPick,
  TeamArcIncomingSigning,
  TeamArcLevers,
  TeamArcResponse,
  TeamArcRosterSummary,
  TeamArcYear,
} from "@/lib/types";

interface TeamArcPanelProps {
  teamAbbreviation: string;
  baseSeason: string;
}

/**
 * Sprint 78 FO4 — Multi-Year Team Arc tab body.
 *
 * Renders four sections:
 *   1. 3-year arc chart (Off Rtg + Def Rtg lines, plus projected wins)
 *   2. Per-year roster table (projected pts_pg, age, contract status)
 *   3. Decision-lever sliders (draft pick at slot N, re-sign player X)
 *   4. Cap-state strip (placeholder if PlayerContract has no rows)
 *
 * Plus a methodology popover (ⓘ) describing the aging-curve methodology.
 */
export default function TeamArcPanel({ teamAbbreviation, baseSeason }: TeamArcPanelProps) {
  const [years, setYears] = useState<number>(3);
  const [response, setResponse] = useState<TeamArcResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [methodologyOpen, setMethodologyOpen] = useState<boolean>(false);

  // Decision-lever inputs.
  const [pickSlot, setPickSlot] = useState<number>(14);
  const [includePick, setIncludePick] = useState<boolean>(false);
  const [pickYear, setPickYear] = useState<number>(() => {
    const baseStart = parseInt(baseSeason.split("-")[0] ?? "2024", 10);
    return baseStart + 1;
  });
  const [resignPlayerId, setResignPlayerId] = useState<number | "">("");
  const [resignSalary, setResignSalary] = useState<number>(25);
  const [releasePlayerId, setReleasePlayerId] = useState<number | "">("");

  // Initial GET load.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getTeamArc(teamAbbreviation, years, baseSeason)
      .then((data) => {
        if (!cancelled) {
          setResponse(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(String(err?.message ?? err));
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [teamAbbreviation, years, baseSeason]);

  const baseRoster = useMemo<TeamArcRosterSummary[]>(
    () => response?.years?.[0]?.roster_summary ?? [],
    [response]
  );

  const handleApplyLevers = async () => {
    setLoading(true);
    setError(null);
    const incomingPicks: TeamArcIncomingPick[] = [];
    if (includePick) {
      incomingPicks.push({
        draft_year: pickYear,
        round: 1,
        expected_slot_low: Math.max(1, pickSlot - 2),
        expected_slot_high: Math.min(60, pickSlot + 2),
      });
    }
    const incomingSignings: TeamArcIncomingSigning[] = [];
    if (resignPlayerId !== "" && resignSalary > 0) {
      incomingSignings.push({
        player_id: Number(resignPlayerId),
        salary: Math.round(resignSalary * 1_000_000),
        years: 1,
      });
    }
    const outgoingReleases: number[] = [];
    if (releasePlayerId !== "") {
      outgoingReleases.push(Number(releasePlayerId));
    }
    const levers: TeamArcLevers = {
      incoming_picks: incomingPicks,
      incoming_signings: incomingSignings,
      outgoing_releases: outgoingReleases,
    };
    try {
      const data = await getTeamArcWithLevers(teamAbbreviation, { years, levers });
      setResponse(data);
    } catch (err) {
      setError(String((err as Error)?.message ?? err));
    } finally {
      setLoading(false);
    }
  };

  if (error) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-300">
        Could not load the multi-year team arc: {error}
      </div>
    );
  }

  if (loading && !response) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-64 rounded-full bg-gray-200 dark:bg-gray-700" />
        <div className="h-64 rounded-2xl bg-gray-200 dark:bg-gray-700" />
        <div className="grid gap-3 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 rounded-2xl bg-gray-200 dark:bg-gray-700" />
          ))}
        </div>
      </div>
    );
  }

  if (!response) return null;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-[var(--foreground)]">
            {response.team_name} — Multi-Year Arc
          </h2>
          <p className="text-sm text-[var(--muted)]">
            Baseline {response.base_season} → projected through{" "}
            {response.years[response.years.length - 1]?.season_label ?? response.base_season}.
            {response.levers_applied.length > 0 ? (
              <span className="ml-2 italic">Levers applied: {response.levers_applied.join("; ")}.</span>
            ) : null}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Horizon</label>
          <select
            value={years}
            onChange={(e) => setYears(parseInt(e.target.value, 10))}
            className="bip-input rounded-xl px-3 py-2 text-sm"
          >
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>
                {n} yr
              </option>
            ))}
          </select>
          <button
            type="button"
            aria-label="Methodology"
            onClick={() => setMethodologyOpen((v) => !v)}
            className="rounded-full border border-[var(--border)] px-3 py-1 text-xs font-semibold"
          >
            ⓘ Methodology
          </button>
        </div>
      </header>

      {methodologyOpen && (
        <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)] p-5 text-sm leading-6 text-[var(--muted-strong)]">
          <h3 className="text-sm font-semibold text-[var(--foreground)]">
            Methodology — {humanizeMethodologyVersion(response.methodology_version)}
          </h3>
          <ul className="mt-2 list-disc pl-5 space-y-1">
            <li>
              Aging curves are computed empirically from every regular-season{" "}
              <code>SeasonStat</code> row in the database, bucketed by primary
              position (G / F / C). Sparse buckets fall back to the league-wide
              curve.
            </li>
            <li>
              For each rostered player we apply the multiplicative delta between
              adjacent ages on the curve to their most recent line. Year 0 is
              the player&apos;s actual baseline; years 1+ are projected.
            </li>
            <li>
              Team off / def / net ratings are proxies derived from the team&apos;s
              aggregated win-share total relative to the league average team
              (~41 WS). Projected wins use the standard rule of thumb that each
              +1 of net rating ≈ 2.7 wins per 82.
            </li>
            <li>
              Levers (incoming picks, incoming signings, outgoing releases) are
              non-mutating overrides applied at projection time. Cap state uses
              the live <code>PlayerContract</code> table when populated.
            </li>
          </ul>
          {response.warnings.length > 0 && (
            <p className="mt-3 text-xs text-amber-600 dark:text-amber-400">
              Warnings: {response.warnings.join(" / ")}
            </p>
          )}
        </div>
      )}

      <ArcChart years={response.years} />

      <div className="grid gap-6 xl:grid-cols-[1.4fr,1fr]">
        <RosterTable years={response.years} />
        <LeverPanel
          baseRoster={baseRoster}
          pickYear={pickYear}
          setPickYear={setPickYear}
          pickSlot={pickSlot}
          setPickSlot={setPickSlot}
          includePick={includePick}
          setIncludePick={setIncludePick}
          resignPlayerId={resignPlayerId}
          setResignPlayerId={setResignPlayerId}
          resignSalary={resignSalary}
          setResignSalary={setResignSalary}
          releasePlayerId={releasePlayerId}
          setReleasePlayerId={setReleasePlayerId}
          onApply={handleApplyLevers}
          loading={loading}
        />
      </div>

      <CapStateStrip capState={response.cap_state} />
    </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────────────
interface ArcChartProps {
  years: TeamArcYear[];
}

/**
 * Compact SVG line chart for projected off / def / net ratings over the
 * arc horizon. Keeps dependencies minimal — no Recharts. Net rating is
 * highlighted as the primary read.
 */
function ArcChart({ years }: ArcChartProps) {
  const width = 720;
  const height = 220;
  const padding = { top: 28, right: 24, bottom: 36, left: 56 };

  const points = years.map((y, idx) => ({
    idx,
    label: y.season_label,
    off: y.projected_off_rtg ?? null,
    def: y.projected_def_rtg ?? null,
    net: y.projected_net_rtg ?? null,
    wins: y.projected_wins ?? null,
  }));

  const allValues = points.flatMap((p) => [p.off, p.def].filter((v): v is number => v != null));
  if (allValues.length === 0) {
    return (
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 text-sm text-[var(--muted)]">
        Not enough projected-stat coverage to draw the arc chart yet.
      </div>
    );
  }

  const yMin = Math.min(...allValues) - 2;
  const yMax = Math.max(...allValues) + 2;
  const xStep = (width - padding.left - padding.right) / Math.max(1, points.length - 1);

  function xPx(idx: number) {
    return padding.left + xStep * idx;
  }
  function yPx(value: number) {
    const usable = height - padding.top - padding.bottom;
    return padding.top + usable - ((value - yMin) / (yMax - yMin)) * usable;
  }

  function buildPath(field: "off" | "def") {
    return points
      .map((p, i) => {
        if (p[field] == null) return null;
        const cmd = i === 0 ? "M" : "L";
        return `${cmd}${xPx(i).toFixed(1)},${yPx(p[field] as number).toFixed(1)}`;
      })
      .filter(Boolean)
      .join(" ");
  }

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Projected ratings arc
          </div>
          <div className="text-sm text-[var(--muted)]">
            Year-on-year off / def rating projection from aging-curve roll-up.
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-2 w-3 rounded-sm bg-emerald-500" />
            Off Rtg
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-2 w-3 rounded-sm bg-rose-500" />
            Def Rtg
          </span>
        </div>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Multi-year ratings arc">
        {/* Y axis grid */}
        {[yMin, (yMin + yMax) / 2, yMax].map((tick, i) => (
          <g key={`y-${i}`}>
            <line
              x1={padding.left}
              x2={width - padding.right}
              y1={yPx(tick)}
              y2={yPx(tick)}
              stroke="var(--border)"
              strokeDasharray="2,3"
            />
            <text
              x={padding.left - 8}
              y={yPx(tick) + 3}
              fontSize={10}
              textAnchor="end"
              fill="var(--muted)"
            >
              {tick.toFixed(1)}
            </text>
          </g>
        ))}
        {/* X axis labels */}
        {points.map((p, i) => (
          <text
            key={p.label}
            x={xPx(i)}
            y={height - padding.bottom + 16}
            fontSize={10}
            textAnchor="middle"
            fill="var(--muted)"
          >
            {p.label}
          </text>
        ))}
        <path d={buildPath("off")} fill="none" stroke="rgb(16,185,129)" strokeWidth={2} />
        <path d={buildPath("def")} fill="none" stroke="rgb(244,63,94)" strokeWidth={2} />
        {points.map((p, i) =>
          p.off != null ? (
            <circle key={`o-${i}`} cx={xPx(i)} cy={yPx(p.off)} r={3} fill="rgb(16,185,129)" />
          ) : null
        )}
        {points.map((p, i) =>
          p.def != null ? (
            <circle key={`d-${i}`} cx={xPx(i)} cy={yPx(p.def)} r={3} fill="rgb(244,63,94)" />
          ) : null
        )}
      </svg>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {points.map((p) => (
          <div key={p.label} className="rounded-xl bg-[var(--surface-alt)] p-3 text-center">
            <div className="text-[10px] uppercase tracking-[0.18em] text-[var(--muted)]">
              {p.label}
            </div>
            <div className="mt-1 text-lg font-semibold tabular-nums text-[var(--foreground)]">
              {p.wins != null ? `${p.wins.toFixed(1)} W` : "—"}
            </div>
            <div className="text-[11px] text-[var(--muted)]">
              Net {p.net != null ? p.net.toFixed(1) : "—"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

interface RosterTableProps {
  years: TeamArcYear[];
}

function RosterTable({ years }: RosterTableProps) {
  const [activeYear, setActiveYear] = useState<number>(0);
  const year = years[activeYear] ?? years[0];
  if (!year) return null;
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm font-semibold text-[var(--foreground)]">
          Projected roster — {year.season_label}
        </div>
        <div className="flex flex-wrap gap-1">
          {years.map((y, i) => (
            <button
              key={y.season_label}
              type="button"
              onClick={() => setActiveYear(i)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                i === activeYear
                  ? "bg-[var(--accent)] text-[var(--surface)]"
                  : "bg-[var(--surface-alt)] text-[var(--foreground)]"
              }`}
            >
              {y.season_label}
            </button>
          ))}
        </div>
      </div>
      <div className="max-h-96 overflow-auto rounded-xl border border-[var(--border)]">
        <table className="w-full text-sm">
          <thead className="bg-[var(--surface-alt)] text-xs uppercase tracking-[0.14em] text-[var(--muted)]">
            <tr>
              <th className="px-3 py-2 text-left">Player</th>
              <th className="px-3 py-2 text-right">Age</th>
              <th className="px-3 py-2 text-right">PTS</th>
              <th className="px-3 py-2 text-right">TS%</th>
              <th className="px-3 py-2 text-right">MIN</th>
              <th className="px-3 py-2 text-right">WS</th>
              <th className="px-3 py-2 text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            {year.roster_summary.map((row) => (
              <tr key={row.player_id} className="border-t border-[var(--border)]">
                <td className="px-3 py-2 text-left text-[var(--foreground)]">
                  {row.player_name}
                  {row.position ? (
                    <span className="ml-1 text-xs text-[var(--muted)]">· {row.position}</span>
                  ) : null}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">{row.age}</td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {row.projected_pts_pg != null ? row.projected_pts_pg.toFixed(1) : "—"}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {row.projected_ts_pct != null ? `${(row.projected_ts_pct * 100).toFixed(1)}%` : "—"}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {row.projected_min_pg != null ? row.projected_min_pg.toFixed(1) : "—"}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {row.projected_win_share != null ? row.projected_win_share.toFixed(1) : "—"}
                </td>
                <td className="px-3 py-2 text-left text-xs text-[var(--muted)]">
                  {row.contract_status ?? "—"}
                </td>
              </tr>
            ))}
            {year.roster_summary.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-sm text-[var(--muted)]">
                  No projected roster rows for {year.season_label}.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

interface LeverPanelProps {
  baseRoster: TeamArcRosterSummary[];
  pickYear: number;
  setPickYear: (n: number) => void;
  pickSlot: number;
  setPickSlot: (n: number) => void;
  includePick: boolean;
  setIncludePick: (v: boolean) => void;
  resignPlayerId: number | "";
  setResignPlayerId: (v: number | "") => void;
  resignSalary: number;
  setResignSalary: (n: number) => void;
  releasePlayerId: number | "";
  setReleasePlayerId: (v: number | "") => void;
  onApply: () => void;
  loading: boolean;
}

function LeverPanel({
  baseRoster,
  pickYear,
  setPickYear,
  pickSlot,
  setPickSlot,
  includePick,
  setIncludePick,
  resignPlayerId,
  setResignPlayerId,
  resignSalary,
  setResignSalary,
  releasePlayerId,
  setReleasePlayerId,
  onApply,
  loading,
}: LeverPanelProps) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 space-y-5">
      <h3 className="text-sm font-semibold text-[var(--foreground)]">Decision levers</h3>

      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-[var(--foreground)]">
          <input
            type="checkbox"
            checked={includePick}
            onChange={(e) => setIncludePick(e.target.checked)}
          />
          Draft a wing at #{pickSlot} ({pickYear})
        </label>
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
          <label className="flex items-center gap-2">
            Year
            <input
              type="number"
              min={2024}
              max={2030}
              value={pickYear}
              onChange={(e) => setPickYear(parseInt(e.target.value, 10))}
              className="bip-input w-24 rounded-lg px-2 py-1"
            />
          </label>
          <label className="flex items-center gap-2">
            Slot
            <input
              type="range"
              min={1}
              max={60}
              value={pickSlot}
              onChange={(e) => setPickSlot(parseInt(e.target.value, 10))}
            />
          </label>
        </div>
      </div>

      <div>
        <label className="text-sm font-medium text-[var(--foreground)]">
          Re-sign player for ${resignSalary}M / yr
        </label>
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
          <select
            value={resignPlayerId}
            onChange={(e) =>
              setResignPlayerId(e.target.value === "" ? "" : Number(e.target.value))
            }
            className="bip-input rounded-lg px-2 py-1"
          >
            <option value="">— none —</option>
            {baseRoster.map((row) => (
              <option key={row.player_id} value={row.player_id}>
                {row.player_name}
              </option>
            ))}
          </select>
          <input
            type="range"
            min={1}
            max={60}
            value={resignSalary}
            onChange={(e) => setResignSalary(parseInt(e.target.value, 10))}
          />
        </div>
      </div>

      <div>
        <label className="text-sm font-medium text-[var(--foreground)]">Release a player</label>
        <select
          value={releasePlayerId}
          onChange={(e) =>
            setReleasePlayerId(e.target.value === "" ? "" : Number(e.target.value))
          }
          className="bip-input mt-2 w-full rounded-lg px-2 py-1 text-xs"
        >
          <option value="">— none —</option>
          {baseRoster.map((row) => (
            <option key={row.player_id} value={row.player_id}>
              {row.player_name}
            </option>
          ))}
        </select>
      </div>

      <button
        type="button"
        onClick={onApply}
        disabled={loading}
        className="bip-btn-primary w-full rounded-full px-4 py-2 text-sm font-medium disabled:opacity-50"
      >
        {loading ? "Recomputing…" : "Apply levers"}
      </button>
    </div>
  );
}

interface CapStateStripProps {
  capState: TeamArcResponse["cap_state"];
}

function CapStateStrip({ capState }: CapStateStripProps) {
  const hasAny = capState.some((c) => c.has_data);
  if (!hasAny) {
    return (
      <div className="rounded-2xl border border-dashed border-[var(--border)] bg-[var(--surface-alt)] p-4 text-sm text-[var(--muted)]">
        Cap state is unavailable — the <code>PlayerContract</code> table is empty for this team.
        Once the FO1 salary ingestion lands, this strip will fill in automatically.
      </div>
    );
  }
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
        Cap state
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {capState.map((c) => (
          <div key={c.season} className="rounded-xl bg-[var(--surface-alt)] p-3">
            <div className="text-[10px] uppercase tracking-[0.18em] text-[var(--muted)]">
              {c.season}
            </div>
            {c.has_data ? (
              <>
                <div className="mt-1 text-base font-semibold tabular-nums text-[var(--foreground)]">
                  ${(c.total_committed / 1_000_000).toFixed(1)}M
                </div>
                <div className="text-[11px] text-[var(--muted)]">
                  {c.contracts_counted} on books · {c.expiring_count} expiring
                </div>
              </>
            ) : (
              <div className="mt-1 text-sm text-[var(--muted)]">No contract data</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
