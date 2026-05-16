"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";

/**
 * Sprint 73: client-side nav links so the conditional "Bracket" item can
 * read `useSeasonPhase()` without forcing the entire layout.tsx to become
 * a client component.
 *
 * Sprint 83a (A2/B5): Above `sm` we render the top 5 nav items inline plus a
 * "More" dropdown for the rest. Sub-`sm` viewports use MobileNav (hamburger);
 * this component is hidden via `hidden sm:flex`.
 */
export default function NavLinks() {
  const { isPlayoffs } = useSeasonPhase();
  const pathname = usePathname() ?? "/";
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement | null>(null);

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");
  const linkClass = (href: string) =>
    isActive(href)
      ? "text-sm font-medium text-[var(--accent)] whitespace-nowrap bip-link"
      : "text-xs text-[var(--muted)] whitespace-nowrap bip-link";
  const isBetaActive = pathname.startsWith("/beta/");
  const betaTriggerClass = isBetaActive
    ? "text-sm font-medium text-[var(--accent)] whitespace-nowrap bip-link inline-flex items-center gap-1"
    : "text-xs text-[var(--muted)] whitespace-nowrap bip-link inline-flex items-center gap-1";

  useEffect(() => {
    if (!moreOpen) return;
    function onClick(e: MouseEvent) {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) {
        setMoreOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setMoreOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [moreOpen]);

  const closeMore = () => setMoreOpen(false);

  const moreItemBase =
    "block rounded-md px-3 py-2 text-sm hover:bg-[var(--surface-alt)] hover:text-[var(--foreground)] transition-colors whitespace-nowrap";
  const moreItemClass = (href: string) =>
    pathname === href
      ? `${moreItemBase} text-[var(--accent)] font-medium`
      : `${moreItemBase} text-[var(--muted-strong)]`;

  return (
    <div className="hidden sm:flex items-center gap-3">
      <Link href="/playoffs" className={linkClass("/playoffs")}>
        Playoffs
      </Link>
      {isPlayoffs && (
        <Link href="/bracket" className={linkClass("/bracket")}>
          Bracket
        </Link>
      )}
      <Link href="/player-stats" className={linkClass("/player-stats")}>
        Player Stats
      </Link>
      <Link href="/standings" className={linkClass("/standings")}>
        Standings
      </Link>

      <div ref={moreRef} className="relative">
        <button
          type="button"
          aria-haspopup="menu"
          aria-expanded={moreOpen}
          onClick={() => setMoreOpen((o) => !o)}
          className={betaTriggerClass}
        >
          Beta
          <svg width="10" height="10" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="3 4.5 6 8 9 4.5" />
          </svg>
        </button>
        {moreOpen && (
          <div
            role="menu"
            aria-label="Beta navigation — pages being reworked"
            className="absolute right-0 top-full mt-2 w-48 max-h-[70vh] overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-lg p-1.5 z-50"
          >
            <Link href="/beta/ask" onClick={closeMore} className={moreItemClass("/beta/ask")}>
              Ask
            </Link>
            <Link href="/beta/compare" onClick={closeMore} className={moreItemClass("/beta/compare")}>
              Compare
            </Link>
            <Link href="/beta/coverage" onClick={closeMore} className={moreItemClass("/beta/coverage")}>
              Coverage
            </Link>
            <Link href="/beta/draft" onClick={closeMore} className={moreItemClass("/beta/draft")}>
              Draft
            </Link>
            <Link href="/beta/free-agency" onClick={closeMore} className={moreItemClass("/beta/free-agency")}>
              Free Agency
            </Link>
            <Link href="/beta/insights" onClick={closeMore} className={moreItemClass("/beta/insights")}>
              Insights
            </Link>
            <Link href="/beta/learn" onClick={closeMore} className={moreItemClass("/beta/learn")}>
              Learn
            </Link>
            <Link href="/beta/lineups" onClick={closeMore} className={moreItemClass("/beta/lineups")}>
              Lineup Lab
            </Link>
            <Link href="/beta/metrics" onClick={closeMore} className={moreItemClass("/beta/metrics")}>
              Metrics
            </Link>
            <Link href="/beta/milestones" onClick={closeMore} className={moreItemClass("/beta/milestones")}>
              Milestones
            </Link>
            <Link href="/beta/mvp" onClick={closeMore} className={moreItemClass("/beta/mvp")}>
              MVP Race
            </Link>
            <Link href="/beta/picks" onClick={closeMore} className={moreItemClass("/beta/picks")}>
              Picks
            </Link>
            <Link href="/beta/pre-read" onClick={closeMore} className={moreItemClass("/beta/pre-read")}>
              Pre-Read
            </Link>
            <Link href="/beta/teams" onClick={closeMore} className={moreItemClass("/beta/teams")}>
              Teams
            </Link>
            <Link href="/beta/trade-machine" onClick={closeMore} className={moreItemClass("/beta/trade-machine")}>
              Trade Machine
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
