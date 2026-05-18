// Sprint 101 (Stream A) — small "n/3" indicator showing how many mock-draft
// sources ranked a prospect. "3/3" = full consensus; "1/3" = single-source
// outlier (typically untrustworthy ranking).
//
// Sprint 100 wired ESPN + NBADraft.net + CBS as the three public sources,
// so 3 is the theoretical max. The denominator is hard-coded to that for
// now; if a source comes back online or a new one is added in a future
// sprint, this component picks up the new total automatically by checking
// the API response's `mock_sources_count` against a default.

const MAX_SOURCES = 3;

interface Props {
  count: number | null | undefined;
  maxSources?: number;
}

export default function MockSourcesPill({ count, maxSources = MAX_SOURCES }: Props) {
  if (count == null || count <= 0) return null;
  // Visual weight scales with consensus strength.
  const full = count >= maxSources;
  const partial = !full && count >= 2;
  const single = count === 1;
  const bg = full
    ? "rgba(33,72,59,0.10)"
    : partial
    ? "rgba(180,137,61,0.10)"
    : "rgba(120,120,120,0.10)";
  const border = full
    ? "rgba(33,72,59,0.40)"
    : partial
    ? "rgba(180,137,61,0.40)"
    : "rgba(120,120,120,0.30)";
  const color = full ? "#21483b" : partial ? "#9a6f24" : "#878787";
  const title = full
    ? "Full consensus across all mock-draft sources"
    : single
    ? "Ranked by only one mock-draft source — outlier"
    : "Partial consensus across mock-draft sources";
  return (
    <span
      className="inline-flex items-center rounded-full border px-1.5 py-0.5 text-[9px] font-semibold tabular-nums"
      style={{ backgroundColor: bg, borderColor: border, color }}
      title={title}
    >
      {count}/{maxSources}
    </span>
  );
}
