"use client";

import Image from "next/image";
import Link from "next/link";
import { useMvpRace } from "@/hooks/usePlayerStats";

const SEASON = "2025-26";

function fmt(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "-";
  return value.toFixed(digits);
}

export default function HomeMvpTeaser() {
  const { data, isLoading } = useMvpRace(SEASON, { top: 3, minGp: 20 });
  const candidates = data?.candidates ?? [];

  return (
    <section>
      <div className="mb-4 flex items-end justify-between gap-4">
        <div>
          <h2 className="bip-display text-2xl font-semibold text-[var(--foreground)]">MVP Race</h2>
          <p className="text-sm text-[var(--muted)]">
            {SEASON} award cases with team lift, impact, and recent form.
          </p>
        </div>
        <Link href="/mvp" className="text-sm bip-link">
          Full race board
        </Link>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {isLoading &&
          Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="h-36 animate-pulse rounded-lg border border-[var(--border)] bg-[var(--surface)]" />
          ))}

        {!isLoading &&
          candidates.map((candidate) => (
            <Link
              key={candidate.player_id}
              href="/mvp"
              className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 transition-colors hover:border-[var(--accent)]"
            >
              <div className="flex items-center gap-3">
                <div className="text-xl font-bold tabular-nums text-[var(--accent)]">{candidate.rank}</div>
                <div className="relative h-12 w-12 overflow-hidden rounded-full bg-[var(--surface-alt)]">
                  {candidate.headshot_url && (
                    <Image src={candidate.headshot_url} alt={candidate.player_name} fill className="object-cover object-top" unoptimized />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-[var(--foreground)]">{candidate.player_name}</p>
                  <p className="text-xs text-[var(--muted)]">{candidate.team_abbreviation} - score {fmt(candidate.composite_score)}</p>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
                <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-2 py-2">
                  <p className="text-[10px] uppercase tracking-[0.08em] text-[var(--muted)]">PTS</p>
                  <p className="mt-1 font-semibold tabular-nums">{fmt(candidate.pts_pg)}</p>
                </div>
                <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-2 py-2">
                  <p className="text-[10px] uppercase tracking-[0.08em] text-[var(--muted)]">On/Off</p>
                  <p className="mt-1 font-semibold tabular-nums">
                    {candidate.on_off?.on_off_net == null ? "-" : `${candidate.on_off.on_off_net >= 0 ? "+" : ""}${fmt(candidate.on_off.on_off_net)}`}
                  </p>
                </div>
                <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] px-2 py-2">
                  <p className="text-[10px] uppercase tracking-[0.08em] text-[var(--muted)]">Team</p>
                  <p className="mt-1 font-semibold tabular-nums">
                    {candidate.team_context?.wins != null && candidate.team_context.losses != null
                      ? `${candidate.team_context.wins}-${candidate.team_context.losses}`
                      : "-"}
                  </p>
                </div>
              </div>
            </Link>
          ))}
      </div>
    </section>
  );
}
