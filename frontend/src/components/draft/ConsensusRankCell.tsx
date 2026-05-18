// Sprint 101 (Stream A) — board cell showing consensus rank + variance.
//
// Renders the Sprint 100 enriched fields:
//   * consensus_rank_float — average rank across mock-draft sources (denormalized)
//   * consensus_variance — population stddev across sources
//   * consensus_rank — legacy single-source rank (fallback)
//
// Layout: large rank value with a small "σ X.Y" variance pill alongside.
// When neither aggregate is present, falls back to the legacy integer rank
// or em-dash. The variance pill is hidden when N=1 (variance == 0) since
// "polarizing" is meaningless with one source.

interface Props {
  consensusRankFloat: number | null | undefined;
  consensusVariance: number | null | undefined;
  consensusRank: number | null | undefined;
}

export default function ConsensusRankCell({
  consensusRankFloat,
  consensusVariance,
  consensusRank,
}: Props) {
  // Prefer the Sprint 100 aggregate when available.
  if (consensusRankFloat != null) {
    const rankDisplay = consensusRankFloat.toFixed(1);
    const showVariance =
      consensusVariance != null && consensusVariance > 0;
    return (
      <span className="inline-flex items-baseline gap-1.5 tabular-nums">
        <span className="font-semibold text-[var(--foreground)]">
          {rankDisplay}
        </span>
        {showVariance ? (
          <span
            className="rounded border border-[var(--border)] bg-[var(--surface-alt)] px-1 py-px text-[9px] font-medium uppercase tracking-wider text-[var(--muted)]"
            title="Spread across mock-draft sources (population stddev)"
          >
            σ {consensusVariance!.toFixed(1)}
          </span>
        ) : null}
      </span>
    );
  }
  // Fall back to legacy integer rank from Sprint 78.
  if (consensusRank != null) {
    return (
      <span className="tabular-nums text-[var(--foreground)]">
        {consensusRank}
      </span>
    );
  }
  return <span className="text-[var(--muted)]">—</span>;
}
