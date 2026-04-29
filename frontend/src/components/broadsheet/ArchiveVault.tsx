"use client";

import Link from "next/link";

/**
 * Sprint 77 (EB2): offseason-only "Vault" panel — a parchment-style retrospective
 * surface that surfaces last year's bracket while the platform waits for the
 * regular season to start. v1 ships hardcoded archive content; the pill links
 * resolve to known star players from each Finals so the surface remains
 * navigable. Future sprint should swap to a real archive API (backlog).
 */

interface FinalsArchiveEntry {
  readonly year: string;
  readonly playerId: number;
  readonly displayName: string;
}

const FINALS_ARCHIVE: ReadonlyArray<FinalsArchiveEntry> = [
  { year: "2024", playerId: 1628369, displayName: "Tatum" },
  { year: "2023", playerId: 203999, displayName: "Jokić" },
  { year: "2022", playerId: 201939, displayName: "Curry" },
  { year: "2021", playerId: 203507, displayName: "Antetokounmpo" },
  { year: "2020", playerId: 2544, displayName: "LeBron" },
];

export default function ArchiveVault() {
  return (
    <section
      aria-labelledby="archive-vault-heading"
      className="bip-panel relative overflow-hidden rounded-[1.85rem] p-8 sm:p-10"
    >
      {/* Parchment ambience */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-60"
        style={{
          background:
            "radial-gradient(circle at 20% 0%, rgba(180, 137, 61, 0.10), transparent 55%), radial-gradient(circle at 95% 85%, rgba(33, 72, 59, 0.08), transparent 60%)",
        }}
      />

      <div className="relative">
        <p className="bip-kicker mb-3">The Vault</p>
        <h2
          id="archive-vault-heading"
          className="bip-display text-3xl sm:text-4xl font-semibold text-[var(--foreground)]"
        >
          Last year&rsquo;s bracket
        </h2>

        {/* Finals MVP block */}
        <div className="mt-6 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 sm:p-6">
          <p className="bip-kicker mb-2">Finals MVP</p>
          <p className="bip-display text-xl sm:text-2xl text-[var(--foreground)]">
            Nikola Jokić
          </p>
          <p className="mt-1 text-sm text-[var(--muted)]">
            2025 Finals MVP &middot; 30.2 / 14.0 / 9.6 across 5 games
          </p>
        </div>

        {/* Historical Finals tag cloud */}
        <div className="mt-7">
          <p className="bip-kicker mb-3">Past Finals</p>
          <div className="flex flex-wrap gap-2">
            {FINALS_ARCHIVE.map((entry) => (
              <Link
                key={entry.year}
                href={`/players/${entry.playerId}`}
                className="bip-pill text-xs hover:border-[var(--accent)] hover:text-[var(--accent)] transition-colors"
              >
                {entry.year} Finals &middot; {entry.displayName}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
