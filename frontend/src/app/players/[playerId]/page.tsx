import type { Metadata } from "next";
import Link from "next/link";
import PlayerDashboard from "@/components/PlayerDashboard";
import ShareCardButton from "@/components/share/ShareCardButton";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ playerId: string }>;
}): Promise<Metadata> {
  const { playerId } = await params;
  const id = parseInt(playerId, 10);
  if (isNaN(id)) {
    return { title: "Player · CourtVue Labs" };
  }
  // Sprint 86 D — point at the parameterized `/og` route so social previews
  // pick up the player-specific brand card (Source Serif/Sans + stat tiles)
  // instead of the legacy `/api/share/player/{id}.png` composition.
  const ogUrl = `/og?type=player&id=${id}`;
  return {
    title: `Player #${id} · CourtVue Labs`,
    openGraph: {
      title: `Player #${id} · CourtVue Labs`,
      images: [
        {
          url: ogUrl,
          width: 1200,
          height: 630,
          alt: "CourtVue player share card",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      images: [ogUrl],
    },
  };
}

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
      <div className="mb-4 flex items-center justify-between gap-3">
        <Link
          href="/"
          className="inline-flex items-center gap-1 text-sm text-[var(--muted)] bip-link"
        >
          ← Back to Home
        </Link>
        <ShareCardButton kind="player" id={id} />
      </div>
      <PlayerDashboard playerId={id} />
    </div>
  );
}
