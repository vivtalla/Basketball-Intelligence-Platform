"use client";

import useSWR from "swr";
import { getPlayerShotDiagnosis, getPlayerScoutingBrief } from "@/lib/api";
import type { ScoutingBriefResponse, ShotDiagnosisResponse } from "@/lib/types";

export function usePlayerShotDiagnosis(
  playerId: number | null,
  season: string,
  seasonType: string = "Regular Season"
) {
  return useSWR<ShotDiagnosisResponse>(
    playerId !== null && season
      ? `shot-diagnosis-${playerId}-${season}-${seasonType}`
      : null,
    () => getPlayerShotDiagnosis(playerId!, season, seasonType)
  );
}

export function usePlayerScoutingBrief(playerId: number | null, season: string) {
  return useSWR<ScoutingBriefResponse>(
    playerId !== null && season ? `scouting-brief-${playerId}-${season}` : null,
    () => getPlayerScoutingBrief(playerId!, season)
  );
}
