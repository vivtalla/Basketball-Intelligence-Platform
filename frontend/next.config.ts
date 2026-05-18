import type { NextConfig } from "next";
// eslint-disable-next-line @typescript-eslint/no-require-imports
const withBundleAnalyzer = require("@next/bundle-analyzer")({
  enabled: process.env.ANALYZE === "1",
});

// Sprint 96: routes migrated under /beta/. 308 redirects preserve external
// bookmarks + share URLs while the UI graduates back to root one page at a
// time. Source uses :path* so dynamic sub-routes (e.g. /teams/LAL,
// /players/123) follow their parent into /beta/.
const BETA_ROUTES = [
  "ask",
  "compare",
  "coverage",
  "free-agency",
  "games",
  "insights",
  "leaderboards",
  "learn",
  "lineups",
  "metrics",
  "milestones",
  "mvp",
  "picks",
  "players",
  "playoff-series",
  "pre-read",
  "teams",
  "trade-machine",
];

// Sprint 101: routes graduated from /beta/ back to root. Reverse redirect
// preserves external bookmarks pointing at the old /beta/<route>/* URLs.
const GRADUATED_ROUTES = [
  "draft",
];

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "cdn.nba.com",
      },
    ],
  },
  async redirects() {
    const betaIn = BETA_ROUTES.flatMap((route) => [
      {
        source: `/${route}`,
        destination: `/beta/${route}`,
        permanent: true,
      },
      {
        source: `/${route}/:path*`,
        destination: `/beta/${route}/:path*`,
        permanent: true,
      },
    ]);
    const graduatedOut = GRADUATED_ROUTES.flatMap((route) => [
      {
        source: `/beta/${route}`,
        destination: `/${route}`,
        permanent: true,
      },
      {
        source: `/beta/${route}/:path*`,
        destination: `/${route}/:path*`,
        permanent: true,
      },
    ]);
    return [...betaIn, ...graduatedOut];
  },
};

export default withBundleAnalyzer(nextConfig);
