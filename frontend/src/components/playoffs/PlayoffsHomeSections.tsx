"use client";

import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import DailyPlayoffSlate from "@/components/playoffs/DailyPlayoffSlate";

/**
 * Sprint 73 (EB3): playoff-only home-page block. Mounts the daily playoff slate
 * when the season phase is in any playoff stage, and renders nothing otherwise
 * so the regular-season home page reverts cleanly.
 */
export default function PlayoffsHomeSections() {
  const { isPlayoffs } = useSeasonPhase();
  if (!isPlayoffs) return null;
  return <DailyPlayoffSlate />;
}
