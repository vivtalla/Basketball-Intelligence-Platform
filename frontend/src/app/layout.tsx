import type { Metadata } from "next";
import Link from "next/link";
import NavSearch from "@/components/NavSearch";
import "./globals.css";

export const metadata: Metadata = {
  title: "CourtVue Labs",
  description: "The basketball-IQ lab where strategy, analytics, and decisions are built and tested.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="bip-shell min-h-full flex flex-col text-[var(--foreground)]">
        {/* Nav */}
        <nav className="sticky top-0 z-40 border-b border-[var(--border)] bg-[rgba(247,239,228,0.86)] backdrop-blur-xl">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2 shrink-0">
              <span className="bip-display text-2xl font-bold tracking-tight text-[var(--foreground)]">
                CourtVue <span className="text-[var(--signal)]">Labs</span>
              </span>
            </Link>
            <NavSearch />
            <div className="hidden md:flex items-center gap-5">
              <Link
                href="/ask"
                className="text-sm text-[var(--muted)] bip-link"
              >
                Ask
              </Link>
              <Link
                href="/mvp"
                className="text-sm text-[var(--muted)] bip-link"
              >
                MVP Race
              </Link>
              <Link
                href="/player-stats"
                className="text-sm text-[var(--muted)] bip-link"
              >
                Player Stats
              </Link>
              <Link
                href="/standings"
                className="text-sm text-[var(--muted)] bip-link"
              >
                Standings
              </Link>
              <Link
                href="/insights"
                className="text-sm text-[var(--muted)] bip-link"
              >
                Insights
              </Link>
              <Link
                href="/metrics"
                className="text-sm text-[var(--muted)] bip-link"
              >
                Metrics
              </Link>
              <Link
                href="/compare"
                className="text-sm text-[var(--muted)] bip-link"
              >
                Compare
              </Link>
              <Link
                href="/pre-read"
                className="text-sm text-[var(--muted)] bip-link"
              >
                Pre-Read
              </Link>
              <Link
                href="/teams"
                className="text-sm text-[var(--muted)] bip-link"
              >
                Teams
              </Link>
              <Link
                href="/coverage"
                className="text-sm text-[var(--muted)] bip-link"
              >
                Coverage
              </Link>
              <Link
                href="/learn"
                className="text-sm text-[var(--muted)] bip-link"
              >
                Learn
              </Link>
            </div>
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
      </body>
    </html>
  );
}
