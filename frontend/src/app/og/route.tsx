/**
 * Sprint 86 Stream D — Open Graph image route.
 *
 * Renders 1200x630 PNGs at request time via `next/og` (Satori). Vercel and
 * Cloudflare cache the response by URL, so per-page cards become effectively
 * free after the first request.
 *
 * Query params:
 *   ?type=home                 (default) — brand card
 *   ?type=player&id=2544       — player card
 *   ?type=team&abbr=BOS        — team card
 *   ?type=series&id=...        — playoff series card
 *   ?type=mvp&season=2024-25   — MVP race card
 *
 * Per-type renderers fetch their data server-side from the existing API.
 * Each renderer falls back to a graceful brand-only card when the upstream
 * fetch fails — never throws so the social preview never 404s.
 *
 * Custom fonts (Source Serif 4 + Source Sans 3) are loaded from
 * `/public/fonts/`. If any font file is missing the route degrades to
 * Satori's default Inter — build still succeeds, visual identity reverts
 * to the Sprint 83 baseline. See `/public/fonts/README.md` for sourcing.
 *
 * Note on runtime: this route uses the Node runtime (not edge) so it can
 * read public/ asset files via the `new URL(..., import.meta.url)` pattern
 * AND so server-side data fetches stay reliable during the build phase.
 */

import { ImageResponse } from "next/og";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

export const runtime = "nodejs";
export const contentType = "image/png";
export const size = { width: 1200, height: 630 };
export const dynamic = "force-dynamic";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "https://api.courtvue.app";

// --- Brand palette -------------------------------------------------------
const COLORS = {
  bgFrom: "#fff9f1",
  bgMid: "#f3e8d4",
  bgTo: "#e7d4ad",
  ink: "#201a16",
  forest: "#21483b",
  forestDeep: "#163128",
  brass: "#b4893d",
  border: "rgba(32,26,22,0.18)",
  hairline: "rgba(32,26,22,0.25)",
  silhouette: "rgba(33,72,59,0.06)",
  silhouetteStrong: "rgba(33,72,59,0.10)",
} as const;

const FONT_SERIF = "Source Serif 4";
const FONT_SANS = "Source Sans 3";

// --- Font loading --------------------------------------------------------
type LoadedFont = {
  name: string;
  data: ArrayBuffer;
  weight: 400 | 700;
  style: "normal";
};

async function tryReadFont(filename: string): Promise<ArrayBuffer | null> {
  try {
    const path = join(process.cwd(), "public", "fonts", filename);
    const buf = await readFile(path);
    // Convert Buffer to a true ArrayBuffer slice that Satori accepts.
    return buf.buffer.slice(
      buf.byteOffset,
      buf.byteOffset + buf.byteLength
    ) as ArrayBuffer;
  } catch {
    return null;
  }
}

async function tryReadFontAnyExt(base: string): Promise<ArrayBuffer | null> {
  // Prefer .woff2 (smaller), fall back to .ttf (Satori accepts both)
  return (await tryReadFont(`${base}.woff2`)) ?? (await tryReadFont(`${base}.ttf`));
}

async function loadFonts(): Promise<LoadedFont[]> {
  const [serifBold, sansRegular, sansBold] = await Promise.all([
    tryReadFontAnyExt("SourceSerif4-Bold"),
    tryReadFontAnyExt("SourceSans3-Regular"),
    tryReadFontAnyExt("SourceSans3-Bold"),
  ]);
  const fonts: LoadedFont[] = [];
  if (serifBold) {
    fonts.push({ name: FONT_SERIF, data: serifBold, weight: 700, style: "normal" });
  }
  if (sansRegular) {
    fonts.push({ name: FONT_SANS, data: sansRegular, weight: 400, style: "normal" });
  }
  if (sansBold) {
    fonts.push({ name: FONT_SANS, data: sansBold, weight: 700, style: "normal" });
  }
  return fonts;
}

// --- Shared chrome -------------------------------------------------------

