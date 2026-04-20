"use client";

import type { TeamSummary } from "@/lib/types";

type Mode = "trajectory" | "usage" | "trends" | "whatif";

interface Props {
  mode: Mode;
  team: string;
  season: string;
  opponent: string;
  playerId: number | null;
  signal: string;
  teams: TeamSummary[];
  onModeChange: (mode: Mode) => void;
  onParamChange: (key: string, value: string | null) => void;
}

const SEASONS = ["2025-26", "2024-25", "2023-24", "2022-23"];

const TABS: { key: Mode; label: string }[] = [
  { key: "trajectory", label: "Trajectory Tracker" },
  { key: "usage", label: "Usage vs Efficiency" },
  { key: "trends", label: "Trend Cards" },
  { key: "whatif", label: "What-If" },
];

export function InsightsHeader({
  mode,
  team,
  season,
  opponent,
  playerId,
  signal,
  teams,
  onModeChange,
  onParamChange,
}: Props) {
  return (
    <section className="bip-panel-strong rounded-[2rem] p-6">
      <div className="flex flex-wrap items-end justify-between gap-5">
        <div className="max-w-3xl">
          <p className="bip-kicker mb-2">Coach Workflow</p>
          <h1 className="bip-display text-4xl font-semibold text-[var(--foreground)]">
            Platform intelligence, not just reporting
          </h1>
          <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
            Trajectory, usage, weekly trend cards, and what-if scenarios for{" "}
            <strong>{team}</strong>. Each tab preserves context and points toward the next
            drill-down.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              Team
            </span>
            <select
              value={team}
              onChange={(e) => onParamChange("team", e.target.value)}
              className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
            >
              {teams.map((t) => (
                <option key={t.abbreviation} value={t.abbreviation}>
                  {t.abbreviation} · {t.name}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              Season
            </span>
            <select
              value={season}
              onChange={(e) => onParamChange("season", e.target.value)}
              className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
            >
              {SEASONS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              Opponent
            </span>
            <select
              value={opponent}
              onChange={(e) =>
                onParamChange("opponent", e.target.value || null)
              }
              className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
            >
              <option value="">Optional matchup context</option>
              {teams
                .filter((t) => t.abbreviation !== team)
                .map((t) => (
                  <option key={t.abbreviation} value={t.abbreviation}>
                    {t.abbreviation} · {t.name}
                  </option>
                ))}
            </select>
          </label>
        </div>
      </div>

      {/* Tab bar */}
      <div className="mt-6 flex overflow-hidden rounded-xl border border-[var(--border)] w-fit text-sm">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => onModeChange(key)}
            className={`px-5 py-2 transition-colors ${
              mode === key ? "bip-toggle-active" : "bip-toggle"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Cross-tab handoff chips */}
      <div className="mt-4 flex flex-wrap gap-2">
        {mode !== "trends" && (
          <button
            onClick={() => onModeChange("trends")}
            className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-[11px] font-medium text-[var(--muted-strong)] transition hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
          >
            Open Trend Cards for {team} →
          </button>
        )}
        {mode !== "trajectory" && playerId != null && (
          <button
            onClick={() => onModeChange("trajectory")}
            className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-[11px] font-medium text-[var(--muted-strong)] transition hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
          >
            See Trajectory for pinned player →
          </button>
        )}
        {mode !== "usage" && (playerId != null || signal) && (
          <button
            onClick={() => onModeChange("usage")}
            className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-[11px] font-medium text-[var(--muted-strong)] transition hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
          >
            Back to Opportunity{signal ? ` · ${signal.replaceAll("_", " ")}` : ""} →
          </button>
        )}
        {playerId != null && (
          <button
            onClick={() => onParamChange("player_id", null)}
            className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-[11px] font-medium text-[var(--muted-strong)] transition hover:border-[var(--danger-ink)] hover:text-[var(--danger-ink)]"
          >
            Clear player pin
          </button>
        )}
        {mode !== "whatif" && opponent && (
          <button
            onClick={() => onModeChange("whatif")}
            className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-[11px] font-medium text-[var(--muted-strong)] transition hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
          >
            What-If: {team} vs {opponent} →
          </button>
        )}
        {mode !== "usage" && (
          <button
            onClick={() => onModeChange("usage")}
            className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-[11px] font-medium text-[var(--muted-strong)] transition hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
          >
            Usage vs Efficiency →
          </button>
        )}
        {mode !== "trajectory" && (
          <button
            onClick={() => onModeChange("trajectory")}
            className="rounded-full border border-[var(--border)] bg-[var(--surface)] px-3 py-1 text-[11px] font-medium text-[var(--muted-strong)] transition hover:border-[var(--accent-strong)] hover:text-[var(--accent-strong)]"
          >
            Player Trajectory →
          </button>
        )}
      </div>
    </section>
  );
}
