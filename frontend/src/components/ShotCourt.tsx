"use client";

interface ShotCourtProps {
  tone?: "light" | "dark";
  className?: string;
}

const PALETTE = {
  light: {
    line: "rgba(33,72,59,0.22)",
    strong: "rgba(33,72,59,0.78)",
    glow: "rgba(255,246,214,0.9)",
    ghost: "rgba(33,72,59,0.12)",
    rim: "rgba(33,72,59,0.94)",
  },
  dark: {
    line: "rgba(230,223,255,0.28)",
    strong: "rgba(255,244,202,0.98)",
    glow: "rgba(255,233,153,0.92)",
    ghost: "rgba(230,223,255,0.16)",
    rim: "rgba(255,250,236,0.98)",
  },
} as const;

export default function ShotCourt({
  tone = "light",
  className,
}: ShotCourtProps) {
  const palette = PALETTE[tone];

  return (
    <g
      className={className}
      stroke={palette.line}
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="none"
    >
      {/* Lane */}
      <rect x="170" y="246" width="160" height="234" />

      {/* Free throw circle */}
      <circle cx="250" cy="246" r="62" stroke={palette.ghost} strokeWidth="1.8" />

      {/* Restricted area */}
      <path d="M 210,430 A 40,40 0 0 0 290,430" stroke={palette.ghost} strokeWidth="1.8" />

      {/* Rim + backboard */}
      <circle cx="250" cy="420" r="7.5" stroke={palette.rim} strokeWidth="2" />
      <line x1="220" y1="430" x2="280" y2="430" stroke={palette.rim} strokeWidth="2.8" />

      {/* Paint markers */}
      <line x1="170" y1="448" x2="176" y2="448" stroke={palette.ghost} />
      <line x1="170" y1="412" x2="176" y2="412" stroke={palette.ghost} />
      <line x1="170" y1="376" x2="176" y2="376" stroke={palette.ghost} />
      <line x1="324" y1="448" x2="330" y2="448" stroke={palette.ghost} />
      <line x1="324" y1="412" x2="330" y2="412" stroke={palette.ghost} />
      <line x1="324" y1="376" x2="330" y2="376" stroke={palette.ghost} />

      {/* Baseline */}
      <line x1="30" y1="480" x2="470" y2="480" stroke={palette.ghost} strokeWidth="1.8" />

      {/* Three-point line glow pass */}
      <line x1="30" y1="480" x2="30" y2="341" stroke={palette.glow} strokeWidth="4.8" opacity="0.36" />
      <line x1="470" y1="480" x2="470" y2="341" stroke={palette.glow} strokeWidth="4.8" opacity="0.36" />
      <path
        d="M 30,341 A 237.5,237.5 0 0 0 470,341"
        stroke={palette.glow}
        strokeWidth="4.8"
        opacity="0.34"
      />

      <line x1="30" y1="480" x2="30" y2="341" stroke={palette.strong} strokeWidth="3" />
      <line x1="470" y1="480" x2="470" y2="341" stroke={palette.strong} strokeWidth="3" />
      <path
        d="M 30,341 A 237.5,237.5 0 0 0 470,341"
        stroke={palette.strong}
        strokeWidth="3"
      />
    </g>
  );
}