function HardwoodBackdrop() {
  return (
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
  );
}

function HairlineFrame() {
  return (
    <div
      style={{
        position: "absolute",
        inset: 24,
        border: `1px solid ${COLORS.border}`,
        borderRadius: 24,
        display: "flex",
      }}
    />
  );
}

/**
 * Faint half-court silhouette behind the wordmark. Inline SVG paths only —
 * Satori does not animate, but it does render basic <path>/<circle>/<line>
 * elements. Anchored to the right side of the canvas so it does not crowd
 * the wordmark column.
 */
function HalfCourtSilhouette({ opacity = 1 }: { opacity?: number }) {
  return (
    <div
      style={{
        position: "absolute",
        right: -120,
        top: 80,
        width: 720,
        height: 540,
        display: "flex",
        opacity,
      }}
    >
      <svg viewBox="0 0 600 600" width="720" height="540">
        {/* Half-court arc (top of the key) */}
        <path
          d="M 100 0 L 100 240 A 200 200 0 0 0 500 240 L 500 0"
          fill="none"
          stroke={COLORS.silhouetteStrong}
          strokeWidth="3"
        />
        {/* Free-throw lane */}
        <rect
          x="220"
          y="0"
          width="160"
          height="240"
          fill="none"
          stroke={COLORS.silhouette}
          strokeWidth="2"
        />
        {/* Restricted-area arc */}
        <path
          d="M 240 60 A 60 60 0 0 0 360 60"
          fill="none"
          stroke={COLORS.silhouette}
          strokeWidth="2"
        />
        {/* Hoop + backboard */}
        <line
          x1="270"
          y1="40"
          x2="330"
          y2="40"
          stroke={COLORS.silhouetteStrong}
          strokeWidth="3"
        />
        <circle
          cx="300"
          cy="60"
          r="14"
          fill="none"
          stroke={COLORS.silhouetteStrong}
          strokeWidth="2"
        />
        {/* Three-point arc */}
        <path
          d="M 60 0 L 60 140 A 240 240 0 0 0 540 140 L 540 0"
          fill="none"
          stroke={COLORS.silhouette}
          strokeWidth="2"
        />
        {/* Center logo half-circle */}
        <path
          d="M 240 540 A 60 60 0 0 1 360 540"
          fill="none"
          stroke={COLORS.silhouette}
          strokeWidth="2"
        />
      </svg>
    </div>
  );
}

/**
 * Inline brand mark mirroring `/public/courtvue-mark.svg`. Sized via the
 * `size` prop so the home card uses a large mark while per-page cards use
 * a smaller header version.
 */
function BrandMark({ size: pixelSize = 220 }: { size?: number }) {
  return (
    <svg
      width={pixelSize}
      height={pixelSize}
      viewBox="0 0 96 96"
      style={{ flexShrink: 0 }}
    >
      <circle cx="48" cy="48" r="36" fill="none" stroke={COLORS.ink} strokeWidth="3" />
      <circle
        cx="48"
        cy="48"
        r="22"
        fill="none"
        stroke={COLORS.ink}
        strokeWidth="1.4"
        opacity="0.45"
      />
      <line x1="6" y1="48" x2="32" y2="48" stroke={COLORS.ink} strokeWidth="3" strokeLinecap="square" />
      <line x1="64" y1="48" x2="90" y2="48" stroke={COLORS.ink} strokeWidth="3" strokeLinecap="square" />
      <path
        d="M 44 30 L 44 40 L 38 60 Q 38 64 42 64 L 54 64 Q 58 64 58 60 L 52 40 L 52 30 Z"
        fill={COLORS.bgFrom}
        stroke={COLORS.forest}
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <line
        x1="42"
        y1="30"
        x2="54"
        y2="30"
        stroke={COLORS.forest}
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M 39 54 Q 41 52 44 54 T 50 54 T 57 54 L 57 60 Q 57 62 55 62 L 41 62 Q 39 62 39 60 Z"
        fill={COLORS.brass}
      />
    </svg>
  );
}

