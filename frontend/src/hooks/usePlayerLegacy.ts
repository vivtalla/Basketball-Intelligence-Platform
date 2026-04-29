"use client";

import useSWR from "swr";
import { getPlayerLegacy } from "@/lib/api";
import type { CareerLegacyResponse } from "@/lib/types";

/**
 * SWR hook for the Sprint 78 CF3 Career Legacy / HOF endpoint.
 *
 * @param playerId  NBA person_id; pass null to skip the fetch.
 * @param peerCount Era-peer cohort size (3..10). Defaults to 8.
 */
export function usePlayerLegacy(playerId: number | null, peerCount = 8) {
  return useSWR<CareerLegacyResponse>(
    playerId !== null ? `player-legacy-${playerId}-${peerCount}` : null,
    () => getPlayerLegacy(playerId!, { peerCount })
  );
}
