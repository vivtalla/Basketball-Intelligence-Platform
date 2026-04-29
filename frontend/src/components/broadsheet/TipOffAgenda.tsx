"use client";

/**
 * Sprint 77 (EB2): offseason-only mini-rail of upcoming season milestones.
 * Renders Draft, Free Agency, Training Camp, and Opening Night with a
 * date kicker, serif headline, and 1-line description. v1 hardcodes the
 * agenda — backlog item to drive from a calendar/league API.
 */

interface Milestone {
  readonly date: string;
  readonly label: string;
  readonly description: string;
}

const MILESTONES: ReadonlyArray<Milestone> = [
  {
    date: "JUNE 26",
    label: "NBA Draft",
    description: "Round 1 starts at 8 PM ET in Brooklyn",
  },
  {
    date: "JULY 1",
    label: "Free Agency Opens",
    description: "Negotiations open at 6 PM ET; signings start July 6",
  },
  {
    date: "SEPT 30",
    label: "Training Camp Opens",
    description: "Veteran reporting day across all 30 franchises",
  },
  {
    date: "OCT 21",
    label: "Opening Night",
    description: "Two-game national doubleheader to tip the regular season",
  },
];

export default function TipOffAgenda() {
  return (
    <section
      aria-labelledby="tipoff-agenda-heading"
      className="bip-panel rounded-[1.85rem] p-8 sm:p-10"
    >
      <div className="flex items-baseline justify-between gap-4 flex-wrap">
        <div>
          <p className="bip-kicker mb-2">Tip-Off Agenda</p>
          <h2
            id="tipoff-agenda-heading"
            className="bip-display text-3xl sm:text-4xl font-semibold text-[var(--foreground)]"
          >
            What&rsquo;s next on the calendar
          </h2>
        </div>
      </div>

      <ul className="mt-7 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {MILESTONES.map((m) => (
          <li
            key={m.label}
            className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5"
          >
            <p className="bip-kicker mb-2">{m.date}</p>
            <h3 className="bip-display text-lg font-semibold text-[var(--foreground)]">
              {m.label}
            </h3>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              {m.description}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
