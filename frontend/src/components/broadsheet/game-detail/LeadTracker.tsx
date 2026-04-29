"use client";

/**
 * Sprint 77 (Stream B / EB3): Lead Tracker — minute-by-minute home-lead
 * bar chart from `data.lead_tracker`. Home leads render in `var(--accent)`
 * above the midline; away leads render in `var(--danger-ink)` below.
 * Quarter dividers drawn at minutes 12 / 24 / 36 / 48 (and OT extensions).
 */

import { useMemo } from "react";
import type { LeadPoint } from "@/lib/types";

interface LeadTrackerProps {
  points: LeadPoint[] | null | undefined;
  homeAbbr: string | null;
  awayAbbr: string | null;
}

const VIEW_W = 720;
const VIEW_H = 240;
const PAD = { l: 44, r: 16, t: 18, b: 28 };

export default function LeadTracker({ points, homeAbbr, awayAbbr }: LeadTrackerProps) {
  // Sprint 77 optimizer (O5): memoize SVG geometry so re-renders triggered
  // by parent polling don't recompute the bar layout when `points` is stable.
  const ready = Array.isArray(points) && points.length > 0;
  const geom = useMemo(() => {
    const data: LeadPoint[] = ready ? (points as LeadPoint[]) : [];
    const maxMinute = data.reduce((m, p) => Math.max(m, p.minute), 48);
    const totalMinutes = Math.max(maxMinute, 48);
    const absMax = Math.max(
      6,
      data.reduce((m, p) => Math.max(m, Math.abs(p.home_lead)), 0)
    );
    const innerW = VIEW_W - PAD.l - PAD.r;
    const innerH = VIEW_H - PAD.t - PAD.b;
    const midY = PAD.t + innerH / 2;
    const barWidth = Math.max(2, innerW / Math.max(totalMinutes, 1) - 1);
    const yScale = innerH / 2 / absMax;
    const quarterMarks: number[] = [];
    for (let q = 12; q <= totalMinutes; q += 12) {
      if (q < totalMinutes) quarterMarks.push(q);
    }
    return { data, totalMinutes, absMax, midY, barWidth, yScale, quarterMarks };
  }, [points, ready]);
  const { data, totalMinutes, absMax, midY, barWidth, yScale, quarterMarks } = geom;
  const x = (minute: number) =>
    PAD.l + (minute / totalMinutes) * (VIEW_W - PAD.l - PAD.r);

  return (
    <section
      className="bip-panel rounded-[1.85rem] px-6 py-7"
      style={{ background: "rgba(255,249,241,0.6)" }}
    >
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="bip-kicker">Margin · minute by minute</p>
          <h2
            className="bip-display mt-2 font-bold text-[var(--foreground)]"
            style={{ fontSize: "clamp(1.5rem, 2.2vw, 2rem)", letterSpacing: "-0.02em" }}
          >
            Lead Tracker
          </h2>
          <p
            className="mt-2 italic text-[var(--muted)]"
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "0.95rem",
              maxWidth: "44rem",
              lineHeight: 1.5,
            }}
          >
            Each bar is one minute of game clock. Above the midline is{" "}
            {homeAbbr ?? "home"}; below is {awayAbbr ?? "away"}.
          </p>
        </div>
      </div>

      {ready ? (
        <div className="overflow-x-auto">
          <svg
            viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
            width="100%"
            role="img"
            aria-label="Home lead by minute"
            style={{ display: "block" }}
          >
            <text
              x={PAD.l - 6}
              y={PAD.t + 12}
              textAnchor="end"
              fontFamily="var(--font-geist-mono)"
              fontSize="9"
              fontWeight={700}
              letterSpacing="0.18em"
              fill="var(--muted)"
            >
              HOME LEAD
            </text>
            <text
              x={PAD.l - 6}
              y={midY + 4}
              textAnchor="end"
              fontFamily="var(--font-geist-mono)"
              fontSize="10"
              fill="var(--muted)"
            >
              0
            </text>
            <text
              x={PAD.l - 6}
              y={PAD.t + 14}
              textAnchor="end"
              fontFamily="var(--font-geist-mono)"
              fontSize="9"
              fill="var(--muted)"
            >
              +{absMax}
            </text>
            <text
              x={PAD.l - 6}
              y={VIEW_H - PAD.b - 2}
              textAnchor="end"
              fontFamily="var(--font-geist-mono)"
              fontSize="9"
              fill="var(--muted)"
            >
              -{absMax}
            </text>

            <line
              x1={PAD.l}
              x2={VIEW_W - PAD.r}
              y1={midY}
              y2={midY}
              stroke="rgba(53,41,33,0.28)"
              strokeWidth="0.8"
            />

            {quarterMarks.map((q) => (
              <g key={`qmark-${q}`}>
                <line
                  x1={x(q)}
                  x2={x(q)}
                  y1={PAD.t}
                  y2={VIEW_H - PAD.b}
                  stroke="rgba(53,41,33,0.14)"
                  strokeDasharray="2 4"
                />
                <text
                  x={x(q)}
                  y={VIEW_H - 10}
                  textAnchor="middle"
                  fontFamily="var(--font-geist-mono)"
                  fontSize="10"
                  fill="var(--muted)"
                >
                  Q{q / 12}
                </text>
              </g>
            ))}
            <text
              x={x(0)}
              y={VIEW_H - 10}
              textAnchor="middle"
              fontFamily="var(--font-geist-mono)"
              fontSize="10"
              fill="var(--muted)"
            >
              TIP
            </text>
            <text
              x={x(totalMinutes)}
              y={VIEW_H - 10}
              textAnchor="middle"
              fontFamily="var(--font-geist-mono)"
              fontSize="10"
              fill="var(--muted)"
            >
              FINAL
            </text>

            {data.map((p) => {
              const lead = p.home_lead;
              const h = Math.abs(lead) * yScale;
              const top = lead >= 0 ? midY - h : midY;
              const fill =
                lead >= 0 ? "var(--accent)" : "var(--danger-ink)";
              return (
                <rect
                  key={`lead-${p.minute}`}
                  x={x(p.minute) - barWidth / 2}
                  y={top}
                  width={barWidth}
                  height={Math.max(0.4, h)}
                  fill={fill}
                  opacity={Math.abs(lead) === 0 ? 0 : 0.92}
                />
              );
            })}
          </svg>
        </div>
      ) : (
        <div
          className="rounded-[1.4rem] border border-dashed px-5 py-10 text-center"
          style={{
            borderColor: "var(--border-strong)",
            background: "rgba(252,255,253,0.4)",
          }}
        >
          <p
            className="text-sm italic"
            style={{ fontFamily: "var(--font-display)", color: "var(--muted)" }}
          >
            Per-minute lead trace not yet available for this game.
          </p>
        </div>
      )}
    </section>
  );
}
