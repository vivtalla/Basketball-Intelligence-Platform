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

  return <PlayerDashboard playerId={id} />;
}
