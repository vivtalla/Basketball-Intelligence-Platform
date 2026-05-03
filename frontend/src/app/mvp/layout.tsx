import type { Metadata } from "next";

/**
 * Sprint 86 D — server-only layout that owns OG metadata for /mvp.
 * The page is a "use client" component, so `generateMetadata` must live
 * in a sibling layout. The OG card pulls the latest race standings via
 * the parameterized `/og?type=mvp` route; season is omitted so the route
 * resolves to whatever the API currently considers the active season.
 */
export async function generateMetadata(): Promise<Metadata> {
  const ogUrl = "/og?type=mvp";
  return {
    title: "MVP Race · CourtVue Labs",
    openGraph: {
      title: "MVP Race · CourtVue Labs",
      images: [
        {
          url: ogUrl,
          width: 1200,
          height: 630,
          alt: "CourtVue MVP race share card",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      images: [ogUrl],
    },
  };
}

export default function MvpLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
