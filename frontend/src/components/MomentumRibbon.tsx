"use client";

interface MomentumRibbonProps {
  delta: number | null;
  inverse?: boolean;
}

export default function MomentumRibbon({
  delta,
  inverse = false,
}: MomentumRibbonProps) {
  const normalized = Math.max(-1, Math.min(1, delta == null ? 0 : delta * (inverse ? -8 : 8)));
  const start = 44;
  const end = 44 - normalized * 24;
  const positive = delta != null ? (inverse ? delta <= 0 : delta >= 0) : false;
  const stroke = delta == null ? "rgba(123,137,131,0.5)" : positive ? "rgba(33,72,59,0.9)" : "rgba(159,63,49,0.88)";
  const fill = delta == null ? "rgba(123,137,131,0.12)" : positive ? "rgba(33,72,59,0.12)" : "rgba(159,63,49,0.12)";

  return (
    <svg viewBox="0 0 160 56" className="h-14 w-full">
      <path
        d={`M 0 ${start} C 32 ${start} 48 ${start - normalized * 10} 80 ${end} C 108 ${end + normalized * 8} 126 ${end} 160 ${end}`}
        fill="none"
        stroke={stroke}
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        d={`M 0 56 L 0 ${start} C 32 ${start} 48 ${start - normalized * 10} 80 ${end} C 108 ${end + normalized * 8} 126 ${end} 160 ${end} L 160 56 Z`}
        fill={fill}
      />
      <circle cx="12" cy={start} r="4" fill={stroke} />
      <circle cx="148" cy={end} r="5" fill={stroke} />
    </svg>
  );
}