function FooterStrip({ statText }: { statText?: string }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 18,
        zIndex: 2,
      }}
    >
      {statText ? (
        <div
          style={{
            display: "flex",
            color: COLORS.forestDeep,
            fontFamily: FONT_SANS,
            fontSize: 22,
            fontWeight: 700,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
          }}
        >
          {statText}
        </div>
      ) : null}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          color: COLORS.forest,
          fontFamily: FONT_SANS,
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
            background: COLORS.brass,
          }}
        />
        <span style={{ display: "flex" }}>NBA Intelligence</span>
      </div>
    </div>
  );
}

function CardShell({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        height: "100%",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        background: `linear-gradient(135deg, ${COLORS.bgFrom} 0%, ${COLORS.bgMid} 55%, ${COLORS.bgTo} 100%)`,
        padding: "70px 90px",
        position: "relative",
        fontFamily: FONT_SANS,
        color: COLORS.ink,
      }}
    >
      <HardwoodBackdrop />
      <HairlineFrame />
      <HalfCourtSilhouette />
      {children}
    </div>
  );
}

// --- Server-side data fetchers ------------------------------------------

type AnyRecord = Record<string, unknown>;

async function fetchJson<T = AnyRecord>(path: string): Promise<T | null> {
  try {
    const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
    const res = await fetch(url, {
      // Server-side fetch — no CORS to worry about. Cache hint for Vercel.
      next: { revalidate: 300 },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

interface PlayerProfileLite {
  id: number;
  full_name: string;
  team_name?: string;
  team_abbreviation?: string;
  position?: string;
  headshot_url?: string;
}

interface SeasonStatLite {
  season: string;
  pts_pg?: number | null;
  reb_pg?: number | null;
  ast_pg?: number | null;
  ts_pct?: number | null;
}

interface TeamRosterLite {
  team_id: number;
  abbreviation: string;
  name: string;
  players: Array<{ pts_pg?: number | null }>;
}

interface TeamAnalyticsLite {
  abbreviation: string;
  name: string;
  season: string;
  w?: number | null;
  l?: number | null;
  net_rating?: number | null;
  off_rating?: number | null;
  def_rating?: number | null;
  pace?: number | null;
}

interface SeriesLite {
  season: string;
  round: number;
  series_id: string;
  top_seed_team_id: number | null;
  bottom_seed_team_id: number | null;
  top_seed_team_abbr: string | null;
  bottom_seed_team_abbr: string | null;
  top_seed: number | null;
  bottom_seed: number | null;
  top_wins: number;
  bottom_wins: number;
  status: string;
}

interface MvpLite {
  season: string;
  candidates: Array<{
    rank: number;
    player_name: string;
    team_abbreviation: string;
    composite_score: number;
    pts_pg: number;
    reb_pg: number;
    ast_pg: number;
    ts_pct: number | null;
  }>;
}

// --- Renderers ----------------------------------------------------------

function renderHomeCard() {
  return (
    <CardShell>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          zIndex: 2,
          color: COLORS.forest,
          fontFamily: FONT_SANS,
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
            background: COLORS.hairline,
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
          marginTop: 70,
          zIndex: 2,
        }}
      >
        <BrandMark size={220} />
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div
            style={{
              color: COLORS.ink,
              fontFamily: FONT_SERIF,
              fontSize: 130,
              fontWeight: 700,
              letterSpacing: "-0.04em",
              lineHeight: 1,
              display: "flex",
            }}
          >
            CourtVue
          </div>
          <div
            style={{
              color: COLORS.forest,
              fontFamily: FONT_SANS,
              fontSize: 50,
              fontWeight: 700,
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

      {/* Tagline */}
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
            color: COLORS.ink,
            fontFamily: FONT_SERIF,
            fontSize: 38,
            fontWeight: 700,
            lineHeight: 1.25,
            maxWidth: 940,
            display: "flex",
          }}
        >
          Search any NBA player. Compare careers. Track team rotations. Build your own metrics.
        </div>
        <div style={{ height: 24, display: "flex" }} />
        <FooterStrip statText="4 OFFICIAL DATA DOMAINS · 30 TEAMS · LIVE PLAYOFFS" />
      </div>
    </CardShell>
  );
}

function renderPlayerCard(args: {
  profile: PlayerProfileLite | null;
  latest: SeasonStatLite | null;
  playerId: string;
}) {
  const { profile, latest, playerId } = args;
  const name = profile?.full_name ?? `Player #${playerId}`;
  const team = profile?.team_abbreviation ?? "—";
  const position = profile?.position ?? "";
  const season = latest?.season ?? "";

  const stats: Array<{ label: string; value: string }> = [
    { label: "PTS", value: fmt(latest?.pts_pg, 1) },
    { label: "REB", value: fmt(latest?.reb_pg, 1) },
    { label: "AST", value: fmt(latest?.ast_pg, 1) },
    { label: "TS%", value: latest?.ts_pct == null ? "—" : `${(latest.ts_pct * 100).toFixed(1)}%` },
  ];

  return (
    <CardShell>
      <KickerStrip
        left="PLAYER PROFILE"
        right={season ? `SEASON ${season}` : "COURTVUE LABS"}
      />
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 24,
          marginTop: 60,
          zIndex: 2,
        }}
      >
        <BrandMark size={120} />
        <div style={{ display: "flex", flexDirection: "column", maxWidth: 820 }}>
          <div
            style={{
              display: "flex",
              fontFamily: FONT_SANS,
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: "0.22em",
              color: COLORS.forest,
              textTransform: "uppercase",
            }}
          >
            {team}
            {position ? `  ·  ${position}` : ""}
          </div>
          <div
            style={{
              display: "flex",
              fontFamily: FONT_SERIF,
              fontSize: 84,
              fontWeight: 700,
              lineHeight: 1.05,
              color: COLORS.ink,
              marginTop: 6,
              letterSpacing: "-0.02em",
            }}
          >
            {truncate(name, 28)}
          </div>
        </div>
      </div>

      <StatGrid stats={stats} />

      <div style={{ marginTop: "auto", zIndex: 2 }}>
        <FooterStrip statText={`courtvue.app/players/${playerId}`} />
      </div>
    </CardShell>
  );
}

