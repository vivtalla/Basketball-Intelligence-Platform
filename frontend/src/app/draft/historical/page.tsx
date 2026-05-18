// Sprint 101 (Stream C) — historical-class year picker landing.
//
// Grid of year cards 2016-2025. Clicking a year navigates to
// /draft/historical/{year}. Used by analysts to backtest projection
// quality ("how did the analyzer score Luka in 2018?").

import Link from "next/link";

const YEARS = [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016];

export const metadata = {
  title: "Historical drafts · CourtVue Labs",
  description: "Past draft classes 2016-2025 with NBA career outcomes.",
};

export default function HistoricalDraftLandingPage() {
  return (
    <div className="space-y-6">
      <header className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
        <p className="bip-kicker">Historical drafts</p>
        <h1 className="bip-display mt-2 text-3xl font-bold tracking-tight text-[var(--foreground)]">
          Past draft classes
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
          Browse 2016-2025 draft classes with NBA career outcomes. Useful for
          backtesting the analyzer&apos;s projections against actual outcomes
          and spotting patterns in mid-round value plus top-pick busts.
        </p>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {YEARS.map((year) => (
          <Link
            key={year}
            href={`/draft/historical/${year}`}
            className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5 hover:bg-[var(--surface-alt)] transition-colors group"
          >
            <div className="text-[10px] uppercase tracking-wider text-[var(--muted)]">Draft class</div>
            <div className="bip-display mt-1 text-3xl font-bold text-[var(--foreground)] group-hover:text-[var(--accent)]">
              {year}
            </div>
            <div className="mt-2 text-[11px] text-[var(--muted)]">
              View outcomes →
            </div>
          </Link>
        ))}
      </section>

      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4 text-xs text-[var(--muted-strong)]">
        Historical outcomes are populated from a curated CSV sourced from
        Basketball-Reference. Career aggregates (games, minutes, Win Shares,
        All-Star / All-NBA selections) reflect each player&apos;s NBA career
        through the most recently-synced season.
      </div>
    </div>
  );
}
