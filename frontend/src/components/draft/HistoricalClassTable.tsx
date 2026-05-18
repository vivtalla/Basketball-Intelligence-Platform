// Sprint 101 (Stream C) — historical draft class table.
//
// Renders one row per past prospect in a draft year (2016-2025), with
// their NBA career outcome tier and a short career summary. Sortable by
// draft pick (default) or outcome tier rank.

import { useMemo, useState } from "react";
import type { HistoricalProspectEntry } from "@/lib/types";
import TierBadge from "./TierBadge";

interface Props {
  prospects: HistoricalProspectEntry[];
}

type SortKey = "pick" | "outcome";

const OUTCOME_RANK: Record<string, number> = {
  superstar: 5,
  star: 4,
  starter: 3,
  role_player: 2,
  bust: 1,
};

export default function HistoricalClassTable({ prospects }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("pick");

  const sorted = useMemo(() => {
    const copy = [...prospects];
    if (sortKey === "outcome") {
      copy.sort((a, b) => {
        const ra = OUTCOME_RANK[a.outcome_tier ?? ""] ?? 0;
        const rb = OUTCOME_RANK[b.outcome_tier ?? ""] ?? 0;
        if (rb !== ra) return rb - ra; // best outcome first
        return (a.draft_pick ?? 9999) - (b.draft_pick ?? 9999);
      });
    } else {
      copy.sort((a, b) => (a.draft_pick ?? 9999) - (b.draft_pick ?? 9999));
    }
    return copy;
  }, [prospects, sortKey]);

  if (prospects.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-8 text-center text-[var(--muted)]">
        No historical prospects loaded for this class yet. Backfill from
        Basketball-Reference is in progress; check back after the next
        deploy.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] bg-[var(--surface-alt)]">
        <span className="text-[12px] font-semibold uppercase tracking-wide text-[var(--muted)]">
          {prospects.length} prospects
        </span>
        <label className="text-xs text-[var(--muted)]">
          Sort:{" "}
          <select
            value={sortKey}
            onChange={(e) => setSortKey(e.target.value as SortKey)}
            className="rounded border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-xs text-[var(--foreground)] ml-1"
          >
            <option value="pick">Draft pick</option>
            <option value="outcome">Outcome tier</option>
          </select>
        </label>
      </div>
      <table className="w-full text-sm">
        <thead className="bg-[var(--surface-alt)] text-[var(--muted)]">
          <tr>
            <th className="px-4 py-3 text-left font-semibold uppercase tracking-wide text-[11px]">Pick</th>
            <th className="px-4 py-3 text-left font-semibold uppercase tracking-wide text-[11px]">Prospect</th>
            <th className="px-4 py-3 text-left font-semibold uppercase tracking-wide text-[11px]">Team</th>
            <th className="px-4 py-3 text-left font-semibold uppercase tracking-wide text-[11px]">NBA Outcome</th>
            <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">GP</th>
            <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">PPG</th>
            <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">All-Star</th>
            <th className="px-4 py-3 text-right font-semibold uppercase tracking-wide text-[11px]">All-NBA</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((p) => {
            const cs = p.career_summary;
            return (
              <tr key={p.prospect_id} className="border-t border-[var(--border)]">
                <td className="px-4 py-2.5 tabular-nums text-[var(--muted)]">
                  {p.draft_pick != null ? `#${p.draft_pick}` : "—"}
                </td>
                <td className="px-4 py-2.5 font-semibold text-[var(--foreground)]">{p.name}</td>
                <td className="px-4 py-2.5 text-[var(--muted-strong)]">{p.draft_team ?? "—"}</td>
                <td className="px-4 py-2.5">
                  <TierBadge tier={p.outcome_tier} />
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums">
                  {cs?.games != null ? cs.games : <span className="text-[var(--muted)]">—</span>}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums">
                  {cs?.ppg != null ? cs.ppg.toFixed(1) : <span className="text-[var(--muted)]">—</span>}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums">
                  {cs?.all_star ? `×${cs.all_star}` : <span className="text-[var(--muted)]">—</span>}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums">
                  {cs?.all_nba ? `×${cs.all_nba}` : <span className="text-[var(--muted)]">—</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
