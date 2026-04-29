import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "outline";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: ButtonVariant;
  style?: CSSProperties;
}

const VARIANTS: Record<ButtonVariant, CSSProperties> = {
  primary: {
    background: "var(--accent)",
    color: "var(--accent-ink)",
    border: 0,
    boxShadow: "0 14px 34px rgba(33,72,59,0.18)",
  },
  secondary: {
    background: "rgba(255,250,244,0.88)",
    color: "var(--foreground)",
    border: "1px solid var(--border)",
  },
  outline: {
    background: "transparent",
    color: "var(--accent)",
    border: "1px solid var(--accent)",
  },
  ghost: {
    background: "transparent",
    color: "var(--accent)",
    border: 0,
  },
};

/**
 * Button — pill-shaped, four variants. Primary = forest fill + cream
 * ink. Secondary = cream surface + foreground. Outline = forest stroke
 * on transparent. Ghost = forest text on transparent.
 */
export default function Button({
  children,
  variant = "primary",
  style,
  ...rest
}: ButtonProps) {
  return (
    <button
      style={{
        padding: "10px 20px",
        borderRadius: 999,
        fontSize: 14,
        fontWeight: 500,
        fontFamily: "var(--font-geist-sans)",
        cursor: "pointer",
        transition: "all 180ms cubic-bezier(0.33,1,0.68,1)",
        ...VARIANTS[variant],
        ...style,
      }}
      {...rest}
    >
      {children}
    </button>
  );
}
