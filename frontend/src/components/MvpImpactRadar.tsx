"use client";

import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { MvpImpactConsensusProfile } from "@/lib/types";

interface Props {
  profile: MvpImpactConsensusProfile | null | undefined;
  playerName: string;
}

export default function MvpImpactRadar({ profile, playerName }: Props) {
  if (!profile) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4 text-xs text-[var(--muted)]">
        Impact consensus unavailable for this candidate.
      </div>
    );
  }

  const data = profile.metrics.map((m) => ({
    metric: m.name,
    percentile: m.percentile ?? 0,
    hasData: m.percentile !== null,
    value: m.value,
    source: m.source,
    as_of: m.as_of,
  }));

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--accent)]">Impact Consensus</p>
          <p className="mt-1 text-xs text-[var(--muted)]">
            Percentile rank across available impact metrics for {playerName}.
          </p>
        </div>
        <div className="text-right text-xs">
          <p className="font-semibold text-[var(--foreground)]">
            {profile.consensus_score !== null ? `${profile.consensus_score.toFixed(1)}%ile` : "—"}
          </p>
          <p className="text-[var(--muted)]">coverage {profile.coverage_ratio}</p>
          {profile.disagreement !== null ? (
            <p className="text-[10px] text-[var(--muted)]">disagreement σ={profile.disagreement.toFixed(1)}</p>
          ) : null}
        </div>
      </div>

      <div className="mt-3 h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data} outerRadius="75%">
            <PolarGrid stroke="var(--border)" />
            <PolarAngleAxis dataKey="metric" tick={{ fill: "var(--muted)", fontSize: 11 }} />
            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "var(--muted)", fontSize: 10 }} />
            <Radar
              name={playerName}
              dataKey="percentile"
              stroke="var(--accent)"
              fill="var(--accent)"
              fillOpacity={0.35}
            />
            <Tooltip
              contentStyle={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                fontSize: 12,
              }}
              formatter={(value: unknown, _name, entry) => {
                const payload = entry?.payload as {
                  metric?: string;
                  value?: number | null;
                  source?: string | null;
                  as_of?: string | null;
                  hasData?: boolean;
                };
                if (!payload?.hasData) return ["no data", payload?.metric ?? ""];
                const raw = payload?.value != null ? payload.value.toFixed(2) : "—";
                const attrib = [payload?.source, payload?.as_of].filter(Boolean).join(" · ");
                return [`${String(value)}%ile (raw ${raw}) — ${attrib}`, payload?.metric ?? ""];
              }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <ul className="mt-3 grid grid-cols-2 gap-1 text-[10px] text-[var(--muted)] sm:grid-cols-4">
        {profile.metrics.map((m) => (
          <li key={m.name} className="flex items-center justify-between rounded border border-[var(--border)] px-2 py-1">
            <span className="font-semibold text-[var(--foreground)]">{m.name}</span>
            <span>{m.percentile !== null ? `${m.percentile.toFixed(0)}` : "—"}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
