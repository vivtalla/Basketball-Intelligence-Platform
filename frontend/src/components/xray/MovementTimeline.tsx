"use client";

import type { StyleMovement } from "@/lib/types";

interface Props {
  movement: StyleMovement | null | undefined;
}

const DIRECTION_STYLE: Record<string, string> = {
  gaining: "bg-[var(--accent-strong)]",
  fading: "bg-[var(--danger-ink)]",
  stable: "bg-[var(--muted)]",
};

export function MovementTimeline({ movement }: Props) {
  if (!movement) return null;
  const features = movement.features ?? [];
  const maxAbs = Math.max(
    0.25,
    ...features.map((f) => Math.abs(f.delta_z ?? 0))
  );
  return (
    <section className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5">
      <header className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-[var(--foreground)]">Style movement</h3>
        <span className="text-[11px] uppercase tracking-[0.14em] text-[var(--muted)]">
          Last {movement.window_games} games vs season
        </span>
      </header>
      <p className="mt-3 text-sm leading-5 text-[var(--muted-strong)]">{movement.narrative}</p>
      {features.length > 0 ? (
        <ul className="mt-4 space-y-2">
          {features.map((f) => {
            const delta = f.delta_z ?? 0;
            const pct = Math.min(100, (Math.abs(delta) / maxAbs) * 50);
            const isPositive = delta >= 0;
            return (
              <li key={f.metric_id} className="flex items-center gap-2 text-[11px]">
                <span className="w-32 shrink-0 text-[var(--muted-strong)]">{f.label}</span>
                <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-[var(--surface-alt)]">
                  <div
                    className="absolute top-0 bottom-0 w-px bg-[var(--border)]"
                    style={{ left: "50%" }}
                  />
                  <div
                    className={`absolute top-0 bottom-0 ${DIRECTION_STYLE[f.direction] ?? ""}`}
                    style={
                      isPositive
                        ? { left: "50%", width: `${pct}%` }
                        : { right: "50%", width: `${pct}%` }
                    }
                  />
                </div>
                <span
                  className="w-12 shrink-0 text-right font-semibold tabular-nums"
                  title={`baseline z ${f.baseline_z?.toFixed(2) ?? "—"}, recent z ${f.recent_z?.toFixed(2) ?? "—"}`}
                >
                  {isPositive ? "+" : ""}
                  {delta.toFixed(2)}
                </span>
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}
