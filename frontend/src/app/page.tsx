import PlayerSearchBar from "@/components/PlayerSearchBar";
import HomeLeagueLeaders from "@/components/HomeLeagueLeaders";
import HomeMvpTeaser from "@/components/HomeMvpTeaser";
import FavoritesList from "@/components/FavoritesList";
import StatCounter from "@/components/StatCounter";
import HeroHardwood from "@/components/HeroHardwood";
import Link from "next/link";

// Heroicons-style SVG icons for platform cards (24×24, 1.7px stroke, round caps/joins)
function PlatformIcon({ name, size = 18 }: { name: string; size?: number }) {
  const paths: Record<string, React.ReactNode> = {
    beaker: (
      <>
        <path d="M9 3h6" />
        <path d="M10 3v6l-5 9a3 3 0 0 0 2.6 4.5h8.8A3 3 0 0 0 19 18l-5-9V3" />
      </>
    ),
    basketball: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M3 12h18" />
        <path d="M12 3v18" />
        <path d="M5.5 5.5c4 3 9 3 13 0" />
        <path d="M5.5 18.5c4-3 9-3 13 0" />
      </>
    ),
    sparkle: <path d="M13 2 3 14h7l-1 8 10-12h-7l1-8z" />,
    shield: <path d="M12 3 4 6v6c0 5 3.5 8.5 8 9 4.5-.5 8-4 8-9V6l-8-3z" />,
    scales: (
      <>
        <path d="M12 3v18" />
        <path d="M4 20h16" />
        <path d="m6 8 3 7H3z" />
        <path d="m18 8 3 7h-6z" />
        <path d="M4 8h16" />
      </>
    ),
    clipboard: (
      <>
        <rect x="6" y="4" width="12" height="17" rx="2" />
        <path d="M9 4h6v3H9z" />
        <path d="M9 11h6" />
        <path d="M9 15h4" />
      </>
    ),
    chart: (
      <>
        <path d="M4 20V10" />
        <path d="M10 20V4" />
        <path d="M16 20v-7" />
        <path d="M22 20H2" />
      </>
    ),
    microscope: (
      <>
        <path d="M6 18h8" />
        <path d="M3 22h18" />
        <path d="M14 22a7 7 0 1 0 0-14h-1" />
        <path d="M9 14h2" />
        <path d="M9 12a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Z" />
        <path d="M12 6V3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3" />
      </>
    ),
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {paths[name] ?? paths.chart}
    </svg>
  );
}

