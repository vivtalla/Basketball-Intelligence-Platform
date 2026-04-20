"use client";

const WEIGHTS: Array<{ signal: string; label: string; weight: number }> = [
  { signal: "ts_pct", label: "TS%", weight: 0.25 },
  { signal: "pts", label: "PTS", weight: 0.2 },
  { signal: "usg_pct", label: "USG%", weight: 0.2 },
  { signal: "ast", label: "AST", weight: 0.15 },
  { signal: "tov_pct", label: "TOV%", weight: -0.1 },
  { signal: "reb", label: "REB", weight: 0.1 },
];

export function TrajectoryMethodologyDrawer() {
  return (
    <details className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 text-xs text-[var(--muted-strong)]">
      <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
        Trajectory methodology
      </summary>
      <div className="mt-3 space-y-3 leading-5">
        <p>
          <span className="font-semibold text-[var(--foreground)]">Inputs.</span>{" "}
          Per-game splits aggregated two ways: the last N games (recent window)
          and the earlier portion of the season (baseline). Each signal is the
          recent-window mean minus the baseline mean, z-scored across the
          qualifying pool.
        </p>
        <div>
          <p className="font-semibold text-[var(--foreground)]">Signal weights.</p>
          <ul className="mt-1 space-y-0.5">
            {WEIGHTS.map((w) => (
              <li key={w.signal} className="tabular-nums">
                <span className="inline-block w-14">{w.label}</span>
                <span className={w.weight < 0 ? "text-[var(--danger-ink)]" : ""}>
                  {w.weight > 0 ? "+" : ""}
                  {w.weight.toFixed(2)}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-1 text-[11px] text-[var(--muted)]">
            Weighted contributions sum to the overall trajectory_score. TOV% is
            weighted negatively — more turnovers move the score down.
          </p>
        </div>
        <div>
          <p className="font-semibold text-[var(--foreground)]">Gating.</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            <li>Recent window must include ≥ N qualifying games at the minutes threshold.</li>
            <li>Players under the minutes floor drop to the excluded list.</li>
            <li>Rate stats with a shallow sample are flagged as context notes rather than hidden.</li>
          </ul>
        </div>
        <div>
          <p className="font-semibold text-[var(--foreground)]">Labels.</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            <li>
              <span className="font-semibold text-[var(--accent-strong)]">Breaking Out / Quietly Rising</span>
              — trajectory_score above the positive threshold.
            </li>
            <li>
              <span className="font-semibold text-[var(--danger-ink)]">Slumping / Collapsing</span>
              — trajectory_score below the negative threshold.
            </li>
            <li>Everything between reads as Steady — drivers still show underlying movement.</li>
          </ul>
        </div>
      </div>
    </details>
  );
}
