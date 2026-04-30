"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getProspectDetail } from "@/lib/api";
import type { ProspectDetail, NbaComp } from "@/lib/types";

function formatHeight(inches: number | null): string {
  if (inches === null || inches === undefined) return "—";
  const ft = Math.floor(inches / 12);
  const inch = Math.round(inches % 12);
  return `${ft}'${inch}"`;
}

function formatPct(value: number | null): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function ConfidencePill({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const tone =
    confidence >= 0.75 ? "bg-[var(--success-tint)] text-[var(--success-ink)]"
    : confidence >= 0.5 ? "bg-[var(--warn-tint)] text-[var(--warn-ink)]"
    : "bg-[var(--danger-tint)] text-[var(--danger-ink)]";
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${tone}`}>
      Confidence {pct}%
    </span>
  );
}

function StatStrip({ label, items }: { label: string; items: { key: string; value: string }[] }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
        {items.map((it) => (
          <div key={it.key}>
            <p className="text-[10px] uppercase tracking-wide text-[var(--muted)]">{it.key}</p>
            <p className="mt-1 text-lg font-semibold tabular-nums text-[var(--foreground)]">{it.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function CompCard({ comp }: { comp: NbaComp }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[var(--foreground)]">{comp.player_name}</p>
          <p className="text-[11px] text-[var(--muted)]">
            {comp.season} · {comp.team_abbreviation ?? "—"}
            {comp.archetype_label ? ` · ${comp.archetype_label}` : ""}
          </p>
        </div>
        <span className="rounded-full bg-[var(--accent-tint)] px-2 py-0.5 text-[11px] font-semibold text-[var(--accent)]">
          {comp.similarity_score.toFixed(1)}
        </span>
      </div>
      <p className="mt-2 text-xs leading-5 text-[var(--muted)]">{comp.rationale}</p>
      <dl className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-[var(--muted)]">
        <div>
          <dt className="uppercase tracking-wide">PPG</dt>
          <dd className="text-sm tabular-nums text-[var(--foreground)]">{comp.pts_pg?.toFixed(1) ?? "—"}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">RPG</dt>
          <dd className="text-sm tabular-nums text-[var(--foreground)]">{comp.reb_pg?.toFixed(1) ?? "—"}</dd>
        </div>
        <div>
          <dt className="uppercase tracking-wide">APG</dt>
          <dd className="text-sm tabular-nums text-[var(--foreground)]">{comp.ast_pg?.toFixed(1) ?? "—"}</dd>
        </div>
      </dl>
    </div>
  );
}

export default function ProspectDetailPage() {
  const params = useParams<{ prospectId: string }>();
  const prospectId = Number(params?.prospectId);
  const [detail, setDetail] = useState<ProspectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(prospectId)) return;
    let cancelled = false;
    setError(null);
    getProspectDetail(prospectId)
      .then((data) => {
        if (!cancelled) setDetail(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : String(err);
          setError(message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [prospectId]);

  if (error) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6 text-sm text-[var(--danger-ink)]">
        Could not load prospect: {error}
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-12 text-center text-[var(--muted)]">
        Loading prospect…
      </div>
    );
  }

  const summary = detail.summary;
  const translation = detail.translation;
  const measurement = detail.measurement;
  const latest = detail.college_stats[0] ?? null;

  const perGameStrip = latest
    ? [
        { key: "PPG", value: latest.pts_pg?.toFixed(1) ?? "—" },
        { key: "RPG", value: latest.reb_pg?.toFixed(1) ?? "—" },
        { key: "APG", value: latest.ast_pg?.toFixed(1) ?? "—" },
        { key: "FG%", value: formatPct(latest.fg_pct) },
        { key: "3P%", value: formatPct(latest.fg3_pct) },
        { key: "TS%", value: formatPct(latest.ts_pct) },
        { key: "USG%", value: latest.usg_pct?.toFixed(1) ?? "—" },
      ]
    : [];

  const per100Strip = translation
    ? [
        { key: "PTS/100", value: translation.projected_pts_per100?.toFixed(1) ?? "—" },
        { key: "REB/100", value: translation.projected_reb_per100?.toFixed(1) ?? "—" },
        { key: "AST/100", value: translation.projected_ast_per100?.toFixed(1) ?? "—" },
        { key: "STL/100", value: translation.projected_stl_per100?.toFixed(1) ?? "—" },
        { key: "BLK/100", value: translation.projected_blk_per100?.toFixed(1) ?? "—" },
        { key: "TS%", value: formatPct(translation.projected_ts_pct) },
        { key: "USG%", value: translation.projected_usg_pct?.toFixed(1) ?? "—" },
      ]
    : [];

  return (
    <div className="space-y-6">
      <nav className="text-xs">
        <Link href="/draft" className="text-[var(--muted)] hover:text-[var(--accent)] bip-link">
          ← Back to {summary.draft_year} draft board
        </Link>
      </nav>

      <header className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-4">
            {summary.headshot_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={summary.headshot_url}
                alt={summary.full_name}
                className="h-20 w-20 rounded-full border border-[var(--border)] object-cover"
              />
            ) : (
              <div className="flex h-20 w-20 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface-alt)] text-2xl font-bold text-[var(--muted)]">
                {summary.full_name.split(" ").map((s) => s[0]).join("").slice(0, 2)}
              </div>
            )}
            <div>
              <p className="bip-kicker">Draft prospect</p>
              <h1 className="bip-display mt-1 text-3xl font-bold tracking-tight text-[var(--foreground)]">
                {summary.full_name}
              </h1>
              <p className="mt-1 text-sm text-[var(--muted)]">
                {summary.school ?? "—"}
                {summary.school_type ? ` · ${summary.school_type.replace(/_/g, " ")}` : ""}
                {summary.primary_position ? ` · ${summary.primary_position}` : ""}
              </p>
              <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
                {summary.consensus_rank ? (
                  <span className="rounded-full bg-[var(--accent-tint)] px-2 py-0.5 font-semibold text-[var(--accent)]">
                    Consensus #{summary.consensus_rank}
                  </span>
                ) : null}
                {summary.age_on_draft_day !== null ? (
                  <span className="rounded-full bg-[var(--surface-alt)] px-2 py-0.5 text-[var(--muted)]">
                    Age {summary.age_on_draft_day.toFixed(1)}
                  </span>
                ) : null}
                {summary.height_inches !== null ? (
                  <span className="rounded-full bg-[var(--surface-alt)] px-2 py-0.5 text-[var(--muted)]">
                    {formatHeight(summary.height_inches)}
                  </span>
                ) : null}
                {summary.weight_lbs !== null ? (
                  <span className="rounded-full bg-[var(--surface-alt)] px-2 py-0.5 text-[var(--muted)]">
                    {summary.weight_lbs.toFixed(0)} lbs
                  </span>
                ) : null}
              </div>
            </div>
          </div>

          {translation ? (
            <div className="flex flex-col items-start gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3 text-[11px] text-[var(--muted)] lg:max-w-xs">
              <ConfidencePill confidence={translation.translation_confidence} />
              <p>
                Pace multiplier <span className="font-semibold text-[var(--foreground)]">{translation.pace_multiplier.toFixed(2)}×</span>
                {" "}( {translation.source_league} ≈ {translation.college_pace.toFixed(0)} pos · NBA ≈ {translation.nba_pace.toFixed(0)} pos )
              </p>
              {translation.confidence_factors.length ? (
                <ul className="list-disc pl-4 text-[11px] leading-5">
                  {translation.confidence_factors.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
        </div>
      </header>

      {perGameStrip.length ? (
        <StatStrip label={`Per-game · ${latest?.season ?? ""} · ${latest?.league ?? ""}`} items={perGameStrip} />
      ) : null}

      {per100Strip.length ? (
        <StatStrip label="Translated NBA per-100 projection" items={per100Strip} />
      ) : null}

      <section>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">NBA comps</h2>
        <p className="mt-1 text-xs text-[var(--muted)]">
          Top 5 NBA player-seasons closest to the prospect&apos;s translated z-vector. Score on a 0–100 scale.
        </p>
        {detail.nba_comps.length ? (
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {detail.nba_comps.map((c) => (
              <CompCard key={`${c.player_id}-${c.season}`} comp={c} />
            ))}
          </div>
        ) : (
          <div className="mt-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6 text-sm text-[var(--muted)]">
            Not enough NBA pool depth to compute comps yet — re-run the daily sync.
          </div>
        )}
      </section>

      {measurement ? (
        <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">Measurements</p>
          <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            <div>
              <p className="text-[10px] uppercase tracking-wide text-[var(--muted)]">Height (no shoes)</p>
              <p className="text-lg font-semibold tabular-nums text-[var(--foreground)]">
                {formatHeight(measurement.height_no_shoes)}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wide text-[var(--muted)]">Height (shoes)</p>
              <p className="text-lg font-semibold tabular-nums text-[var(--foreground)]">
                {formatHeight(measurement.height_with_shoes)}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wide text-[var(--muted)]">Wingspan</p>
              <p className="text-lg font-semibold tabular-nums text-[var(--foreground)]">
                {formatHeight(measurement.wingspan)}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wide text-[var(--muted)]">Standing reach</p>
              <p className="text-lg font-semibold tabular-nums text-[var(--foreground)]">
                {formatHeight(measurement.standing_reach)}
              </p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wide text-[var(--muted)]">Weight</p>
              <p className="text-lg font-semibold tabular-nums text-[var(--foreground)]">
                {measurement.weight ? `${measurement.weight.toFixed(0)} lbs` : "—"}
              </p>
            </div>
          </div>
          <p className="mt-3 text-[11px] text-[var(--muted)]">Source: {measurement.source ?? "n/a"}</p>
        </section>
      ) : null}
    </div>
  );
}
