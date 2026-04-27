"use client";

import { useEffect, useRef, useState } from "react";

export interface LadderTeam {
  rank: number;
  name: string;
  abbr: string;
  color: string;
  w: number;
  l: number;
  change: number;
}

interface StandingsLadderProps {
  teams: LadderTeam[];
  playoffCutoff?: number;
}

export default function StandingsLadder({ teams, playoffCutoff = 6 }: StandingsLadderProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [seen, setSeen] = useState(false);

  useEffect(() => {
    if (!ref.current || seen) return;
    const node = ref.current;
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

  const max = Math.max(...teams.map((t) => t.w), 1);

  return (
    <div ref={ref} style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {teams.map((t, i) => (
        <div
          key={t.abbr}
          style={{
            display: "grid",
            gridTemplateColumns: "32px 56px 1fr 110px 70px 70px",
            gap: 12,
            alignItems: "center",
            padding: "10px 14px",
            background: "rgba(255,249,241,0.86)",
            border: "1px solid var(--border)",
            borderRadius: 14,
            opacity: seen ? 1 : 0,
            transform: seen ? "translateX(0)" : "translateX(-12px)",
            transition: `all 500ms ${i * 70}ms cubic-bezier(0.33,1,0.68,1)`,
          }}
        >
          <div
            style={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: 12,
              color: i < playoffCutoff ? "var(--accent)" : "var(--muted)",
              fontWeight: 700,
            }}
          >
            {String(t.rank).padStart(2, "0")}
          </div>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: t.color,
              color: "#fff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: "var(--font-geist-mono)",
              fontWeight: 700,
              fontSize: 11,
              letterSpacing: "0.04em",
            }}
          >
            {t.abbr}
          </div>
          <div style={{ fontFamily: "var(--font-display)", fontSize: 14, fontWeight: 600 }}>{t.name}</div>
          <div style={{ position: "relative", height: 6, background: "#f2e8d4", borderRadius: 999, overflow: "hidden" }}>
            <div
              style={{
                position: "absolute",
                inset: 0,
                width: seen ? `${(t.w / max) * 100}%` : "0%",
                background: t.color,
                transition: `width 900ms ${i * 60}ms cubic-bezier(0.33,1,0.68,1)`,
                borderRadius: 999,
              }}
            />
          </div>
          <div
            style={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: 12,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {t.w}–{t.l}
          </div>
          <div
            style={{
              fontFamily: "var(--font-geist-mono)",
              fontSize: 11,
              color:
                t.change > 0
                  ? "var(--success-ink)"
                  : t.change < 0
                  ? "var(--danger-ink)"
                  : "var(--muted)",
              fontVariantNumeric: "tabular-nums",
              textAlign: "right",
            }}
          >
            {t.change > 0 ? `▲${t.change}` : t.change < 0 ? `▼${Math.abs(t.change)}` : "—"}
          </div>
        </div>
      ))}
    </div>
  );
}
