"use client";

import { useSearchParams } from "next/navigation";

// Human-friendly labels for diagnosis tag keys so the banner reads like a
// sentence instead of a snake_case token. Kept in the component since it's
// presentation-only; service-side tag keys remain the source of truth.
const DIAGNOSIS_TAG_LABELS: Record<string, string> = {
  elite_corner_gravity: "Elite corner gravity",
  dead_corners: "Dead corners",
  midrange_dependency: "Mid-range dependency",
  rim_pressure_elite: "Elite rim pressure",
  rim_finishing_variance: "Rim finishing variance",
  three_point_volume_low: "Low 3-point volume",
  long_two_diet_problem: "Long-two diet problem",
  high_ftr_creator: "Foul-drawing creator",
  low_ftr_floor_spacer: "Floor-spacer (low FTR)",
  catch_and_shoot_specialist: "Catch-and-shoot specialist",
  off_dribble_heavy: "Off-dribble heavy",
  heat_check_overperformance: "Heat-check overperformance",
  insufficient_sample: "Insufficient sample",
};

const CARD_LABELS: Record<string, string> = {
  role: "Role card",
  strengths: "Strengths & weaknesses",
  shot_profile: "Shot profile",
  usage_efficiency: "Usage & efficiency",
  trajectory: "Trajectory",
};

/** Small inbound-context banner shown above a section when the user arrived
 * via a Scouting Brief card deep link. Renders null when the URL doesn't
 * carry `source=brief`, so it's safe to drop anywhere without a parent guard.
 *
 * Mirrors the Sprint-65 `source=opportunity` / `source=scouting` banner
 * pattern from `/compare` and `/pre-read`.
 */
export function BriefSourceBanner({ anchor }: { anchor: "archetype" | "shot-lab" }) {
  const searchParams = useSearchParams();
  const source = searchParams.get("source");
  if (source !== "brief") return null;

  const card = searchParams.get("card");
  const tagKey = searchParams.get("diagnosis_tag");

  // Only render when the banner anchor matches the card type that deep-linked
  // here — we don't want a shot-lab banner showing above the archetype block.
  if (anchor === "archetype" && card !== "role" && card !== "strengths") return null;
  if (anchor === "shot-lab" && card !== "shot_profile") return null;

  const cardLabel = CARD_LABELS[card ?? ""] ?? "Scouting brief";
  const tagLabel = tagKey ? DIAGNOSIS_TAG_LABELS[tagKey] ?? tagKey : null;

  return (
    <div className="rounded-[1.5rem] border border-[rgba(181,145,78,0.22)] bg-[rgba(181,145,78,0.10)] px-5 py-3 text-sm leading-6 text-[var(--muted-strong)]">
      From <span className="font-semibold text-[var(--foreground)]">Scouting Brief</span> ·{" "}
      <span className="font-semibold text-[var(--foreground)]">{cardLabel}</span>
      {tagLabel ? (
        <>
          {" "}
          · pinning <span className="font-semibold text-[var(--foreground)]">{tagLabel}</span>
        </>
      ) : null}
      .
    </div>
  );
}