function renderTeamCard(args: {
  roster: TeamRosterLite | null;
  analytics: TeamAnalyticsLite | null;
  abbr: string;
}) {
  const { roster, analytics, abbr } = args;
  const name = roster?.name ?? analytics?.name ?? abbr;
  const season = analytics?.season ?? "";
  const record =
    analytics && analytics.w != null && analytics.l != null
      ? `${analytics.w}-${analytics.l}`
      : "—";
  const stats: Array<{ label: string; value: string }> = [
    { label: "RECORD", value: record },
    { label: "OFF RTG", value: fmt(analytics?.off_rating, 1) },
    { label: "DEF RTG", value: fmt(analytics?.def_rating, 1) },
    { label: "NET RTG", value: fmtSigned(analytics?.net_rating, 1) },
  ];
  return (
    <CardShell>
      <KickerStrip
        left="TEAM REPORT"
        right={season ? `SEASON ${season}` : "COURTVUE LABS"}
      />
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 24,
          marginTop: 60,
          zIndex: 2,
        }}
      >
        <BrandMark size={120} />
        <div style={{ display: "flex", flexDirection: "column", maxWidth: 820 }}>
          <div
            style={{
              display: "flex",
              fontFamily: FONT_SANS,
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: "0.22em",
              color: COLORS.forest,
              textTransform: "uppercase",
            }}
          >
            {abbr.toUpperCase()}
          </div>
          <div
            style={{
              display: "flex",
              fontFamily: FONT_SERIF,
              fontSize: 84,
              fontWeight: 700,
              lineHeight: 1.05,
              color: COLORS.ink,
              marginTop: 6,
              letterSpacing: "-0.02em",
            }}
          >
            {truncate(name, 24)}
          </div>
        </div>
      </div>

      <StatGrid stats={stats} />

      <div style={{ marginTop: "auto", zIndex: 2 }}>
        <FooterStrip statText={`courtvue.app/teams/${abbr.toUpperCase()}`} />
      </div>
    </CardShell>
  );
}

