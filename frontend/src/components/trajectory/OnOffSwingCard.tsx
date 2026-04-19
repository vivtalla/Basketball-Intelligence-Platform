"use client";

import type { LineupContextResponse, TrajectoryOnOffContext } from "@/lib/types";

interface Props {
  onOffContext: TrajectoryOnOffContext | null;
  lineupContext: LineupContextResponse | null | undefined;
}

function confidenceColor(c: string) {
  if (c === "high") return "text-[var(--accent-strong)]";
  if (c === "medium") return "text-[var(--foreground)]";
  return "text-[var(--muted)]";
}

export function OnOffSwingCard({ onOffContext, lineupContext }: Props) {
  const hasOnOff = onOffContext && onOffContext.on_off_net !== null;
  const hasLineup = lineupContext && lineupContext.top_teammates.length > 0;

  if (!hasOnOff && !hasLineup) {
    return (
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">On/Off Swing</p>
        <p className="mt-1 text-xs text-[var(--muted)]">Insufficient play-by-play data for this player.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">On/Off Swing</p>

      {hasOnOff && (
        <div className="flex items-center gap-4">
          <div className="text-center">
            <p
              className={`text-2xl font-bold tabular-nums ${
                (onOffContext.on_off_net ?? 0) >= 0
                  ? "text-[var(--accent-strong)]"
                  : "text-[var(--danger-ink)]"
              }`}
            >
              {(onOffContext.on_off_net ?? 0) >= 0 ? "+" : ""}
              {(onOffContext.on_off_net ?? 0).toFixed(1)}
            </p>
            <p className="text-[10px] text-[var(--muted)]">Net Rtg swing</p>
          </div>
          <div className="flex flex-col gap-1 text-xs text-[var(--muted)]">
            <span>
              On: {onOffContext.on_minutes !== null ? `${Math.round(onOffContext.on_minutes)} min` : "—"}
            </span>
            <span>
              Off: {onOffContext.off_minutes !== null ? `${Math.round(onOffContext.off_minutes)} min` : "—"}
            </span>
            <span className={`text-[10px] ${confidenceColor(onOffContext.confidence)}`}>
              {onOffContext.confidence} confidence
            </span>
          </div>
        </div>
      )}

      {hasLineup && (
        <div>
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
            Top lineup partners
          </p>
          <div className="space-y-1">
            {lineupContext.top_teammates.slice(0, 3).map((t) => (
              <div key={t.teammate_id} className="flex items-center justify-between text-xs">
                <span className="font-medium text-[var(--foreground)]">{t.teammate_name}</span>
                <div className="flex items-center gap-3 text-[var(--muted)]">
                  <span>{t.possessions?.toLocaleString() ?? "—"} poss</span>
                  {t.net_rating_with !== null && (
                    <span
                      className={`font-semibold ${
                        t.net_rating_with >= 0
                          ? "text-[var(--accent-strong)]"
                          : "text-[var(--danger-ink)]"
                      }`}
                    >
                      {t.net_rating_with >= 0 ? "+" : ""}
                      {t.net_rating_with.toFixed(1)} NR
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[10px] text-[var(--muted)]">
            Net rating of shared lineups · min. 100 possessions
          </p>
        </div>
      )}
    </div>
  );
}
