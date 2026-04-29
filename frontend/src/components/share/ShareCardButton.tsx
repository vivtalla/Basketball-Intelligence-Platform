"use client";

/**
 * Sprint 78 (CF1): ShareCardButton.
 *
 * Pill-styled button that opens the corresponding /api/share/{kind}/...png
 * endpoint in a new tab so the user can save the broadsheet share card.
 * The button is intentionally tiny — meant to live in headers, card
 * corners, and panel chrome rather than dominating any layout.
 *
 * Usage:
 *   <ShareCardButton kind="player" id="1628369" season="2024-25" />
 *   <ShareCardButton kind="game"   id="0042500111" />
 *   <ShareCardButton kind="series" id="2025-26-W-R1-OKC-IND" compact />
 *   <ShareCardButton kind="milestone" id="1628369" milestoneKey="20k-points" />
 *
 * The href resolves against ``NEXT_PUBLIC_API_URL`` so it works in dev,
 * preview, and production without per-environment URL building.
 */

import { useMemo } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ShareKind = "player" | "game" | "series" | "milestone";

export interface ShareCardButtonProps {
  /** Which share endpoint to hit. */
  kind: ShareKind;
  /** Primary id (player_id, game_id, series_id, or player_id for milestone). */
  id: string | number;
  /** Player season — used only when kind === "player". */
  season?: string;
  /** Milestone key — used only when kind === "milestone". */
  milestoneKey?: string;
  /** When true, render only the icon — fits in a card corner. */
  compact?: boolean;
  /** Optional extra className passed through to the anchor. */
  className?: string;
}

function buildHref(props: ShareCardButtonProps): string {
  const id = encodeURIComponent(String(props.id));
  switch (props.kind) {
    case "player": {
      const qs = props.season ? `?season=${encodeURIComponent(props.season)}` : "";
      return `${API_BASE}/api/share/player/${id}.png${qs}`;
    }
    case "game":
      return `${API_BASE}/api/share/game/${id}.png`;
    case "series":
      return `${API_BASE}/api/share/series/${id}.png`;
    case "milestone": {
      const key = encodeURIComponent(props.milestoneKey ?? "milestone");
      return `${API_BASE}/api/share/milestone/${id}/${key}.png`;
    }
  }
}

function ShareIcon({ size = 14 }: { size?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <circle cx="18" cy="5" r="3" />
      <circle cx="6" cy="12" r="3" />
      <circle cx="18" cy="19" r="3" />
      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
      <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
    </svg>
  );
}

export default function ShareCardButton(props: ShareCardButtonProps) {
  const href = useMemo(() => buildHref(props), [props]);
  const label =
    props.kind === "player"
      ? "Share player card"
      : props.kind === "game"
        ? "Share game card"
        : props.kind === "series"
          ? "Share series card"
          : "Share milestone card";

  if (props.compact) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={label}
        title={label}
        className={`inline-flex items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface-alt)] hover:bg-[var(--accent)] hover:text-[var(--surface)] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--accent)] ${props.className ?? ""}`}
        style={{ width: 28, height: 28, color: "var(--muted)" }}
      >
        <ShareIcon size={14} />
      </a>
    );
  }

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={label}
      title={label}
      className={`inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface-alt)] px-3 py-1.5 text-xs font-medium text-[var(--foreground)] hover:bg-[var(--accent)] hover:text-[var(--surface)] hover:border-[var(--accent)] transition-colors focus:outline-none focus:ring-2 focus:ring-[var(--accent)] ${props.className ?? ""}`}
      style={{
        fontFamily: "var(--font-geist-mono)",
        letterSpacing: "0.06em",
        textTransform: "uppercase",
      }}
    >
      <ShareIcon size={13} />
      Share card
    </a>
  );
}
