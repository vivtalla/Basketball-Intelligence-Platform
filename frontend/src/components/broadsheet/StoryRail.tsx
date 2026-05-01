"use client";

import useSWR from "swr";
import Link from "next/link";
import { getPlayoffStoryRail } from "@/lib/api";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import type {
  PlayoffStoryRailResponse,
  PlayoffStoryTile,
} from "@/lib/types";

/**
 * Auto-generated story tiles for the broadsheet rail.
 *
 * Tiles are computed by `/api/playoffs/story-rail`:
 *   - Heat Check     — biggest positive scoring delta over last 3 games
 *   - Efficiency Desk — highest TS% among qualified high-volume scorers
 *   - X-Factor       — best impact composite among non-headline scorers
 *
 * Every tile links to an internal player route — no external URLs, so
 * there's no copyright exposure and no paywalled content surprises. The
 * rail refreshes every 5 minutes (same cadence as Narrative Leaders).
 */

const ACTIVE_SEASON_FALLBACK = "2025-26";

function formatFreshness(
  dataAsOf?: string | null,
  computedAt?: string | null,
): { label: string; title: string } | null {
  if (!dataAsOf && !computedAt) return null;

  const parts: string[] = [];
  let title = "";

  if (dataAsOf) {
    const d = new Date(`${dataAsOf}T00:00:00Z`);
    if (!isNaN(d.getTime())) {
      const month = d.toLocaleString("en-US", { month: "short", timeZone: "UTC" });
      const day = d.getUTCDate();
      parts.push(`Through ${month} ${day}`);
      title += `Stories reflect playoff games through ${dataAsOf}.`;
    }
  }

  if (computedAt) {
    const ms = Date.parse(computedAt);
    if (!isNaN(ms)) {
      const ageMin = Math.max(0, Math.round((Date.now() - ms) / 60_000));
      let rel: string;
      if (ageMin < 1) rel = "just now";
      else if (ageMin < 60) rel = `${ageMin} min ago`;
      else if (ageMin < 60 * 24) rel = `${Math.round(ageMin / 60)}h ago`;
      else rel = `${Math.round(ageMin / (60 * 24))}d ago`;
      parts.push(rel);
      title += ` Recomputed ${rel}.`;
    }
  }

  if (parts.length === 0) return null;
  return { label: parts.join(" · "), title: title.trim() };
}

function StoryTile({ tile }: { tile: PlayoffStoryTile }) {
  return (
    <Link
      href={tile.href}
      className="bip-panel rounded-2xl px-5 py-5 h-full flex flex-col hover:-translate-y-0.5 transition-transform focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
      style={{
        background: "rgba(255,249,241,0.6)",
      }}
    >
      <p className="bip-kicker mb-3">{tile.kicker}</p>
      <h3
        className="bip-display font-semibold text-[var(--foreground)]"
        style={{
          fontSize: "1.15rem",
          lineHeight: 1.3,
          letterSpacing: "-0.01em",
        }}
      >
        {tile.headline}
      </h3>
      {tile.subhead ? (
        <p
          className="mt-3 text-sm text-[var(--muted)] flex-1"
          style={{ fontFamily: "var(--font-display)", lineHeight: 1.5 }}
        >
          {tile.subhead}
        </p>
      ) : (
        <div className="flex-1" />
      )}
      <p
        className="mt-4 text-xs"
        style={{
          fontFamily: "var(--font-geist-mono)",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "var(--muted)",
        }}
      >
        {tile.byline}
        {tile.read_time ? ` · ${tile.read_time}` : ""}
      </p>
    </Link>
  );
}

export default function StoryRail() {
  const { season } = useSeasonPhase();
  const seasonKey = season ?? ACTIVE_SEASON_FALLBACK;

  const { data, isLoading, error } = useSWR<PlayoffStoryRailResponse>(
    ["broadsheet-story-rail", seasonKey],
    () => getPlayoffStoryRail(seasonKey),
    {
      refreshInterval: 5 * 60_000,
      revalidateOnFocus: false,
    }
  );

  const tiles = data?.tiles ?? [];
  const freshness = formatFreshness(data?.data_as_of, data?.computed_at);

  return (
    <section>
      <header className="mb-3 px-1 flex items-baseline justify-between gap-3">
        <p className="bip-kicker">Story Rail</p>
        {freshness && (
          <p
            className="text-[10px] tracking-[0.14em] uppercase text-[var(--muted)] tabular-nums"
            style={{ fontFamily: "var(--font-geist-mono)" }}
            title={freshness.title}
          >
            {freshness.label}
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
          The Numbers Desk is between editions.
        </p>
      )}

      {!isLoading && !error && tiles.length === 0 && (
        <p
          className="px-2 py-6 text-sm italic text-[var(--muted)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          No stories tonight — the data is too quiet.
        </p>
      )}

      {!isLoading && !error && tiles.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-1 gap-4">
          {tiles.map((tile) => (
            <StoryTile key={`${tile.kicker}-${tile.headline}`} tile={tile} />
          ))}
        </div>
      )}
    </section>
  );
}
