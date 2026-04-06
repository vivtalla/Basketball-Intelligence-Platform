"use client";

import Link from "next/link";
import { useTrendCards } from "@/hooks/usePlayerStats";

interface TrendCardsPanelProps {
  teamAbbreviation: string;
  season: string;
}

function formatMagnitude(value: number | null | undefined) {
  if (value == null) return "Limited evidence";
  return `${value.toFixed(3)} shift`;
}

function formatSupportKey(key: string) {
  return key.replaceAll("_", " ");
}

function significanceTone(level: "high" | "medium" | "low") {
  if (level === "high") return "bg-[rgba(33,72,59,0.12)] text-[var(--accent-strong)]";
  if (level === "medium") return "bg-[rgba(181,145,78,0.14)] text-[var(--foreground)]";
  return "bg-[var(--surface-alt)] text-[var(--muted-strong)]";
}

function directionLabel(direction: "up" | "down" | "flat") {
  if (direction === "up") return "Rising";
  if (direction === "down") return "Falling";
  return "Stable";
}

function compactDrilldownLabel(href: string) {
  if (href.startsWith("/compare")) return "Open compare";
  if (href.startsWith("/pre-read")) return "Open pre-read";
  if (href.startsWith("/teams/")) return "Open team view";
  if (href.startsWith("/games")) return "Open Game Explorer";
  return "Open drilldown";
}

export default function TrendCardsPanel({
  teamAbbreviation,
  season,
}: TrendCardsPanelProps) {
  const { data, isLoading } = useTrendCards(teamAbbreviation, season, 10);

  return (
    <section className="bip-panel-strong rounded-[2rem] p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="bip-kicker">Trend Cards</div>
          <h2 className="bip-display mt-3 text-3xl font-semibold text-[var(--foreground)]">
            What is drifting for {teamAbbreviation}?
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">
            These cards now stay tied to actual recent-game evidence, so the next click can move directly into a replay-ready Game Explorer sequence instead of stopping at a static summary.
          </p>
        </div>
        <Link
          href={`/teams/${teamAbbreviation}?tab=decision`}
          className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
        >
          Open decision tools
        </Link>
      </div>

      {isLoading ? (
        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="h-72 animate-pulse rounded-[1.5rem] bg-[var(--surface-alt)]" />
          ))}
        </div>
      ) : null}

      {!isLoading && !data ? (
        <div className="bip-empty mt-6 rounded-3xl p-6 text-sm leading-6">
          Trend cards are unavailable for {teamAbbreviation} in {season}. Once team-game support is synced, this workspace will expose replay-aware drift cards.
        </div>
      ) : null}

      {data?.warnings?.length ? (
        <div className="mt-6 rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] px-5 py-4 text-sm leading-6 text-[var(--muted-strong)]">
          {data.warnings.join(" ")}
        </div>
      ) : null}

      {data?.cards?.length ? (
        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data.cards.map((card) => {
            const supportRows = Object.entries(card.supporting_stats ?? {}).slice(0, 3);
            return (
              <article
                key={card.card_id}
                className="rounded-[1.5rem] border border-[var(--border)] bg-[rgba(255,255,255,0.72)] p-5"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${significanceTone(card.significance)}`}>
                    {card.significance} signal
                  </span>
                  <span className="rounded-full border border-[var(--border)] bg-white/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--muted-strong)]">
                    {directionLabel(card.direction)}
                  </span>
                </div>

                <h3 className="mt-3 text-xl font-semibold text-[var(--foreground)]">
                  {card.title}
                </h3>
                <p className="mt-2 text-sm text-[var(--muted)]">
                  {formatMagnitude(card.magnitude)}
                </p>
                <p className="mt-3 text-sm leading-6 text-[var(--muted-strong)]">
                  {card.summary}
                </p>

                {card.replay_target ? (
                  <div className="mt-4 rounded-[1.2rem] border border-[rgba(33,72,59,0.16)] bg-[rgba(216,228,221,0.22)] p-4">
                    <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                      Replay follow-through
                    </div>
                    <div className="mt-2 text-sm font-semibold text-[var(--foreground)]">
                      {card.replay_target.target_opponent_abbreviation ?? "Recent game"} · {card.replay_target.linkage_quality}
                    </div>
                    <div className="mt-1 text-sm leading-6 text-[var(--muted-strong)]">
                      {card.replay_target.reason}
                    </div>
                  </div>
                ) : null}

                {supportRows.length ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {supportRows.map(([key, value]) => (
                      <span
                        key={key}
                        className="rounded-full border border-[var(--border)] bg-white/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-[var(--muted-strong)]"
                      >
                        {formatSupportKey(key)} {value == null ? "—" : value.toFixed(3)}
                      </span>
                    ))}
                  </div>
                ) : null}

                <div className="mt-5 flex flex-wrap gap-3">
                  {card.replay_target ? (
                    <Link
                      href={card.replay_target.deep_link_url}
                      className="bip-btn-primary rounded-full px-4 py-2 text-sm font-medium"
                    >
                      Open replay
                    </Link>
                  ) : null}
                  {card.drilldowns.slice(0, 2).map((href) => (
                    <Link
                      key={href}
                      href={href}
                      className="rounded-full border border-[var(--border-strong)] px-4 py-2 text-sm font-medium text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.08)]"
                    >
                      {compactDrilldownLabel(href)}
                    </Link>
                  ))}
                </div>
              </article>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
