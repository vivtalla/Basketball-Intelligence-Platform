"use client";

import type { TeamComparisonResponse } from "@/lib/types";

interface TeamComparisonViewProps {
  comparison: TeamComparisonResponse;
}

function formatValue(value: number | null, format: "number" | "percent" | "signed") {
  if (value == null) return "—";
  if (format === "percent") return `${(value * 100).toFixed(1)}%`;
  if (format === "signed") return `${value > 0 ? "+" : ""}${value.toFixed(1)}`;
  return value.toFixed(1);
}

function edgeTone(edge: "team_a" | "team_b" | "even", team: "team_a" | "team_b") {
  if (edge === "even") return "text-[var(--foreground)]";
  if (edge === team) return "text-[var(--accent-strong)]";
  return "text-[var(--muted)]";
}

function storyTone(edge: "team_a" | "team_b" | "even") {
  if (edge === "team_a") return "bg-[rgba(33,72,59,0.08)] text-[var(--accent-strong)]";
  if (edge === "team_b") return "bg-[rgba(181,145,78,0.12)] text-[var(--foreground)]";
  return "bg-[var(--surface-alt)] text-[var(--muted-strong)]";
}

export default function TeamComparisonView({ comparison }: TeamComparisonViewProps) {
  return (
    <div className="space-y-6">
      <section className="grid gap-4 lg:grid-cols-2">
        {[comparison.team_a, comparison.team_b].map((team) => (
          <article key={team.abbreviation} className="bip-panel rounded-[1.8rem] p-6">
            <p className="bip-kicker">{team.abbreviation}</p>
            <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
              {team.name}
            </h2>
            <div className="mt-5 grid grid-cols-2 gap-3">
              <div className="rounded-2xl bip-metric p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Recent form</div>
                <div className="mt-2 text-2xl font-semibold text-[var(--foreground)]">{team.recent_record ?? "—"}</div>
              </div>
              <div className="rounded-2xl bip-accent-card p-4">
                <div className="text-xs uppercase tracking-[0.18em] text-[var(--accent)]">Net rating</div>
                <div className="mt-2 text-2xl font-semibold text-[var(--accent-strong)]">{formatValue(team.net_rating, "signed")}</div>
              </div>
            </div>
          </article>
        ))}
      </section>

      <section className="bip-panel rounded-[1.8rem] p-6">
        <div className="flex flex-wrap gap-3">
          {comparison.stories.map((story) => (
            <div key={`${story.label}-${story.summary}`} className={`rounded-full px-4 py-2 text-sm font-medium ${storyTone(story.edge)}`}>
              {story.label}
            </div>
          ))}
        </div>
        <div className="mt-5 space-y-3">
          {comparison.rows.map((row) => (
            <div key={row.stat_id} className="grid grid-cols-[1fr_auto_1fr] items-center gap-4 rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.65)] px-4 py-3">
              <div className={`text-right text-lg font-semibold tabular-nums ${edgeTone(row.edge, "team_a")}`}>
                {formatValue(row.team_a_value, row.format)}
              </div>
              <div className="text-center text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                {row.label}
              </div>
              <div className={`text-left text-lg font-semibold tabular-nums ${edgeTone(row.edge, "team_b")}`}>
                {formatValue(row.team_b_value, row.format)}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        {comparison.stories.map((story) => (
          <article key={story.summary} className="rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">{story.label}</p>
            <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">{story.summary}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
