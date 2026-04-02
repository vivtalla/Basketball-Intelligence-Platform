import useSWR from "swr";
import { fetchCompareAvailability } from "@/lib/api";
import type { CompareAvailabilityResponse } from "@/lib/types";

export function useCompareAvailability(
  playerAId: number | null,
  playerBId: number | null,
  season = "2024-25"
) {
  return useSWR<CompareAvailabilityResponse>(
    playerAId && playerBId
      ? `compare-availability-${playerAId}-${playerBId}-${season}`
      : null,
    () => fetchCompareAvailability(playerAId!, playerBId!, season)
  );
}
