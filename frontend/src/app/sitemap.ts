import type { MetadataRoute } from "next";

/**
 * Sprint 83 (B3): static sitemap covering the public marketing + workspace
 * surfaces. Per-player and per-team detail pages are intentionally NOT
 * enumerated here — they're long-tail and best discovered via internal
 * links + the search bar, not the sitemap.
 */
const BASE_URL = "https://courtvue.app";

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  const staticRoutes = [
    "",
    "/leaderboards",
    "/standings",
    "/compare",
    "/teams",
    "/learn",
    "/draft",
    "/free-agency",
    "/trade-machine",
    "/mvp",
    "/playoffs",
    "/player-stats",
    "/metrics",
    "/milestones",
    "/picks",
    "/ask",
    "/pre-read",
    "/insights",
    "/coverage",
    "/bracket",
  ];

  return staticRoutes.map((route) => ({
    url: `${BASE_URL}${route}`,
    lastModified,
    changeFrequency: route === "" ? "daily" : "weekly",
    priority: route === "" ? 1.0 : 0.7,
  }));
}
