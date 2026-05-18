// Sprint 101 (Stream C) — server-component wrapper for the historical class
// route. Forces dynamic rendering so each visit reflects the current state
// of the seed CSV (which grows as the Stream D backfill expands).
//
// Mirrors the Sprint 100 PR #22 BracketPage pattern: thin server wrapper
// holds the `dynamic = "force-dynamic"` segment config; client component
// does the actual fetch + render.

import HistoricalClassClient from "./HistoricalClassClient";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ year: string }>;
}

export default async function HistoricalClassPage({ params }: Props) {
  const { year } = await params;
  const yearNum = parseInt(year, 10);
  // Guard non-numeric paths; the client will also call the API which
  // returns 404 for out-of-range years.
  if (!Number.isFinite(yearNum)) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-6 text-sm text-[var(--danger-ink)]">
        Invalid draft year.
      </div>
    );
  }
  return <HistoricalClassClient year={yearNum} />;
}
