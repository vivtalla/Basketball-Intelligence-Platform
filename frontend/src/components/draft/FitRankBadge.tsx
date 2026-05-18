// Sprint 102 (Stream B) — compact "best fit DAL" chip for historical class table.
//
// Three-letter abbreviation + small score on hover. Color matches the
// projected_tier palette: higher fit score = greener, lower = more muted.

interface Props {
  abbr: string | null | undefined;
  score: number | null | undefined;
}

function tone(score: number): { bg: string; border: string; text: string } {
  if (score >= 70) return { bg: "rgba(33,72,59,0.10)",    border: "rgba(33,72,59,0.40)",    text: "#21483b" };
  if (score >= 55) return { bg: "rgba(180,137,61,0.10)",  border: "rgba(180,137,61,0.45)",  text: "#9a6f24" };
  return                 { bg: "rgba(120,120,120,0.08)", border: "rgba(120,120,120,0.30)", text: "#878787" };
}

export default function FitRankBadge({ abbr, score }: Props) {
  if (!abbr || score == null) return <span className="text-[var(--muted)]">—</span>;
  const t = tone(score);
  return (
    <span
      className="inline-flex items-baseline gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide tabular-nums"
      style={{ backgroundColor: t.bg, borderColor: t.border, color: t.text }}
      title={`Best team-fit: ${abbr} (score ${score.toFixed(1)})`}
    >
      <span>{abbr}</span>
      <span className="text-[9px] font-normal opacity-75">{score.toFixed(0)}</span>
    </span>
  );
}
