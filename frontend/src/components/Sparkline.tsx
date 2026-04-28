interface SparklineProps {
  values: number[];
  width?: number;
  height?: number;
  stroke?: string;
  baseline?: number;
  delta?: number;
}

/**
 * Minimal SVG sparkline. Pure presentational component — accepts a numeric
 * series and renders a polyline scaled to its min/max. Intentionally
 * lightweight (no Recharts) so it can render dozens of times in a leader
 * column without measurable cost.
 *
 * Behaviour:
 * - Fewer than 2 values → renders an em-dash placeholder.
 * - When ``delta`` is provided, the stroke is colored green for positive,
 *   red for negative, muted for zero. Otherwise falls back to ``stroke``
 *   (defaults to ``var(--accent)``).
 * - Optional ``baseline`` draws a dashed reference line at that value.
 * - Animation is intentionally avoided; users with prefers-reduced-motion
 *   see the same static rendering.
 */
export default function Sparkline({
  values,
  width = 60,
  height = 18,
  stroke = "var(--accent)",
  baseline,
  delta,
}: SparklineProps) {
  if (!values || values.length < 2) {
    return (
      <span
        aria-label="No trend data"
        className="text-[var(--muted)] text-xs tabular-nums"
        style={{ display: "inline-block", width, textAlign: "center" }}
      >
        —
      </span>
    );
  }

  const min = Math.min(...values, baseline ?? Number.POSITIVE_INFINITY);
  const max = Math.max(...values, baseline ?? Number.NEGATIVE_INFINITY);
  const span = max - min || 1;

  const padX = 1;
  const padY = 1;
  const innerWidth = Math.max(width - padX * 2, 1);
  const innerHeight = Math.max(height - padY * 2, 1);

  const xStep = values.length > 1 ? innerWidth / (values.length - 1) : 0;

  const yFor = (value: number) => {
    const norm = (value - min) / span;
    return padY + (1 - norm) * innerHeight;
  };

  const points = values
    .map((v, i) => `${(padX + i * xStep).toFixed(2)},${yFor(v).toFixed(2)}`)
    .join(" ");

  const resolvedStroke =
    typeof delta === "number"
      ? delta > 0
        ? "var(--success-ink)"
        : delta < 0
        ? "var(--danger-ink)"
        : "var(--muted)"
      : stroke;

  const lastX = padX + (values.length - 1) * xStep;
  const lastY = yFor(values[values.length - 1]);

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`Trend sparkline for last ${values.length} games`}
      style={{ display: "inline-block", verticalAlign: "middle" }}
    >
      {typeof baseline === "number" && (
        <line
          x1={padX}
          x2={width - padX}
          y1={yFor(baseline)}
          y2={yFor(baseline)}
          stroke="var(--muted)"
          strokeWidth={0.75}
          strokeDasharray="2 2"
          opacity={0.55}
        />
      )}
      <polyline
        fill="none"
        stroke={resolvedStroke}
        strokeWidth={1.25}
        strokeLinejoin="round"
        strokeLinecap="round"
        points={points}
      />
      <circle cx={lastX} cy={lastY} r={1.5} fill={resolvedStroke} />
    </svg>
  );
}
