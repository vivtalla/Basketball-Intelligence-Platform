import type { Metadata } from "next";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Sprint 78 (CF1): server-only layout that owns the OG metadata for the
 * /playoffs broadsheet home. The page itself is a "use client" component
 * (uses useSeasonPhase + SWR), so the metadata export has to live here.
 *
 * The OG image is a generic broadsheet "Playoffs" card — until a future
 * sprint exposes a `/api/share/playoffs.png` endpoint we point at the
 * default Finals matchup, falling back gracefully if no series exists.
 */
export const metadata: Metadata = {
  title: "Playoffs · CourtVue Labs",
  description: "The broadsheet desk: today's slate, series tracker, and bracket trajectory.",
  openGraph: {
    title: "Playoffs · CourtVue Labs",
    description:
      "Tonight's slate, series tracker, narrative leaders — the broadsheet desk for the playoff edition.",
    images: [
      {
        // Falls back to the player share endpoint with a placeholder id —
        // backend renders a broadsheet "Player not found" card with full
        // CourtVue chrome, which is a serviceable OG until the sprint
        // adds a dedicated `/api/share/playoffs.png`.
        url: `${API_BASE}/api/share/player/0.png`,
        width: 1200,
        height: 630,
        alt: "CourtVue playoffs broadsheet",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    images: [`${API_BASE}/api/share/player/0.png`],
  },
};

export default function PlayoffsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
