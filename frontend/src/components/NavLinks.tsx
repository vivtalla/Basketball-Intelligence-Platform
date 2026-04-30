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
    <div className="hidden md:flex items-center gap-3">
      <Link href="/playoffs" className="text-sm font-medium text-[var(--accent)] whitespace-nowrap bip-link">
        Playoffs
      </Link>
      <Link href="/ask" className="text-xs text-[var(--muted)] whitespace-nowrap bip-link">
        Ask
      </Link>
      <Link href="/mvp" className="text-xs text-[var(--muted)] whitespace-nowrap bip-link">
        MVP Race
      </Link>
      <Link href="/player-stats" className="text-xs text-[var(--muted)] whitespace-nowrap bip-link">
        Player Stats
      </Link>
      <Link href="/standings" className="text-xs text-[var(--muted)] whitespace-nowrap bip-link">
        Standings
      </Link>
      <Link href="/insights" className="text-xs text-[var(--muted)] whitespace-nowrap bip-link">
        Insights
      </Link>
      <Link href="/metrics" className="text-xs text-[var(--muted)] whitespace-nowrap bip-link">
        Metrics
      </Link>
      <Link href="/compare" className="text-xs text-[var(--muted)] whitespace-nowrap bip-link">
        Compare
      </Link>
      <Link href="/pre-read" className="text-xs text-[var(--muted)] whitespace-nowrap bip-link">
        Pre-Read
      </Link>
      <Link href="/teams" className="text-xs text-[var(--muted)] whitespace-nowrap bip-link">
        Teams
      </Link>
      <Link href="/trade-machine" className="text-xs text-[var(--muted)] whitespace-nowrap bip-link">
        Trade Machine
      </Link>
      <Link href="/free-agency" className="text-xs text-[var(--muted)] whitespace-nowrap bip-link">
        Free Agency
      </Link>
      {isPlayoffs && (
        <Link href="/bracket" className="text-xs text-[var(--muted)] whitespace-nowrap bip-link">
          Bracket
        </Link>
      )}
      <Link href="/coverage" className="text-xs text-[var(--muted)] whitespace-nowrap bip-link">
        Coverage
      </Link>
      <Link href="/milestones" className="text-xs text-[var(--muted)] whitespace-nowrap bip-link">
        Milestones
      </Link>
      <Link href="/learn" className="text-xs text-[var(--muted)] whitespace-nowrap bip-link">
        Learn
      </Link>
    </div>
  );
}
