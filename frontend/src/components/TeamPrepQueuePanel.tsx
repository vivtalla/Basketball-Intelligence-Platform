import Link from "next/link";
import { useState, useTransition } from "react";
import { createPreReadSnapshot } from "@/lib/api";
import type { TeamPrepQueueResponse, TeamSplitsResponse } from "@/lib/types";

interface TeamPrepQueuePanelProps {
  queue: TeamPrepQueueResponse;
  splits?: TeamSplitsResponse | null;
}

function restLabel(days: number | null | undefined) {
  if (days == null) return "rest unknown";
  if (days === 0) return "B2B";
  if (days === 1) return "1 day rest";
  return `${days} days rest`;
}

function restTone(value: number | null | undefined) {
  if (value == null || value === 0) return "text-[var(--muted)]";
  return value > 0 ? "text-[var(--success-ink)]" : "text-[var(--danger-ink)]";
}

function statusTone(status: TeamPrepQueueResponse["data_status"]) {
  if (status === "ready") return "bip-success";
  if (status === "partial") return "bip-pill";
  if (status === "limited") return "bg-[rgba(201,168,84,0.18)] text-[var(--accent-strong)]";
  return "bg-[var(--surface-alt)] text-[var(--muted)]";
}

function urgencyTone(value: string) {
  if (value === "high") return "bg-[rgba(165,72,54,0.14)] text-[var(--danger-ink)]";
  if (value === "medium") return "bg-[rgba(181,145,78,0.16)] text-[var(--foreground)]";
  return "bg-[rgba(47,109,74,0.12)] text-[var(--success-ink)]";
}

function fmtPct(value: number | null | undefined): string {
  if (value == null) return "—";
  return (value * 100).toFixed(1) + "%";
}

function fmtPlusMinus(value: number | null | undefined): string {
  if (value == null) return "—";
  return (value >= 0 ? "+" : "") + value.toFixed(1);
}

function plusMinusTone(value: number | null | undefined): string {
  if (value == null) return "text-[var(--muted)]";
  return value > 0 ? "text-[var(--success-ink)]" : value < 0 ? "text-[var(--danger-ink)]" : "text-[var(--muted)]";
}

