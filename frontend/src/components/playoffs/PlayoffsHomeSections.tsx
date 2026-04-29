"use client";

import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import { useViewMode } from "@/hooks/useViewMode";
import DailyPlayoffSlate from "@/components/playoffs/DailyPlayoffSlate";

/**
 * Sprint 73 (EB3): playoff-only home-page block. Mounts the daily playoff slate
 * when the season phase is in any playoff stage, and renders nothing otherwise
 * so the regular-season home page reverts cleanly.
 *
 * Sprint 77 (EB1): added a `viewMode === "playoff"` gate so this block does
 * NOT render when the broadsheet playoff home is active — the broadsheet's
 * `<TodaysSlate>` is the canonical surface in that mode and we don't want to
 * double-render the daily slate.
 */
export default function PlayoffsHomeSections() {
  const { isPlayoffs } = useSeasonPhase();
  const { viewMode } = useViewMode();
  if (!isPlayoffs) return null;
  // Suppress when the broadsheet home is rendering — `<TodaysSlate>` already
  // covers tonight's slate there.
  if (viewMode === "playoff") return null;
  return <DailyPlayoffSlate />;
}