const platformAreas = [
  {
    href: "/ask",
    eyebrow: "CourtVue Ask",
    icon: "beaker",
    title: "Ask a basketball question",
    description:
      "Get instant player leaders, team rankings, filters, recent form, and profile links from synced CourtVue data.",
  },
  {
    href: "/standings",
    eyebrow: "League Context",
    icon: "chart",
    title: "Check the standings",
    description:
      "Conference standings with W-L records, last 10, home/away splits, and scoring differential.",
  },
  {
    href: "/player-stats",
    eyebrow: "Player Stats",
    icon: "basketball",
    title: "Scan player leaderboards",
    description:
      "Advanced, external, and play-by-play-informed leaderboards across every key stat.",
  },
  {
    href: "/metrics",
    eyebrow: "Metrics Workspace",
    icon: "sparkle",
    title: "Build your own metric",
    description:
      "Load starter presets, share metric links, and rank the player pool through your own weighted model.",
  },
  {
    href: "/teams",
    eyebrow: "Team Context",
    icon: "shield",
    title: "Browse team intelligence",
    description:
      "Team efficiency ratings, four factors, roster leaders, and rotation intelligence.",
  },
  {
    href: "/coverage",
    eyebrow: "Operations",
    icon: "microscope",
    title: "Audit PBP sync coverage",
    description:
      "See which teams and players are ready, partial, or missing play-by-play-derived data.",
  },
  {
    href: "/compare",
    eyebrow: "Compare",
    icon: "scales",
    title: "Stack careers side by side",
    description:
      "Put two players in the same frame to compare production, efficiency, and arc.",
  },
  {
    href: "/pre-read",
    eyebrow: "Coach Workflow",
    icon: "clipboard",
    title: "Build a pre-read deck",
    description:
      "Generate a short printable briefing with focus levers, matchup edges, and tactical adjustments.",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-14">
      {/* ── Hero ─────────────────────────────────────────────────── */}
      <div className="bip-panel-strong relative overflow-hidden rounded-[2.2rem] px-6 sm:px-12 min-h-[88vh] flex flex-col items-center justify-center">

        {/* ── Warm woodgrain texture ── */}
        <HeroHardwood opacity={0.18} tint="#b07a37" seed={7} />

        {/* ── Decorative court art (purely visual) ── */}
        <div className="absolute inset-0 overflow-hidden rounded-[2.2rem] pointer-events-none select-none">
          {/* Three-point arc */}
          <div className="absolute bottom-[-20px] left-1/2 -translate-x-1/2 w-[520px] h-[260px] rounded-t-full border-t-2 border-l-2 border-r-2 border-[rgba(33,72,59,0.09)]" />
          {/* Paint box */}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[180px] h-[150px] border-2 border-[rgba(33,72,59,0.08)]" />
          {/* Free throw circle */}
          <div className="absolute bottom-[148px] left-1/2 -translate-x-1/2 w-[120px] h-[120px] rounded-full border border-[rgba(33,72,59,0.07)]" />
          {/* Concentric decorative rings */}
          <div className="absolute bottom-[-120px] left-1/2 -translate-x-1/2 w-[700px] h-[700px] rounded-full border border-[rgba(33,72,59,0.055)]" />
          <div className="absolute bottom-[-200px] left-1/2 -translate-x-1/2 w-[900px] h-[900px] rounded-full border border-[rgba(33,72,59,0.04)]" />
          {/* Ambient glow blobs */}
          <div className="absolute right-[-5rem] top-[-5rem] h-72 w-72 rounded-full bg-[rgba(33,72,59,0.11)] blur-3xl" />
          <div className="absolute left-[-4rem] bottom-[6rem] h-60 w-60 rounded-full bg-[rgba(180,137,61,0.10)] blur-3xl" />
          <div className="absolute inset-x-0 top-0 h-48 bg-gradient-to-b from-[rgba(180,137,61,0.14)] via-[rgba(244,236,222,0)] to-transparent" />
        </div>

        {/* ── Content ── */}
        <div className="relative text-center max-w-3xl py-20">
          <p
            className="bip-kicker mb-5 animate-fade-up"
            style={{ animationDelay: "0ms" }}
          >
            CourtVue Labs
          </p>
          <h1
            className="bip-display text-5xl font-bold tracking-tight mb-5 text-[var(--foreground)] sm:text-7xl animate-fade-up"
            style={{ animationDelay: "80ms" }}
          >
            Court-side intelligence,
            <br />
            <span className="text-[var(--accent)]">in full view.</span>
          </h1>
          <p
            className="text-lg text-[var(--muted)] mb-8 max-w-2xl mx-auto leading-8 animate-fade-up"
            style={{ animationDelay: "160ms" }}
          >
            The basketball-IQ lab where strategy, analytics, and decisions are built and tested.
          </p>

          {/* Animated stat counter */}
          <div
            className="mb-8 animate-fade-up"
            style={{ animationDelay: "240ms" }}
          >
            <StatCounter target={4892} label="players tracked" />
          </div>

          <div
            className="animate-fade-up"
            style={{ animationDelay: "320ms" }}
          >
            <PlayerSearchBar />
          </div>

          <div
            className="mt-8 flex flex-wrap items-center justify-center gap-3 animate-fade-up"
            style={{ animationDelay: "400ms" }}
          >
            <span className="bip-pill">Team rotation intelligence</span>
            <span className="bip-pill">Play-by-play context</span>
            <span className="bip-pill">Analyst-first workflows</span>
          </div>
        </div>
      </div>

      {/* ── Platform areas ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {platformAreas.map((area) => (
          <Link
            key={area.href}
            href={area.href}
            className="group bip-panel rounded-[1.85rem] p-6 hover:-translate-y-1 hover:border-[var(--accent)] hover:shadow-[0_24px_60px_rgba(33,72,59,0.16)] transition-all duration-200"
          >
            <div className="flex items-center gap-2 mb-1 text-[var(--accent)]">
              <PlatformIcon name={area.icon} size={18} />
              <p className="bip-kicker">{area.eyebrow}</p>
            </div>
            <h2 className="bip-display mt-3 text-2xl font-semibold text-[var(--foreground)]">
              {area.title}
            </h2>
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
              {area.description}
            </p>
            <div className="mt-6 text-sm font-medium text-[var(--accent)] group-hover:text-[var(--accent-strong)] transition-colors">
              Open workspace →
            </div>
          </Link>
        ))}
      </div>

      {/* ── Watchlist ────────────────────────────────────────────── */}
      <FavoritesList />

      {/* ── MVP race teaser ──────────────────────────────────────── */}
      <HomeMvpTeaser />

      {/* ── Live league leaders ──────────────────────────────────── */}
      <HomeLeagueLeaders />
    </div>
  );
}
