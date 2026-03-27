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
      <div className="text-center py-20">
        <h2 className="text-2xl font-bold mb-2">Invalid Player ID</h2>
        <p className="text-gray-500">Please search for a valid player.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
        >
          ← Back to Home
        </Link>
      </div>
      <PlayerDashboard playerId={id} />
    </div>
  );
}
