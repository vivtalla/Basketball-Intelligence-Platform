"use client";

import { usePlayerPlayTypes } from "@/hooks/usePlayerStats";
import type { PlayTypeRow } from "@/lib/types";

interface Props {
  playerId: number;
  season: string;
}

const MIN_POSS = 10;

const PLAY_TYPE_LABELS: Record<string, string> = {
  Isolation: "Isolation",
  Transition: "Transition",
  PRBallHandler: "P&R Ball Handler",
  PRRollMan: "P&R Roll Man",
  Postup: "Post-Up",
  Spotup: "Spot-Up",
  Handoff: "Hand-Off",
  Cut: "Cut",
  OffScreen: "Off Screen",
  Putbacks: "Putbacks",
  Misc: "Misc",
};

function fmtPct(v: number | null): string {
  if (v == null) return "—";
  return (v * 100).toFixed(1) + "%";
}

function pppTone(v: number | null): string {
  if (v == null) return "text-[var(--muted)]";
  if (v >= 1.05) return "text-[var(--success-ink)]";
  if (v < 0.9) return "text-[var(--danger-ink)]";
  return "text-[var(--foreground)]";
}

function percentileTone(v: number | null): string {
  if (v == null) return "text-[var(--muted)]";
  if (v >= 70) return "text-[var(--success-ink)]";
  if (v <= 30) return "text-[var(--danger-ink)]";
  return "text-[var(--foreground)]";
}

function PlayTypeSkeleton() {
  return (
    <div className="space-y-6">
      <div className="bip-panel-strong rounded-[2rem] p-6 animate-pulse space-y-4">
        <div className="h-4 w-40 rounded bg-[var(--surface-alt)]" />
        <div className="h-6 w-64 rounded bg-[var(--surface-alt)]" />
      </div>
      <div className="bip-panel rounded-[1.8rem] p-6 animate-pulse space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-8 rounded bg-[var(--surface-alt)]" />
        ))}
      </div>
    </div>
  );
}

export default function PlayTypePanel({ playerId, season }: Props) {
  const { data, isLoading, error } = usePlayerPlayTypes(playerId, season);

  if (isLoading) return <PlayTypeSkeleton />;

  if (error) {
    return (
      <div className="bip-panel rounded-[1.8rem] p-6 text-sm text-[var(--muted-strong)]">
        Play-type data unavailable for {season}.
      </div>
    );
  }

  const rows: PlayTypeRow[] = (data?.play_types ?? [])
    .filter((r) => r.poss >= MIN_POSS)
    .sort((a, b) => b.poss - a.poss);

  if (rows.length === 0) {
    return (
      <div className="bip-panel rounded-[1.8rem] p-6 text-sm text-[var(--muted-strong)]">
        No play-type data available for {season}.
      </div>
    );
  }

  const maxPossPct = rows.length > 0 ? Math.max(...rows.map((r) => r.poss_pct)) : 1;

  const thCls =
    "py-2 px-3 text-right text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)] whitespace-nowrap";
  const tdCls =
    "py-2.5 px-3 text-right tabular-nums text-sm text-[var(--muted-strong)] whitespace-nowrap";

  return (
    <div className="space-y-6">
      <section className="bip-panel-strong rounded-[2rem] p-6">
        <p className="bip-kicker">Play-Type Breakdown</p>
        <h2
          className="bip-display mt-3 font-semibold text-[var(--foreground)]"
          style={{ fontSize: "1.6rem", lineHeight: 1.15, letterSpacing: "-0.02em" }}
        >
          Offensive role by play type
        </h2>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--muted-strong)]">
          Synergy play-type data for the {season} regular season. Sorted by possession volume.
          Minimum {MIN_POSS} possessions to appear.
        </p>
      </section>

      <section className="bip-panel rounded-[1.8rem] p-6">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className={thCls + " text-left pr-4"}>Play Type</th>
                <th className="py-2 px-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)] w-28">
                  Share
                </th>
                <th className={thCls}>POSS</th>
                <th className={thCls}>PPP</th>
                <th className={thCls}>Pctile</th>
                <th className={thCls}>Score%</th>
                <th className={thCls}>TOV%</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {rows.map((row) => {
                const barWidth = maxPossPct > 0 ? (row.poss_pct / maxPossPct) * 100 : 0;
                return (
                  <tr
                    key={`${row.play_type}-${row.play_role}`}
                    className="hover:bg-[rgba(255,255,255,0.4)] transition-colors"
                  >
                    <td className="py-2.5 px-3 text-left text-sm font-medium text-[var(--foreground)] whitespace-nowrap pr-4">
                      {PLAY_TYPE_LABELS[row.play_type] ?? row.play_type}
                    </td>
                    <td className="py-2.5 px-3 w-28">
                      <div className="w-full bg-[var(--surface-alt)] rounded-full h-1.5 mb-1">
                        <div
                          className="h-1.5 rounded-full bg-[var(--accent)]"
                          style={{ width: `${barWidth}%`, opacity: 0.7 }}
                        />
                      </div>
                      <span className="text-[11px] text-[var(--muted)] tabular-nums">
                        {(row.poss_pct * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className={tdCls}>{row.poss}</td>
                    <td
                      className={
                        "py-2.5 px-3 text-right tabular-nums text-sm font-semibold whitespace-nowrap " +
                        pppTone(row.ppp)
                      }
                    >
                      {row.ppp != null ? row.ppp.toFixed(3) : "—"}
                    </td>
                    <td
                      className={
                        "py-2.5 px-3 text-right tabular-nums text-sm font-semibold whitespace-nowrap " +
                        percentileTone(row.percentile)
                      }
                    >
                      {row.percentile != null ? row.percentile.toFixed(1) : "—"}
                    </td>
                    <td className={tdCls}>{fmtPct(row.score_freq_pct)}</td>
                    <td className={tdCls}>{fmtPct(row.tov_freq_pct)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