function renderSeriesCard(args: {
  series: SeriesLite | null;
  seriesId: string;
}) {
  const { series, seriesId } = args;
  const top = series?.top_seed_team_abbr ?? "TBD";
  const bottom = series?.bottom_seed_team_abbr ?? "TBD";
  const topSeed = series?.top_seed ?? null;
  const bottomSeed = series?.bottom_seed ?? null;
  const topWins = series?.top_wins ?? 0;
  const bottomWins = series?.bottom_wins ?? 0;
  const round = series?.round ?? null;
  const roundLabel =
    round === 1
      ? "FIRST ROUND"
      : round === 2
      ? "CONFERENCE SEMIFINALS"
      : round === 3
      ? "CONFERENCE FINALS"
      : round === 4
      ? "NBA FINALS"
      : "PLAYOFF SERIES";

  let headline: string;
  if (!series) {
    headline = "Series tracker";
  } else if (series.status === "closed") {
    const winner = topWins > bottomWins ? top : bottom;
    headline = `${winner} won ${Math.max(topWins, bottomWins)}-${Math.min(topWins, bottomWins)}`;
  } else if (series.status === "scheduled") {
    headline = "Tipoff TBD";
  } else if (topWins === bottomWins) {
    headline = `Tied ${topWins}-${bottomWins}`;
  } else {
    const leader = topWins > bottomWins ? top : bottom;
    headline = `${leader} leads ${Math.max(topWins, bottomWins)}-${Math.min(topWins, bottomWins)}`;
  }

  return (
    <CardShell>
      <KickerStrip
        left={roundLabel}
        right={series?.season ? `${series.season} PLAYOFFS` : "COURTVUE LABS"}
      />

      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 60,
          marginTop: 80,
          zIndex: 2,
        }}
      >
        <SeriesTeamBlock abbr={top} seed={topSeed} wins={topWins} />
        <div
          style={{
            display: "flex",
            fontFamily: FONT_SERIF,
            fontSize: 96,
            fontWeight: 700,
            color: COLORS.forest,
            letterSpacing: "-0.04em",
          }}
        >
          vs
        </div>
        <SeriesTeamBlock abbr={bottom} seed={bottomSeed} wins={bottomWins} />
      </div>

      <div
        style={{
          display: "flex",
          marginTop: 50,
          fontFamily: FONT_SERIF,
          fontSize: 44,
          fontWeight: 700,
          color: COLORS.ink,
          justifyContent: "center",
          letterSpacing: "-0.01em",
          zIndex: 2,
        }}
      >
        {headline}
      </div>

      <div style={{ marginTop: "auto", zIndex: 2 }}>
        <FooterStrip statText={`courtvue.app/playoff-series/${seriesId}`} />
      </div>
    </CardShell>
  );
}

