import type { CSSProperties, HTMLAttributes, ReactNode } from "react";

interface KickerProps extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode;
  style?: CSSProperties;
}

/**
 * Kicker — section eyebrow. ALL CAPS mono, gold (var(--signal)),
 * 0.18em letter-spacing. Use above headings.
 */
export default function Kicker({ children, style, ...rest }: KickerProps) {
  return (
    <span
      style={{
        fontFamily: "var(--font-geist-mono)",
        fontWeight: 700,
        fontSize: 11,
        lineHeight: 1.2,
        letterSpacing: "0.18em",
        textTransform: "uppercase",
        color: "var(--signal)",
        ...style,
      }}
      {...rest}
    >
      {children}
    </span>
  );
}
