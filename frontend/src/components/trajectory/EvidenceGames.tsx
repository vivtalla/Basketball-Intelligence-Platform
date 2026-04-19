"use client";

import Link from "next/link";
import type { TrajectoryEvidenceGame } from "@/lib/types";

interface Props {
  games: TrajectoryEvidenceGame[];
  teamAbbr: string;
}

export function EvidenceGames({ games, teamAbbr }: Props) {
  if (!games.length) return null;

  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
        Top games driving this swing
      </p>
      <div className="flex flex-wrap gap-2">
        {games.map((g) => (
          <Link
            key={g.game_id}
            href={`/game-explorer?game_id=${g.game_id}&team=${teamAbbr}`}
            className="group flex flex-col gap-0.5 rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs transition hover:border-[var(--accent-strong)] hover:shadow-sm"
          >
            <span className="font-semibold text-[var(--foreground)] group-hover:text-[var(--accent-strong)]">
              {g.headline_stat}
            </span>
            <span className="text-[10px] text-[var(--muted)]">
              {g.opponent ? `vs ${g.opponent}` : "—"}
              {g.result ? ` · ${g.result}` : ""}
              {g.date ? ` · ${g.date}` : ""}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
