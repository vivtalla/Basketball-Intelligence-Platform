"use client";

/**
 * Sprint 77 (EB4): two-pill toggle that lets a user override the auto-picked
 * `/games/[gameId]` chrome variant (Broadsheet vs Scoreboard).
 *
 * Lives in the page header, ABOVE the chrome. Auto-picks live/halftime games
 * into Scoreboard; final / pre-game into Broadsheet. The user override is
 * persisted in localStorage under the global key `bip-game-variant` so a
 * preference carries across games, matching the small-toggle aesthetic of
 * `<ModeToggle>` from EB2 but with no `null`/auto reset surfaced inline —
 * the override is cleared by the page when the auto-pick re-aligns.
 */

export type GameVariant = "broadsheet" | "scoreboard";

interface GameVariantToggleProps {
  variant: GameVariant;
  onSetVariant: (next: GameVariant) => void;
  /**
   * When true, a small "Auto" pill is rendered after the toggle so the user
   * can clear their localStorage override and return to the auto-picked
   * variant.
   */
  isOverridden?: boolean;
  onResetAuto?: () => void;
}

const VARIANTS: ReadonlyArray<{ value: GameVariant; label: string }> = [
  { value: "broadsheet", label: "BROADSHEET" },
  { value: "scoreboard", label: "SCOREBOARD" },
];

export default function GameVariantToggle({
  variant,
  onSetVariant,
  isOverridden = false,
  onResetAuto,
}: GameVariantToggleProps) {
  return (
    <div
      className="flex items-center gap-2"
      role="group"
      aria-label="Game detail chrome variant"
    >
      <div
        className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-[var(--surface)] p-1"
        role="radiogroup"
        aria-label="Chrome variant"
      >
        {VARIANTS.map((entry) => {
          const isActive = entry.value === variant;
          return (
            <button
              key={entry.value}
              type="button"
              role="radio"
              aria-checked={isActive}
              onClick={() => onSetVariant(entry.value)}
              className={
                "px-2.5 py-1 rounded-full text-[10px] font-mono font-bold tracking-[0.18em] transition-colors duration-150 " +
                (isActive
                  ? "bg-[var(--accent)] text-[var(--accent-ink)] shadow-sm"
                  : "text-[var(--muted)] hover:text-[var(--foreground)]")
              }
            >
              {entry.label}
            </button>
          );
        })}
      </div>
      {isOverridden && onResetAuto ? (
        <button
          type="button"
          onClick={onResetAuto}
          className="text-[10px] font-mono tracking-[0.16em] uppercase text-[var(--muted)] underline-offset-4 hover:text-[var(--accent)] hover:underline transition-colors"
        >
          Auto
        </button>
      ) : null}
    </div>
  );
}
