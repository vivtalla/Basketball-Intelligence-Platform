import type { CSSProperties, HTMLAttributes, ReactNode } from "react";

export type PillTone = "default" | "accent" | "signal" | "positive" | "negative";

interface PillProps extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode;
  tone?: PillTone;
  style?: CSSProperties;
}

const TONES: Record<PillTone, CSSProperties> = {
  default: {
    background: "#fff9f1",
    color: "var(--muted)",
    border: "1px solid var(--border)",
  },
  signal: {
    background: "var(--signal-soft)",
    color: "var(--signal-ink)",
    border: "1px solid rgba(180,137,61,0.16)",
  },
  accent: {
    background: "var(--accent-soft)",
    color: "var(--accent-strong)",
    border: "1px solid rgba(33,72,59,0.10)",
  },
  positive: {
    background: "var(--success-soft)",
    color: "var(--success-ink)",
    border: "1px solid rgba(40,80,55,0.10)",
  },
  negative: {
    background: "var(--danger-soft)",
    color: "var(--danger-ink)",
    border: "1px solid rgba(127,51,43,0.12)",
  },
};

/**
 * Pill — small rounded badge with five tonal variants. Sentence case,
 * 12px body. Inline-flex so it composes with icons via gap.
 */
export default function Pill({ children, tone = "signal", style, ...rest }: PillProps) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "5px 12px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 500,
        ...TONES[tone],
        ...style,
      }}
      {...rest}
    >
      {children}
    </span>
  );
}
