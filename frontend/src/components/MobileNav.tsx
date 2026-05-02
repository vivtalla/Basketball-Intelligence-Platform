"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";

/**
 * Sprint 83a (A2): Hamburger menu for sub-`sm` viewports. Click-outside and
 * Esc both close the panel. The panel is a vertical list of every nav link
 * NavLinks renders, including the playoff-gated Bracket item.
 */
export default function MobileNav() {
  const { isPlayoffs } = useSeasonPhase();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

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

  const linkClass =
    "block rounded-md px-3 py-2 text-sm text-[var(--muted-strong)] hover:bg-[var(--surface-alt)] hover:text-[var(--foreground)] transition-colors";

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
          <Link href="/playoffs" onClick={close} className={`${linkClass} text-[var(--accent)] font-medium`}>
            Playoffs
          </Link>
          <Link href="/player-stats" onClick={close} className={linkClass}>
            Player Stats
          </Link>
          <Link href="/standings" onClick={close} className={linkClass}>
            Standings
          </Link>
          <Link href="/compare" onClick={close} className={linkClass}>
            Compare
          </Link>
          <Link href="/learn" onClick={close} className={linkClass}>
            Learn
          </Link>
          <div className="my-1 border-t border-[var(--border)]" />
          <Link href="/ask" onClick={close} className={linkClass}>
            Ask
          </Link>
          <Link href="/mvp" onClick={close} className={linkClass}>
            MVP Race
          </Link>
          <Link href="/insights" onClick={close} className={linkClass}>
            Insights
          </Link>
          <Link href="/metrics" onClick={close} className={linkClass}>
            Metrics
          </Link>
          <Link href="/pre-read" onClick={close} className={linkClass}>
            Pre-Read
          </Link>
          <Link href="/teams" onClick={close} className={linkClass}>
            Teams
          </Link>
          <Link href="/trade-machine" onClick={close} className={linkClass}>
            Trade Machine
          </Link>
          <Link href="/free-agency" onClick={close} className={linkClass}>
            Free Agency
          </Link>
          <Link href="/draft" onClick={close} className={linkClass}>
            Draft
          </Link>
          {isPlayoffs && (
            <Link href="/bracket" onClick={close} className={linkClass}>
              Bracket
            </Link>
          )}
          <Link href="/picks" onClick={close} className={linkClass}>
            Picks
          </Link>
          <Link href="/coverage" onClick={close} className={linkClass}>
            Coverage
          </Link>
          <Link href="/milestones" onClick={close} className={linkClass}>
            Milestones
          </Link>
        </div>
      )}
    </div>
  );
}
