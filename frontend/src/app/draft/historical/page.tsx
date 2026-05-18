// Sprint 101 (Stream C) — historical-class year picker landing.
// Sprint 102 (Stream A) — polished with HeroHardwood + Reveal stagger.
//
// Grid of year cards 2016-2025. Clicking a year navigates to
// /draft/historical/{year}. Used by analysts to backtest projection
// quality ("how did the analyzer score Luka in 2018?").

import Link from "next/link";
import HeroHardwood from "@/components/HeroHardwood";
import Reveal from "@/components/Reveal";

const YEARS = [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016];

export const metadata = {
  title: "Historical drafts · CourtVue Labs",
  description: "Past draft classes 2016-2025 with NBA career outcomes.",
};

export default function HistoricalDraftLandingPage() {
  return (
    <div className="space-y-6">
      <Reveal>
      <header className="bip-panel-strong relative overflow-hidden rounded-[2.2rem] p-6 sm:p-8">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 rounded-[2.2rem] overflow-hidden">
          <HeroHardwood opacity={0.10} />
        </div>
        <p className="bip-kicker">Historical drafts</p>
        <h1 className="bip-display mt-2 text-3xl sm:text-4xl font-bold tracking-tight text-[var(--foreground)]">
          Past draft classes
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
          Browse 2016-2025 draft classes with NBA career outcomes. Useful for
          backtesting the analyzer&apos;s projections against actual outcomes
          and spotting patterns in mid-round value plus top-pick busts.
        </p>
      </header>
      </Reveal>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {YEARS.map((year, idx) => (
          <Reveal key={year} delay={idx * 60}>
          <Link
            href={`/draft/historical/${year}`}
            className="group bip-panel rounded-[1.85rem] p-5 hover:-translate-y-1 hover:border-[var(--accent)] hover:shadow-[0_24px_60px_rgba(33,72,59,0.16)] transition-all duration-200 block h-full"
          >
            <div className="text-[10px] uppercase tracking-wider text-[var(--muted)]">Draft class</div>
            <div className="bip-display mt-1 text-3xl font-bold text-[var(--foreground)] group-hover:text-[var(--accent)]">
              {year}
            </div>
            <div className="mt-2 text-[11px] text-[var(--muted)]">
              View outcomes →
            </div>
          </Link>
          </Reveal>
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
