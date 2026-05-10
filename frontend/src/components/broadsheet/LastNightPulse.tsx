"use client";

import Link from "next/link";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import { useLastNightPulse } from "@/hooks/usePlayerStats";
import type {
  LastNightHeroTile,
  SeriesMomentumTile,
  TonightHeadlinerTile,
} from "@/lib/types";

/**
 * Sprint 96 — Last Night Pulse.
 *
 * Replaces the Sprint 73 StoryRail on the playoffs surface. Three game-driven
 * tiles powered by /api/playoffs/last-night-pulse:
 *
 *   - Tonight on the floor — biggest matchup on tonight's slate (lowest seed sum)
 *   - Last night's hero    — top playoff PlayerGameLog by Game Score (last 36h)
 *   - Series momentum      — most recently updated PlayoffSeries (W/L flip / close)
 *
 * Refreshes every 5 minutes — same cadence as the SeriesTrackerStrip — so the
 * rail tracks the post-game sync directly, no SeasonStat aggregation lag.
 */

const ACTIVE_SEASON_FALLBACK = "2025-26";

function formatFreshness(computedAt?: string | null): string | null {
  if (!computedAt) return null;
  const ms = Date.parse(computedAt);
  if (Number.isNaN(ms)) return null;
  const ageMin = Math.max(0, Math.round((Date.now() - ms) / 60_000));
  if (ageMin < 1) return "Just now";
  if (ageMin < 60) return `${ageMin} min ago`;
  if (ageMin < 60 * 24) return `${Math.round(ageMin / 60)}h ago`;
  return `${Math.round(ageMin / (60 * 24))}d ago`;
}

function PulseTile({
  href,
  kicker,
  headline,
  subhead,
  caption,
  testid,
}: {
  href: string;
  kicker: string;
  headline: string;
  subhead?: string | null;
  caption?: string | null;
  testid?: string;
}) {
  return (
    <Link
      data-testid={testid}
      href={href}
      className="bip-panel rounded-2xl px-5 py-5 h-full flex flex-col hover:-translate-y-0.5 transition-transform focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
      style={{ background: "rgba(255,249,241,0.6)" }}
    >
      <p className="bip-kicker mb-3">{kicker}</p>
      <h3
        className="bip-display font-semibold text-[var(--foreground)]"
        style={{
          fontSize: "1.15rem",
          lineHeight: 1.3,
          letterSpacing: "-0.01em",
        }}
      >
        {headline}
      </h3>
      {subhead ? (
        <p
          className="mt-3 text-sm text-[var(--muted)] flex-1"
          style={{ fontFamily: "var(--font-display)", lineHeight: 1.5 }}
        >
          {subhead}
        </p>
      ) : (
        <div className="flex-1" />
      )}
      {caption ? (
        <p
          className="mt-4 text-xs"
          style={{
            fontFamily: "var(--font-geist-mono)",
            letterSpacing: "0.1em",
            textTransform: "uppercase",
            color: "var(--muted)",
          }}
        >
          {caption}
        </p>
      ) : null}
    </Link>
  );
}

function HeroTile({ tile }: { tile: LastNightHeroTile }) {
  const subParts: string[] = [tile.line];
  if (tile.matchup) subParts.push(tile.matchup);
  return (
    <PulseTile
      testid="last-night-hero"
      href={tile.href}
      kicker="Last night's hero"
      headline={tile.player_name}
      subhead={subParts.join(" · ")}
      caption={`Game Score ${tile.game_score.toFixed(1)}${
        tile.team_abbreviation ? ` · ${tile.team_abbreviation}` : ""
      }`}
    />
  );
}

function HeadlinerTile({ tile }: { tile: TonightHeadlinerTile }) {
  const subParts: string[] = [];
  if (tile.seeds_label) subParts.push(tile.seeds_label);
  if (tile.series_state) subParts.push(tile.series_state);
  return (
    <PulseTile
      testid="tonight-headliner"
      href={tile.href}
      kicker="Tonight on the floor"
      headline={tile.matchup}
      subhead={subParts.length > 0 ? subParts.join(" · ") : "Tipoff tonight."}
      caption={tile.round != null ? `Round ${tile.round}` : null}
    />
  );
}

function MomentumTile({ tile }: { tile: SeriesMomentumTile }) {
  return (
    <PulseTile
      testid="series-momentum"
      href={tile.href}
      kicker="Series momentum"
      headline={tile.matchup}
      subhead={tile.summary}
      caption={tile.round != null ? `Round ${tile.round}` : null}
    />
  );
}

export default function LastNightPulse() {
  const { season } = useSeasonPhase();
  const seasonKey = season ?? ACTIVE_SEASON_FALLBACK;
  const { data, isLoading, error } = useLastNightPulse(seasonKey);

  const headliner = data?.tonight_headliner ?? null;
  const hero = data?.last_night_hero ?? null;
  const momentum = data?.series_momentum ?? null;
  const hasAny = Boolean(headliner || hero || momentum);
  const freshness = formatFreshness(data?.computed_at);

  return (
    <section>
      <header className="mb-3 px-1 flex items-baseline justify-between gap-3">
        <p className="bip-kicker">Last Night Pulse</p>
        {freshness && (
          <p
            className="text-[10px] tracking-[0.14em] uppercase text-[var(--muted)] tabular-nums"
            style={{ fontFamily: "var(--font-geist-mono)" }}
            title={`Computed ${freshness}.`}
          >
            {freshness}
          </p>
        )}
      </header>

      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-1 gap-4 animate-pulse">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="rounded-2xl border border-[var(--border)]"
              style={{
                height: 168,
                background: "rgba(255,249,241,0.4)",
              }}
            />
          ))}
        </div>
      )}

      {!isLoading && error && (
        <p
          className="px-2 py-6 text-sm italic text-[var(--muted)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          The pulse is between editions.
        </p>
      )}

      {!isLoading && !error && !hasAny && (
        <p
          className="px-2 py-6 text-sm italic text-[var(--muted)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          The bracket is quiet — no recent games, no tipoff tonight.
        </p>
      )}

      {!isLoading && !error && hasAny && (
        <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-1 gap-4">
          {headliner && <HeadlinerTile tile={headliner} />}
          {hero && <HeroTile tile={hero} />}
          {momentum && <MomentumTile tile={momentum} />}
        </div>
      )}
    </section>
  );
}
