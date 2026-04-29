"use client";

import { useViewMode, type ViewMode } from "@/hooks/useViewMode";

/**
 * Sprint 77 (EB2): three-pill mode toggle (Playoff / Regular / Offseason)
 * with a localStorage-backed override on top of the auto-detected season phase.
 *
 * Reads + writes via {@link useViewMode}. The active pill receives the
 * accent background with cream ink; inactive pills are muted and clickable.
 * When the user has overridden the auto-detected mode, a "Reset to auto"
 * button appears next to the pills and clears the override.
 *
 * Designed to live ABOVE the wordmark inside `<BroadsheetMasthead>`.
 */

const MODES: ReadonlyArray<{ value: ViewMode; label: string }> = [
  { value: "playoff", label: "PLAYOFF" },
  { value: "regular", label: "REGULAR" },
  { value: "offseason", label: "OFFSEASON" },
];

const MODE_HINT_LABEL: Record<ViewMode, string> = {
  playoff: "playoff",
  regular: "regular-season",
  offseason: "offseason",
};

export default function ModeToggle() {
  const { viewMode, setViewMode, isOverridden } = useViewMode();

  const hint = isOverridden
    ? "Override active — click Reset to auto"
    : `Showing ${MODE_HINT_LABEL[viewMode]} content (auto-detected)`;

  return (
    <div
      className="flex flex-col items-center gap-1.5"
      role="group"
      aria-label="Home page view mode"
    >
      <div className="flex items-center gap-2">
        <div
          className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface)] p-1"
          role="radiogroup"
          aria-label="View mode"
        >
          {MODES.map((mode) => {
            const isActive = mode.value === viewMode;
            return (
              <button
                key={mode.value}
                type="button"
                role="radio"
                aria-checked={isActive}
                onClick={() => setViewMode(mode.value)}
                className={
                  "px-3 py-1 rounded-full text-[11px] font-mono font-bold tracking-[0.18em] transition-colors duration-150 " +
                  (isActive
                    ? "bg-[var(--accent)] text-[var(--accent-ink)] shadow-sm"
                    : "text-[var(--muted)] hover:text-[var(--foreground)]")
                }
              >
                {mode.label}
              </button>
            );
          })}
        </div>
        {isOverridden ? (
          <button
            type="button"
            onClick={() => setViewMode(null)}
            className="text-[11px] font-mono tracking-[0.16em] uppercase text-[var(--muted)] underline-offset-4 hover:text-[var(--accent)] hover:underline transition-colors"
          >
            Reset to auto
          </button>
        ) : null}
      </div>
      <p className="text-[10px] font-mono tracking-[0.14em] uppercase text-[var(--muted)]">
        {hint}
      </p>
    </div>
  );
}
