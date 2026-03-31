"use client";

import { type FormEvent, useEffect, useMemo, useState } from "react";
import { getAvailableSeasons, getLeaderboardTeams } from "@/lib/api";
import {
  useCustomMetric,
  type CustomMetricComponentInput,
} from "@/hooks/useCustomMetric";

const STAT_GROUPS = [
  {
    label: "Scoring",
    options: [
      { key: "pts_pg", label: "Points Per Game" },
      { key: "fg_pct", label: "Field Goal %" },
      { key: "fg3_pct", label: "3-Point %" },
      { key: "ft_pct", label: "Free Throw %" },
      { key: "ts_pct", label: "True Shooting %" },
      { key: "efg_pct", label: "Effective FG %" },
    ],
  },
  {
    label: "Production",
    options: [
      { key: "reb_pg", label: "Rebounds Per Game" },
      { key: "ast_pg", label: "Assists Per Game" },
      { key: "stl_pg", label: "Steals Per Game" },
      { key: "blk_pg", label: "Blocks Per Game" },
      { key: "tov_pg", label: "Turnovers Per Game" },
      { key: "min_pg", label: "Minutes Per Game" },
    ],
  },
  {
    label: "Advanced",
    options: [
      { key: "per", label: "PER" },
      { key: "bpm", label: "BPM" },
      { key: "ws", label: "Win Shares" },
      { key: "vorp", label: "VORP" },
      { key: "usg_pct", label: "Usage Rate" },
      { key: "off_rating", label: "Offensive Rating" },
      { key: "def_rating", label: "Defensive Rating" },
      { key: "net_rating", label: "Net Rating" },
      { key: "pie", label: "PIE" },
      { key: "darko", label: "DARKO" },
      { key: "obpm", label: "OBPM" },
      { key: "dbpm", label: "DBPM" },
    ],
  },
  {
    label: "External",
    options: [
      { key: "epm", label: "EPM" },
      { key: "rapm", label: "RAPM" },
      { key: "lebron", label: "LEBRON" },
      { key: "raptor", label: "RAPTOR" },
      { key: "pipm", label: "PIPM" },
    ],
  },
];

const ALL_STATS = STAT_GROUPS.flatMap((group) => group.options);
const POSITION_OPTIONS = ["G", "F", "C", "PG", "SG", "SF", "PF"];

function getStatLabel(statId: string) {
  return ALL_STATS.find((option) => option.key === statId)?.label ?? statId;
}

function scoreTone(score: number) {
  if (score >= 1.0) return "text-[var(--accent-strong)]";
  if (score <= -1.0) return "text-[var(--danger-ink)]";
  return "text-[var(--foreground)]";
}

