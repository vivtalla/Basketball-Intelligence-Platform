import { ImageResponse } from "next/og";

export const runtime = "edge";
export const contentType = "image/png";
export const size = { width: 1200, height: 630 };

// Sprint 83 follow-up: home-page Open Graph card.
// Generated at request time via next/og (Satori). Uses the same brand mark
// (courtvue-mark.svg) + palette as the site nav so social previews stay
// visually consistent with what visitors land on.
//
// Cache-friendly: Vercel and Cloudflare cache by URL; the response includes
// `Cache-Control: public, immutable, no-transform, max-age=31536000` by default.
export async function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          background:
            "linear-gradient(135deg, #fff9f1 0%, #f3e8d4 55%, #e7d4ad 100%)",
          padding: "70px 90px",
          position: "relative",
        }}
      >
        {/* Subtle hardwood grain stripes via repeated linear gradients */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            background:
              "repeating-linear-gradient(90deg, rgba(180,137,61,0.04) 0px, rgba(180,137,61,0.04) 2px, transparent 2px, transparent 28px)",
            pointerEvents: "none",
          }}
        />

        {/* Hairline border */}
        <div
          style={{
            position: "absolute",
            inset: 24,
            border: "1px solid rgba(32,26,22,0.18)",
            borderRadius: 24,
            display: "flex",
          }}
        />

        {/* Top kicker line */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 14,
            zIndex: 2,
            color: "#21483b",
            fontSize: 22,
            fontWeight: 700,
            letterSpacing: "0.32em",
            textTransform: "uppercase",
          }}
        >
          <span style={{ display: "flex" }}>EST. 2025</span>
          <span
            style={{
              display: "flex",
              flex: 1,
              height: 1,
              background: "rgba(32,26,22,0.25)",
              alignSelf: "center",
            }}
          />
          <span style={{ display: "flex" }}>NBA INTELLIGENCE</span>
        </div>

        {/* Brand mark + wordmark cluster */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 36,
            marginTop: 80,
            zIndex: 2,
          }}
        >
          {/* Inline brand mark — geometry mirrors /public/courtvue-mark.svg */}
          <svg width="220" height="220" viewBox="0 0 96 96" style={{ flexShrink: 0 }}>
            <circle cx="48" cy="48" r="36" fill="none" stroke="#201a16" strokeWidth="3" />
            <circle cx="48" cy="48" r="22" fill="none" stroke="#201a16" strokeWidth="1.4" opacity="0.45" />
            <line x1="6" y1="48" x2="32" y2="48" stroke="#201a16" strokeWidth="3" strokeLinecap="square" />
            <line x1="64" y1="48" x2="90" y2="48" stroke="#201a16" strokeWidth="3" strokeLinecap="square" />
            <path
              d="M 44 30 L 44 40 L 38 60 Q 38 64 42 64 L 54 64 Q 58 64 58 60 L 52 40 L 52 30 Z"
              fill="#fff9f1"
              stroke="#21483b"
              strokeWidth="2"
              strokeLinejoin="round"
            />
            <line x1="42" y1="30" x2="54" y2="30" stroke="#21483b" strokeWidth="2" strokeLinecap="round" />
            <path
              d="M 39 54 Q 41 52 44 54 T 50 54 T 57 54 L 57 60 Q 57 62 55 62 L 41 62 Q 39 62 39 60 Z"
              fill="#b4893d"
            />
          </svg>

          <div style={{ display: "flex", flexDirection: "column" }}>
            <div
              style={{
                color: "#201a16",
                fontSize: 130,
                fontWeight: 800,
                letterSpacing: "-0.04em",
                lineHeight: 1,
                display: "flex",
              }}
            >
              CourtVue
            </div>
            <div
              style={{
                color: "#21483b",
                fontSize: 50,
                fontWeight: 600,
                letterSpacing: "0.32em",
                marginTop: 12,
                textTransform: "uppercase",
                display: "flex",
              }}
            >
              Labs
            </div>
          </div>
        </div>

        {/* Tagline + footer cluster */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            marginTop: "auto",
            zIndex: 2,
          }}
        >
          <div
            style={{
              color: "#201a16",
              fontSize: 38,
              fontWeight: 500,
              lineHeight: 1.25,
              maxWidth: 940,
              display: "flex",
            }}
          >
            Search any NBA player. Compare careers. Track team rotations. Build your own metrics.
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 18,
              marginTop: 28,
              color: "#21483b",
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: "0.28em",
              textTransform: "uppercase",
            }}
          >
            <span style={{ display: "flex" }}>courtvue.app</span>
            <span
              style={{
                display: "flex",
                width: 8,
                height: 8,
                borderRadius: 4,
                background: "#b4893d",
              }}
            />
            <span style={{ display: "flex" }}>Front offices &middot; Serious fans</span>
          </div>
        </div>
      </div>
    ),
    { ...size }
  );
}
