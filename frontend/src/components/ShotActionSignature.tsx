"use client";

import type { ShotChartShot } from "@/lib/types";

interface ShotActionSignatureProps {
  shots: ShotChartShot[];
}

interface ActionRow {
  action: string;
  attempts: number;
  made: number;
  fgPct: number;
  freq: number;
  threeShare: number;
  avgDistance: number;
}

function formatAction(action: string): string {
  return action
    .replace(/\s*shot$/i, "")
    .replace(/\s*jump\s*/i, " jumper ")
    .replace(/\s+/g, " ")
    .trim();
}

function buildActionRows(shots: ShotChartShot[]): ActionRow[] {
  const total = Math.max(shots.length, 1);
  const buckets = new Map<string, { attempts: number; made: number; threes: number; distance: number }>();

  for (const shot of shots) {
    const action = shot.action_type || "Unspecified";
    const current = buckets.get(action) ?? { attempts: 0, made: 0, threes: 0, distance: 0 };
    current.attempts += 1;
    current.made += shot.shot_made ? 1 : 0;
    current.threes += shot.shot_type === "3PT Field Goal" || shot.distance >= 22 ? 1 : 0;
    current.distance += Math.max(0, shot.distance ?? 0);
    buckets.set(action, current);
  }

  return Array.from(buckets.entries())
    .map(([action, stat]) => ({
      action,
      attempts: stat.attempts,
      made: stat.made,
      fgPct: stat.made / Math.max(stat.attempts, 1),
      freq: stat.attempts / total,
      threeShare: stat.threes / Math.max(stat.attempts, 1),
      avgDistance: stat.distance / Math.max(stat.attempts, 1),
    }))
    .sort((left, right) => right.attempts - left.attempts)
    .slice(0, 8);
}

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export default function ShotActionSignature({ shots }: ShotActionSignatureProps) {
  const rows = buildActionRows(shots);
  const maxAttempts = Math.max(...rows.map((row) => row.attempts), 1);
  const leadingAction = rows[0];
  const jumperShare = rows
    .filter((row) => row.action.toLowerCase().includes("jump"))
    .reduce((sum, row) => sum + row.freq, 0);
  const rimShare = shots.filter((shot) => shot.distance < 8).length / Math.max(shots.length, 1);

  if (rows.length === 0) {
    return null;
  }

  return (
    <section className="rounded-lg border border-[rgba(53,41,33,0.14)] bg-[linear-gradient(135deg,rgba(255,251,246,0.98),rgba(234,219,183,0.58))] p-4 shadow-[0_18px_46px_rgba(46,32,19,0.10)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="bip-kicker mb-2">Shot Creation Fingerprint</p>
          <h3 className="bip-display text-2xl font-bold tracking-tight text-[var(--foreground)]">
            How the attempts are created
          </h3>
          <p className="mt-1 max-w-2xl text-sm font-medium leading-6 text-[var(--muted)]">
            Action mix separates the player&apos;s shot diet from location alone: pull-ups, drives, cuts, hooks, and catch-and-shoot chances can carry very different scouting meaning.
          </p>
        </div>

        <div className="grid grid-cols-3 overflow-hidden rounded-md border border-[rgba(53,41,33,0.14)] bg-[rgba(255,251,246,0.86)] text-sm shadow-sm">
          <div className="border-r border-[rgba(53,41,33,0.12)] px-3 py-2">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted)]">Lead Action</p>
            <p className="mt-1 truncate font-bold text-[var(--foreground)]">{leadingAction ? formatAction(leadingAction.action) : "—"}</p>
          </div>
          <div className="border-r border-[rgba(53,41,33,0.12)] px-3 py-2">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted)]">Jumpers</p>
            <p className="mt-1 font-bold text-[var(--foreground)]">{pct(jumperShare)}</p>
          </div>
          <div className="px-3 py-2">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--muted)]">At Rim</p>
            <p className="mt-1 font-bold text-[var(--foreground)]">{pct(rimShare)}</p>
          </div>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {rows.map((row, index) => {
          const volumeWidth = Math.max(8, (row.attempts / maxAttempts) * 100);
          const makeWidth = Math.max(3, row.fgPct * 100);
          const distanceLeft = Math.min(96, Math.max(4, (row.avgDistance / 32) * 100));

          return (
            <div key={row.action} className="grid gap-2 lg:grid-cols-[220px_1fr_230px] lg:items-center">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="inline-flex h-6 w-6 items-center justify-center rounded-md bg-[var(--surface-ink)] font-mono text-[11px] font-bold text-white">
                    {index + 1}
                  </span>
                  <p className="truncate text-sm font-bold text-[var(--foreground)]">{formatAction(row.action)}</p>
                </div>
                <p className="mt-0.5 text-xs font-medium text-[var(--muted)]">
                  {row.made}/{row.attempts} FG · {row.avgDistance.toFixed(1)} ft avg
                </p>
              </div>

              <div className="relative h-10 rounded-md border border-[rgba(53,41,33,0.12)] bg-[rgba(255,255,255,0.68)]">
                <div
                  className="absolute inset-y-0 left-0 rounded-md bg-[rgba(180,137,61,0.24)]"
                  style={{ width: `${volumeWidth}%` }}
                />
                <div
                  className="absolute inset-y-1 left-1 rounded bg-[rgba(33,72,59,0.74)]"
                  style={{ width: `${Math.min(volumeWidth, makeWidth)}%` }}
                />
                <div
                  className="absolute top-1/2 h-5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--danger-ink)] shadow-sm"
                  style={{ left: `${distanceLeft}%` }}
                  title={`${row.avgDistance.toFixed(1)} ft average distance`}
                />
              </div>

              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="rounded-md border border-[rgba(53,41,33,0.10)] bg-white/70 px-2 py-1.5">
                  <p className="font-bold text-[var(--foreground)]">{pct(row.freq)}</p>
                  <p className="font-medium text-[var(--muted)]">volume</p>
                </div>
                <div className="rounded-md border border-[rgba(53,41,33,0.10)] bg-white/70 px-2 py-1.5">
                  <p className="font-bold text-[var(--foreground)]">{pct(row.fgPct)}</p>
                  <p className="font-medium text-[var(--muted)]">FG</p>
                </div>
                <div className="rounded-md border border-[rgba(53,41,33,0.10)] bg-white/70 px-2 py-1.5">
                  <p className="font-bold text-[var(--foreground)]">{pct(row.threeShare)}</p>
                  <p className="font-medium text-[var(--muted)]">3PA</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 flex flex-wrap gap-3 text-xs font-medium text-[var(--muted)]">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-6 rounded bg-[rgba(180,137,61,0.34)]" />
          Attempt volume
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2 w-6 rounded bg-[rgba(33,72,59,0.74)]" />
          Make rate overlay
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-4 w-1.5 rounded-full bg-[var(--danger-ink)]" />
          Average distance marker
        </span>
      </div>
    </section>
  );
}
