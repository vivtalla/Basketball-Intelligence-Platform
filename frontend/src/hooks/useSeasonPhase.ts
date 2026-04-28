"use client";

import useSWR from "swr";
import type { SeasonPhaseResponse } from "@/lib/types";
import { getSeasonPhase } from "@/lib/api";

/**
 * Sprint 73: hook over `GET /api/season-phase`. Powers the conditional
 * Bracket nav item and gates every playoff UI surface so the regular-season
 * → playoffs toggle-back guarantee holds.
 */
export function useSeasonPhase() {
  const { data, error, isLoading } = useSWR<SeasonPhaseResponse>(
    "season-phase",
    () => getSeasonPhase(),
    {
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
      dedupingInterval: 60_000,
    }
  );
  const isPlayoffs =
    data?.phase != null &&
    data.phase !== "regular_season" &&
    data.phase !== "offseason";
  return {
    phase: data?.phase,
    season: data?.season,
    roundLabel: data?.round_label,
    isPlayoffs,
    isLoading,
    error,
  };
}
