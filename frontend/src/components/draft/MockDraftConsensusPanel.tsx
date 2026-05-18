// Sprint 101 (Stream B) — per-source mock-draft rankings on the prospect
// detail page.
//
// Renders a small table: one row per source (ESPN / NBADraft.net / CBS),
// with rank, tier, comp suggestion (if any), and a "view source" link.
// Hides entirely when no mock rankings exist — keeps prospect-detail clean
// for prospects without scraped data yet.

import type { MockRanking } from "@/lib/types";
import TierBadge from "./TierBadge";

interface Props {
  rankings: MockRanking[] | null | undefined;
  consensusRank: number | null | undefined;
  consensusVariance: number | null | undefined;
}

function sourceLabel(source: string): string {
  switch (source) {
    case "espn": return "ESPN";
    case "nbadraft_net": return "NBADraft.net";
    case "cbs": return "CBS Sports";
    default: return source;
  }
}

function formatAsOf(asOf: string | null | undefined): string | null {
  if (!asOf) return null;
  try {
    return new Date(asOf).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return asOf;
  }
}

export default function MockDraftConsensusPanel({
  rankings,
  consensusRank,
  consensusVariance,
}: Props) {
  if (!rankings || rankings.length === 0) return null;

  return (
    <section className="bip-panel rounded-[1.85rem] p-5 sm:p-6">
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <p className="bip-kicker">Mock-draft consensus</p>
          <h2 className="bip-display mt-1 text-xl font-bold text-[var(--foreground)]">
            Where the boards put this prospect
          </h2>
        </div>
        {consensusRank != null ? (
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-wider text-[var(--muted)]">Consensus</div>
            <div className="text-2xl font-bold tabular-nums text-[var(--foreground)]">
              {consensusRank.toFixed(1)}
            </div>
            {consensusVariance != null && consensusVariance > 0 ? (
              <div className="text-[11px] tabular-nums text-[var(--muted)]">
                σ {consensusVariance.toFixed(1)}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      <table className="mt-4 w-full text-sm">
        <thead className="text-[var(--muted)]">
          <tr>
            <th className="px-2 py-2 text-left font-semibold uppercase tracking-wide text-[11px]">Source</th>
            <th className="px-2 py-2 text-right font-semibold uppercase tracking-wide text-[11px]">Rank</th>
            <th className="px-2 py-2 text-left font-semibold uppercase tracking-wide text-[11px]">Tier</th>
            <th className="px-2 py-2 text-left font-semibold uppercase tracking-wide text-[11px]">NBA Comp</th>
            <th className="px-2 py-2 text-right font-semibold uppercase tracking-wide text-[11px]">As of</th>
          </tr>
        </thead>
        <tbody>
          {rankings.map((r, i) => (
            <tr key={`${r.source}-${r.as_of ?? i}`} className="border-t border-[var(--border)]">
              <td className="px-2 py-2.5">
                {r.source_url ? (
                  <a
                    href={r.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bip-link font-medium text-[var(--foreground)]"
                  >
                    {sourceLabel(r.source)} ↗
                  </a>
                ) : (
                  <span className="font-medium text-[var(--foreground)]">
                    {sourceLabel(r.source)}
                  </span>
                )}
              </td>
              <td className="px-2 py-2.5 text-right tabular-nums font-semibold text-[var(--foreground)]">
                {r.rank}
              </td>
              <td className="px-2 py-2.5">
                <TierBadge tier={r.tier} />
              </td>
              <td className="px-2 py-2.5 text-[var(--muted-strong)]">
                {r.comp_player_name ?? <span className="text-[var(--muted)]">—</span>}
              </td>
              <td className="px-2 py-2.5 text-right text-[11px] text-[var(--muted)]">
                {formatAsOf(r.as_of) ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
