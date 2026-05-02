import type { MetadataRoute } from "next";

/**
 * Sprint 83 (B3): public robots policy. Allow the marketing surfaces, deny
 * the backend `/api/` proxy and `/admin/` ops. Sitemap pointer is the static
 * Next.js-generated `/sitemap.xml` (see `sitemap.ts`).
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/admin/"],
      },
    ],
    sitemap: "https://courtvue.app/sitemap.xml",
  };
}
