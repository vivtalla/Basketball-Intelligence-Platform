"use client";

import Link from "next/link";
import type { ShotReplayExample } from "@/lib/types";

interface Props {
  examples: ShotReplayExample[];
  heading?: string;
}

const LINKAGE_LABEL: Record<ShotReplayExample["linkage_quality"], string> = {
  exact: "exact",
  derived: "derived",
  timeline: "timeline",
};

const LINKAGE_TONE: Record<ShotReplayExample["linkage_quality"], string> = {
  exact: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  derived: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  timeline: "bg-slate-500/10 text-[var(--muted)] border-[var(--border)]",
};

function headline(ex: ShotReplayExample): string {
  const dist = ex.shot_distance != null ? `${ex.shot_distance}ft` : "";
  const result = ex.shot_made ? "made" : "miss";
  return [dist, result].filter(Boolean).join(" · ") || result;
}

function subtitle(ex: ShotReplayExample): string {
  const parts: string[] = [];
  if (ex.opponent_abbreviation) parts.push(`vs ${ex.opponent_abbreviation}`);
  if (ex.period != null && ex.clock) parts.push(`Q${ex.period} ${ex.clock}`);
  else if (ex.period != null) parts.push(`Q${ex.period}`);
  if (ex.game_date) parts.push(ex.game_date);
  return parts.join(" · ");
}

export default function ShotExamplesChips({ examples, heading = "Show me examples" }: Props) {
  if (!examples || !examples.length) return null;

  return (
    <div className="space-y-2">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
        {heading}
      </p>
      <div className="flex flex-wrap gap-2">
        {examples.map((ex, idx) => (
          <Link
            key={`${ex.game_id}-${ex.action_number ?? ex.shot_event_id ?? idx}`}
            href={ex.deep_link_url}
            className="group flex flex-col gap-0.5 rounded-2xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs transition hover:border-[var(--accent-strong)] hover:shadow-sm"
          >
            <span className="flex items-center gap-1.5 font-semibold text-[var(--foreground)] group-hover:text-[var(--accent-strong)]">
              {headline(ex)}
              <span
                className={`rounded-full border px-1.5 py-0.5 text-[9px] uppercase tracking-wider ${LINKAGE_TONE[ex.linkage_quality]}`}
                title={`Linkage: ${LINKAGE_LABEL[ex.linkage_quality]}`}
              >
                {LINKAGE_LABEL[ex.linkage_quality]}
              </span>
            </span>
            <span className="text-[10px] text-[var(--muted)]">{subtitle(ex) || "—"}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
