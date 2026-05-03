// Sprint 88 (D) — ISR for /standings. Updates post-game; 30min cache balances
// freshness with backend load.
export const revalidate = 1800;

export default function StandingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
