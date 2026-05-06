import type { Metadata } from "next";
import Link from "next/link";
import { Analytics } from "@vercel/analytics/react";
import NavSearch from "@/components/NavSearch";
import NavLinks from "@/components/NavLinks";
import MobileNav from "@/components/MobileNav";
import LiveTicker from "@/components/LiveTicker";
import SWRProvider from "@/components/SWRProvider";
import "./globals.css";

// Sprint 83 (B2): root metadata used as the default + home-page OG/Twitter
// card. Per-route layouts (e.g. `/playoffs/layout.tsx`) override these for
// their own surfaces. The /og endpoint is a dynamic Next.js ImageResponse
// (see frontend/src/app/og/route.tsx) — generates a 1200x630 PNG using the
// same brand mark + palette as the site nav.
export const metadata: Metadata = {
  metadataBase: new URL("https://courtvue.app"),
  title: "CourtVue Labs — NBA basketball intelligence",
  description:
    "Search any NBA player, compare careers, track team rotations, and build your own metrics. Built for front offices and serious fans.",
  openGraph: {
    title: "CourtVue Labs — NBA basketball intelligence",
    description:
      "Search any NBA player, compare careers, track team rotations, and build your own metrics. Built for front offices and serious fans.",
    url: "https://courtvue.app",
    type: "website",
    siteName: "CourtVue Labs",
    images: [
      {
        url: "/og",
        width: 1200,
        height: 630,
        alt: "CourtVue Labs — NBA basketball intelligence",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "CourtVue Labs — NBA basketball intelligence",
    description:
      "Search any NBA player, compare careers, track team rotations, and build your own metrics. Built for front offices and serious fans.",
    images: ["/og"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="bip-shell min-h-full flex flex-col text-[var(--foreground)]">
        <SWRProvider>
          {/* Live game ticker */}
          <LiveTicker />

          {/* Nav */}
          <nav className="sticky top-9 z-40 border-b border-[var(--border)] bg-[rgba(247,239,228,0.86)] backdrop-blur-xl">
            <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-4">
              <Link href="/" className="flex items-center gap-3.5 shrink-0">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/courtvue-mark.svg" alt="" width={56} height={56} />
                <span
                  className="bip-display font-bold text-[var(--foreground)]"
                  style={{ fontSize: 34, letterSpacing: "-0.015em" }}
                >
                  CourtVue <span className="text-[var(--signal)]">Labs</span>
                </span>
              </Link>
              <NavSearch />
              <NavLinks />
              <MobileNav />
            </div>
          </nav>

          {/* Main */}
          <main className="flex-grow max-w-7xl mx-auto w-full px-4 py-8 md:py-10">
            {children}
          </main>

          {/* Footer */}
          <footer className="border-t border-[var(--border)] py-5 text-center text-sm text-[var(--muted)] bg-[rgba(247,239,228,0.78)]">
            CourtVue Labs · The basketball-IQ lab where strategy, analytics, and decisions are built and tested.
          </footer>

          {/* Sprint 83 (B4): Vercel Analytics — no-op outside Vercel deploys. */}
          <Analytics />
        </SWRProvider>
      </body>
    </html>
  );
}
