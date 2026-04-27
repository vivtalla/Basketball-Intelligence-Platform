// FloatingBall — gently bouncing basketball decoration for hero panels.
// Pure SVG + CSS keyframes, server-component safe.
// Matches the FloatingBall primitive from the CourtVue Labs design system.

interface FloatingBallProps {
  size?: number;
  className?: string;
  style?: React.CSSProperties;
}

export default function FloatingBall({ size = 56, className, style }: FloatingBallProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 56 56"
      aria-hidden
      className={className}
      style={{
        animation: "cv-ball-float 4.2s ease-in-out infinite",
        filter: "drop-shadow(0 8px 18px rgba(184,79,29,0.32))",
        ...style,
      }}
    >
      <style>{`
        @keyframes cv-ball-float {
          0%, 100% { transform: translateY(0) rotate(-12deg); }
          50%      { transform: translateY(-10px) rotate(8deg); }
        }
      `}</style>
      <defs>
        <radialGradient id="cv-ball-grad" cx="35%" cy="30%" r="80%">
          <stop offset="0%" stopColor="#dd8b4d" />
          <stop offset="55%" stopColor="#b8581d" />
          <stop offset="100%" stopColor="#7a3a14" />
        </radialGradient>
      </defs>
      <circle cx="28" cy="28" r="26" fill="url(#cv-ball-grad)" />
      <path d="M 4 28 Q 28 20 52 28" fill="none" stroke="#3b1e0c" strokeWidth="1.4" opacity="0.5" />
      <path d="M 4 28 Q 28 36 52 28" fill="none" stroke="#3b1e0c" strokeWidth="1.4" opacity="0.5" />
      <path d="M 28 2 Q 22 28 28 54" fill="none" stroke="#3b1e0c" strokeWidth="1.4" opacity="0.5" />
      <path d="M 9 8 Q 28 28 9 48" fill="none" stroke="#3b1e0c" strokeWidth="1.2" opacity="0.4" />
      <path d="M 47 8 Q 28 28 47 48" fill="none" stroke="#3b1e0c" strokeWidth="1.2" opacity="0.4" />
    </svg>
  );
}
