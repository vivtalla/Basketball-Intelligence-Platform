"use client";

import ModeToggle from "@/components/broadsheet/ModeToggle";

/**
 * Sprint 77 (Stream B): Newsprint masthead used across every home-page
 * view-mode variant.
 *
 * Layout (top → bottom):
 *   ┌───────────────────────────────────────────────────────────────────┐
 *   │ Volume / Edition kicker line  ·  Date stamp  ·  Sky-line phrase   │  ← top rule
 *   ├───────────────────────────────────────────────────────────────────┤
 *   │              [ ModeToggle: PLAYOFF / REGULAR / OFFSEASON ]        │
 *   │                                                                   │
 *   │                  T H E   C O U R T V U E   D A I L Y              │  ← serif wordmark
 *   │                                                                   │
 *   │     Broadsheet edition · "Court-side intelligence in full view"   │
 *   │              · season date sub-line ·                             │
 *   ├───────────────────────────────────────────────────────────────────┤
 *
 * EB1 shipped the chrome with a placeholder pill row; EB2 (Sprint 77)
 * replaced the placeholder with the real interactive `<ModeToggle>` so
 * the toggle persists across reloads and is keyboard-accessible.
 */

const TODAY = new Date();

const DATE_FORMATTER = new Intl.DateTimeFormat("en-US", {
  weekday: "long",
  month: "long",
  day: "numeric",
  year: "numeric",
});

const VOLUME = "Vol. LXXVIII";
const EDITION = "Playoff Edition";

export interface BroadsheetMastheadProps {
  /** Optional override for the date line (defaults to today). */
  date?: Date;
  /** Optional season string ("2024-25", "2025-26"). Renders alongside the motto. */
  season?: string;
}

export default function BroadsheetMasthead({
  date,
  season,
}: BroadsheetMastheadProps) {
  const dateLabel = DATE_FORMATTER.format(date ?? TODAY);

  return (
    <header
      className="bip-panel rounded-[1.85rem] overflow-hidden"
      style={{
        background:
          "linear-gradient(180deg, rgba(255,249,241,0.94) 0%, rgba(244,236,222,0.92) 100%)",
        borderColor: "var(--border-strong)",
      }}
    >
      {/* ── Top rule: volume / date / sky-line ─────────────────────────── */}
      <div
        className="flex flex-wrap items-center justify-between gap-3 px-6 py-3 border-b border-[var(--border)]"
        style={{
          fontFamily: "var(--font-geist-mono)",
          fontSize: 11,
          letterSpacing: "0.16em",
          textTransform: "uppercase",
          color: "var(--muted)",
        }}
      >
        <span>{VOLUME} · {EDITION}</span>
        <span className="hidden sm:inline">{dateLabel}</span>
        <span className="text-[var(--signal)]">Late edition · 25 cents</span>
      </div>

      {/* ── Mode toggle (EB2): sets the active view-mode for the home page. */}
      <div className="flex items-center justify-center px-6 pt-5">
        <ModeToggle />
      </div>

      {/* ── Wordmark ───────────────────────────────────────────────────── */}
      <div className="px-6 py-6 text-center">
        <h1
          className="bip-display font-bold text-[var(--foreground)]"
          style={{
            fontSize: "clamp(2.6rem, 6vw, 4.8rem)",
            letterSpacing: "-0.02em",
            lineHeight: 1.02,
          }}
        >
          The CourtVue Daily
        </h1>
        {/* ── Sub-line: motto + season ─────────────────────────────────── */}
        <p
          className="mt-3 text-sm text-[var(--muted)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Broadsheet edition ·{" "}
          <em className="text-[var(--accent)]">
            &ldquo;Court-side intelligence, in full view.&rdquo;
          </em>
          {season ? <> · Season {season}</> : null}
        </p>
        {/* On mobile, repeat the date stamp underneath. */}
        <p
          className="sm:hidden mt-1 text-xs"
          style={{
            fontFamily: "var(--font-geist-mono)",
            letterSpacing: "0.16em",
            textTransform: "uppercase",
            color: "var(--muted)",
          }}
        >
          {dateLabel}
        </p>
      </div>
    </header>
  );
}
