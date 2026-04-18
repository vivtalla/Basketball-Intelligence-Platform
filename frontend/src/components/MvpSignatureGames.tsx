"use client";

import type { MvpSignatureGame } from "@/lib/types";

interface Props {
  games: MvpSignatureGame[];
}

const tierLabel: Record<string, { label: string; tone: string }> = {
  top10_def: { label: "Top-10 D", tone: "border-[var(--success-ink)] text-[var(--success-ink)]" },
  mid_def: { label: "Mid D", tone: "border-[var(--border)] text-[var(--muted)]" },
  bottom_def: { label: "Bottom D", tone: "border-[var(--warning-ink)] text-[var(--warning-ink)]" },
};

export default function MvpSignatureGames({ games }: Props) {
  if (!games || games.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4 text-xs text-[var(--muted)]">
        No signature games captured yet.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--accent)]">Signature Games</p>
        <p className="text-[10px] text-[var(--muted)]">Ranked by leverage (opp quality × performance × result)</p>
      </div>

      <ul className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {games.map((g) => {
          const tier = tierLabel[g.opponent_tier] ?? tierLabel.mid_def;
          return (
            <li
              key={g.game_id}
              className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3"
            >
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-[var(--foreground)]">{g.opponent}</p>
                <span className={`rounded border px-1.5 py-0.5 text-[9px] font-semibold ${tier.tone}`}>
                  {tier.label}
                  {g.opponent_drtg_rank ? ` #${g.opponent_drtg_rank}` : ""}
                </span>
              </div>
              <p className="mt-1 text-[10px] text-[var(--muted)]">
                {g.date ?? "—"} · {g.result ?? "—"}
              </p>
              <div className="mt-2 grid grid-cols-3 gap-1 text-[10px] text-[var(--muted)]">
                <Stat label="PTS" value={String(g.pts)} />
                <Stat label="TS" value={g.ts_pct != null ? `${(g.ts_pct * 100).toFixed(0)}%` : "—"} />
                <Stat label="+/-" value={g.plus_minus != null ? String(g.plus_minus) : "—"} />
              </div>
              <p className="mt-2 text-[10px] text-[var(--muted)]">
                leverage <span className="font-semibold text-[var(--foreground)]">{g.leverage_score.toFixed(1)}</span>
              </p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-[var(--border)] px-1.5 py-1 text-center">
      <p className="text-[9px] uppercase text-[var(--muted)]">{label}</p>
      <p className="text-xs font-semibold text-[var(--foreground)]">{value}</p>
    </div>
  );
}
