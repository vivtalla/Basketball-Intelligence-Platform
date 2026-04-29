import type { CSSProperties, ReactNode } from "react";
import Ticker from "./Ticker";

export type StatTone = "default" | "accent" | "soft" | "signal";
export type StatSize = "sm" | "md" | "lg";

interface StatProps {
  label: string;
  value: number | string;
  delta?: string | null;
  tone?: StatTone;
  size?: StatSize;
  decimals?: number;
  /** When true and `value` is numeric, animate the count-up. */
  animate?: boolean;
  style?: CSSProperties;
  children?: ReactNode;
}

const TONES: Record<StatTone, CSSProperties> = {
  default: {
    background: "#fff9f1",
    border: "1px solid var(--border)",
    color: "var(--foreground)",
  },
  accent: {
    background: "var(--accent)",
    border: "none",
    color: "var(--accent-ink)",
  },
  soft: {
    background: "var(--accent-soft)",
    border: "none",
    color: "var(--accent-strong)",
  },
  signal: {
    background: "var(--signal-soft)",
    border: "none",
    color: "var(--signal-ink)",
  },
};

const SIZES: Record<StatSize, { padding: string; value: number }> = {
  sm: { padding: "10px 12px", value: 20 },
  md: { padding: "14px 16px", value: 28 },
  lg: { padding: "18px 20px", value: 40 },
};

/**
 * Stat — large serif tabular numeral with mono label kicker and
 * optional ▲/▼ delta footer. Numeric `value` can animate via `animate`
 * prop (delegates to <Ticker />); string values render as-is.
 *
 * Tones map to: default cream surface, forest accent (inverse), pale
 * forest soft, pale gold signal. Sizes are sm/md/lg.
 */
export default function Stat({
  label,
  value,
  delta,
  tone = "default",
  size = "md",
  decimals = 1,
  animate = false,
  style,
  children,
}: StatProps) {
  const sizes = SIZES[size];
  const tones = TONES[tone];
  const numericValue = typeof value === "number" ? value : null;
  const deltaIsNegative = typeof delta === "string" && delta.startsWith("-");
  const deltaColor =
    tone === "accent"
      ? "#b4893d"
      : deltaIsNegative
      ? "var(--danger-ink)"
      : "var(--success-ink)";

  return (
    <div
      style={{
        borderRadius: 18,
        ...tones,
        padding: sizes.padding,
        ...style,
      }}
    >
      <div
        style={{
          fontFamily: "var(--font-geist-mono)",
          fontSize: 10,
          letterSpacing: "0.10em",
          opacity: 0.72,
          textTransform: "uppercase",
        }}
      >
        {label}
      </div>
      <div
        className="tabular-nums"
        style={{
          fontFamily: "var(--font-display)",
          fontSize: sizes.value,
          fontWeight: 700,
          lineHeight: 1,
          marginTop: 6,
          fontVariantNumeric: "tabular-nums",
          letterSpacing: "-0.02em",
        }}
      >
        {animate && numericValue != null ? (
          <Ticker value={numericValue} decimals={decimals} />
        ) : (
          value
        )}
      </div>
      {delta != null && (
        <div
          className="tabular-nums"
          style={{
            fontFamily: "var(--font-geist-mono)",
            fontSize: 11,
            marginTop: 4,
            color: deltaColor,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {deltaIsNegative ? "▼ " : "▲ "}
          {delta.replace(/^[+-]/, "")}
        </div>
      )}
      {children}
    </div>
  );
}
