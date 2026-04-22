"use client";

import type { StyleShotProfileDriver } from "@/lib/types";

interface Props {
  drivers: StyleShotProfileDriver[];
}

function fmtPct(value: number | null | undefined) {
  if (value == null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function fmtSignedPoints(value: number | null | undefined) {
  if (value == null) return "—";
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1)} pts`;
}

const FAMILY_LABELS: Record<string, string> = {
  ShotAreaTeamDashboard: "Shot Area",
  ShotTypeTeamDashboard: "Shot Type",
  Shot8FTTeamDashboard: "Shot Distance (8ft)",
  Shot5FTTeamDashboard: "Shot Distance (5ft)",
  AssitedShotTeamDashboard: "Assisted Shot",
  OverallTeamDashboard: "Overall",
};

export function ShotProfileDriversCard({ drivers }: Props) {
  if (!drivers.length) return null;

  return (
    <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 lg:col-span-2">
      <header className="flex items-baseline justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Shot Profile Drivers</h3>
          <p className="mt-1 text-xs text-[var(--muted)]">
            Buckets with the biggest volume or efficiency separation versus league peers.
          </p>
        </div>
        <span className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">
          Persisted shooting splits
        </span>
      </header>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {drivers.map((driver) => (
          <article
            key={`${driver.split_family}-${driver.split_value}`}
            className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-xs uppercase tracking-[0.14em] text-[var(--muted)]">
                  {FAMILY_LABELS[driver.split_family] ?? driver.split_family}
                </div>
                <h4 className="mt-1 text-sm font-semibold text-[var(--foreground)]">{driver.label}</h4>
              </div>
              <div className="rounded-full border border-[var(--border)] px-2 py-[2px] text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted-strong)]">
                {fmtSignedPoints(driver.league_delta)}
              </div>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2 text-[11px]">
              <div className="rounded-lg bg-[var(--surface)] px-3 py-2">
                <div className="text-[var(--muted)]">Attempt share</div>
                <div className="mt-1 font-semibold text-[var(--foreground)]">{fmtPct(driver.attempt_share)}</div>
              </div>
              <div className="rounded-lg bg-[var(--surface)] px-3 py-2">
                <div className="text-[var(--muted)]">eFG%</div>
                <div className="mt-1 font-semibold text-[var(--foreground)]">{fmtPct(driver.efg_pct)}</div>
              </div>
              <div className="rounded-lg bg-[var(--surface)] px-3 py-2">
                <div className="text-[var(--muted)]">League delta</div>
                <div className="mt-1 font-semibold text-[var(--foreground)]">{fmtSignedPoints(driver.league_delta)}</div>
              </div>
            </div>

            <p className="mt-3 text-sm leading-5 text-[var(--muted-strong)]">{driver.summary}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
