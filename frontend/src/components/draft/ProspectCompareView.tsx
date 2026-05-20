// Sprint 105 (Stream A) — side-by-side prospect comparison panel.
//
// Renders a curated subset of the prospect-detail sections for two
// prospects with delta pills on every numeric row. Reuses the existing
// ProspectDetail response shape — no new backend endpoint.

"use client";

import type { ProspectDetail } from "@/lib/types";
import { formatDelta, type DeltaResult } from "@/lib/compare-deltas";

interface Props {
  a: ProspectDetail;
  b: ProspectDetail;
}

function formatHeight(inches: number | null | undefined): string {
  if (inches == null) return "—";
  const ft = Math.floor(inches / 12);
  const inch = Math.round(inches % 12);
  return `${ft}'${inch}"`;
}

function pillToneFor(side: "a" | "b", winner: "a" | "b" | "tie"): string {
  if (winner === "tie") {
    return "bg-[var(--surface-alt)] text-[var(--muted)] border-[var(--border)]";
  }
  if (winner === side) {
    return "bg-[rgba(33,72,59,0.10)] text-[var(--success-ink)] border-[rgba(33,72,59,0.25)]";
  }
  return "bg-[var(--surface-alt)] text-[var(--muted)] border-[var(--border)]";
}

function MetricRow({
  label,
  aValue,
  bValue,
  delta,
  formatValue,
}: {
  label: string;
  aValue: number | null | undefined;
  bValue: number | null | undefined;
  delta: DeltaResult;
  formatValue: (v: number | null | undefined) => string;
}) {
  const aTone = pillToneFor("a", delta.winner);
  const bTone = pillToneFor("b", delta.winner);

  return (
    <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3 py-2 border-b border-[var(--border)] last:border-b-0">
      <div className={`rounded-lg border px-3 py-2 text-right ${aTone}`}>
        <span className="text-[10px] uppercase tracking-wide text-[var(--muted)] block">{label}</span>
        <span className="text-base font-semibold tabular-nums text-[var(--foreground)]">{formatValue(aValue)}</span>
      </div>
      <div className="flex justify-center min-w-[80px]">
        <span
          className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide ${
            delta.missingData
              ? "text-[var(--muted)]"
              : delta.winner === "tie"
              ? "bg-[var(--surface-alt)] text-[var(--muted)]"
              : "bg-[var(--accent-tint)] text-[var(--accent)]"
          }`}
        >
          {delta.label}
        </span>
      </div>
      <div className={`rounded-lg border px-3 py-2 text-left ${bTone}`}>
        <span className="text-[10px] uppercase tracking-wide text-[var(--muted)] block">{label}</span>
        <span className="text-base font-semibold tabular-nums text-[var(--foreground)]">{formatValue(bValue)}</span>
      </div>
    </div>
  );
}

function PairedIdentity({ a, b }: Props) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {[a, b].map((p, idx) => (
        <div key={idx} className="bip-panel-strong rounded-[1.85rem] p-5">
          <p className="bip-kicker">{idx === 0 ? "Prospect A" : "Prospect B"}</p>
          <h2 className="bip-display mt-1 text-2xl font-bold tracking-tight text-[var(--foreground)]">
            {p.summary.full_name}
          </h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {p.summary.school ?? "—"}
            {p.summary.primary_position ? ` · ${p.summary.primary_position}` : ""}
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5 text-[11px]">
            {p.summary.consensus_rank != null ? (
              <span className="rounded-full bg-[var(--accent-tint)] px-2 py-0.5 font-semibold text-[var(--accent)]">
                Consensus #{p.summary.consensus_rank}
              </span>
            ) : null}
            {p.summary.age_on_draft_day != null ? (
              <span className="rounded-full bg-[var(--surface-alt)] px-2 py-0.5 text-[var(--muted)]">
                Age {p.summary.age_on_draft_day.toFixed(1)}
              </span>
            ) : null}
            {p.summary.height_inches != null ? (
              <span className="rounded-full bg-[var(--surface-alt)] px-2 py-0.5 text-[var(--muted)]">
                {formatHeight(p.summary.height_inches)}
              </span>
            ) : null}
            {p.summary.weight_lbs != null ? (
              <span className="rounded-full bg-[var(--surface-alt)] px-2 py-0.5 text-[var(--muted)]">
                {p.summary.weight_lbs.toFixed(0)} lbs
              </span>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ProspectCompareView({ a, b }: Props) {
  // Per-game stats from each prospect's most-recent college season.
  // The backend returns college_stats sorted by season DESC, so [0] is latest.
  const aLatest = a.college_stats[0] ?? null;
  const bLatest = b.college_stats[0] ?? null;

  // Numeric helpers.
  const num1 = (v: number | null | undefined) => (v == null ? "—" : v.toFixed(1));
  const pct1 = (v: number | null | undefined) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);

  const aProfile = a.profile;
  const bProfile = b.profile;

  const aComp = a.historical_comps?.[0];
  const bComp = b.historical_comps?.[0];

  const aFit = a.team_fit_top?.[0];
  const bFit = b.team_fit_top?.[0];

  const aTranslationV2 = a.translation_v2;
  const bTranslationV2 = b.translation_v2;

  return (
    <div className="space-y-6">
      <PairedIdentity a={a} b={b} />

      {/* Per-game */}
      <section className="bip-panel rounded-[1.85rem] p-5">
        <p className="bip-kicker">Per-game · most recent season</p>
        <div className="mt-3">
          <MetricRow
            label="PPG"
            aValue={aLatest?.pts_pg}
            bValue={bLatest?.pts_pg}
            delta={formatDelta(aLatest?.pts_pg, bLatest?.pts_pg, { digits: 1, suffix: " PPG" })}
            formatValue={num1}
          />
          <MetricRow
            label="RPG"
            aValue={aLatest?.reb_pg}
            bValue={bLatest?.reb_pg}
            delta={formatDelta(aLatest?.reb_pg, bLatest?.reb_pg, { digits: 1, suffix: " RPG" })}
            formatValue={num1}
          />
          <MetricRow
            label="APG"
            aValue={aLatest?.ast_pg}
            bValue={bLatest?.ast_pg}
            delta={formatDelta(aLatest?.ast_pg, bLatest?.ast_pg, { digits: 1, suffix: " APG" })}
            formatValue={num1}
          />
          <MetricRow
            label="TS%"
            aValue={aLatest?.ts_pct}
            bValue={bLatest?.ts_pct}
            delta={formatDelta(aLatest?.ts_pct, bLatest?.ts_pct, { asPercent: true })}
            formatValue={pct1}
          />
          <MetricRow
            label="USG%"
            aValue={aLatest?.usg_pct}
            bValue={bLatest?.usg_pct}
            delta={formatDelta(aLatest?.usg_pct, bLatest?.usg_pct, { digits: 1, suffix: "%" })}
            formatValue={(v) => (v == null ? "—" : `${v.toFixed(1)}%`)}
          />
        </div>
      </section>

      {/* Translated NBA per-100 */}
      <section className="bip-panel rounded-[1.85rem] p-5">
        <p className="bip-kicker">Translated NBA per-100</p>
        <div className="mt-3">
          <MetricRow
            label="PTS/100"
            aValue={aTranslationV2?.pts_per100?.point}
            bValue={bTranslationV2?.pts_per100?.point}
            delta={formatDelta(aTranslationV2?.pts_per100?.point, bTranslationV2?.pts_per100?.point, { digits: 1 })}
            formatValue={num1}
          />
          <MetricRow
            label="REB/100"
            aValue={aTranslationV2?.reb_per100?.point}
            bValue={bTranslationV2?.reb_per100?.point}
            delta={formatDelta(aTranslationV2?.reb_per100?.point, bTranslationV2?.reb_per100?.point, { digits: 1 })}
            formatValue={num1}
          />
          <MetricRow
            label="AST/100"
            aValue={aTranslationV2?.ast_per100?.point}
            bValue={bTranslationV2?.ast_per100?.point}
            delta={formatDelta(aTranslationV2?.ast_per100?.point, bTranslationV2?.ast_per100?.point, { digits: 1 })}
            formatValue={num1}
          />
          <MetricRow
            label="TS%"
            aValue={aTranslationV2?.ts_pct?.point}
            bValue={bTranslationV2?.ts_pct?.point}
            delta={formatDelta(aTranslationV2?.ts_pct?.point, bTranslationV2?.ts_pct?.point, { asPercent: true })}
            formatValue={pct1}
          />
        </div>
      </section>

      {/* Archetype + strengths/weaknesses */}
      <section className="bip-panel rounded-[1.85rem] p-5">
        <p className="bip-kicker">Profile synthesis</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
          {[
            { side: "A" as const, profile: aProfile, name: a.summary.full_name },
            { side: "B" as const, profile: bProfile, name: b.summary.full_name },
          ].map(({ side, profile, name }) => (
            <div key={side} className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
              <div className="flex items-center justify-between gap-2 mb-3">
                <span className="text-xs text-[var(--muted)]">{name}</span>
                <span className="inline-flex items-center gap-1 rounded-full bg-[var(--surface-alt)] px-3 py-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted-strong)]">
                  {profile?.archetype_label ?? "—"}
                </span>
              </div>
              <p className="text-[10px] uppercase tracking-wide text-[var(--muted)] mb-1">Strengths</p>
              {profile?.strengths.length ? (
                <ul className="space-y-1 mb-3">
                  {profile.strengths.map((s) => (
                    <li
                      key={s.feature_key}
                      className="flex items-center justify-between rounded border border-[rgba(33,72,59,0.18)] bg-[rgba(33,72,59,0.06)] px-2 py-1 text-xs"
                    >
                      <span className="font-medium text-[var(--foreground)]">{s.label}</span>
                      <span className="tabular-nums text-[var(--muted-strong)]">
                        z {s.z_score >= 0 ? "+" : ""}{s.z_score.toFixed(2)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-[var(--muted)] mb-3">—</p>
              )}
              <p className="text-[10px] uppercase tracking-wide text-[var(--muted)] mb-1">Weaknesses</p>
              {profile?.weaknesses.length ? (
                <ul className="space-y-1">
                  {profile.weaknesses.map((w) => (
                    <li
                      key={w.feature_key}
                      className="flex items-center justify-between rounded border border-[rgba(168,117,58,0.22)] bg-[rgba(168,117,58,0.08)] px-2 py-1 text-xs"
                    >
                      <span className="font-medium text-[var(--foreground)]">{w.label}</span>
                      <span className="tabular-nums text-[var(--muted-strong)]">z {w.z_score.toFixed(2)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-[var(--muted)]">None notable</p>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Top comp + top team fit */}
      <section className="bip-panel rounded-[1.85rem] p-5">
        <p className="bip-kicker">Top comp · top team fit</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
          {[
            { side: "A" as const, comp: aComp, fit: aFit, name: a.summary.full_name },
            { side: "B" as const, comp: bComp, fit: bFit, name: b.summary.full_name },
          ].map(({ side, comp, fit, name }) => (
            <div key={side} className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 space-y-3">
              <p className="text-xs text-[var(--muted)]">{name}</p>
              <div>
                <p className="text-[10px] uppercase tracking-wide text-[var(--muted)]">Top NBA comp</p>
                {comp ? (
                  <p className="mt-1 text-sm font-semibold text-[var(--foreground)]">
                    {comp.player_name}
                    <span className="ml-2 tabular-nums text-[var(--accent)]">{comp.similarity.toFixed(1)}</span>
                    {comp.outcome_tier ? (
                      <span className="ml-2 text-[10px] uppercase tracking-wide text-[var(--muted)]">
                        {comp.outcome_tier.replace(/_/g, " ")}
                      </span>
                    ) : null}
                  </p>
                ) : (
                  <p className="mt-1 text-sm text-[var(--muted)]">—</p>
                )}
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wide text-[var(--muted)]">Best team fit</p>
                {fit ? (
                  <p className="mt-1 text-sm font-semibold text-[var(--foreground)]">
                    {fit.team_abbreviation}
                    <span className="ml-2 tabular-nums text-[var(--accent)]">{fit.fit_score.toFixed(0)}</span>
                    <span className="ml-2 text-[10px] uppercase tracking-wide text-[var(--muted)]">{fit.fit_label.replace(/_/g, " ")}</span>
                  </p>
                ) : (
                  <p className="mt-1 text-sm text-[var(--muted)]">—</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