function renderMvpCard(args: {
  mvp: MvpLite | null;
  season: string;
}) {
  const { mvp, season } = args;
  const top3 = (mvp?.candidates ?? []).slice(0, 3);
  return (
    <CardShell>
      <KickerStrip
        left="MVP RACE"
        right={season ? `SEASON ${season}` : "COURTVUE LABS"}
      />

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 24,
          marginTop: 50,
          zIndex: 2,
        }}
      >
        <BrandMark size={120} />
        <div
          style={{
            display: "flex",
            fontFamily: FONT_SERIF,
            fontSize: 80,
            fontWeight: 700,
            color: COLORS.ink,
            letterSpacing: "-0.02em",
          }}
        >
          MVP Ladder
        </div>
      </div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 16,
          marginTop: 40,
          zIndex: 2,
        }}
      >
        {top3.length === 0 ? (
          <div
            style={{
              display: "flex",
              fontFamily: FONT_SERIF,
              fontSize: 32,
              color: COLORS.forest,
            }}
          >
            Race standings unavailable.
          </div>
        ) : (
          top3.map((candidate, idx) => (
            <div
              key={candidate.rank ?? idx}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 24,
                padding: "12px 24px",
                background: idx === 0 ? "rgba(33,72,59,0.08)" : "rgba(32,26,22,0.04)",
                borderRadius: 16,
                border: idx === 0 ? `2px solid ${COLORS.brass}` : `1px solid ${COLORS.border}`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  fontFamily: FONT_SERIF,
                  fontSize: 56,
                  fontWeight: 700,
                  color: idx === 0 ? COLORS.brass : COLORS.forest,
                  width: 60,
                  justifyContent: "center",
                }}
              >
                {candidate.rank ?? idx + 1}
              </div>
              <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
                <div
                  style={{
                    display: "flex",
                    fontFamily: FONT_SERIF,
                    fontSize: 36,
                    fontWeight: 700,
                    color: COLORS.ink,
                    letterSpacing: "-0.01em",
                  }}
                >
                  {truncate(candidate.player_name, 26)}
                </div>
                <div
                  style={{
                    display: "flex",
                    fontFamily: FONT_SANS,
                    fontSize: 18,
                    fontWeight: 700,
                    color: COLORS.forest,
                    letterSpacing: "0.18em",
                    textTransform: "uppercase",
                    marginTop: 2,
                  }}
                >
                  {candidate.team_abbreviation}  ·  {fmt(candidate.pts_pg, 1)} PPG  ·  {fmt(candidate.reb_pg, 1)} RPG  ·  {fmt(candidate.ast_pg, 1)} APG
                </div>
              </div>
              <div
                style={{
                  display: "flex",
                  fontFamily: FONT_SERIF,
                  fontSize: 36,
                  fontWeight: 700,
                  color: COLORS.ink,
                }}
              >
                {fmt(candidate.composite_score, 1)}
              </div>
            </div>
          ))
        )}
      </div>

      <div style={{ marginTop: "auto", zIndex: 2 }}>
        <FooterStrip statText="courtvue.app/mvp" />
      </div>
    </CardShell>
  );
}

// --- Small shared sub-components ----------------------------------------

function KickerStrip({ left, right }: { left: string; right: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 14,
        zIndex: 2,
        color: COLORS.forest,
        fontFamily: FONT_SANS,
        fontSize: 22,
        fontWeight: 700,
        letterSpacing: "0.32em",
        textTransform: "uppercase",
      }}
    >
      <span style={{ display: "flex" }}>{left}</span>
      <span
        style={{
          display: "flex",
          flex: 1,
          height: 1,
          background: COLORS.hairline,
          alignSelf: "center",
        }}
      />
      <span style={{ display: "flex" }}>{right}</span>
    </div>
  );
}

function StatGrid({ stats }: { stats: Array<{ label: string; value: string }> }) {
  return (
    <div
      style={{
        display: "flex",
        gap: 18,
        marginTop: 60,
        zIndex: 2,
      }}
    >
      {stats.map((stat) => (
        <div
          key={stat.label}
          style={{
            display: "flex",
            flexDirection: "column",
            flex: 1,
            padding: "20px 24px",
            background: "rgba(255,249,241,0.7)",
            border: `1px solid ${COLORS.border}`,
            borderRadius: 18,
          }}
        >
          <div
            style={{
              display: "flex",
              fontFamily: FONT_SANS,
              fontSize: 16,
              fontWeight: 700,
              letterSpacing: "0.22em",
              color: COLORS.forest,
              textTransform: "uppercase",
            }}
          >
            {stat.label}
          </div>
          <div
            style={{
              display: "flex",
              fontFamily: FONT_SERIF,
              fontSize: 56,
              fontWeight: 700,
              color: COLORS.ink,
              letterSpacing: "-0.02em",
              marginTop: 4,
            }}
          >
            {stat.value}
          </div>
        </div>
      ))}
    </div>
  );
}