export default function TeamPrepQueuePanel({ queue, splits }: TeamPrepQueuePanelProps) {
  const [copiedGameId, setCopiedGameId] = useState<string | null>(null);
  const [savedGameId, setSavedGameId] = useState<string | null>(null);
  const [isSaving, startSaving] = useTransition();

  async function copyShareLink(url: string, gameId: string) {
    if (typeof window === "undefined" || !navigator.clipboard) return;
    const absolute = new URL(url, window.location.origin).toString();
    await navigator.clipboard.writeText(absolute);
    setCopiedGameId(gameId);
    window.setTimeout(() => {
      setCopiedGameId((current) => (current === gameId ? null : current));
    }, 1600);
  }

  function saveSnapshot(item: TeamPrepQueueResponse["items"][number]) {
    startSaving(async () => {
      try {
        await createPreReadSnapshot({
          team: queue.abbreviation,
          opponent: item.opponent_abbreviation ?? "",
          season: queue.season,
          game_id: item.game_id,
          source_view: "prep-queue-card",
          context: {
            prep_urgency: item.prep_urgency,
            urgency_rationale: item.urgency_rationale ?? "",
            first_adjustment_label: item.first_adjustment_label ?? "",
            recommended_factor: item.first_adjustment_factor_id ?? item.best_edge_factor_id ?? "",
          },
        });
        setSavedGameId(item.game_id);
        window.setTimeout(() => {
          setSavedGameId((current) => (current === item.game_id ? null : current));
        }, 1800);
      } catch {
        setSavedGameId("error");
      }
    });
  }

  return (
    <div className="space-y-6">
      <section className="bip-panel-strong rounded-[2rem] p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="bip-kicker">Prep Queue</p>
            <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
              Upcoming opponents, already framed for staff prep
            </h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--muted-strong)]">
              Use the queue to spot the next opponent, the schedule pressure, the availability watchlist, and the first lever worth emphasizing before opening the full pre-read deck.
            </p>
          </div>
          <div className="text-right space-y-2">
            <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${statusTone(queue.data_status)}`}>
              {queue.data_status}
            </span>
            <p className="mt-2 text-xs text-[var(--muted)]">
              Source: {queue.canonical_source}
            </p>
            <p className="text-xs text-[var(--muted)]">
              {queue.generated_at ? `Refreshed ${new Date(queue.generated_at).toLocaleString()}` : "Live local snapshot"}
            </p>
          </div>
        </div>
      </section>

      {queue.items.length === 0 ? (
        <section className="bip-panel rounded-[1.8rem] p-6 text-sm leading-6 text-[var(--muted-strong)]">
          No prep cards are available for this window yet. Once upcoming warehouse schedule rows are present, this tab will line up the next opponents automatically.
        </section>
      ) : (
        <section className="grid gap-4 xl:grid-cols-2">
          {queue.items.map((item) => (
            <article
              key={item.game_id}
              className="relative overflow-hidden rounded-[1.8rem] border border-[var(--border)] bg-[linear-gradient(145deg,rgba(255,255,255,0.95),rgba(231,239,235,0.82))] p-6 shadow-[0_18px_45px_rgba(20,37,29,0.08)]"
            >
              <div className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-[linear-gradient(90deg,var(--accent),rgba(181,145,78,0.7),rgba(165,72,54,0.7))]" />
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${urgencyTone(item.prep_urgency)}`}>
                      {item.prep_urgency} urgency
                    </span>
                    <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                      {item.game_date ?? "TBD"} · {item.is_home ? "vs" : "at"}
                    </span>
                  </div>
                  <h3 className="mt-2 text-2xl font-semibold text-[var(--foreground)]">
                    {item.opponent_abbreviation ?? item.opponent_name ?? "Opponent TBD"}
                  </h3>
                  <p className="mt-2 text-sm text-[var(--muted-strong)]">
                    {item.opponent_record
                      ? `${item.opponent_record}${item.opponent_playoff_rank ? ` · ${item.opponent_conference ?? "Conference"} #${item.opponent_playoff_rank}` : ""}`
                      : "Standings context is still filling in."}
                  </p>
                  <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--muted-strong)]">
                    {item.prep_headline}
                  </p>
                  {item.urgency_rationale ? (
                    <p className="mt-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                      Why now: {item.urgency_rationale}
                    </p>
                  ) : null}
                </div>
                <div className="rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.68)] px-4 py-3 text-right">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                    Schedule
                  </div>
                  <div className="mt-2 text-sm font-semibold text-[var(--foreground)]">
                    {item.schedule_pressure}
                  </div>
                  <div className={`mt-1 text-xs ${restTone(item.rest_advantage)}`}>
                    {restLabel(item.team_rest_days)} vs {restLabel(item.opponent_rest_days)}
                  </div>
                </div>
              </div>

              {splits && splits.splits.length > 0 && (() => {
                const locationValue = item.is_home ? "Home" : "Away";
                const locationRow = splits.splits.find(
                  (r) => r.split_family === "Location" && r.split_value === locationValue
                );
                const wlRow = splits.splits.find(
                  (r) => r.split_family === "Win/Loss" && r.split_value === "Wins"
                );
                if (!locationRow && !wlRow) return null;
                return (
                  <div className="mt-4 flex flex-wrap gap-3">
                    {locationRow && (
                      <div className="rounded-xl border border-[var(--border)] bg-[rgba(255,255,255,0.56)] px-3 py-2 text-xs">
                        <span className="font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                          {locationValue} W%
                        </span>
                        <span className="ml-2 font-bold text-[var(--foreground)]">
                          {fmtPct(locationRow.w_pct)}
                        </span>
                        <span className="ml-1 text-[var(--muted)]">
                          ({locationRow.w}–{locationRow.l})
                        </span>
                        {locationRow.plus_minus != null && (
                          <span className={`ml-2 font-semibold ${plusMinusTone(locationRow.plus_minus)}`}>
                            {fmtPlusMinus(locationRow.plus_minus)} +/-
                          </span>
                        )}
                      </div>
                    )}
                    {wlRow && (
                      <div className="rounded-xl border border-[var(--border)] bg-[rgba(255,255,255,0.56)] px-3 py-2 text-xs">
                        <span className="font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                          In Wins
                        </span>
                        <span className="ml-2 font-bold text-[var(--foreground)]">
                          {fmtPct(wlRow.w_pct)}
                        </span>
                        {wlRow.pts != null && (
                          <span className="ml-2 text-[var(--muted-strong)]">
                            {wlRow.pts.toFixed(1)} PTS
                          </span>
                        )}
                        {wlRow.plus_minus != null && (
                          <span className={`ml-2 font-semibold ${plusMinusTone(wlRow.plus_minus)}`}>
                            {fmtPlusMinus(wlRow.plus_minus)} +/-
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                );
              })()}

              <div className="mt-5 grid gap-3 md:grid-cols-3">
                <div className="rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                    Availability Watch
                  </div>
                  <div className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">
                    {item.availability_summary}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-semibold uppercase tracking-[0.16em]">
                    <span className="rounded-full bg-[rgba(165,72,54,0.12)] px-2 py-1 text-[var(--danger-ink)]">
                      Out {item.unavailable_count}
                    </span>
                    <span className="rounded-full bg-[rgba(181,145,78,0.14)] px-2 py-1 text-[var(--foreground)]">
                      Q {item.questionable_count}
                    </span>
                    <span className="rounded-full bg-[rgba(33,72,59,0.08)] px-2 py-1 text-[var(--accent-strong)]">
                      P {item.probable_count}
                    </span>
                  </div>
                </div>
                <div className="rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                    Best Edge To Press
                  </div>
                  <div className="mt-2 text-sm font-semibold text-[var(--foreground)]">
                    {item.best_edge_label ?? "Still calibrating"}
                  </div>
                  <div className="mt-1 text-sm leading-6 text-[var(--muted-strong)]">
                    {item.best_edge_summary ?? "This matchup needs more local data before a clean edge call shows up."}
                  </div>
                  {item.best_edge_rationale ? (
                    <div className="mt-2 text-xs leading-5 text-[var(--muted)]">
                      {item.best_edge_rationale}
                    </div>
                  ) : null}
                </div>
                <div className="rounded-2xl border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                    First Adjustment
                  </div>
                  <div className="mt-2 text-sm font-semibold text-[var(--foreground)]">
                    {item.first_adjustment_label ?? "Still calibrating"}
                  </div>
                  <div className="mt-1 text-sm leading-6 text-[var(--muted-strong)]">
                    {item.first_adjustment_summary ?? "Adjustment guidance will appear once more team-game stats are available."}
                  </div>
                  {item.first_adjustment_rationale ? (
                    <div className="mt-2 text-xs leading-5 text-[var(--muted)]">
                      {item.first_adjustment_rationale}
                    </div>
                  ) : null}
                </div>
              </div>

              <div className="mt-5 flex flex-wrap gap-3">
                <Link
                  href={item.pre_read_url}
                  className="bip-btn-primary rounded-full px-4 py-2 text-sm font-medium"
                >
                  Open pre-read
                </Link>
                <Link
                  href={item.scouting_url}
                  className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
                >
                  Open scouting mode
                </Link>
                <Link
                  href={item.compare_url}
                  className="bip-btn-secondary rounded-full px-4 py-2 text-sm font-medium"
                >
                  Open team compare
                </Link>
                <Link
                  href={item.follow_through_url}
                  className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
                >
                  Open follow-through
                </Link>
                <Link
                  href={item.game_review_url}
                  className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
                >
                  Open game review
                </Link>
                <button
                  type="button"
                  onClick={() => saveSnapshot(item)}
                  className="rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--foreground)] transition hover:bg-[rgba(255,255,255,0.5)]"
                >
                  {savedGameId === item.game_id ? "Saved snapshot" : isSaving ? "Saving..." : "Save snapshot"}
                </button>
                <button
                  type="button"
                  onClick={() => copyShareLink(item.latest_snapshot_share_url ?? item.pre_read_url, item.game_id)}
                  className="rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--foreground)] transition hover:bg-[rgba(255,255,255,0.5)]"
                >
                  {copiedGameId === item.game_id ? "Copied link" : "Copy share link"}
                </button>
              </div>
              {item.latest_snapshot_share_url ? (
                <div className="mt-4 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                  Latest snapshot: <Link href={item.latest_snapshot_share_url} className="text-[var(--accent-strong)] underline underline-offset-4">{item.latest_snapshot_id?.slice(0, 8)}</Link>
                </div>
              ) : null}
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
