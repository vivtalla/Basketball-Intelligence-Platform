"use client";

import Link from "next/link";
import { useState } from "react";
import { useTrendCards } from "@/hooks/usePlayerStats";
import type { TrendCard, TrendPlayerRow } from "@/lib/types";

interface TrendCardsPanelProps {
  teamAbbreviation: string;
  season: string;
  pinnedPlayerId: number | null;
  signal: string;
  onPlayerPin: (playerId: number | null) => void;
  onSignalChange: (signal: string | null) => void;
}

function fmt(value: number | null | undefined, digits = 1, suffix = "") {
  if (value == null) return "-";
  return `${value.toFixed(digits)}${suffix}`;
}

function fmtSigned(value: number | null | undefined, digits = 2) {
  if (value == null) return "-";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}`;
}

function directionLabel(direction: TrendCard["direction"]) {
  if (direction === "up") return "Rising";
  if (direction === "down") return "Falling";
  return "Stable";
}

function signalLabel(signal: string | null | undefined) {
  if (!signal) return "team";
  return signal.replaceAll("_", " ");
}

const TREND_SIGNAL_DESCRIPTIONS: Record<string, string> = {
  pts: "Points per game — raw scoring output over the recent window vs baseline.",
  ts_pct: "True-shooting percentage — scoring efficiency across 2s, 3s, and FTs.",
  usg_pct: "Usage rate — share of team possessions finished while on the floor.",
  ast: "Assists per game — creation volume for teammates.",
  reb: "Rebounds per game — board activity in the recent window.",
  tov_pct: "Turnover rate — turnovers per possession used. Higher = worse.",
  plus_minus: "On-court point differential per game.",
  on_off_net: "On/off net rating — team net when player is on minus off.",
  gravity_score: "Defensive gravity / attention pulled from the weakside.",
  shot_quality_delta: "Shot quality delta — actual TS% minus expected TS% given shot location.",
  minutes: "Minutes per game over the recent window.",
};

function confidenceTone(level: "high" | "medium" | "low") {
  if (level === "high") return "bg-[rgba(33,72,59,0.14)] text-[var(--accent-strong)]";
  if (level === "medium") return "bg-[rgba(111,101,90,0.14)] text-[var(--muted-strong)]";
  return "bg-[var(--surface-alt)] text-[var(--muted)]";
}

function significanceTone(level: TrendCard["significance"]) {
  if (level === "high") return "bg-[rgba(33,72,59,0.12)] text-[var(--accent-strong)]";
  if (level === "medium") return "bg-[rgba(181,145,78,0.14)] text-[var(--foreground)]";
  return "bg-[var(--surface-alt)] text-[var(--muted-strong)]";
}

function scoreTone(score: number) {
  if (score >= 0.5) return "text-[var(--accent-strong)]";
  if (score <= -0.5) return "text-[var(--danger-ink)]";
  return "text-[var(--foreground)]";
}

function statusTone(status: "ready" | "partial" | "missing") {
  if (status === "ready") return "text-[var(--accent-strong)]";
  if (status === "partial") return "text-[var(--warning-ink)]";
  return "text-[var(--muted)]";
}

function PlayerMoverButton({
  row,
  isSelected,
  onSelect,
}: {
  row: TrendPlayerRow;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-xl border p-3 text-left transition ${
        isSelected
          ? "border-[var(--accent-strong)] bg-[rgba(33,72,59,0.07)]"
          : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--border-strong)]"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold text-[var(--foreground)]">
            {row.player_name}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] uppercase tracking-[0.12em] text-[var(--muted)]">
              {row.team_abbreviation} · {row.primary_signal.replaceAll("_", " ")}
            </span>
            <span
              className={`rounded-full px-2 py-[1px] text-[9px] font-semibold uppercase tracking-[0.12em] ${confidenceTone(row.confidence)}`}
              title={`${row.confidence} confidence — derived from trend_score magnitude and sample support (${row.recent_games} recent games).`}
            >
              {row.confidence}
            </span>
            {row.recent_games < 8 ? (
              <span
                className="rounded-full border border-[var(--border)] px-2 py-[1px] text-[9px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]"
                title={`Only ${row.recent_games} games in the recent window — treat as early-read.`}
              >
                thin sample
              </span>
            ) : null}
          </div>
        </div>
        <div className="text-right">
          <div className={`text-lg font-bold tabular-nums ${scoreTone(row.trend_score)}`}>
            {fmtSigned(row.trend_score)}
          </div>
          <div className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
            {row.trend_label}
          </div>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
        <div>
          <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">PTS</div>
          <div className="font-semibold text-[var(--foreground)]">{fmt(row.recent_pts_pg)}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">TS</div>
          <div className="font-semibold text-[var(--foreground)]">{fmt(row.recent_ts_pct == null ? null : row.recent_ts_pct * 100, 1, "%")}</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">MPG</div>
          <div className="font-semibold text-[var(--foreground)]">{fmt(row.recent_minutes_pg)}</div>
        </div>
      </div>
    </button>
  );
}

export default function TrendCardsPanel({
  teamAbbreviation,
  season,
  pinnedPlayerId,
  signal,
  onPlayerPin,
  onSignalChange,
}: TrendCardsPanelProps) {
  const { data, isLoading, error } = useTrendCards(
    teamAbbreviation,
    season,
    10,
    pinnedPlayerId,
    signal || null
  );
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const activeCard = data?.cards.find((card) => card.card_id === activeCardId) ?? data?.cards[0] ?? null;
  const pinned = data?.pinned_player ?? null;

  return (
    <section className="mx-auto max-w-7xl space-y-6">
      <div className="rounded-[2rem] border border-[var(--border-strong)] bg-[var(--surface)] p-6">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-3xl">
            <p className="bip-kicker mb-2">Trend Intelligence</p>
            <h2 className="bip-display text-4xl font-semibold text-[var(--foreground)]">
              {teamAbbreviation} team drift, player drivers
            </h2>
            <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
              Recent team movement with the players, lineups, shot quality, tracking,
              hustle, gravity, and clutch context behind the trend.
            </p>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] px-4 py-3 text-sm">
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
              Data status
            </div>
            <div className="mt-1 font-semibold capitalize text-[var(--foreground)]">
              {data?.data_status ?? "loading"}
            </div>
          </div>
        </div>

        {data?.overview ? (
          <div className="mt-6 grid gap-3 md:grid-cols-4">
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-4">
              <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">Recent</div>
              <div className="mt-1 text-2xl font-bold text-[var(--foreground)]">{data.overview.recent_record ?? "-"}</div>
              <div className="text-xs text-[var(--muted)]">{data.overview.games_in_window} games</div>
            </div>
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-4">
              <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">Net</div>
              <div className="mt-1 text-2xl font-bold text-[var(--foreground)]">{fmtSigned(data.overview.recent_net_rating, 1)}</div>
              <div className="text-xs text-[var(--muted)]">baseline {fmtSigned(data.overview.baseline_net_rating, 1)}</div>
            </div>
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-4">
              <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">TS</div>
              <div className="mt-1 text-2xl font-bold text-[var(--foreground)]">{fmt(data.overview.recent_ts_pct == null ? null : data.overview.recent_ts_pct * 100, 1, "%")}</div>
              <div className="text-xs text-[var(--muted)]">baseline {fmt(data.overview.baseline_ts_pct == null ? null : data.overview.baseline_ts_pct * 100, 1, "%")}</div>
            </div>
            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-4">
              <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">Movers</div>
              <div className="mt-1 text-2xl font-bold text-[var(--foreground)]">{data.overview.player_count}</div>
              <div className="text-xs text-[var(--muted)]">foundation-scored players</div>
            </div>
          </div>
        ) : null}
      </div>

      {isLoading ? (
        <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
          <div className="h-96 animate-pulse rounded-[1.5rem] bg-[var(--surface-alt)]" />
          <div className="h-96 animate-pulse rounded-[1.5rem] bg-[var(--surface-alt)]" />
        </div>
      ) : null}

      {error ? (
        <div className="rounded-xl border border-[rgba(159,63,49,0.24)] bg-[rgba(159,63,49,0.08)] p-4 text-sm text-[var(--danger-ink)]">
          Trend intelligence failed to load for {teamAbbreviation}.
        </div>
      ) : null}

      {data?.warnings?.length ? (
        <div className="rounded-xl border border-[rgba(181,145,78,0.24)] bg-[rgba(181,145,78,0.08)] p-4 text-sm leading-6 text-[var(--muted-strong)]">
          {data.warnings.join(" ")}
        </div>
      ) : null}

      {data ? (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr),380px]">
          <div className="space-y-5">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {data.cards.map((card) => (
                <button
                  key={card.card_id}
                  type="button"
                  onClick={() => {
                    setActiveCardId(card.card_id);
                    onSignalChange(card.driver_signal);
                  }}
                  className={`rounded-xl border p-4 text-left transition ${
                    activeCard?.card_id === card.card_id
                      ? "border-[var(--accent-strong)] bg-[rgba(33,72,59,0.07)]"
                      : "border-[var(--border)] bg-[var(--surface)] hover:border-[var(--border-strong)]"
                  }`}
                >
                  <div className="flex flex-wrap gap-2">
                    <span className={`rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] ${significanceTone(card.significance)}`}>
                      {card.significance}
                    </span>
                    <span className="rounded-full border border-[var(--border)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
                      {directionLabel(card.direction)}
                    </span>
                  </div>
                  <h3 className="mt-3 text-lg font-semibold text-[var(--foreground)]">{card.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">{card.summary}</p>
                  <div className="mt-3 text-xs font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
                    {signalLabel(card.driver_signal)}
                  </div>
                </button>
              ))}
            </div>

            {activeCard ? (
              <div className="rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                      Active team signal
                    </div>
                    <h3 className="mt-1 text-2xl font-semibold text-[var(--foreground)]">{activeCard.title}</h3>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {activeCard.replay_target ? (
                      <Link href={activeCard.replay_target.deep_link_url} className="bip-btn-primary rounded-full px-4 py-2 text-sm">
                        Open replay
                      </Link>
                    ) : null}
                    {activeCard.drilldowns.slice(0, 2).map((href) => (
                      <Link key={href} href={href} className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)]">
                        Open
                      </Link>
                    ))}
                  </div>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-4">
                  {Object.entries(activeCard.supporting_stats).slice(0, 8).map(([key, value]) => {
                    const desc = TREND_SIGNAL_DESCRIPTIONS[key];
                    return (
                      <div
                        key={key}
                        className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-3"
                        title={desc || undefined}
                      >
                        <div
                          className={`text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)] ${desc ? "cursor-help underline decoration-dotted decoration-[var(--muted)] underline-offset-2" : ""}`}
                        >
                          {key.replaceAll("_", " ")}
                        </div>
                        <div className="mt-1 text-lg font-bold text-[var(--foreground)]">{fmt(value, 3)}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : null}

            <div className="rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                    Player movers
                  </div>
                  <h3 className="mt-1 text-xl font-semibold text-[var(--foreground)]">
                    Who is driving the drift?
                  </h3>
                </div>
                {signal ? (
                  <button
                    type="button"
                    onClick={() => onSignalChange(null)}
                    className="rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted-strong)]"
                  >
                    Clear signal
                  </button>
                ) : null}
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {data.player_movers.map((row) => (
                  <PlayerMoverButton
                    key={row.player_id}
                    row={row}
                    isSelected={pinned?.row.player_id === row.player_id}
                    onSelect={() => onPlayerPin(row.player_id)}
                  />
                ))}
              </div>
            </div>
          </div>

          <aside className="space-y-4">
            {pinned ? (
              <div className="rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] p-5">
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                  Pinned player
                </div>
                <Link href={`/players/${pinned.row.player_id}`} className="mt-1 block text-2xl font-semibold text-[var(--foreground)] hover:underline">
                  {pinned.row.player_name}
                </Link>
                <div className="mt-2 flex items-center justify-between gap-3">
                  <span className="text-sm text-[var(--muted-strong)]">{pinned.row.primary_signal.replaceAll("_", " ")} · {pinned.row.confidence}</span>
                  <span className={`text-2xl font-bold tabular-nums ${scoreTone(pinned.row.trend_score)}`}>{fmtSigned(pinned.row.trend_score)}</span>
                </div>
                <div className="mt-4 space-y-2">
                  {pinned.row.driver_contributions.slice(0, 5).map((driver) => (
                    <div key={driver.signal} className="rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-semibold text-[var(--foreground)]">{driver.label}</span>
                        <span className="text-xs font-bold tabular-nums text-[var(--foreground)]">{fmtSigned(driver.contribution, 2)}</span>
                      </div>
                      <p className="mt-1 text-xs leading-5 text-[var(--muted)]">{driver.note}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-4 grid gap-2">
                  {pinned.foundation.map((item) => (
                    <div key={item.signal} className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-semibold text-[var(--foreground)]">{item.label}</span>
                        <span className={`text-[10px] font-semibold uppercase tracking-[0.12em] ${statusTone(item.status)}`}>{item.status}</span>
                      </div>
                      <div className="mt-1 text-sm font-bold text-[var(--foreground)]">{fmt(item.value, 2)}</div>
                      <p className="mt-1 text-xs leading-5 text-[var(--muted)]">{item.context}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-5 flex flex-wrap gap-2">
                  <Link href={`/insights?tab=trajectory&team=${teamAbbreviation}&season=${season}&player_id=${pinned.row.player_id}`} className="rounded-full border border-[var(--border-strong)] px-3 py-1 text-xs font-medium text-[var(--accent-strong)]">
                    Trajectory
                  </Link>
                  <Link href={`/insights?tab=usage&team=${teamAbbreviation}&season=${season}&player_id=${pinned.row.player_id}&signal=${pinned.row.primary_signal}`} className="rounded-full border border-[var(--border-strong)] px-3 py-1 text-xs font-medium text-[var(--accent-strong)]">
                    Opportunity
                  </Link>
                  <button type="button" onClick={() => onPlayerPin(null)} className="rounded-full border border-[var(--border)] px-3 py-1 text-xs text-[var(--muted-strong)]">
                    Clear pin
                  </button>
                </div>
              </div>
            ) : (
              <div className="rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] p-8 text-sm text-[var(--muted-strong)]">
                Select a player mover to inspect the foundation signals behind the trend.
              </div>
            )}

            {data.methodology ? (
              <details className="rounded-[1.5rem] border border-[var(--border)] bg-[var(--surface)] p-5">
                <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                  Methodology · {data.methodology.version}
                </summary>
                <div className="mt-3 space-y-3 text-xs leading-5 text-[var(--muted-strong)]">
                  <p>
                    <span className="font-semibold text-[var(--foreground)]">Window.</span>{" "}
                    Last {data.methodology.window_games} games compared to the
                    earlier season baseline.
                  </p>
                  <div>
                    <p className="font-semibold text-[var(--foreground)]">
                      Scoring inputs
                    </p>
                    <ul className="mt-1 list-disc space-y-0.5 pl-4">
                      {data.methodology.scoring_inputs.map((inp) => (
                        <li key={inp}>
                          <span
                            className={
                              TREND_SIGNAL_DESCRIPTIONS[inp]
                                ? "cursor-help underline decoration-dotted decoration-[var(--muted)] underline-offset-2"
                                : ""
                            }
                            title={TREND_SIGNAL_DESCRIPTIONS[inp] || undefined}
                          >
                            {inp.replaceAll("_", " ")}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="font-semibold text-[var(--foreground)]">
                      Significance bands
                    </p>
                    <ul className="mt-1 list-disc space-y-0.5 pl-4">
                      <li>
                        <span className="font-semibold text-[var(--accent-strong)]">high</span>
                        — trend_score magnitude ≥ 0.75 with full sample support.
                      </li>
                      <li>
                        <span className="font-semibold text-[var(--foreground)]">medium</span>
                        — |trend_score| ≥ 0.4 or partial foundation coverage.
                      </li>
                      <li>
                        <span className="text-[var(--muted)]">low</span>
                        — movement present but sample thin or mixed signal.
                      </li>
                    </ul>
                  </div>
                  <div>
                    <p className="font-semibold text-[var(--foreground)]">
                      Confidence pills
                    </p>
                    <p className="mt-1">
                      Derived per player from trend_score magnitude and sample
                      support. Players under 8 recent games also carry a thin-sample badge.
                    </p>
                  </div>
                  {data.methodology.coverage_notes.length ? (
                    <div>
                      <p className="font-semibold text-[var(--foreground)]">
                        Coverage notes
                      </p>
                      <ul className="mt-1 list-disc space-y-0.5 pl-4">
                        {data.methodology.coverage_notes.map((note) => (
                          <li key={note}>{note}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              </details>
            ) : null}
          </aside>
        </div>
      ) : null}
    </section>
  );
}
