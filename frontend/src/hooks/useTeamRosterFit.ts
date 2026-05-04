"use client";

import useSWR from "swr";
import { getTeamRosterFit } from "@/lib/api";
import type { TeamRosterFitResponse } from "@/lib/types";

export function useTeamRosterFit(
  teamAbbr: string | null,
  season: string,
  seasonType: string = "Regular Season",
  limit: number = 25
) {
  return useSWR<TeamRosterFitResponse>(
    teamAbbr && season
      ? `team-roster-fit-${teamAbbr}-${season}-${seasonType}-${limit}`
      : null,
    () => getTeamRosterFit(teamAbbr!, season, seasonType, limit)
  );
}
