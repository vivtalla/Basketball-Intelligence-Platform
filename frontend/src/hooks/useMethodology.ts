"use client";

import useSWR from "swr";
import { getMethodologyDomain, getMethodologyRegistry } from "@/lib/api";
import type { MethodologyDetailResponse, MethodologyRegistryResponse } from "@/lib/types";

export function useMethodologyRegistry() {
  return useSWR<MethodologyRegistryResponse>("/api/methodology", getMethodologyRegistry);
}

export function useMethodologyDomain(domain: string | null | undefined) {
  return useSWR<MethodologyDetailResponse>(
    domain ? `/api/methodology/${domain}` : null,
    () => getMethodologyDomain(domain as string)
  );
}
