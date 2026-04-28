"use client";

import Link from "next/link";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";

/**
 * Sprint 73: client-side nav links so the conditional "Bracket" item can
 * read `useSeasonPhase()` without forcing the entire layout.tsx to become
 * a client component.
 */
export default function NavLinks() {
  const { isPlayoffs } = useSeasonPhase();

  return (
    <div className="hidden md:flex items-center gap-5">
      <Link href="/ask" className="text-sm text-[var(--muted)] bip-link">
        Ask
      </Link>
      <Link href="/mvp" className="text-sm text-[var(--muted)] bip-link">
        MVP Race
      </Link>
      <Link href="/player-stats" className="text-sm text-[var(--muted)] bip-link">
        Player Stats
      </Link>
      <Link href="/standings" className="text-sm text-[var(--muted)] bip-link">
        Standings
      </Link>
      <Link href="/insights" className="text-sm text-[var(--muted)] bip-link">
        Insights
      </Link>
      <Link href="/metrics" className="text-sm text-[var(--muted)] bip-link">
        Metrics
      </Link>
      <Link href="/compare" className="text-sm text-[var(--muted)] bip-link">
        Compare
      </Link>
      <Link href="/pre-read" className="text-sm text-[var(--muted)] bip-link">
        Pre-Read
      </Link>
      <Link href="/teams" className="text-sm text-[var(--muted)] bip-link">
        Teams
      </Link>
      {isPlayoffs && (
        <Link href="/bracket" className="text-sm text-[var(--muted)] bip-link">
          Bracket
        </Link>
      )}
      <Link href="/coverage" className="text-sm text-[var(--muted)] bip-link">
        Coverage
      </Link>
      <Link href="/learn" className="text-sm text-[var(--muted)] bip-link">
        Learn
      </Link>
    </div>
  );
}
