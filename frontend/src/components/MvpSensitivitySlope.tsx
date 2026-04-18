"use client";

import { useMemo, useState } from "react";
import type { MvpSensitivityResponse } from "@/lib/types";

interface Props {
  data: MvpSensitivityResponse | undefined;
  isLoading?: boolean;
}

const WIDTH = 640;
const HEIGHT = 380;
const MARGIN = { top: 40, right: 140, bottom: 30, left: 40 };

function interpolate(i: number, total: number): string {
  const h = (200 + (i / Math.max(total - 1, 1)) * 140) % 360;
  return `hsl(${h.toFixed(0)}, 60%, 55%)`;
}

export default function MvpSensitivitySlope({ data, isLoading }: Props) {
  const [highlightId, setHighlightId] = useState<number | null>(null);

  const chart = useMemo(() => {
    if (!data) return null;
    const profiles = data.profiles;
    const players = data.players.slice(0, 10);
    if (profiles.length === 0 || players.length === 0) return null;

    const innerW = WIDTH - MARGIN.left - MARGIN.right;
    const innerH = HEIGHT - MARGIN.top - MARGIN.bottom;
    const maxRank = players.length;

    const colX = (i: number) => MARGIN.left + (profiles.length === 1 ? innerW / 2 : (i / (profiles.length - 1)) * innerW);
    const rowY = (rank: number) => MARGIN.top + ((rank - 1) / Math.max(maxRank - 1, 1)) * innerH;

    return { profiles, players, colX, rowY, maxRank };
  }, [data]);

  if (isLoading) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-6 text-xs text-[var(--muted)]">
        Loading sensitivity data…
      </div>
    );
  }
  if (!chart) {
    return (
      <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-6 text-xs text-[var(--muted)]">
        Sensitivity data unavailable.
      </div>
    );
  }

  const { profiles, players, colX, rowY } = chart;

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--accent)]">Ranking Sensitivity</p>
          <h3 className="mt-1 text-sm font-semibold text-[var(--foreground)]">
            How does rank change between Basketball Value, Award Case, and legacy profiles?
          </h3>
          <p className="mt-1 text-xs text-[var(--muted)]">
            Each line is a candidate. The first two columns are the refined v3 scores; the remaining columns preserve legacy profile comparison.
          </p>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-[var(--muted)]">
            Use this as a robustness check: a stable line means the case survives different assumptions, while a steep line shows the candidate depends on a specific way of valuing production, impact, or award modifiers.
          </p>
        </div>
      </div>

      <div className="mt-4 overflow-x-auto">
        <svg width={WIDTH} height={HEIGHT} role="img" aria-label="Ranking sensitivity slope chart">
          {/* column headers */}
          {profiles.map((p, i) => (
            <text
              key={p}
              x={colX(i)}
              y={MARGIN.top - 14}
              textAnchor="middle"
              className="fill-[var(--foreground)]"
              style={{ fontSize: 12, fontWeight: 600 }}
            >
              {data!.profile_labels[p] ?? p}
            </text>
          ))}

          {/* slope lines */}
          {players.map((player, idx) => {
            const color = interpolate(idx, players.length);
            const highlighted = highlightId === player.player_id;
            const dim = highlightId !== null && !highlighted;
            const points = profiles
              .map((p, i) => {
                const rank = player.rank_by_profile[p];
                if (!rank || rank > players.length) return null;
                return `${colX(i)},${rowY(rank)}`;
              })
              .filter(Boolean)
              .join(" ");

            return (
              <g
                key={player.player_id}
                onMouseEnter={() => setHighlightId(player.player_id)}
                onMouseLeave={() => setHighlightId(null)}
                style={{ cursor: "pointer", opacity: dim ? 0.25 : 1 }}
              >
                <polyline points={points} fill="none" stroke={color} strokeWidth={highlighted ? 3 : 1.5} />
                {profiles.map((p, i) => {
                  const rank = player.rank_by_profile[p];
                  if (!rank || rank > players.length) return null;
                  return (
                    <circle
                      key={`${player.player_id}-${p}`}
                      cx={colX(i)}
                      cy={rowY(rank)}
                      r={highlighted ? 5 : 3}
                      fill={color}
                    />
                  );
                })}
              </g>
            );
          })}

          {/* labels on the right */}
          {players.map((player) => {
            const lastProfile = profiles[profiles.length - 1];
            const rank = player.rank_by_profile[lastProfile];
            if (!rank || rank > players.length) return null;
            return (
              <text
                key={`${player.player_id}-label`}
                x={colX(profiles.length - 1) + 10}
                y={rowY(rank) + 4}
                className="fill-[var(--foreground)]"
                style={{ fontSize: 11, fontWeight: highlightId === player.player_id ? 700 : 500 }}
              >
                {player.player_name}
              </text>
            );
          })}
        </svg>
      </div>

      <p className="mt-2 text-[10px] text-[var(--muted)]">
        Profiles shown: {profiles.map((p) => data!.profile_labels[p] ?? p).join(" · ")}. Default: {data!.default_profile}.
      </p>
    </div>
  );
}
