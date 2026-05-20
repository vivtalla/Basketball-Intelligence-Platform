// Sprint 105 (Stream A) — pure delta helpers for the /draft/compare view.
//
// Compute the head-to-head edge for paired numeric metrics. Components
// consume this helper to render delta pills without re-doing arithmetic
// at each call site.

export type DeltaWinner = "a" | "b" | "tie";

export interface DeltaResult {
  winner: DeltaWinner;
  /** Absolute magnitude of the difference (a - b). */
  magnitude: number;
  /** Pre-formatted label like "+1.7 PPG" or "+2.5%" — empty string for tie. */
  label: string;
  /** Whether either input was nullish (tie + label="—"). */
  missingData: boolean;
}

export interface FormatDeltaOptions {
  /** Decimal places for the magnitude (default 1). */
  digits?: number;
  /** Suffix appended after the magnitude (e.g. "%", " PPG"). */
  suffix?: string;
  /**
   * Set false for stats where lower is better (e.g. TOV). Default true.
   * When false, the smaller value wins.
   */
  higherIsBetter?: boolean;
  /** Render as percent (multiply by 100). Use for 0..1 fractional values. */
  asPercent?: boolean;
}

/**
 * Returns the head-to-head delta for two numeric values, with a
 * pre-formatted label suitable for direct rendering in a chip.
 *
 * Null/undefined on either side returns a "tie" with `label: "—"` and
 * `missingData: true` so callers can dim the chip.
 */
export function formatDelta(
  a: number | null | undefined,
  b: number | null | undefined,
  opts: FormatDeltaOptions = {},
): DeltaResult {
  const { digits = 1, suffix = "", higherIsBetter = true, asPercent = false } = opts;

  if (a == null || b == null) {
    return { winner: "tie", magnitude: 0, label: "—", missingData: true };
  }

  const aScaled = asPercent ? a * 100 : a;
  const bScaled = asPercent ? b * 100 : b;
  const diff = aScaled - bScaled;
  const magnitude = Math.abs(diff);

  // Treat tiny differences as ties so we don't show "+0.0" chips.
  const tieEpsilon = Math.pow(10, -digits) / 2;
  if (magnitude < tieEpsilon) {
    return { winner: "tie", magnitude: 0, label: "Tie", missingData: false };
  }

  // Direction-aware winner.
  let winner: DeltaWinner;
  if (higherIsBetter) {
    winner = diff > 0 ? "a" : "b";
  } else {
    winner = diff < 0 ? "a" : "b";
  }

  const sign = "+";
  const formatted = magnitude.toFixed(digits);
  const renderedSuffix = asPercent ? (suffix || "%") : suffix;
  const label = `${sign}${formatted}${renderedSuffix}`;

  return { winner, magnitude, label, missingData: false };
}

/** Convenience: just the winner direction, no formatting. */
export function deltaWinner(
  a: number | null | undefined,
  b: number | null | undefined,
  higherIsBetter = true,
): DeltaWinner {
  return formatDelta(a, b, { higherIsBetter }).winner;
}
