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

  return (
    <section>
      <header className="mb-3 px-1">
        <p className="bip-kicker">Story Rail</p>
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
