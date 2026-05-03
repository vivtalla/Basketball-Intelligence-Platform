// Sprint 88 (D) — ISR for /leaderboards. Daily-synced data; cache HTML for 1hr
// at the Vercel edge, revalidate in background. SWR on the client picks up live
// changes when filters change. Page is "use client" so revalidate must live in
// this sibling layout.
export const revalidate = 3600;

export default function LeaderboardsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
