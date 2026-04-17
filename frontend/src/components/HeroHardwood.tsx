// HeroHardwood — warm woodgrain SVG texture for the hero panel.
// Server component (pure computation, no browser APIs).
// Matches the Hardwood primitive from the CourtVue Labs design system.

interface HeroHardwoodProps {
  opacity?: number;
  tint?: string;
  seed?: number;
}

export default function HeroHardwood({
  opacity = 0.14,
  tint = "#a8753a",
  seed = 7,
}: HeroHardwoodProps) {
  // Vertical plank seam positions with a deterministic jitter
  const plankCount = 9;
  const planks: number[] = [];
  for (let i = 1; i < plankCount; i++) {
    const jitter = ((i * 37 + seed * 11) % 13) / 13 - 0.5;
    planks.push(i * (100 / plankCount) + jitter * 1.4);
  }

  // Horizontal grain lines — long sinusoidal sweeps
  type GrainLine = { d: string; op: number };
  const grains: GrainLine[] = [];
  for (let i = 0; i < 26; i++) {
    const y = (i * 4.1 + seed) % 100;
    const amp = 0.6 + ((i * 13) % 5) * 0.25;
    const freq = 0.9 + ((i * 7) % 4) * 0.2;
    const phase = (i * 17) % 360;
    const pts: string[] = [`M 0 ${y.toFixed(2)}`];
    for (let x = 0; x <= 100; x += 4) {
      const yy = y + Math.sin((x * freq + phase) * 0.06) * amp;
      pts.push(`L ${x} ${yy.toFixed(2)}`);
    }
    grains.push({ d: pts.join(" "), op: 0.25 + ((i * 3) % 5) * 0.07 });
  }

  const gradId = `hw-warm-${seed}`;

  return (
    <div
      aria-hidden
      style={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        pointerEvents: "none",
        borderRadius: "inherit",
        opacity,
      }}
    >
      <svg
        width="100%"
        height="100%"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        style={{ position: "absolute", inset: 0, mixBlendMode: "multiply" }}
      >
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={tint} stopOpacity="0" />
            <stop offset="40%" stopColor={tint} stopOpacity="0.55" />
            <stop offset="100%" stopColor={tint} stopOpacity="0" />
          </linearGradient>
        </defs>
        <rect width="100" height="100" fill={`url(#${gradId})`} />
        {grains.map((g, i) => (
          <path key={i} d={g.d} stroke={tint} strokeWidth="0.18" fill="none" opacity={g.op} />
        ))}
        {planks.map((x, i) => (
          <line key={`p-${i}`} x1={x} y1="0" x2={x} y2="100" stroke={tint} strokeWidth="0.22" opacity="0.35" />
        ))}
      </svg>
    </div>
  );
}
