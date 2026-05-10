import type { Metadata } from "next";

/**
 * Sprint 86 D — server-only layout that owns OG metadata for
 * /playoff-series/[seriesId]. The page is a "use client" component.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ seriesId: string }>;
}): Promise<Metadata> {
  const { seriesId } = await params;
  const safeId = seriesId ?? "";
  const ogUrl = `/og?type=series&id=${encodeURIComponent(safeId)}`;
  return {
    title: `Series ${safeId} · CourtVue Labs`,
    openGraph: {
      title: `Series ${safeId} · CourtVue Labs`,
      images: [
        {
          url: ogUrl,
          width: 1200,
          height: 630,
          alt: "CourtVue playoff series share card",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      images: [ogUrl],
    },
  };
}

export default function PlayoffSeriesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
