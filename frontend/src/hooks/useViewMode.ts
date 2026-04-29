"use client";

import { useCallback, useEffect, useSyncExternalStore } from "react";
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

// ─── Shared external store ───────────────────────────────────────────────
// All `useViewMode()` consumers subscribe to the same in-memory cache.
// Without this, each call to useViewMode would have its own useState slot
// and ModeToggle's setViewMode would only re-render itself, leaving the
// HomePage stuck on the auto-detected mode.

const overrideListeners = new Set<() => void>();
let cachedOverride: ViewMode | null = null;
let didHydrateFromStorage = false;

function readFromStorage(): ViewMode | null {
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

function ensureHydrated() {
  if (didHydrateFromStorage || typeof window === "undefined") {
    return;
  }
  didHydrateFromStorage = true;
  cachedOverride = readFromStorage();
}

function getOverrideSnapshot(): ViewMode | null {
  ensureHydrated();
  return cachedOverride;
}

function getOverrideServerSnapshot(): ViewMode | null {
  // SSR + initial hydration render: no override known yet.
  return null;
}

function subscribeToOverride(cb: () => void): () => void {
  overrideListeners.add(cb);
  return () => {
    overrideListeners.delete(cb);
  };
}

function writeOverride(next: ViewMode | null) {
  cachedOverride = next;
  didHydrateFromStorage = true;
  if (typeof window !== "undefined") {
    try {
      if (next === null) {
        window.localStorage.removeItem(STORAGE_KEY);
      } else {
        window.localStorage.setItem(STORAGE_KEY, next);
      }
    } catch {
      // Storage write failed — in-memory override still applies for this tab.
    }
  }
  overrideListeners.forEach((cb) => cb());
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
 * choice is persisted in localStorage and overrides the auto-detect. The
 * override is held in a shared external store so every consumer of this
 * hook (ModeToggle, HomePage, etc.) re-renders together when it changes.
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
  const override = useSyncExternalStore(
    subscribeToOverride,
    getOverrideSnapshot,
    getOverrideServerSnapshot,
  );

  // Cross-tab sync: if the user toggles view mode in another tab, mirror it here.
  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const handler = (event: StorageEvent) => {
      if (event.key !== STORAGE_KEY) {
        return;
      }
      cachedOverride = isViewMode(event.newValue) ? event.newValue : null;
      overrideListeners.forEach((cb) => cb());
    };
    window.addEventListener("storage", handler);
    return () => {
      window.removeEventListener("storage", handler);
    };
  }, []);

  const setViewMode = useCallback((next: ViewMode | null) => {
    writeOverride(next);
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
