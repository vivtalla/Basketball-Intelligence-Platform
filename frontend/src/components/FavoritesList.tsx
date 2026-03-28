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
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
          My Players
        </h2>
        <span className="text-xs text-gray-400 dark:text-gray-500">
          Saved to this browser
        </span>
      </div>

      <div className="flex flex-wrap gap-3">
        {favorites.map((player) => (
          <div
            key={player.id}
            className="flex items-center gap-3 rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3 hover:border-blue-400 dark:hover:border-blue-500 transition-colors group"
          >
            <div className="relative w-9 h-9 rounded-full overflow-hidden bg-gray-100 dark:bg-gray-700 shrink-0">
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
                className="block text-sm font-medium text-gray-900 dark:text-gray-100 hover:text-blue-500 dark:hover:text-blue-400 transition-colors truncate"
              >
                {player.name}
              </Link>
              <p className="text-xs text-gray-400 dark:text-gray-500 truncate">
                {player.team || "Free Agent"}
              </p>
            </div>

            <button
              onClick={() => toggleFavorite(player)}
              title="Remove from My Players"
              className="ml-1 opacity-0 group-hover:opacity-100 transition-opacity text-gray-300 dark:text-gray-600 hover:text-red-400 dark:hover:text-red-400"
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
