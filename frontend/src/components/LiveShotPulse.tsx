"use client";

import { useEffect, useState } from "react";

type Shot = { x: number; y: number; made: boolean; id: number };

const SEED: { x: number; y: number; made: boolean }[] = [
  { x: 50, y: 165, made: true },
  { x: 62, y: 158, made: false },
  { x: 30, y: 70, made: true },
  { x: 70, y: 90, made: true },
  { x: 22, y: 140, made: false },
  { x: 88, y: 110, made: true },
  { x: 55, y: 55, made: false },
  { x: 14, y: 50, made: true },
  { x: 100, y: 165, made: false },
  { x: 78, y: 165, made: true },
];

interface LiveShotPulseProps {
  width?: number;
  height?: number;
}

export default function LiveShotPulse({ width = 280, height = 200 }: LiveShotPulseProps) {
  const [shots, setShots] = useState<Shot[]>([]);

  useEffect(() => {
    let i = 0;
    const id = setInterval(() => {
      setShots((arr) => {
        const seed = SEED[i % SEED.length];
        const next: Shot[] = [...arr, { ...seed, id: Date.now() + i }];
        return next.slice(-12);
      });
      i++;
    }, 700);
    return () => clearInterval(id);
  }, []);

  return (
    <svg
      viewBox="0 0 120 200"
      width={width}
      height={height}
      style={{
        display: "block",
        borderRadius: 18,
        background: "linear-gradient(180deg, #f4ecde 0%, #ead7b6 100%)",
        border: "1px solid rgba(33,72,59,0.18)",
      }}
    >
      <style>{`
        @keyframes cv-shot-pop  { from { r: 0; opacity: 1; } to { r: 8;   opacity: 0; } }
        @keyframes cv-shot-mark { from { r: 0; opacity: 0; } to { r: 2.2; opacity: 1; } }
      `}</style>
      <rect x="40" y="120" width="40" height="78" fill="none" stroke="rgba(33,72,59,0.4)" strokeWidth="0.6" />
      <circle cx="60" cy="160" r="14" fill="none" stroke="rgba(33,72,59,0.4)" strokeWidth="0.6" />
      <path d="M 6 200 L 6 138 A 54 54 0 0 1 114 138 L 114 200" fill="none" stroke="rgba(33,72,59,0.4)" strokeWidth="0.6" />
      <circle cx="60" cy="180" r="1.4" fill="#b4893d" />
      {shots.map((s) => (
        <g key={s.id}>
          <circle
            cx={s.x}
            cy={s.y}
            r="2.2"
            fill={s.made ? "#21483b" : "#a7484a"}
            style={{ animation: "cv-shot-mark 360ms ease-out both" }}
          />
          <circle
            cx={s.x}
            cy={s.y}
            fill="none"
            stroke={s.made ? "#21483b" : "#a7484a"}
            strokeWidth="0.5"
            style={{ animation: "cv-shot-pop 1100ms ease-out forwards" }}
          />
        </g>
      ))}
    </svg>
  );
}
