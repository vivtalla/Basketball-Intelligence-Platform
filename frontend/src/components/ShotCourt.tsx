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

const COURT = {
  hoopX: 250,
  hoopY: 420,
  baselineY: 476,
  leftEdge: 0,
  rightEdge: 500,
  cornerThreeLeftX: 30,
  cornerThreeRightX: 470,
  threeRadius: 237.5,
} as const;

const threeArcDy = Math.sqrt(
  COURT.threeRadius ** 2 - (COURT.hoopX - COURT.cornerThreeLeftX) ** 2
);
const threeArcY = COURT.hoopY - threeArcDy;
const threeArcPath = `M ${COURT.cornerThreeLeftX},${threeArcY.toFixed(1)} A ${COURT.threeRadius},${COURT.threeRadius} 0 0 1 ${COURT.cornerThreeRightX},${threeArcY.toFixed(1)}`;

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
      <line x1={COURT.leftEdge} y1={COURT.baselineY} x2={COURT.rightEdge} y2={COURT.baselineY} stroke={palette.ghost} strokeWidth="1.8" />

      {/* Three-point line glow pass */}
      <line x1={COURT.cornerThreeLeftX} y1={COURT.baselineY} x2={COURT.cornerThreeLeftX} y2={threeArcY} stroke={palette.glow} strokeWidth="4.8" opacity="0.36" />
      <line x1={COURT.cornerThreeRightX} y1={COURT.baselineY} x2={COURT.cornerThreeRightX} y2={threeArcY} stroke={palette.glow} strokeWidth="4.8" opacity="0.36" />
      <path
        d={threeArcPath}
        stroke={palette.glow}
        strokeWidth="4.8"
        opacity="0.34"
      />

      <line x1={COURT.cornerThreeLeftX} y1={COURT.baselineY} x2={COURT.cornerThreeLeftX} y2={threeArcY} stroke={palette.strong} strokeWidth="3" />
      <line x1={COURT.cornerThreeRightX} y1={COURT.baselineY} x2={COURT.cornerThreeRightX} y2={threeArcY} stroke={palette.strong} strokeWidth="3" />
      <path
        d={threeArcPath}
        stroke={palette.strong}
        strokeWidth="3"
      />
    </g>
  );
}