function SeriesTeamBlock({
  abbr,
  seed,
  wins,
}: {
  abbr: string;
  seed: number | null;
  wins: number;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 6,
      }}
    >
      {seed != null ? (
        <div
          style={{
            display: "flex",
            fontFamily: FONT_SANS,
            fontSize: 18,
            fontWeight: 700,
            letterSpacing: "0.22em",
            color: COLORS.forest,
            textTransform: "uppercase",
          }}
        >
          SEED {seed}
        </div>
      ) : null}
      <div
        style={{
          display: "flex",
          fontFamily: FONT_SERIF,
          fontSize: 110,
          fontWeight: 700,
          color: COLORS.ink,
          lineHeight: 1,
          letterSpacing: "-0.04em",
        }}
      >
        {abbr}
      </div>
      <div
        style={{
          display: "flex",
          fontFamily: FONT_SANS,
          fontSize: 28,
          fontWeight: 700,
          color: COLORS.forest,
          marginTop: 4,
        }}
      >
        {wins} W
      </div>
    </div>
  );
}

// --- helpers -----------------------------------------------------------

function fmt(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function fmtSigned(value: number | null | undefined, digits = 1): string {
  if (value == null || Number.isNaN(value)) return "—";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(digits)}`;
}

function truncate(str: string, max: number): string {
  if (!str) return "";
  if (str.length <= max) return str;
  return `${str.slice(0, max - 1).trim()}…`;
}

// --- GET handler -------------------------------------------------------

export async function GET(req: Request): Promise<Response> {
  const { searchParams } = new URL(req.url);
  const type = (searchParams.get("type") ?? "home").toLowerCase();
  const fonts = await loadFonts();

  let element: React.ReactElement;

  if (type === "player") {
    const id = searchParams.get("id") ?? "";
    if (!id || !/^\d+$/.test(id)) {
      element = renderHomeCard();
    } else {
      const profile = await fetchJson<PlayerProfileLite>(`/api/players/${id}`);
      // Latest season stat: try the season-stats endpoint, fall back to null.
      const seasonStats = await fetchJson<SeasonStatLite[]>(
        `/api/stats/${id}?season=`
      );
      const latest = Array.isArray(seasonStats) && seasonStats.length > 0
        ? seasonStats[seasonStats.length - 1]
        : null;
      element = renderPlayerCard({ profile, latest, playerId: id });
    }
  } else if (type === "team") {
    const abbr = (searchParams.get("abbr") ?? "").toUpperCase();
    if (!abbr || !/^[A-Z]{2,4}$/.test(abbr)) {
      element = renderHomeCard();
    } else {
      const roster = await fetchJson<TeamRosterLite>(`/api/teams/${abbr}`);
      const analytics = await fetchJson<TeamAnalyticsLite>(
        `/api/teams/${abbr}/analytics`
      );
      element = renderTeamCard({ roster, analytics, abbr });
    }
  } else if (type === "series") {
    const id = searchParams.get("id") ?? "";
    if (!id) {
      element = renderHomeCard();
    } else {
      const series = await fetchJson<SeriesLite>(
        `/api/playoffs/series/${encodeURIComponent(id)}`
      );
      element = renderSeriesCard({ series, seriesId: id });
    }
  } else if (type === "mvp") {
    const season = searchParams.get("season") ?? "";
    const seasonQuery = season ? `?season=${encodeURIComponent(season)}&top=3` : "?top=3";
    const mvp = await fetchJson<MvpLite>(`/api/mvp/race${seasonQuery}`);
    element = renderMvpCard({ mvp, season: mvp?.season ?? season });
  } else {
    element = renderHomeCard();
  }

  return new ImageResponse(element, {
    width: size.width,
    height: size.height,
    fonts: fonts.length > 0 ? fonts : undefined,
  });
}
