"use client";

// FloatingBall — gently bouncing basketball decoration for hero panels.
// Pure SVG + CSS keyframes, client component (uses useId for SVG id collision safety).
// Matches the FloatingBall primitive from the CourtVue Labs design system.

import { useId } from "react";

interface FloatingBallProps {
  size?: number;
  className?: string;
  style?: React.CSSProperties;
}

export default function FloatingBall({ size = 56, className, style }: FloatingBallProps) {
  const reactId = useId();
  // useId can include characters (":") that aren't valid inside SVG url(#...) refs in some renderers.
  const ID = reactId.replace(/[^a-zA-Z0-9_-]/g, "");
  const fillId = `cv-ball-fill-${ID}`;
  const shineId = `cv-ball-shine-${ID}`;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 56 56"
      aria-hidden
      className={className}
      style={{
        animation: "cv-ball-float 4.2s ease-in-out infinite",
        filter:
          "drop-shadow(0 6px 14px rgba(184,79,29,0.42)) drop-shadow(0 2px 6px rgba(122,58,20,0.35))",
        ...style,
      }}
    >
      <defs>
        <radialGradient id={fillId} cx="0.45" cy="0.40" r="0.65">
          <stop offset="0%" stopColor="#e89456" />
          <stop offset="50%" stopColor="#c5662a" />
          <stop offset="88%" stopColor="#8a4318" />
          <stop offset="100%" stopColor="#5a2e10" />
        </radialGradient>
        <radialGradient id={shineId} cx="0.32" cy="0.28" r="0.55">
          <stop offset="0%" stopColor="rgba(255,255,255,0.55)" />
          <stop offset="55%" stopColor="rgba(255,255,255,0.10)" />
          <stop offset="100%" stopColor="rgba(255,255,255,0)" />
        </radialGradient>
      </defs>
      <g data-cv-ball={ID}>
        <circle cx="28" cy="28" r="26" fill={`url(#${fillId})`} />
        <circle cx="28" cy="28" r="26" fill={`url(#${shineId})`} />
        {/* Center vertical seam — main spine */}
        <path
          d="M 28 2 Q 22 28 28 54"
          fill="none"
          stroke="#3b1e0c"
          strokeWidth="1.8"
          opacity="0.65"
        />
        {/* Horizontal curves — top and bottom */}
        <path
          d="M 4 28 Q 28 20 52 28"
          fill="none"
          stroke="#3b1e0c"
          strokeWidth="1.2"
          opacity="0.5"
        />
        <path
          d="M 4 28 Q 28 36 52 28"
          fill="none"
          stroke="#3b1e0c"
          strokeWidth="1.2"
          opacity="0.5"
        />
        {/* Shoulder/angled curves */}
        <path
          d="M 9 8 Q 28 28 9 48"
          fill="none"
          stroke="#3b1e0c"
          strokeWidth="0.8"
          opacity="0.35"
        />
        <path
          d="M 47 8 Q 28 28 47 48"
          fill="none"
          stroke="#3b1e0c"
          strokeWidth="0.8"
          opacity="0.35"
        />
      </g>
    </svg>
  );
}
