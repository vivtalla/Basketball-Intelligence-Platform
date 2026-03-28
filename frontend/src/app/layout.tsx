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
      <body className="min-h-full flex flex-col bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
        {/* Nav */}
        <nav className="border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900">
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2 shrink-0">
              <span className="text-xl font-bold tracking-tight">BIP</span>
              <span className="text-sm text-gray-500 hidden md:inline">
                Basketball Intelligence Platform
              </span>
            </Link>
            <NavSearch />
            <div className="flex items-center gap-5">
              <Link
                href="/standings"
                className="text-sm text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
              >
                Standings
              </Link>
              <Link
                href="/insights"
                className="text-sm text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
              >
                Insights
              </Link>
              <Link
                href="/compare"
                className="text-sm text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
              >
                Compare
              </Link>
              <Link
                href="/leaderboards"
                className="text-sm text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
              >
                Leaderboards
              </Link>
              <Link
                href="/teams"
                className="text-sm text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
              >
                Teams
              </Link>
              <Link
                href="/coverage"
                className="text-sm text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
              >
                Coverage
              </Link>
              <Link
                href="/learn"
                className="text-sm text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
              >
                Learn
              </Link>
            </div>
          </div>
        </nav>

        {/* Main */}
        <main className="flex-grow max-w-7xl mx-auto w-full px-4 py-8">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-gray-200 dark:border-gray-800 py-4 text-center text-sm text-gray-400">
          Basketball Intelligence Platform — Data from NBA.com
        </footer>
      </body>
    </html>
  );
}
