"use client";

/**
 * Sprint 77 (Stream B / EB1): Story Rail.
 *
 * 3-column article tease grid, broadsheet-styled. Each tile carries a
 * mono-uppercase kicker, a serif headline, and a byline.
 *
 * TODO: Story Rail CMS wiring. For v1 the editorial copy is hardcoded
 * here so the broadsheet ships looking finished. When the editorial
 * service lands, swap this list for an SWR fetch and keep the same
 * tile shape.
 */

interface StoryTease {
  kicker: string;
  headline: string;
  byline: string;
  readTime: string;
}

const STORIES: readonly StoryTease[] = [
  {
    kicker: "Editorial",
    headline:
      "Why this OKC defense isn't a fluke — and what Jokić is testing.",
    byline: "S. Vaidya",
    readTime: "8 min read",
  },
  {
    kicker: "Numbers Desk",
    headline:
      "Boston's catch-and-shoot diet has stayed open three rounds.",
    byline: "M. Adelin",
    readTime: "4 min read",
  },
  {
    kicker: "Game Mechanics",
    headline:
      "The new hack-a-Hartenstein math — and why Malone is wrong about it.",
    byline: "K. Barros",
    readTime: "6 min read",
  },
];

function StoryTile({ story }: { story: StoryTease }) {
  return (
    <article
      className="bip-panel rounded-2xl px-5 py-5 h-full flex flex-col"
      style={{
        background: "rgba(255,249,241,0.6)",
      }}
    >
      <p className="bip-kicker mb-3">{story.kicker}</p>
      <h3
        className="bip-display font-semibold text-[var(--foreground)] flex-1"
        style={{
          fontSize: "1.15rem",
          lineHeight: 1.3,
          letterSpacing: "-0.01em",
        }}
      >
        {story.headline}
      </h3>
      <p
        className="mt-4 text-xs"
        style={{
          fontFamily: "var(--font-geist-mono)",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          color: "var(--muted)",
        }}
      >
        {story.byline} · {story.readTime}
      </p>
    </article>
  );
}

export default function StoryRail() {
  return (
    <section>
      <header className="mb-3 px-1">
        <p className="bip-kicker">Story Rail</p>
      </header>
      <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-1 gap-4">
        {STORIES.map((story) => (
          <StoryTile key={story.headline} story={story} />
        ))}
      </div>
    </section>
  );
}
