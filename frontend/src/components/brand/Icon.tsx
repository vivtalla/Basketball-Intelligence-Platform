import type { ReactNode } from "react";

export type IconName =
  | "search"
  | "arrow-right"
  | "star"
  | "close"
  | "chart"
  | "basketball"
  | "beaker"
  | "shield"
  | "scales"
  | "clipboard"
  | "print"
  | "sparkle"
  | "check"
  | "spark"
  | "clock"
  | "flame"
  | "trophy"
  | "calendar"
  | "line-chart";

interface IconProps {
  name: IconName;
  size?: number;
  stroke?: number;
  color?: string;
  className?: string;
}

const PATHS: Record<IconName, ReactNode> = {
  search: (
    <>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </>
  ),
  "arrow-right": (
    <>
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </>
  ),
  star: (
    <path
      d="M12 2.5l2.8 6 6.6.6-5 4.4 1.5 6.5L12 16.8 6.1 20l1.5-6.5-5-4.4 6.6-.6L12 2.5z"
      strokeLinejoin="round"
    />
  ),
  close: (
    <>
      <path d="M6 6l12 12" />
      <path d="M18 6l-12 12" />
    </>
  ),
  chart: (
    <>
      <path d="M4 20V10" />
      <path d="M10 20V4" />
      <path d="M16 20v-7" />
      <path d="M22 20H2" />
    </>
  ),
  basketball: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18" />
      <path d="M12 3v18" />
      <path d="M5.5 5.5c4 3 9 3 13 0" />
      <path d="M5.5 18.5c4-3 9-3 13 0" />
    </>
  ),
  beaker: (
    <>
      <path d="M9 3h6" />
      <path d="M10 3v6l-5 9a3 3 0 0 0 2.6 4.5h8.8A3 3 0 0 0 19 18l-5-9V3" />
    </>
  ),
  shield: <path d="M12 3 4 6v6c0 5 3.5 8.5 8 9 4.5-.5 8-4 8-9V6l-8-3z" />,
  scales: (
    <>
      <path d="M12 3v18" />
      <path d="M4 20h16" />
      <path d="m6 8 3 7H3z" />
      <path d="m18 8 3 7h-6z" />
      <path d="M4 8h16" />
    </>
  ),
  clipboard: (
    <>
      <rect x="6" y="4" width="12" height="17" rx="2" />
      <path d="M9 4h6v3H9z" />
      <path d="M9 11h6" />
      <path d="M9 15h4" />
    </>
  ),
  print: (
    <>
      <path d="M6 9V4h12v5" />
      <rect x="4" y="9" width="16" height="8" rx="2" />
      <path d="M6 17h12v4H6z" />
    </>
  ),
  sparkle: <path d="M12 3l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" />,
  check: <path d="m5 13 4 4L19 7" />,
  spark: <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8z" />,
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  flame: <path d="M12 2c2 4 6 6 6 11a6 6 0 1 1-12 0c0-3 2-5 3-7 1 2 3 2 3-4z" />,
  trophy: (
    <>
      <path d="M8 4h8v6a4 4 0 0 1-8 0V4z" />
      <path d="M4 5h4v3a3 3 0 0 1-3-3z" />
      <path d="M20 5h-4v3a3 3 0 0 0 3-3z" />
      <path d="M9 17h6" />
      <path d="M10 21h4" />
      <path d="M12 14v3" />
    </>
  ),
  calendar: (
    <>
      <rect x="4" y="5" width="16" height="16" rx="2" />
      <path d="M8 3v4" />
      <path d="M16 3v4" />
      <path d="M4 11h16" />
    </>
  ),
  "line-chart": (
    <>
      <path d="M4 19h16" />
      <path d="M4 19V5" />
      <path d="m4 16 4-5 4 3 4-7 4 4" />
    </>
  ),
};

const FILLED: ReadonlySet<IconName> = new Set<IconName>(["star", "spark"]);

/**
 * Icon — single-line stroked SVG icon set tuned for nav, kickers, and
 * card chrome. 24×24 viewBox. Default stroke 1.8, color = currentColor
 * so the parent's text color drives it.
 */
export default function Icon({
  name,
  size = 20,
  stroke = 1.8,
  color = "currentColor",
  className,
}: IconProps) {
  const isFilled = FILLED.has(name);
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={isFilled ? color : "none"}
      stroke={color}
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden
    >
      {PATHS[name] ?? PATHS.search}
    </svg>
  );
}
