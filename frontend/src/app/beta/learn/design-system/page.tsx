"use client";

import HeroHardwood from "@/components/HeroHardwood";
import LiveTicker from "@/components/LiveTicker";
import FloatingBall from "@/components/FloatingBall";
import LiveShotPulse from "@/components/LiveShotPulse";
import Parallax from "@/components/Parallax";
import SpotlightCursor from "@/components/SpotlightCursor";
import Reveal from "@/components/Reveal";
import StandingsLadder, { type LadderTeam } from "@/components/StandingsLadder";
import WinProbabilityChart, { type WinProbPoint } from "@/components/WinProbabilityChart";
import HomeLiveCourt from "@/components/HomeLiveCourt";

// Demo data mirrors the constants used inside HomeLiveCourt so the showcase
// renders identical reference visuals for StandingsLadder + WinProbabilityChart.
const DEMO_LADDER: LadderTeam[] = [
  { rank: 1, name: "Oklahoma City Thunder", abbr: "OKC", color: "#0072ce", w: 58, l: 14, change: 0 },
  { rank: 2, name: "Boston Celtics", abbr: "BOS", color: "#007a33", w: 55, l: 17, change: 1 },
  { rank: 3, name: "Denver Nuggets", abbr: "DEN", color: "#0e2240", w: 52, l: 20, change: -1 },
  { rank: 4, name: "Minnesota Timberwolves", abbr: "MIN", color: "#0c2340", w: 49, l: 23, change: 2 },
  { rank: 5, name: "Dallas Mavericks", abbr: "DAL", color: "#00538c", w: 47, l: 25, change: 0 },
  { rank: 6, name: "New York Knicks", abbr: "NYK", color: "#f58426", w: 46, l: 26, change: 1 },
  { rank: 7, name: "Milwaukee Bucks", abbr: "MIL", color: "#00471b", w: 44, l: 28, change: -2 },
  { rank: 8, name: "Philadelphia 76ers", abbr: "PHI", color: "#006bb6", w: 41, l: 31, change: 0 },
];

const DEMO_WP: WinProbPoint[] = [
  { t: 0, prob: 0.5 },
  { t: 4, prob: 0.55 },
  { t: 8, prob: 0.62, event: "+8 RUN" },
  { t: 12, prob: 0.58 },
  { t: 16, prob: 0.51 },
  { t: 20, prob: 0.46 },
  { t: 24, prob: 0.49 },
  { t: 28, prob: 0.55 },
  { t: 32, prob: 0.63 },
  { t: 36, prob: 0.71, event: "TIMEOUT" },
  { t: 40, prob: 0.66 },
  { t: 44, prob: 0.78, event: "CLUTCH 3" },
  { t: 48, prob: 0.92 },
];

interface CssVarSwatch {
  label: string;
  varName: string;
}

const CSS_VAR_SWATCHES: CssVarSwatch[] = [
  { label: "--accent", varName: "--accent" },
  { label: "--signal", varName: "--signal" },
  { label: "--foreground", varName: "--foreground" },
  { label: "--muted", varName: "--muted" },
  { label: "--background", varName: "--background" },
];

interface PrimitiveCellProps {
  caption: string;
  children: React.ReactNode;
}

function PrimitiveCell({ caption, children }: PrimitiveCellProps) {
  return (
    <div className="rounded-[1.4rem] border border-[var(--border)] bg-white/70 p-4">
      <div className="flex min-h-[180px] items-center justify-center">{children}</div>
      <p className="mt-3 text-center text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
        {caption}
      </p>
    </div>
  );
}

