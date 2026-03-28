"use client";

import { useState, useCallback } from "react";

const STORAGE_KEY = "bip_favorites";

export interface FavoritePlayer {
  id: number;
  name: string;
  team: string;
  headshot_url: string | null;
}

function load(): FavoritePlayer[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as FavoritePlayer[]) : [];
  } catch {
    return [];
  }
}

function save(players: FavoritePlayer[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(players));
}

export function useFavorites() {
  const [favorites, setFavorites] = useState<FavoritePlayer[]>(() => load());

  const isFavorite = useCallback(
    (id: number) => favorites.some((f) => f.id === id),
    [favorites]
  );

  const addFavorite = useCallback((player: FavoritePlayer) => {
    setFavorites((prev) => {
      if (prev.some((f) => f.id === player.id)) return prev;
      const next = [...prev, player];
      save(next);
      return next;
    });
  }, []);

  const removeFavorite = useCallback((id: number) => {
    setFavorites((prev) => {
      const next = prev.filter((f) => f.id !== id);
      save(next);
      return next;
    });
  }, []);

  const toggleFavorite = useCallback(
    (player: FavoritePlayer) => {
      if (isFavorite(player.id)) {
        removeFavorite(player.id);
      } else {
        addFavorite(player);
      }
    },
    [isFavorite, addFavorite, removeFavorite]
  );

  return { favorites, isFavorite, toggleFavorite };
}
