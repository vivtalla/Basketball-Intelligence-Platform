"use client";

import type { OpportunityPlayerRow, LineupContextResponse } from "@/lib/types";

interface Props {
  row: OpportunityPlayerRow;
  lineupCtx: LineupContextResponse | undefined;
}

export function TeamImpactCard({ row, lineupCtx }: Props) {
  const hasOnOff = row.on_off_net != null;
  const sign = (row.on_off_net ?? 0) >= 0;
  const topTeammates = lineupCtx?.top_teammates?.slice(0, 3) ?? [];
  return (
    <section className="rounded-[1.25rem] border border-[var(--border)] bg-[var(--surface)] p-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
        Team Impact & Lineup Synergy
      </p>
      <h3 className="mt-0.5 text-base font-semibold text-[var(--foreground)]">
        Does the team play better with him on the floor?
      </h3>
      <div className="mt-3 grid gap-4 sm:grid-cols-[auto,1fr]">
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-4 py-3">
          <div className="text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
            On/Off Net
          </div>
          <div
            className={`mt-1 text-2xl font-semibold tabular-nums ${
              hasOnOff
                ? sign
                  ? "text-[var(--accent-strong)]"
                  : "text-[var(--danger-ink)]"
                : "text-[var(--muted-strong)]"
            }`}
          >
            {hasOnOff
              ? `${sign ? "+" : ""}${(row.on_off_net as number).toFixed(1)}`
              : "—"}
          </div>
          <div className="mt-1 text-[10px] text-[var(--muted)]">
            {row.on_minutes != null
              ? `${row.on_minutes.toFixed(0)} on-min`
              : "— on-min"}
            {row.off_minutes != null
              ? ` · ${row.off_minutes.toFixed(0)} off`
              : ""}
          </div>
        </div>
        <div className="space-y-2">
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted-strong)]">
            Top lineup partners (min. 100 possessions)
          </div>
          {topTeammates.length ? (
            <ul className="space-y-1 text-xs">
              {topTeammates.map((t) => (
                <li
                  key={t.teammate_id}
                  className="flex items-center justify-between"
                >
                  <span className="font-medium text-[var(--foreground)]">
                    {t.teammate_name}
                  </span>
                  <span className="flex items-center gap-3 text-[var(--muted-strong)]">
                    <span>
                      {t.possessions != null
                        ? t.possessions.toLocaleString()
                        : "—"}{" "}
                      poss
                    </span>
                    {t.net_rating_with != null ? (
                      <span
                        className={`font-semibold tabular-nums ${
                          t.net_rating_with >= 0
                            ? "text-[var(--accent-strong)]"
                            : "text-[var(--danger-ink)]"
                        }`}
                      >
                        {t.net_rating_with >= 0 ? "+" : ""}
                        {t.net_rating_with.toFixed(1)} NR
                      </span>
                    ) : null}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-[var(--muted)]">
              No qualifying lineup partners this season (≥100 possessions together).
            </p>
          )}
        </div>
      </div>
      {row.top_teammate ? (
        <p className="mt-3 text-[11px] leading-5 text-[var(--muted-strong)]">
          Strongest pair this season:{" "}
          <span className="font-semibold text-[var(--foreground)]">
            {row.top_teammate.teammate_name}
          </span>
          {row.top_teammate.net_rating_with != null
            ? ` · lineups together at ${
                row.top_teammate.net_rating_with >= 0 ? "+" : ""
              }${row.top_teammate.net_rating_with.toFixed(1)} NR`
            : null}
          {row.top_teammate.shared_possessions
            ? ` across ${row.top_teammate.shared_possessions.toLocaleString()} possessions.`
            : "."}
        </p>
      ) : null}
    </section>
  );
}
