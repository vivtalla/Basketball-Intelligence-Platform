// Sprint 102 (Stream B) — per-prospect team-fit grid.
//
// Renders the Sprint 100 backend's `ProspectDetail.team_fit_top` array
// as a grid of 5 team cards, each showing fit score + colored fit-label
// badge + summary + value-driver chips + overlap-flag chips. Hides
// entirely when `team_fit_top` is empty/null.
//
// Reuses the visual language of `frontend/src/components/team-fit/TeamFitPanel.tsx`
// (the player-side panel) — same fit-score color tones, same chip patterns
// — but as a tighter, draft-prospect-specific variant.

import type { ProspectTeamFit, ProspectTeamFitLabel } from "@/lib/types";

interface Props {
  teams: ProspectTeamFit[] | null | undefined;
}

function labelStyle(label: ProspectTeamFitLabel): { bg: string; border: string; text: string; copy: string } {
  switch (label) {
    case "better_fit":
      return {
        bg: "rgba(33,72,59,0.10)",
        border: "rgba(33,72,59,0.40)",
        text: "#21483b",
        copy: "Better fit",
      };
    case "similar_fit":
      return {
        bg: "rgba(180,137,61,0.10)",
        border: "rgba(180,137,61,0.45)",
        text: "#9a6f24",
        copy: "Similar fit",
      };
    case "different_fit":
    default:
      return {
        bg: "rgba(120,120,120,0.08)",
        border: "rgba(120,120,120,0.30)",
        text: "#878787",
        copy: "Different fit",
      };
  }
}

function scoreTone(score: number): string {
  if (score >= 70) return "text-[var(--accent)]";
  if (score >= 55) return "text-[var(--foreground)]";
  return "text-[var(--muted-strong)]";
}

function Chip({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "warn" }) {
  const styles =
    tone === "warn"
      ? "border-[var(--border)] bg-[rgba(196,66,58,0.06)] text-[var(--muted-strong)]"
      : "border-[var(--border)] bg-[var(--surface-alt)] text-[var(--muted-strong)]";
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] ${styles}`}>
      {children}
    </span>
  );
}

export default function TeamFitPanel({ teams }: Props) {
  if (!teams || teams.length === 0) return null;

  return (
    <section className="bip-panel rounded-[1.85rem] p-5 sm:p-6">
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <p className="bip-kicker">Team fit · v3 (draft adapter)</p>
          <h2 className="bip-display mt-1 text-xl font-bold text-[var(--foreground)]">
            Best NBA destinations
          </h2>
        </div>
        <span className="text-[10px] uppercase tracking-wider text-[var(--muted)]">
          Top {teams.length} of 30 teams
        </span>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {teams.map((team) => {
          const style = labelStyle(team.fit_label);
          return (
            <div
              key={team.team_abbreviation}
              className="rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] p-3"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="bip-display text-2xl font-bold text-[var(--foreground)]">
                  {team.team_abbreviation}
                </span>
                <span
                  className="rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider"
                  style={{ backgroundColor: style.bg, borderColor: style.border, color: style.text }}
                >
                  {style.copy}
                </span>
              </div>

              <div className="mt-2 flex items-baseline gap-1">
                <span className={`text-3xl font-bold tabular-nums ${scoreTone(team.fit_score)}`}>
                  {team.fit_score.toFixed(1)}
                </span>
                <span className="text-[10px] uppercase tracking-wider text-[var(--muted)]">
                  fit
                </span>
              </div>

              <p className="mt-2 text-[11px] leading-snug text-[var(--muted-strong)]">
                {team.summary}
              </p>

              {team.value_drivers.length > 0 ? (
                <div className="mt-3">
                  <div className="text-[9px] uppercase tracking-wider text-[var(--muted)] mb-1">
                    Value unlock
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {team.value_drivers.slice(0, 3).map((d) => (
                      <Chip key={d.feature_key}>{d.label}</Chip>
                    ))}
                  </div>
                </div>
              ) : null}

              {team.overlap_flags.length > 0 ? (
                <div className="mt-2">
                  <div className="text-[9px] uppercase tracking-wider text-[var(--muted)] mb-1">
                    Already covered
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {team.overlap_flags.slice(0, 2).map((f) => (
                      <Chip key={`${f.feature_key}-${f.teammate_id ?? f.teammate_name}`} tone="warn">
                        {f.teammate_name}
                      </Chip>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="mt-4 text-[10px] text-[var(--muted)]">
        Methodology: {teams[0]?.methodology_version ?? "team_fit_v3_draft_adapter"}{" · "}
        Adapts the player-side team-fit v3 algorithm to score the prospect&apos;s
        translated NBA stat profile against current NBA team rosters.
      </div>
    </section>
  );
}
