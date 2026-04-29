import type { Metadata } from "next";
import Link from "next/link";
import NavSearch from "@/components/NavSearch";
import NavLinks from "@/components/NavLinks";
import LiveTicker from "@/components/LiveTicker";
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
