"use client";

import Image from "next/image";
import Link from "next/link";
import { useFavorites } from "@/hooks/useFavorites";

export default function FavoritesList() {
  const { favorites, toggleFavorite } = useFavorites();

  if (favorites.length === 0) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="bip-display text-2xl font-semibold text-[var(--foreground)]">
          My Players
        </h2>
        <span className="text-xs text-[var(--muted)]">
          Saved to this browser
        </span>
      </div>

      <div className="flex flex-wrap gap-3">
        {favorites.map((player) => (
          <div
            key={player.id}
            className="group bip-panel flex items-center gap-3 rounded-[1.4rem] px-4 py-3 hover:border-[var(--border-strong)]"
          >
            <div className="relative w-9 h-9 rounded-full overflow-hidden bg-[var(--surface-alt)] shrink-0">
              {player.headshot_url && (
                <Image
                  src={player.headshot_url}
                  alt={player.name}
                  fill
                  className="object-cover object-top"
                  unoptimized
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
              )}
            </div>

            <div className="min-w-0">
              <Link
                href={`/players/${player.id}`}
                className="block text-sm font-medium text-[var(--foreground)] bip-link truncate"
              >
                {player.name}
              </Link>
              <p className="text-xs text-[var(--muted)] truncate">
                {player.team || "Free Agent"}
              </p>
            </div>

            <button
              onClick={() => toggleFavorite(player)}
              title="Remove from My Players"
              className="ml-1 opacity-0 group-hover:opacity-100 transition-opacity text-[var(--muted)] hover:text-[var(--danger-ink)]"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="w-4 h-4"
              >
                <path d="M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 1 0 1.06 1.06L10 11.06l3.72 3.72a.75.75 0 1 0 1.06-1.06L11.06 10l3.72-3.72a.75.75 0 0 0-1.06-1.06L10 8.94 6.28 5.22Z" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
