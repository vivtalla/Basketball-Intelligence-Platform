import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import NavSearch from "@/components/NavSearch";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Basketball Intelligence Platform",
  description: "NBA player analytics and advanced statistics dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="bip-shell min-h-full flex flex-col text-[var(--foreground)]">
        {/* Nav */}
        <nav className="sticky top-0 z-40 border-b border-[var(--border)] bg-[rgba(247,239,228,0.86)] backdrop-blur-xl">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2 shrink-0">
              <span className="bip-display text-2xl font-bold tracking-tight text-[var(--foreground)]">BIP</span>
              <span className="text-sm text-[var(--muted)] hidden lg:inline">
                Basketball Intelligence Platform
              </span>
            </Link>
            <NavSearch />
            <div className="hidden md:flex items-center gap-5">
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
                href="/compare"
                className="text-sm text-[var(--muted)] bip-link"
              >
                Compare
              </Link>
              <Link
                href="/leaderboards"
                className="text-sm text-[var(--muted)] bip-link"
              >
                Leaderboards
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
          Basketball Intelligence Platform · Hardwood Editorial prototype · Data from NBA.com
        </footer>
      </body>
    </html>
  );
}
