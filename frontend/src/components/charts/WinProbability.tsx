"use client";

import { useEffect, useRef, useState } from "react";

export interface WinProbPoint {
  /** Game minute, 0–48 (regulation). Overtime extends past 48. */
  t: number;
  /** Home win probability, 0..1. */
  prob: number;
  event?: string;
}

interface WinProbabilityProps {
  data: WinProbPoint[];
  width?: number;
  height?: number;
  /** Caption shown immediately under the chart. Optional. */
  caption?: string;
}

/**
 * WinProbability — single-curve home win-probability chart with
 * momentum shading (forest above 50%, gold below), quarter dividers,
 * 50% reference line, and optional event markers.
 *
 * The visual sibling of the existing <WinProbabilityChart> in the
 * components root, but with a different prop shape: this one accepts
 * `caption` and is intended for the new /playoffs and /games surfaces
 * that compose primitives directly.
 */
export default function WinProbability({
  data,
  width = 720,
  height = 220,
  caption,
}: WinProbabilityProps) {
  const ref = useRef<SVGSVGElement | null>(null);
  const [seen, setSeen] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node || seen) return;
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            setSeen(true);
            io.disconnect();
          }
        });
      },
      { threshold: 0.18 },
    );
    io.observe(node);
    return () => io.disconnect();
  }, [seen]);

  const PAD = { l: 28, r: 16, t: 18, b: 28 };
  const W = width;
  const H = height;
  const totalT = Math.max(48, ...data.map((d) => d.t));
  const x = (t: number) => PAD.l + (t / totalT) * (W - PAD.l - PAD.r);
  const y = (p: number) => PAD.t + (1 - p) * (H - PAD.t - PAD.b);

  const path = data
    .map((d, i) => `${i === 0 ? "M" : "L"} ${x(d.t).toFixed(1)} ${y(d.prob).toFixed(1)}`)
    .join(" ");
  const homeArea =
    `M ${x(0).toFixed(1)} ${y(0.5).toFixed(1)} ` +
    data.map((d) => `L ${x(d.t).toFixed(1)} ${y(Math.max(0.5, d.prob)).toFixed(1)}`).join(" ") +
    ` L ${x(totalT).toFixed(1)} ${y(0.5).toFixed(1)} Z`;
  const awayArea =
    `M ${x(0).toFixed(1)} ${y(0.5).toFixed(1)} ` +
    data.map((d) => `L ${x(d.t).toFixed(1)} ${y(Math.min(0.5, d.prob)).toFixed(1)}`).join(" ") +
    ` L ${x(totalT).toFixed(1)} ${y(0.5).toFixed(1)} Z`;

  const events = data.filter((d) => d.event);
  const dashLen = data.length * 24;
  const quarters = totalT === 48 ? [12, 24, 36] : [12, 24, 36, 48];
  const labels = totalT === 48 ? [0, 12, 24, 36, 48] : [0, 12, 24, 36, 48, totalT];

  return (
    <div>
      <svg
        ref={ref}
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        style={{ display: "block" }}
      >
        <defs>
          <linearGradient id="cv-wp2-home" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#21483b" stopOpacity="0.32" />
            <stop offset="100%" stopColor="#21483b" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="cv-wp2-away" x1="0" x2="0" y1="1" y2="0">
            <stop offset="0%" stopColor="#b4893d" stopOpacity="0.28" />
            <stop offset="100%" stopColor="#b4893d" stopOpacity="0" />
          </linearGradient>
        </defs>
        {quarters.map((q) => (
          <line
            key={q}
            x1={x(q)}
            x2={x(q)}
            y1={PAD.t}
            y2={H - PAD.b}
            stroke="rgba(53,41,33,0.1)"
            strokeDasharray="2 4"
          />
        ))}
        {labels.map((q) => (
          <text
            key={q}
            x={x(q)}
            y={H - 8}
            fontFamily="var(--font-geist-mono)"
            fontSize="10"
            fill="var(--muted)"
            textAnchor="middle"
          >
            {q === 0 ? "TIP" : q === totalT ? "FINAL" : `Q${q / 12}`}
          </text>
        ))}
        <line
          x1={PAD.l}
          x2={W - PAD.r}
          y1={y(0.5)}
          y2={y(0.5)}
          stroke="rgba(53,41,33,0.18)"
          strokeWidth="0.8"
        />
        <text
          x={PAD.l - 6}
          y={y(0.5) + 4}
          fontFamily="var(--font-geist-mono)"
          fontSize="9"
          fill="var(--muted)"
          textAnchor="end"
        >
          50
        </text>
        <path
          d={homeArea}
          fill="url(#cv-wp2-home)"
          opacity={seen ? 1 : 0}
          style={{ transition: "opacity 1000ms 200ms" }}
        />
        <path
          d={awayArea}
          fill="url(#cv-wp2-away)"
          opacity={seen ? 1 : 0}
          style={{ transition: "opacity 1000ms 280ms" }}
        />
        <path
          d={path}
          fill="none"
          stroke="var(--accent)"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeDasharray={dashLen}
          strokeDashoffset={seen ? 0 : dashLen}
          style={{ transition: "stroke-dashoffset 1400ms cubic-bezier(0.33,1,0.68,1)" }}
        />
        {events.map((e, i) => (
          <g
            key={i}
            style={{
              opacity: seen ? 1 : 0,
              transition: `opacity 400ms ${800 + i * 100}ms`,
            }}
          >
            <circle
              cx={x(e.t)}
              cy={y(e.prob)}
              r="4"
              fill="var(--signal)"
              stroke="#fcfffd"
              strokeWidth="1.5"
            />
            <line
              x1={x(e.t)}
              x2={x(e.t)}
              y1={y(e.prob) - 6}
              y2={y(e.prob) - 18}
              stroke="var(--signal)"
              strokeWidth="0.8"
            />
            <text
              x={x(e.t)}
              y={y(e.prob) - 22}
              fontFamily="var(--font-geist-mono)"
              fontSize="9"
              fill="var(--foreground)"
              textAnchor="middle"
              fontWeight="700"
              letterSpacing="0.05em"
            >
              {e.event}
            </text>
          </g>
        ))}
      </svg>
      {caption && (
        <p
          className="mt-3 text-sm italic text-[var(--muted)]"
          style={{ fontFamily: "var(--font-display)", maxWidth: 720 }}
        >
          {caption}
        </p>
      )}
    </div>
  );
}
