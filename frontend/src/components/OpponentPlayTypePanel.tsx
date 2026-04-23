"use client";

import { useOpponentPlayTypes } from "@/hooks/usePlayerStats";
import type { OpponentPlayTypeRow } from "@/lib/types";

interface OpponentPlayTypePanelProps {
  teamAbbreviation: string;
  season: string;
}

export default function OpponentPlayTypePanel({
  teamAbbreviation,
  season,
}: OpponentPlayTypePanelProps) {
  const { data, isLoading, error } = useOpponentPlayTypes(teamAbbreviation, season);

  if (error) {
    return (
      <div className="bg-[var(--surface-alt)] border border-[var(--border-color)] rounded-md p-4 text-sm text-[var(--muted)]">
        Play-type data unavailable for this matchup.
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="bg-[var(--surface-alt)] border border-[var(--border-color)] rounded-md p-4 text-sm text-[var(--muted)]">
        Loading opponent play-type tendencies...
      </div>
    );
  }

  if (!data?.plays || data.plays.length === 0) {
    return (
      <div className="bg-[var(--surface-alt)] border border-[var(--border-color)] rounded-md p-4 text-sm text-[var(--muted)]">
        Play-type data unavailable for this matchup.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-[var(--text-secondary)]">Opponent Play-Type Tendencies</h3>
      <div className="bip-table-shell">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[var(--border-color)]">
              <th className="px-3 py-2 text-left font-semibold">Play Type</th>
              <th className="px-3 py-2 text-right font-semibold">Frequency</th>
              <th className="px-3 py-2 text-right font-semibold">PPP</th>
              <th className="px-3 py-2 text-right font-semibold">FG%</th>
            </tr>
          </thead>
          <tbody>
            {data.plays.map((play: OpponentPlayTypeRow) => (
              <tr key={play.play_type} className="border-b border-[var(--border-color)] hover:bg-[var(--surface-alt)]">
                <td className="px-3 py-2">{play.play_type}</td>
                <td className="px-3 py-2 text-right">
                  {play.poss_pct ? `${(play.poss_pct * 100).toFixed(1)}%` : "—"}
                </td>
                <td className={`px-3 py-2 text-right font-medium ${getPppColor(play.ppp)}`}>
                  {play.ppp ? play.ppp.toFixed(2) : "—"}
                </td>
                <td className="px-3 py-2 text-right">
                  {play.fg_pct ? `${(play.fg_pct * 100).toFixed(1)}%` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function getPppColor(ppp: number | null): string {
  if (!ppp) return "text-[var(--text-secondary)]";
  if (ppp > 1.05) return "text-green-600";
  if (ppp < 0.9) return "text-red-600";
  return "text-[var(--text-secondary)]";
}
