"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";

/**
 * Sprint 83a (A2): Hamburger menu for sub-`sm` viewports. Click-outside and
 * Esc both close the panel. The panel is a vertical list of every nav link
 * NavLinks renders, including the playoff-gated Bracket item.
 */
export default function MobileNav() {
  const { isPlayoffs } = useSeasonPhase();
  const pathname = usePathname() ?? "/";
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(href + "/");

  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const close = () => setOpen(false);

  const linkBase =
    "block rounded-md px-3 py-2 text-sm hover:bg-[var(--surface-alt)] hover:text-[var(--foreground)] transition-colors";
  const itemClass = (href: string) =>
    isActive(href)
      ? `${linkBase} text-[var(--accent)] font-medium`
      : `${linkBase} text-[var(--muted-strong)]`;

  return (
    <div ref={containerRef} className="relative sm:hidden">
      <button
        type="button"
        aria-label={open ? "Close navigation" : "Open navigation"}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-[var(--border)] bg-[var(--surface-alt)] text-[var(--foreground)]"
      >
        {open ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        )}
      </button>

      {open && (
        <div
          role="menu"
          aria-label="Site navigation"
          className="absolute right-0 top-full mt-2 w-56 max-h-[80vh] overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-lg p-2 z-50"
        >
          <Link href="/playoffs" onClick={close} className={itemClass("/playoffs")}>
            Playoffs
          </Link>
          <Link href="/player-stats" onClick={close} className={itemClass("/player-stats")}>
            Player Stats
          </Link>
          <Link href="/standings" onClick={close} className={itemClass("/standings")}>
            Standings
          </Link>
          <Link href="/beta/compare" onClick={close} className={itemClass("/beta/compare")}>
            Compare
          </Link>
          <Link href="/beta/learn" onClick={close} className={itemClass("/beta/learn")}>
            Learn
          </Link>
          <div className="my-1 border-t border-[var(--border)]" />
          <Link href="/beta/ask" onClick={close} className={itemClass("/beta/ask")}>
            Ask
          </Link>
          <Link href="/beta/mvp" onClick={close} className={itemClass("/beta/mvp")}>
            MVP Race
          </Link>
          <Link href="/beta/insights" onClick={close} className={itemClass("/beta/insights")}>
            Insights
          </Link>
          <Link href="/beta/metrics" onClick={close} className={itemClass("/beta/metrics")}>
            Metrics
          </Link>
          <Link href="/beta/pre-read" onClick={close} className={itemClass("/beta/pre-read")}>
            Pre-Read
          </Link>
          <Link href="/beta/teams" onClick={close} className={itemClass("/beta/teams")}>
            Teams
          </Link>
          <Link href="/beta/trade-machine" onClick={close} className={itemClass("/beta/trade-machine")}>
            Trade Machine
          </Link>
          <Link href="/beta/free-agency" onClick={close} className={itemClass("/beta/free-agency")}>
            Free Agency
          </Link>
          <Link href="/beta/draft" onClick={close} className={itemClass("/beta/draft")}>
            Draft
          </Link>
          {isPlayoffs && (
            <Link href="/bracket" onClick={close} className={itemClass("/bracket")}>
              Bracket
            </Link>
          )}
          <Link href="/beta/picks" onClick={close} className={itemClass("/beta/picks")}>
            Picks
          </Link>
          <Link href="/beta/coverage" onClick={close} className={itemClass("/beta/coverage")}>
            Coverage
          </Link>
          <Link href="/beta/milestones" onClick={close} className={itemClass("/beta/milestones")}>
            Milestones
          </Link>
        </div>
      )}
    </div>
  );
}
