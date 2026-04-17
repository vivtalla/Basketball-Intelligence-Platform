import PlayerSearchBar from "@/components/PlayerSearchBar";
import HomeLeagueLeaders from "@/components/HomeLeagueLeaders";
import FavoritesList from "@/components/FavoritesList";
import StatCounter from "@/components/StatCounter";
import Link from "next/link";

const platformAreas = [
  {
    href: "/ask",
    eyebrow: "CourtVue Ask",
    icon: "Q",
    title: "Ask a basketball question",
    description:
      "Get instant player leaders, team rankings, filters, recent form, and profile links from synced CourtVue data.",
  },
  {
    href: "/standings",
    eyebrow: "League Context",
    icon: "📊",
    title: "Check the standings",
    description:
      "Conference standings with W-L records, last 10, home/away splits, and scoring differential.",
  },
  {
    href: "/player-stats",
    eyebrow: "Player Stats",
    icon: "🏀",
    title: "Scan player leaderboards",
    description:
      "Advanced, external, and play-by-play-informed leaderboards across every key stat.",
  },
  {
    href: "/metrics",
    eyebrow: "Metrics Workspace",
    icon: "⚗️",
    title: "Build your own metric",
    description:
      "Load starter presets, share metric links, and rank the player pool through your own weighted model.",
  },
  {
    href: "/teams",
    eyebrow: "Explore Context",
    icon: "🛡️",
    title: "Browse team intelligence",
    description:
      "Team efficiency ratings, four factors, roster leaders, and player dashboards.",
  },
  {
    href: "/coverage",
    eyebrow: "Operations",
    icon: "🔬",
    title: "Audit PBP sync coverage",
    description:
      "See which teams and players are ready, partial, or missing play-by-play-derived data.",
  },
  {
    href: "/compare",
    eyebrow: "Compare Stars",
    icon: "⚖️",
    title: "Stack careers side by side",
    description:
      "Put two players in the same frame to compare production, efficiency, and arc.",
  },
  {
    href: "/pre-read",
    eyebrow: "Coach Workflow",
    icon: "📋",
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
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {platformAreas.map((area) => (
          <Link
            key={area.href}
            href={area.href}
            className="group bip-panel rounded-[1.85rem] p-6 hover:-translate-y-1 hover:border-[var(--accent)] hover:shadow-[0_24px_60px_rgba(33,72,59,0.16)] transition-all duration-200"
          >
            <div className="flex items-center gap-2 mb-1">
              <span className="text-lg leading-none" aria-hidden="true">{area.icon}</span>
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

      {/* ── Live league leaders ──────────────────────────────────── */}
      <HomeLeagueLeaders />
    </div>
  );
}
