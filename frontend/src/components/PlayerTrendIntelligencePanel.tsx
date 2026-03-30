"use client";

import Link from "next/link";
import { usePlayerTrendReport } from "@/hooks/usePlayerStats";

interface PlayerTrendIntelligencePanelProps {
  playerId: number;
  season: string | null;
  isPlayoffs: boolean;
}

function fmt(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : value.toFixed(digits);
}

function signed(value: number | null | undefined, digits = 1) {
  if (value == null) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function pct(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : `${(value * 100).toFixed(digits)}%`;
}

function pctPoints(value: number | null | undefined, digits = 1) {
  if (value == null) return "—";
  const converted = value * 100;
  return `${converted > 0 ? "+" : ""}${converted.toFixed(digits)} pts`;
}

function titleizeRole(roleStatus: string) {
  return roleStatus
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function roleTone(roleStatus: string) {
  if (roleStatus === "rising_rotation" || roleStatus === "entrenched_starter") {
    return "text-[var(--success-ink)]";
  }
  if (roleStatus === "losing_trust") {
    return "text-[var(--danger-ink)]";
  }
  if (roleStatus === "volatile_role") {
    return "text-[var(--signal-ink)]";
  }
  return "text-[var(--foreground)]";
}

function coverageTone(status: string) {
  if (status === "ready") return "bip-success";
  if (status === "partial") return "bip-pill";
  return "bip-tag";
}

function coverageLabel(status: string) {
  if (status === "ready") return "PBP Ready";
  if (status === "partial") return "PBP Partial";
  return "No PBP Support";
}

function deltaTone(value: number | null | undefined) {
  if (value == null) return "text-[var(--muted)]";
  if (value > 0) return "text-[var(--success-ink)]";
  if (value < 0) return "text-[var(--danger-ink)]";
  return "text-[var(--foreground)]";
}

export default function PlayerTrendIntelligencePanel({
  playerId,
  season,
  isPlayoffs,
}: PlayerTrendIntelligencePanelProps) {
  const { data: report, error } = usePlayerTrendReport(
    isPlayoffs ? null : playerId,
    isPlayoffs ? null : season
  );

  if (!season) {
    return null;
  }

  if (isPlayoffs) {
    return (
      <section className="bip-panel-strong rounded-[2rem] p-6">
        <div className="bip-kicker">Player Trend Intelligence</div>
        <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
          Recent role-change decision support
        </h2>
        <div className="bip-empty mt-6 rounded-3xl p-6 text-sm leading-6">
          Player Trend Intelligence is available for regular-season game-log windows only.
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="bip-panel-strong rounded-[2rem] p-6">
        <div className="bip-kicker">Player Trend Intelligence</div>
        <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
          Recent role-change decision support
        </h2>
        <div className="mt-6 rounded-3xl border border-[rgba(127,51,43,0.18)] bg-[var(--danger-soft)] p-6 text-sm leading-6 text-[var(--danger-ink)]">
          The player trend report could not be loaded right now.
        </div>
      </section>
    );
  }

  if (!report) {
    return (
      <section className="bip-panel-strong rounded-[2rem] p-6">
        <div className="bip-kicker">Player Trend Intelligence</div>
        <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
          Recent role-change decision support
        </h2>
        <div className="mt-6 grid gap-4 md:grid-cols-4">
          <div className="h-28 rounded-3xl bg-[var(--surface-alt)] animate-pulse" />
          <div className="h-28 rounded-3xl bg-[var(--surface-alt)] animate-pulse" />
          <div className="h-28 rounded-3xl bg-[var(--surface-alt)] animate-pulse" />
          <div className="h-28 rounded-3xl bg-[var(--surface-alt)] animate-pulse" />
        </div>
      </section>
    );
  }

  const bestGame = report.recommended_games[0] ?? null;
  const comparisonRows = [
    {
      label: "Minutes",
      recent: fmt(report.recent_form.avg_minutes),
      seasonValue: fmt(report.season_baseline.avg_minutes),
      delta: signed(report.trust_signals.minutes_delta),
      deltaClass: deltaTone(report.trust_signals.minutes_delta),
    },
    {
      label: "Points",
      recent: fmt(report.recent_form.avg_points),
      seasonValue: fmt(report.season_baseline.avg_points),
      delta: signed(report.trust_signals.points_delta),
      deltaClass: deltaTone(report.trust_signals.points_delta),
    },
    {
      label: "Rebounds",
      recent: fmt(report.recent_form.avg_rebounds),
      seasonValue: fmt(report.season_baseline.avg_rebounds),
      delta: signed(
        report.recent_form.avg_rebounds != null && report.season_baseline.avg_rebounds != null
          ? report.recent_form.avg_rebounds - report.season_baseline.avg_rebounds
          : null
      ),
      deltaClass: deltaTone(
        report.recent_form.avg_rebounds != null && report.season_baseline.avg_rebounds != null
          ? report.recent_form.avg_rebounds - report.season_baseline.avg_rebounds
          : null
      ),
    },
    {
      label: "Assists",
      recent: fmt(report.recent_form.avg_assists),
      seasonValue: fmt(report.season_baseline.avg_assists),
      delta: signed(
        report.recent_form.avg_assists != null && report.season_baseline.avg_assists != null
          ? report.recent_form.avg_assists - report.season_baseline.avg_assists
          : null
      ),
      deltaClass: deltaTone(
        report.recent_form.avg_assists != null && report.season_baseline.avg_assists != null
          ? report.recent_form.avg_assists - report.season_baseline.avg_assists
          : null
      ),
    },
    {
      label: "FG%",
      recent: pct(report.recent_form.avg_fg_pct),
      seasonValue: pct(report.season_baseline.avg_fg_pct),
      delta: pctPoints(report.trust_signals.efficiency_delta),
      deltaClass: deltaTone(report.trust_signals.efficiency_delta),
    },
    {
      label: "3PT%",
      recent: pct(report.recent_form.avg_fg3_pct),
      seasonValue: pct(report.season_baseline.avg_fg3_pct),
      delta: pctPoints(
        report.recent_form.avg_fg3_pct != null && report.season_baseline.avg_fg3_pct != null
          ? report.recent_form.avg_fg3_pct - report.season_baseline.avg_fg3_pct
          : null
      ),
      deltaClass: deltaTone(
        report.recent_form.avg_fg3_pct != null && report.season_baseline.avg_fg3_pct != null
          ? report.recent_form.avg_fg3_pct - report.season_baseline.avg_fg3_pct
          : null
      ),
    },
    {
      label: "Plus/Minus",
      recent: signed(report.recent_form.avg_plus_minus),
      seasonValue: signed(report.season_baseline.avg_plus_minus),
      delta: signed(
        report.recent_form.avg_plus_minus != null && report.season_baseline.avg_plus_minus != null
          ? report.recent_form.avg_plus_minus - report.season_baseline.avg_plus_minus
          : null
      ),
      deltaClass: deltaTone(
        report.recent_form.avg_plus_minus != null && report.season_baseline.avg_plus_minus != null
          ? report.recent_form.avg_plus_minus - report.season_baseline.avg_plus_minus
          : null
      ),
    },
  ];

  return (
    <section className="bip-panel-strong rounded-[2rem] p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="bip-kicker">Player Trend Intelligence</div>
          <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
            Recent role-change decision support
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
            Compare the last {report.window_games || 10} regular-season games against the season baseline, check whether the shift is trust, production, or efficiency driven, then open the right game next.
          </p>
        </div>
        <span className={`w-fit rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${coverageTone(report.impact_snapshot.pbp_coverage_status)}`}>
          {coverageLabel(report.impact_snapshot.pbp_coverage_status)}
        </span>
      </div>

      {report.status === "limited" ? (
        <div className="bip-empty mt-6 rounded-3xl p-6 text-sm leading-6">
          This player trend report needs at least five regular-season game logs in the selected season before the decision board unlocks.
        </div>
      ) : (
        <div className="mt-6 space-y-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="bip-metric rounded-3xl p-5">
              <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                Role status
              </div>
              <div className={`mt-3 text-3xl font-bold ${roleTone(report.role_status)}`}>
                {titleizeRole(report.role_status)}
              </div>
              <div className="mt-2 text-sm text-[var(--muted)]">
                {report.team_abbreviation ?? "Team"} · {report.season}
              </div>
            </div>
            <div className="bip-metric rounded-3xl p-5">
              <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                Starts / bench trust
              </div>
              <div className="mt-3 text-3xl font-bold text-[var(--foreground)]">
                {report.trust_signals.starts_last_10} / {report.trust_signals.bench_games_last_10}
              </div>
              <div className="mt-2 text-sm text-[var(--muted)]">
                Starts vs bench games in the last {report.window_games}
              </div>
            </div>
            <div className="bip-metric rounded-3xl p-5">
              <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                Minutes delta
              </div>
              <div className={`mt-3 text-3xl font-bold ${deltaTone(report.trust_signals.minutes_delta)}`}>
                {signed(report.trust_signals.minutes_delta)}
              </div>
              <div className="mt-2 text-sm text-[var(--muted)]">
                Versus season average minutes
              </div>
            </div>
            <div className="bip-metric rounded-3xl p-5">
              <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                Best game to review
              </div>
              {bestGame ? (
                <>
                  <div className="mt-3 text-xl font-semibold text-[var(--foreground)]">
                    {bestGame.matchup ?? "Game review"}
                  </div>
                  <div className="mt-2 text-sm text-[var(--muted)]">
                    {bestGame.trend_note}
                  </div>
                </>
              ) : (
                <div className="mt-3 text-lg font-semibold text-[var(--muted)]">
                  No review game yet
                </div>
              )}
            </div>
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.08fr,0.92fr]">
            <div className="space-y-6">
              <div>
                <div className="flex items-end justify-between gap-4">
                  <div>
                    <div className="bip-kicker">Recent Vs Season</div>
                    <h3 className="mt-2 text-xl font-semibold text-[var(--foreground)]">
                      What changed in the production mix
                    </h3>
                  </div>
                  <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                    Last {report.window_games} games
                  </div>
                </div>
                <div className="bip-table-shell mt-4 overflow-hidden rounded-3xl">
                  <div className="grid grid-cols-[minmax(0,1.2fr)_repeat(3,minmax(72px,0.7fr))] gap-3 px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                    <div>Signal</div>
                    <div className="text-right">Recent</div>
                    <div className="text-right">Season</div>
                    <div className="text-right">Delta</div>
                  </div>
                  <div className="divide-y divide-[var(--border)]">
                    {comparisonRows.map((row) => (
                      <div
                        key={row.label}
                        className="grid grid-cols-[minmax(0,1.2fr)_repeat(3,minmax(72px,0.7fr))] gap-3 px-4 py-3 text-sm"
                      >
                        <div className="font-medium text-[var(--foreground)]">{row.label}</div>
                        <div className="text-right font-semibold text-[var(--foreground)]">{row.recent}</div>
                        <div className="text-right text-[var(--muted)]">{row.seasonValue}</div>
                        <div className={`text-right font-semibold ${row.deltaClass}`}>{row.delta}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div>
                <div className="bip-kicker">Trust Signals</div>
                <h3 className="mt-2 text-xl font-semibold text-[var(--foreground)]">
                  Is the role change real or noisy?
                </h3>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div className="bip-accent-card rounded-3xl p-5">
                    <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                      Minutes profile
                    </div>
                    <div className="mt-3 flex items-end justify-between gap-3">
                      <div className={`text-3xl font-bold ${deltaTone(report.trust_signals.minutes_delta)}`}>
                        {signed(report.trust_signals.minutes_delta)}
                      </div>
                      <div className="text-sm text-[var(--muted)]">
                        {report.trust_signals.games_30_plus_last_10} games at 30+
                      </div>
                    </div>
                    <div className="mt-2 text-sm leading-6 text-[var(--foreground)]">
                      {report.trust_signals.games_under_20_last_10} games under 20 minutes · volatility {fmt(report.trust_signals.minute_volatility)}
                    </div>
                  </div>
                  <div className="bip-signal-card rounded-3xl p-5">
                    <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                      Output shift
                    </div>
                    <div className="mt-3 flex items-end justify-between gap-3">
                      <div className={`text-3xl font-bold ${deltaTone(report.trust_signals.points_delta)}`}>
                        {signed(report.trust_signals.points_delta)}
                      </div>
                      <div className={`text-sm font-semibold ${deltaTone(report.trust_signals.efficiency_delta)}`}>
                        {pctPoints(report.trust_signals.efficiency_delta)}
                      </div>
                    </div>
                    <div className="mt-2 text-sm leading-6 text-[var(--foreground)]">
                      Points delta vs season with FG efficiency shift called out separately.
                    </div>
                  </div>
                  <div className="bip-panel rounded-3xl p-5">
                    <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                      Start cadence
                    </div>
                    <div className="mt-3 text-3xl font-bold text-[var(--foreground)]">
                      {report.trust_signals.starts_last_10}
                    </div>
                    <div className="mt-2 text-sm leading-6 text-[var(--foreground)]">
                      Starts in the last {report.window_games} games, with {report.trust_signals.bench_games_last_10} bench appearances.
                    </div>
                  </div>
                  <div className="bip-panel rounded-3xl p-5">
                    <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                      Stability read
                    </div>
                    <div className={`mt-3 text-3xl font-bold ${roleTone(report.role_status)}`}>
                      {titleizeRole(report.role_status)}
                    </div>
                    <div className="mt-2 text-sm leading-6 text-[var(--foreground)]">
                      Label driven by starts, recent minute swing, and recent minute volatility.
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-6">
              <div className="bip-panel rounded-3xl p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="bip-kicker">Impact Snapshot</div>
                    <h3 className="mt-2 text-xl font-semibold text-[var(--foreground)]">
                      How much impact support is behind the trend
                    </h3>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${coverageTone(report.impact_snapshot.pbp_coverage_status)}`}>
                    {coverageLabel(report.impact_snapshot.pbp_coverage_status)}
                  </span>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="bip-metric rounded-2xl p-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">On/Off Net</div>
                    <div className={`mt-2 text-2xl font-bold ${deltaTone(report.impact_snapshot.on_off_net)}`}>
                      {signed(report.impact_snapshot.on_off_net)}
                    </div>
                  </div>
                  <div className="bip-metric rounded-2xl p-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">On Minutes</div>
                    <div className="mt-2 text-2xl font-bold text-[var(--foreground)]">
                      {fmt(report.impact_snapshot.on_minutes, 0)}
                    </div>
                  </div>
                  <div className="bip-metric rounded-2xl p-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">BPM</div>
                    <div className={`mt-2 text-2xl font-bold ${deltaTone(report.impact_snapshot.bpm)}`}>
                      {signed(report.impact_snapshot.bpm)}
                    </div>
                  </div>
                  <div className="bip-metric rounded-2xl p-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">PER</div>
                    <div className="mt-2 text-2xl font-bold text-[var(--foreground)]">
                      {fmt(report.impact_snapshot.per)}
                    </div>
                  </div>
                  <div className="bip-metric rounded-2xl p-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">PPG</div>
                    <div className="mt-2 text-2xl font-bold text-[var(--foreground)]">
                      {fmt(report.impact_snapshot.pts_pg)}
                    </div>
                  </div>
                  <div className="bip-metric rounded-2xl p-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--muted)]">TS%</div>
                    <div className="mt-2 text-2xl font-bold text-[var(--foreground)]">
                      {pct(report.impact_snapshot.ts_pct)}
                    </div>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-6 text-[var(--muted)]">
                  On/off support is optional inside this report. Missing PBP-derived values should not block the overall trend read.
                </p>
              </div>

              <div>
                <div className="bip-kicker">Games To Review Next</div>
                <h3 className="mt-2 text-xl font-semibold text-[var(--foreground)]">
                  Open the most revealing recent tape first
                </h3>
                <div className="mt-4 space-y-3">
                  {report.recommended_games.map((game) => (
                    <Link
                      key={game.game_id}
                      href={`/games/${game.game_id}`}
                      className={`block rounded-3xl p-4 transition-colors hover:border-[rgba(33,72,59,0.28)] hover:bg-[rgba(216,228,221,0.24)] ${game.is_starter ? "bip-accent-card" : "bip-panel"}`}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">
                            {game.game_date ?? "Date unavailable"}
                          </div>
                          <div className="mt-1 text-lg font-semibold text-[var(--foreground)]">
                            {game.matchup ?? "Game review"}
                          </div>
                          <div className="mt-2 text-sm text-[var(--muted)]">
                            {game.is_starter ? "Starter look" : "Bench role"} · {fmt(game.minutes)} min · {game.points ?? "—"} pts
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`text-sm font-semibold ${game.result === "W" ? "text-[var(--success-ink)]" : "text-[var(--danger-ink)]"}`}>
                            {game.result ?? "—"}
                          </div>
                          <div className={`mt-1 text-base font-semibold ${deltaTone(game.plus_minus)}`}>
                            {signed(game.plus_minus)}
                          </div>
                        </div>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-[var(--foreground)]">
                        {game.trend_note}
                      </p>
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
