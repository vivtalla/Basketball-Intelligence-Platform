"use client";

import Link from "next/link";
import type { StyleNeighbor } from "@/lib/types";

interface Props {
  neighbors: StyleNeighbor[];
  season: string;
}

const QUALITY_STYLE: Record<string, string> = {
  high: "border-[var(--accent-strong)] text-[var(--accent-strong)]",
  medium: "border-[var(--border)] text-[var(--muted-strong)]",
  low: "border-[var(--border)] text-[var(--muted)]",
};

export function NeighborQualityList({ neighbors, season }: Props) {
  if (!neighbors.length) {
    return (
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 text-sm text-[var(--muted)]">
        No neighbor matches yet — the season sample is too thin.
      </div>
    );
  }
  return (
    <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5">
      <header className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-[var(--foreground)]">Nearest neighbors</h3>
        <span className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">
          Style distance
        </span>
      </header>
      <ul className="mt-4 space-y-2">
        {neighbors.map((n) => {
          const quality = n.quality ?? "medium";
          return (
            <li
              key={n.team_abbreviation}
              className="flex items-center justify-between gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-2"
            >
              <div className="flex min-w-0 flex-col">
                <Link
                  href={`/teams/${n.team_abbreviation}?season=${season}`}
                  className="truncate text-sm font-semibold text-[var(--foreground)] hover:text-[var(--accent-strong)]"
                >
                  {n.team_abbreviation} · {n.team_name}
                </Link>
                <span className="truncate text-[11px] text-[var(--muted)]">{n.archetype}</span>
                {n.matchup_label ? (
                  <span className="mt-1 w-fit rounded-full border border-[var(--border)] px-2 py-[2px] text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted-strong)]">
                    {n.matchup_label}
                  </span>
                ) : null}
                <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-[var(--muted-strong)]">{n.summary}</p>
              </div>
              <div className="flex items-center gap-3">
                <span
                  className={`rounded-full border px-2 py-[2px] text-[10px] font-semibold uppercase tracking-[0.14em] ${
                    QUALITY_STYLE[quality] ?? QUALITY_STYLE.medium
                  }`}
                  title={`${quality} quality match (style distance ${n.distance.toFixed(2)})`}
                >
                  {quality}
                </span>
                <span className="w-14 text-right text-[11px] font-semibold tabular-nums text-[var(--muted-strong)]">
                  {n.net_rating == null ? "—" : `${n.net_rating >= 0 ? "+" : ""}${n.net_rating.toFixed(1)}`}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
