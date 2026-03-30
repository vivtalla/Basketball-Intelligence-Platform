"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useTeams } from "@/hooks/usePlayerStats";

export default function TeamsPage() {
  const { data: teams, error } = useTeams();

  const sortedTeams = useMemo(
    () => [...(teams ?? [])].sort((a, b) => b.player_count - a.player_count),
    [teams]
  );

  if (error) {
    return (
      <div className="max-w-5xl mx-auto py-16 text-center">
        <h1 className="bip-display text-3xl font-semibold text-[var(--foreground)]">
          Team Explorer
        </h1>
        <p className="mt-4 text-[var(--muted)]">
          Team data could not be loaded right now.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="space-y-3">
        <Link
          href="/"
          className="bip-link inline-flex items-center gap-1 text-sm"
        >
          ← Back to Home
        </Link>
        <div>
          <p className="bip-kicker">
            Explore Teams
          </p>
          <h1 className="bip-display text-4xl font-semibold text-[var(--foreground)]">
            Team Explorer
          </h1>
          <p className="mt-2 max-w-2xl text-[var(--muted)]">
            Browse synced NBA rosters and jump into player-level intelligence
            from each team context.
          </p>
        </div>
      </div>

      {!teams && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-40 rounded-3xl bip-panel animate-pulse"
            />
          ))}
        </div>
      )}

      {teams && teams.length === 0 && (
        <div className="bip-empty rounded-3xl p-10 text-center">
          <h2 className="text-xl font-semibold text-[var(--foreground)]">
            No teams have been synced yet
          </h2>
          <p className="mt-2 text-[var(--muted)]">
            Open a few player pages first and their teams will appear here.
          </p>
        </div>
      )}

      {sortedTeams.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {sortedTeams.map((team) => (
            <Link
              key={team.team_id}
              href={`/teams/${team.abbreviation}`}
              className="bip-panel group rounded-3xl p-6 transition-all hover:-translate-y-0.5 hover:border-[rgba(33,72,59,0.28)] hover:shadow-[var(--shadow-strong)]"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="bip-kicker">
                    {team.abbreviation}
                  </p>
                  <h2 className="bip-display mt-2 text-2xl font-semibold text-[var(--foreground)]">
                    {team.name}
                  </h2>
                </div>
                <div className="bip-accent-card rounded-2xl px-3 py-2 text-right">
                  <div className="text-2xl font-bold text-[var(--accent)]">
                    {team.player_count}
                  </div>
                  <div className="text-xs text-[var(--accent)]/80">
                    active players
                  </div>
                </div>
              </div>
              <p className="mt-6 text-sm text-[var(--muted)]">
                Open the roster, identify leading scorers and creators, and
                jump straight into player dashboards.
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
