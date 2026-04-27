"use client";

import useSWR from "swr";
import { getPlayerAnalysisContexts } from "@/lib/api";
import type { AnalysisContextListResponse } from "@/lib/types";

export function usePlayerAnalysisContexts(
  playerId: number | null,
  season: string | null,
  includeAuto = true
) {
  return useSWR<AnalysisContextListResponse>(
    playerId !== null && season
      ? `player-analysis-contexts-${playerId}-${season}-${includeAuto}`
      : null,
    () => getPlayerAnalysisContexts(playerId!, season!, includeAuto)
  );
}