export default function DesignSystemShowcasePage() {
  return (
    <div className="mx-auto max-w-6xl space-y-12 py-8">
      {/* 1 — Header */}
      <section className="bip-panel rounded-[1.85rem] p-8">
        <p className="bip-kicker">Design System</p>
        <h1 className="bip-display mt-3 text-4xl font-semibold text-[var(--foreground)] sm:text-5xl">
          CourtVue Labs primitives
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-6 text-[var(--muted-strong)]">
          This is an internal reference page for the design-system primitives shipped in
          Sprint 70. Use it to spot-check typography, color tokens, motion, and the data-viz
          building blocks before composing them into product surfaces.
        </p>
      </section>

      {/* 2 — Hardwood texture */}
      <section className="bip-panel rounded-[1.85rem] p-8">
        <p className="bip-kicker">Texture</p>
        <h2 className="bip-display mt-2 text-2xl font-semibold text-[var(--foreground)]">
          Hardwood
        </h2>
        <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">
          Procedural woodgrain SVG layered over hero panels and metric cards.
        </p>
        <div
          className="mt-5 overflow-hidden rounded-[1.4rem] border border-[var(--border)] bg-[var(--surface)]"
          style={{ position: "relative", width: 320, height: 120 }}
        >
          <HeroHardwood opacity={0.18} tint="#b07a37" seed={7} />
        </div>
      </section>

      {/* 3 — Typography scale */}
      <section className="bip-panel rounded-[1.85rem] p-8">
        <p className="bip-kicker">Typography</p>
        <h2 className="bip-display mt-2 text-2xl font-semibold text-[var(--foreground)]">
          Type scale
        </h2>
        <div className="mt-5 space-y-4">
          <div className="bip-display text-5xl font-bold text-[var(--foreground)]">Display 5xl</div>
          <div className="bip-display text-3xl font-semibold text-[var(--foreground)]">Display 3xl</div>
          <p className="bip-kicker">Kicker label</p>
          <p className="text-sm leading-6 text-[var(--foreground)]">
            Regular sans body text — Source Sans 3 at 14px / 24px line height. Used for body copy
            across panels, briefings, and tabular descriptions.
          </p>
          <p className="font-mono text-xs uppercase tracking-wider text-[var(--muted)]">
            Mono caption
          </p>
        </div>
      </section>

      {/* 4 — Buttons + Pills + Color tokens */}
      <section className="bip-panel rounded-[1.85rem] p-8">
        <p className="bip-kicker">Buttons &amp; Pills</p>
        <h2 className="bip-display mt-2 text-2xl font-semibold text-[var(--foreground)]">
          Pills and color tokens
        </h2>

        <div className="mt-5 flex flex-wrap gap-3">
          <span className="bip-pill">Primary pill</span>
          <span className="bip-pill">Forest accent</span>
          <span className="bip-pill">Pinned claim</span>
          <span className="bip-pill">High confidence</span>
        </div>

        <div className="mt-6">
          <p className="bip-kicker">CSS variable swatches</p>
          <div className="mt-3 flex flex-wrap gap-4">
            {CSS_VAR_SWATCHES.map((swatch) => (
              <div key={swatch.varName} className="flex items-center gap-3">
                <span
                  aria-hidden
                  className="rounded-md border border-[var(--border)]"
                  style={{
                    width: 36,
                    height: 36,
                    background: `var(${swatch.varName})`,
                  }}
                />
                <span className="font-mono text-xs uppercase tracking-wider text-[var(--muted-strong)]">
                  {swatch.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 5 — Live FX */}
      <section className="bip-panel rounded-[1.85rem] p-8">
        <p className="bip-kicker">Live FX</p>
        <h2 className="bip-display mt-2 text-2xl font-semibold text-[var(--foreground)]">
          Motion primitives
        </h2>
        <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">
          Hover cells with cursor-driven primitives (Parallax, SpotlightCursor) to see them
          respond. Reveal animates on first scroll into view.
        </p>

        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <PrimitiveCell caption="LiveTicker (renders inline for reference)">
            <div style={{ width: "100%" }}>
              <LiveTicker />
            </div>
          </PrimitiveCell>

          <PrimitiveCell caption="FloatingBall">
            <div style={{ position: "relative", width: 80, height: 80 }}>
              <FloatingBall size={48} />
            </div>
          </PrimitiveCell>

          <PrimitiveCell caption="LiveShotPulse">
            <LiveShotPulse width={280} height={180} />
          </PrimitiveCell>

          <PrimitiveCell caption="Parallax (hover to tilt)">
            <Parallax strength={10} style={{ width: 200, height: 100 }}>
              <div
                className="bip-panel flex h-full w-full items-center justify-center rounded-xl"
                style={{ height: "100%", width: "100%" }}
              >
                <span className="text-sm font-semibold text-[var(--foreground)]">Tilt me</span>
              </div>
            </Parallax>
          </PrimitiveCell>

          <PrimitiveCell caption="SpotlightCursor (hover the card)">
            <div
              style={{
                position: "relative",
                width: 220,
                height: 120,
                borderRadius: 14,
                background: "var(--surface-alt)",
                border: "1px solid var(--border)",
                overflow: "hidden",
              }}
            >
              <SpotlightCursor />
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  pointerEvents: "none",
                }}
              >
                <span className="text-sm font-semibold text-[var(--foreground)]">Hover me</span>
              </div>
            </div>
          </PrimitiveCell>

          <PrimitiveCell caption="Reveal (fade-up on scroll)">
            <Reveal>
              <div className="bip-panel rounded-xl p-4">
                <p className="text-sm font-semibold text-[var(--foreground)]">Reveal content</p>
                <p className="mt-1 text-xs text-[var(--muted-strong)]">
                  Animates in once it intersects the viewport.
                </p>
              </div>
            </Reveal>
          </PrimitiveCell>
        </div>
      </section>

      {/* 6 — Data viz */}
      <section className="bip-panel rounded-[1.85rem] p-8 space-y-6">
        <div>
          <p className="bip-kicker">Data Viz</p>
          <h2 className="bip-display mt-2 text-2xl font-semibold text-[var(--foreground)]">
            Standings + win probability
          </h2>
          <p className="mt-2 text-sm leading-6 text-[var(--muted-strong)]">
            The same demo data used by HomeLiveCourt, isolated here for inspection.
          </p>
        </div>

        <div className="space-y-3">
          <p className="bip-kicker">Standings ladder</p>
          <StandingsLadder teams={DEMO_LADDER} />
        </div>

        <div className="space-y-3">
          <p className="bip-kicker">Win probability</p>
          <div className="bip-shot-canvas !p-3">
            <WinProbabilityChart data={DEMO_WP} />
          </div>
        </div>
      </section>

      {/* 7 — HomeLiveCourt */}
      <section className="bip-panel rounded-[1.85rem] p-8">
        <p className="bip-kicker">Composed surface</p>
        <h2 className="bip-display mt-2 text-2xl font-semibold text-[var(--foreground)]">
          HomeLiveCourt
        </h2>
        <p className="mt-2 mb-5 text-sm leading-6 text-[var(--muted-strong)]">
          The full composed home-page section pairing LiveShotPulse, WinProbabilityChart, and
          StandingsLadder.
        </p>
        <HomeLiveCourt />
      </section>
    </div>
  );
}
