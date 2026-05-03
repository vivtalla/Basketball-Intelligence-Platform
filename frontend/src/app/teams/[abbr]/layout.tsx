import type { Metadata } from "next";

// Sprint 88 (D) — ISR. Team detail is daily-synced; cache HTML for 1hr at the
// Vercel edge, revalidate in background. SWR on the client picks up live data.
export const revalidate = 3600;

/**
 * Sprint 86 D — server-only layout that owns OG metadata for /teams/[abbr].
 * The page is a "use client" component, so `generateMetadata` lives here.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ abbr: string }>;
}): Promise<Metadata> {
  const { abbr } = await params;
  const safeAbbr = (abbr ?? "").toUpperCase();
  const ogUrl = `/og?type=team&abbr=${encodeURIComponent(safeAbbr)}`;
  return {
    title: `${safeAbbr || "Team"} · CourtVue Labs`,
    openGraph: {
      title: `${safeAbbr || "Team"} · CourtVue Labs`,
      images: [
        {
          url: ogUrl,
          width: 1200,
          height: 630,
          alt: `${safeAbbr || "Team"} share card`,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      images: [ogUrl],
    },
  };
}

export default function TeamLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
