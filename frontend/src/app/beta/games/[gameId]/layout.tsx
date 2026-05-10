import type { Metadata } from "next";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Sprint 78 (CF1): server-only layout that owns the OG metadata for
 * /games/[gameId]. The page itself is a "use client" component, so we
 * cannot export `metadata` from it directly — Next.js metadata APIs
 * are restricted to server components.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ gameId: string }>;
}): Promise<Metadata> {
  const { gameId } = await params;
  const ogUrl = `${API_BASE}/api/share/game/${encodeURIComponent(gameId)}.png`;
  return {
    title: `Game ${gameId} · CourtVue Labs`,
    openGraph: {
      title: `Game ${gameId} · CourtVue Labs`,
      images: [
        {
          url: ogUrl,
          width: 1200,
          height: 630,
          alt: "CourtVue game share card",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      images: [ogUrl],
    },
  };
}

export default function GameLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
