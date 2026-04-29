"use client";

import { useCallback, useEffect, useState } from "react";
import type { SeasonPhase } from "@/lib/types";
import { useSeasonPhase } from "./useSeasonPhase";

export type ViewMode = "playoff" | "regular" | "offseason";

const STORAGE_KEY = "bip-view-mode";
const VALID_VIEW_MODES: readonly ViewMode[] = ["playoff", "regular", "offseason"];

function isViewMode(value: unknown): value is ViewMode {
  return (
    typeof value === "string" &&
    (VALID_VIEW_MODES as readonly string[]).includes(value)
  );
}

function deriveAutoMode(phase: SeasonPhase | undefined): ViewMode {
  if (phase === "regular_season") {
    return "regular";
  }
  if (phase === "offseason") {
    return "offseason";
  }
  // Any playoff_*, conference_finals, or finals → "playoff".
  if (phase != null) {
    return "playoff";
  }
  // Phase still loading — default to "regular" until SWR resolves.
  return "regular";
}

function readStoredOverride(): ViewMode | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return isViewMode(raw) ? raw : null;
  } catch {
    // localStorage may throw in private mode / sandboxed iframes.
    return null;
  }
}

/**
 * View-mode hook that wraps useSeasonPhase with a localStorage override.
 *
 * Default behavior: viewMode mirrors useSeasonPhase().phase, mapped to
 * three buckets:
 *   - "playoff" if phase starts with "playoff" or is "conference_finals"/"finals"
 *   - "regular" if phase === "regular_season"
 *   - "offseason" if phase === "offseason"
 *
 * Override behavior: if the user has previously called setViewMode(), the
 * choice is persisted in localStorage and overrides the auto-detect.
 *
 * Returns:
 *   - phase: raw SeasonPhase from useSeasonPhase (auto-detected)
 *   - viewMode: ViewMode (auto-detected OR override if set)
 *   - setViewMode(next): persists next to localStorage; clears the override
 *     if next === null (reverts to auto-detect)
 *   - isOverridden: boolean — true when localStorage value differs from auto-detect
 *   - isLoading: boolean — true while the season-phase fetch is still in flight
 */
export function useViewMode(): {
  phase: SeasonPhase | undefined;
  viewMode: ViewMode;
  setViewMode: (next: ViewMode | null) => void;
  isOverridden: boolean;
  isLoading: boolean;
} {
  const { phase, isLoading } = useSeasonPhase();
  // Read localStorage post-mount to avoid hydration mismatch — the first
  // render uses `null` (no override), and `useEffect` fills in the stored
  // value once the client has hydrated.
  const [override, setOverride] = useState<ViewMode | null>(null);

  useEffect(() => {
    // One-time hydration sync from localStorage. The lint rule
    // react-hooks/set-state-in-effect flags this pattern, but reading from
    // an external store (window.localStorage) is the documented escape.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setOverride(readStoredOverride());
  }, []);

  const setViewMode = useCallback((next: ViewMode | null) => {
    if (typeof window !== "undefined") {
      try {
        if (next === null) {
          window.localStorage.removeItem(STORAGE_KEY);
        } else {
          window.localStorage.setItem(STORAGE_KEY, next);
        }
      } catch {
        // Swallow storage errors — the override still applies in-memory.
      }
    }
    setOverride(next);
  }, []);

  const autoMode = deriveAutoMode(phase);
  const viewMode: ViewMode = override ?? autoMode;
  const isOverridden = override !== null && override !== autoMode;

  return {
    phase,
    viewMode,
    setViewMode,
    isOverridden,
    isLoading,
  };
}
