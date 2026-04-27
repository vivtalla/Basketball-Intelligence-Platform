"use client";

import { useEffect, useState } from "react";

type TickerGame = {
  home: { abbr: string; color: string; score: number };
  away: { abbr: string; color: string; score: number };
  status: string;
  live: boolean;
};

const GAMES: TickerGame[] = [
  { home: { abbr: "OKC", color: "#0072ce", score: 84 }, away: { abbr: "DEN", color: "#0e2240", score: 79 }, status: "Q3 4:12", live: true },
  { home: { abbr: "BOS", color: "#007a33", score: 32 }, away: { abbr: "NYK", color: "#f58426", score: 28 }, status: "Q2 1:48", live: true },
  { home: { abbr: "DAL", color: "#00538c", score: 112 }, away: { abbr: "LAL", color: "#552583", score: 119 }, status: "FINAL", live: false },
  { home: { abbr: "GSW", color: "#1d428a", score: 56 }, away: { abbr: "MIN", color: "#0c2340", score: 61 }, status: "Q3 9:22", live: true },
  { home: { abbr: "MIA", color: "#98002e", score: 102 }, away: { abbr: "PHI", color: "#006bb6", score: 98 }, status: "FINAL", live: false },
  { home: { abbr: "MIL", color: "#00471b", score: 24 }, away: { abbr: "IND", color: "#fdbb30", score: 30 }, status: "Q2 6:01", live: true },
  { home: { abbr: "PHX", color: "#1d1160", score: 91 }, away: { abbr: "MEM", color: "#5d76a9", score: 88 }, status: "Q4 2:34", live: true },
  { home: { abbr: "TOR", color: "#ce1141", score: 66 }, away: { abbr: "ORL", color: "#0077c0", score: 71 }, status: "Q3 5:55", live: true },
];

export default function LiveTicker() {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 4000);
    return () => clearInterval(id);
  }, []);

  const games = GAMES.map((g, i) => {
    if (!g.live) return g;
    const bumpHome = (tick + i) % 7 === 0;
    const bumpAway = (tick + i) % 5 === 0;
    return {
      ...g,
      home: { ...g.home, score: g.home.score + (bumpHome ? 2 : 0) + (bumpHome && (tick + i) % 11 === 0 ? 1 : 0) },
      away: { ...g.away, score: g.away.score + (bumpAway ? 2 : 0) + (bumpAway && (tick + i) % 13 === 0 ? 1 : 0) },
    };
  });
  const doubled = [...games, ...games];

  return (
    <div
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        background: "linear-gradient(180deg, #1d1612 0%, #2a201a 100%)",
        borderBottom: "1px solid rgba(180,137,61,0.32)",
        overflow: "hidden",
        height: 36,
      }}
    >
      <style>{`
        @keyframes cv-ticker-scroll { from { transform: translateX(0); } to { transform: translateX(-50%); } }
        @keyframes cv-live-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
        .cv-ticker-track { animation: cv-ticker-scroll 90s linear infinite; }
        .cv-ticker-track:hover { animation-play-state: paused; }
        .cv-live-dot { animation: cv-live-pulse 1.4s ease-in-out infinite; }
      `}</style>
      <div
        className="cv-ticker-track"
        style={{ display: "flex", whiteSpace: "nowrap", height: "100%", alignItems: "center", width: "fit-content" }}
      >
        {doubled.map((g, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "0 22px",
              borderRight: "1px solid rgba(180,137,61,0.16)",
              height: "100%",
              color: "#f4ecde",
              fontFamily: "var(--font-geist-mono)",
              fontSize: 11.5,
              letterSpacing: "0.04em",
            }}
          >
            {g.live && (
              <span
                className="cv-live-dot"
                style={{ width: 6, height: 6, borderRadius: "50%", background: "#e85b3c", marginRight: 2, flexShrink: 0 }}
              />
            )}
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: g.away.color }} />
              <span style={{ fontWeight: 700 }}>{g.away.abbr}</span>
              <span
                style={{
                  color: g.away.score > g.home.score ? "#f4ecde" : "rgba(244,236,222,0.55)",
                  fontVariantNumeric: "tabular-nums",
                  fontWeight: 700,
                  minWidth: 26,
                  textAlign: "right",
                }}
              >
                {g.away.score}
              </span>
            </span>
            <span style={{ opacity: 0.4 }}>·</span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: g.home.color }} />
              <span style={{ fontWeight: 700 }}>{g.home.abbr}</span>
              <span
                style={{
                  color: g.home.score > g.away.score ? "#f4ecde" : "rgba(244,236,222,0.55)",
                  fontVariantNumeric: "tabular-nums",
                  fontWeight: 700,
                  minWidth: 26,
                  textAlign: "right",
                }}
              >
                {g.home.score}
              </span>
            </span>
            <span
              style={{
                marginLeft: 10,
                color: g.live ? "#b4893d" : "rgba(244,236,222,0.55)",
                fontSize: 10,
                letterSpacing: "0.1em",
                fontWeight: 700,
              }}
            >
              {g.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
