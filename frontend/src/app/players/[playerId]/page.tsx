import Link from "next/link";
import PlayerDashboard from "@/components/PlayerDashboard";

export default async function PlayerPage({
  params,
}: {
  params: Promise<{ playerId: string }>;
}) {
  const { playerId } = await params;
  const id = parseInt(playerId, 10);

  if (isNaN(id)) {
    return (
      <div className="bip-panel mx-auto max-w-3xl rounded-[2rem] px-8 py-20 text-center">
        <h2 className="bip-display text-3xl font-bold mb-2">Invalid Player ID</h2>
        <p className="text-[var(--muted)]">Please search for a valid player.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-[var(--muted)] bip-link"
        >
          ← Back to Home
        </Link>
      </div>
      <PlayerDashboard playerId={id} />
    </div>
  );
}