export function CustomMetricBuilder() {
  const [metricName, setMetricName] = useState("");
  const [season, setSeason] = useState("");
  const [seasons, setSeasons] = useState<string[]>([]);
  const [teams, setTeams] = useState<string[]>([]);
  const [playerPool, setPlayerPool] = useState<"all" | "position_filter" | "team_filter">("all");
  const [teamAbbreviation, setTeamAbbreviation] = useState("");
  const [position, setPosition] = useState("G");
  const [components, setComponents] = useState<CustomMetricComponentInput[]>([
    { stat_id: "pts_pg", label: "Points Per Game", weight: 0.4, inverse: false },
    { stat_id: "ast_pg", label: "Assists Per Game", weight: 0.35, inverse: false },
    { stat_id: "tov_pg", label: "Turnovers Per Game", weight: 0.25, inverse: true },
  ]);
  const { data, error, isLoading, runMetric } = useCustomMetric();

  useEffect(() => {
    getAvailableSeasons()
      .then((nextSeasons) => {
        setSeasons(nextSeasons);
        if (nextSeasons.length > 0) {
          setSeason(nextSeasons[0]);
        }
      })
      .catch(() => setSeasons([]));
  }, []);

  useEffect(() => {
    if (!season) return;
    getLeaderboardTeams(season)
      .then(setTeams)
      .catch(() => setTeams([]));
  }, [season]);

  const totalWeight = useMemo(
    () => components.reduce((sum, component) => sum + Number(component.weight || 0), 0),
    [components]
  );

  function addComponent() {
    const fallback = ALL_STATS.find(
      (option) => !components.some((component) => component.stat_id === option.key)
    );
    if (!fallback) return;
    setComponents((current) => [
      ...current,
      {
        stat_id: fallback.key,
        label: fallback.label,
        weight: 0.1,
        inverse: false,
      },
    ]);
  }

  function updateComponent(index: number, updates: Partial<CustomMetricComponentInput>) {
    setComponents((current) =>
      current.map((component, componentIndex) =>
        componentIndex === index ? { ...component, ...updates } : component
      )
    );
  }

  function removeComponent(index: number) {
    setComponents((current) => current.filter((_, componentIndex) => componentIndex !== index));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runMetric({
      metric_name: metricName || undefined,
      player_pool: playerPool,
      season,
      team_abbreviation: playerPool === "team_filter" ? teamAbbreviation : undefined,
      position: playerPool === "position_filter" ? position : undefined,
      components: components.map((component) => ({
        ...component,
        label: getStatLabel(component.stat_id),
        weight: Number(component.weight) || 0,
      })),
    });
  }

  return (
    <section className="mb-8 rounded-[2rem] border border-[var(--border-strong)] bg-[linear-gradient(135deg,rgba(248,244,232,0.98),rgba(239,232,214,0.96))] p-5 shadow-[0_24px_80px_rgba(47,43,36,0.08)] sm:p-7">
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <div className="space-y-5">
          <div>
            <p className="bip-kicker mb-2">Decision Surface</p>
            <h2 className="bip-display text-3xl font-semibold text-[var(--foreground)]">
              Build Your Own Metric
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted-strong)]">
              Blend the stats you trust, weight them your way, and rank the pool through a z-score normalized composite instead of a raw-stat mashup.
            </p>
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                  Metric Label
                </span>
                <input
                  value={metricName}
                  onChange={(event) => setMetricName(event.target.value)}
                  placeholder="Optional custom label"
                  className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
                />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                  Season
                </span>
                <select
                  value={season}
                  onChange={(event) => setSeason(event.target.value)}
                  className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
                >
                  {seasons.map((seasonOption) => (
                    <option key={seasonOption} value={seasonOption}>
                      {seasonOption}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                  Player Pool
                </span>
                <select
                  value={playerPool}
                  onChange={(event) =>
                    setPlayerPool(event.target.value as "all" | "position_filter" | "team_filter")
                  }
                  className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
                >
                  <option value="all">All Players</option>
                  <option value="position_filter">Position Filter</option>
                  <option value="team_filter">Team Filter</option>
                </select>
              </label>
              {playerPool === "team_filter" ? (
                <label className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                    Team
                  </span>
                  <select
                    value={teamAbbreviation}
                    onChange={(event) => setTeamAbbreviation(event.target.value)}
                    className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
                  >
                    <option value="">Select team</option>
                    {teams.map((team) => (
                      <option key={team} value={team}>
                        {team}
                      </option>
                    ))}
                  </select>
                </label>
              ) : playerPool === "position_filter" ? (
                <label className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                    Position
                  </span>
                  <select
                    value={position}
                    onChange={(event) => setPosition(event.target.value)}
                    className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
                  >
                    {POSITION_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <div className="rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.6)] px-4 py-3 text-sm text-[var(--muted-strong)]">
                  Multi-season presets like <span className="font-semibold text-[var(--foreground)]">3yr_avg</span> and custom ranges are deferred in v1 until the backing data path is explicit.
                </div>
              )}
            </div>

            <div className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                    Components
                  </h3>
                  <p className="mt-1 text-sm text-[var(--muted-strong)]">
                    Total entered weight: <span className="font-semibold text-[var(--foreground)]">{totalWeight.toFixed(2)}</span>
                  </p>
                </div>
                <button
                  type="button"
                  onClick={addComponent}
                  className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
                >
                  Add Stat
                </button>
              </div>
              <div className="space-y-3">
                {components.map((component, index) => (
                  <div
                    key={`${component.stat_id}-${index}`}
                    className="grid gap-3 rounded-[1.25rem] border border-[var(--border)] bg-[var(--surface)] p-3 md:grid-cols-[minmax(0,1.4fr)_120px_96px_auto]"
                  >
                    <select
                      value={component.stat_id}
                      onChange={(event) =>
                        updateComponent(index, {
                          stat_id: event.target.value,
                          label: getStatLabel(event.target.value),
                        })
                      }
                      className="bip-input rounded-2xl px-4 py-3 text-sm"
                    >
                      {STAT_GROUPS.map((group) => (
                        <optgroup key={group.label} label={group.label}>
                          {group.options.map((option) => (
                            <option key={option.key} value={option.key}>
                              {option.label}
                            </option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                    <label className="space-y-1">
                      <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                        Weight
                      </span>
                      <input
                        type="number"
                        min="0"
                        max="1"
                        step="0.05"
                        value={component.weight}
                        onChange={(event) =>
                          updateComponent(index, { weight: Number(event.target.value) || 0 })
                        }
                        className="bip-input w-full rounded-2xl px-4 py-3 text-sm"
                      />
                    </label>
                    <label className="flex items-center gap-2 rounded-2xl border border-[var(--border)] px-3 py-3 text-sm text-[var(--muted-strong)]">
                      <input
                        type="checkbox"
                        checked={component.inverse}
                        onChange={(event) => updateComponent(index, { inverse: event.target.checked })}
                        className="h-4 w-4 rounded border-[var(--border-strong)] text-[var(--accent-strong)]"
                      />
                      Inverse
                    </label>
                    <button
                      type="button"
                      onClick={() => removeComponent(index)}
                      disabled={components.length <= 1}
                      className="rounded-2xl border border-[rgba(140,58,42,0.25)] px-4 py-3 text-sm font-medium text-[var(--danger-ink)] transition hover:bg-[var(--danger-soft)] disabled:opacity-40"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={
                  isLoading ||
                  !season ||
                  components.length === 0 ||
                  (playerPool === "team_filter" && !teamAbbreviation)
                }
                className="rounded-full bg-[var(--accent-strong)] px-5 py-3 text-sm font-semibold uppercase tracking-[0.18em] text-[var(--surface)] transition hover:bg-[var(--accent)] disabled:cursor-wait disabled:opacity-60"
              >
                {isLoading ? "Scoring..." : "Score Metric"}
              </button>
              <p className="text-sm text-[var(--muted-strong)]">
                Scores are rounded to 2 decimals after every stat is z-score normalized against the active pool.
              </p>
            </div>
          </form>
        </div>

        <div className="space-y-4 rounded-[1.75rem] border border-[var(--border)] bg-[rgba(255,255,255,0.7)] p-4 sm:p-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              Output Profile
            </p>
            <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
              {data?.metric_label ?? "Awaiting metric run"}
            </h3>
            <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">
              {data?.metric_interpretation ??
                "The result panel will name your metric, explain the player type it rewards, and surface the most weight-sensitive outliers."}
            </p>
          </div>

          {error && (
            <div className="rounded-[1.25rem] border border-[rgba(140,58,42,0.24)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger-ink)]">
              {error}
            </div>
          )}

          {data?.validation_warnings?.length ? (
            <div className="rounded-[1.25rem] border border-[rgba(161,119,55,0.24)] bg-[rgba(181,145,78,0.08)] px-4 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Validation Warnings
              </p>
              <ul className="mt-2 space-y-2 text-sm text-[var(--muted-strong)]">
                {data.validation_warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-3">
            {(data?.top_player_narratives ?? []).map((entry) => (
              <div
                key={entry.player_name}
                className="rounded-[1.25rem] border border-[var(--border)] bg-[var(--surface)] px-4 py-4"
              >
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                  Top Rank
                </p>
                <h4 className="mt-2 text-base font-semibold text-[var(--foreground)]">
                  {entry.player_name}
                </h4>
                <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">
                  {entry.narrative}
                </p>
              </div>
            ))}
          </div>

          {data?.anomalies?.length ? (
            <div className="rounded-[1.25rem] border border-[rgba(161,119,55,0.24)] bg-[rgba(161,119,55,0.08)] px-4 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Weight-Sensitive Outliers
              </p>
              <div className="mt-3 space-y-2">
                {data.anomalies.slice(0, 4).map((anomaly) => (
                  <div key={`${anomaly.player_name}-${anomaly.dominant_stat}`} className="flex items-center justify-between gap-3 text-sm">
                    <span className="font-medium text-[var(--foreground)]">{anomaly.player_name}</span>
                    <span className="text-[var(--muted-strong)]">
                      {getStatLabel(anomaly.dominant_stat)} · {anomaly.contribution_pct.toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="mt-6 overflow-hidden rounded-[1.75rem] border border-[var(--border)] bg-[var(--surface)]">
        <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] px-4 py-4 sm:px-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
              Rankings
            </p>
            <h3 className="mt-1 text-xl font-semibold text-[var(--foreground)]">
              Composite Leaderboard
            </h3>
          </div>
          {data ? (
            <span className="rounded-full bg-[rgba(33,72,59,0.08)] px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--accent-strong)]">
              {data.player_rankings.length} ranked
            </span>
          ) : null}
        </div>
        {data ? (
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[rgba(244,238,223,0.8)]">
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">#</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Player</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Team</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Score</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">Component Breakdown</th>
                </tr>
              </thead>
              <tbody>
                {data.player_rankings.slice(0, 15).map((row) => (
                  <tr key={`${row.rank}-${row.player_name}`} className="border-b border-[var(--border)] last:border-0">
                    <td className="px-4 py-3 text-sm text-[var(--muted-strong)]">{row.rank}</td>
                    <td className="px-4 py-3 text-sm font-semibold text-[var(--foreground)]">
                      {row.player_name}
                    </td>
                    <td className="px-4 py-3 text-sm text-[var(--muted-strong)]">{row.team}</td>
                    <td className={`px-4 py-3 text-right text-sm font-semibold tabular-nums ${scoreTone(row.composite_score)}`}>
                      {row.composite_score.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-sm text-[var(--muted-strong)]">
                      <div className="flex flex-wrap gap-2">
                        {Object.entries(row.component_breakdown).map(([statId, value]) => (
                          <span
                            key={`${row.player_name}-${statId}`}
                            className="rounded-full border border-[var(--border)] bg-[rgba(244,238,223,0.72)] px-2.5 py-1 text-xs"
                          >
                            {getStatLabel(statId)}: <span className={scoreTone(value)}>{value.toFixed(2)}</span>
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="px-5 py-10 text-center text-sm text-[var(--muted-strong)]">
            Run a metric to see ranked players, narratives, and anomalies.
          </div>
        )}
      </div>

      <p className="mt-4 text-xs text-[var(--muted)]">
        Missing-stat players are excluded rather than fabricated. For game-level context after ranking, jump back into the player page or Game Explorer from the top names.
      </p>
    </section>
  );
}
