"use client";

/**
 * Sprint 78 CF5 — Player profile streak chip.
 *
 * Renders a single small chip showing the player's longest active streak
 * (e.g. "6 STRAIGHT 30+ PT GAMES"). Only rendered when the player has at
 * least one active streak with length >= 2. Chip clicks deep-link to the
 * `/milestones` page so the streak can be viewed alongside league context.
 *
 * Reads the league-wide active-streaks board and filters to the requested
 * player rather than introducing a per-player endpoint — the league-wide
 * payload is small (< 50 rows) and refreshes identically. This avoids
 * adding a second fetch path for what is essentially a single read.
 */
import Link from "next/link";
import useSWR from "swr";

import { getActiveStreaks } from "@/lib/api";
import type { ActiveStreaksResponse, PlayerStreakSummary } from "@/lib/types";

interface PlayerStreakChipProps {
  playerId: number;
}

const REFRESH_MS = 5 * 60_000;
const FETCH_LIMIT = 100; // wide enough that any rotation player's streak appears

export default function PlayerStreakChip({ playerId }: PlayerStreakChipProps) {
  const { data } = useSWR<ActiveStreaksResponse>(
    ["player-streak-chip", playerId],
    () => getActiveStreaks(undefined, FETCH_LIMIT),
    { refreshInterval: REFRESH_MS, revalidateOnFocus: false }
  );

  const streaks: PlayerStreakSummary[] = data?.streaks ?? [];
  const playerStreaks = streaks.filter((s) => s.player_id === playerId);
  if (playerStreaks.length === 0) return null;

  // The backend already orders by length desc, so the first match is
  // the longest. Only render the chip when length >= 2 — a single-game
  // "streak" doesn't deserve a chip.
  const top = playerStreaks[0];
  if (top.length < 2) return null;

  return (
    <Link
      href="/milestones"
      title={`${top.length} consecutive ${top.streak_label} - view league streaks board`}
      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-[0.14em] bg-[var(--accent-soft)] text-[var(--accent-strong)] hover:bg-[var(--accent)] hover:text-white transition-colors"
    >
      <span className="tabular-nums">{top.length}</span>
      <span>straight {top.streak_label}</span>
    </Link>
  );
}
