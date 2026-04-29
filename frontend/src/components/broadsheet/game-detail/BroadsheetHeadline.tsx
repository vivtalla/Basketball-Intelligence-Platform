"use client";

/**
 * Sprint 77 (Stream B / EB3): Broadsheet headline + italic subhead + byline
 * for the game-detail surface. The headline is auto-generated from the
 * (winner, score_diff, top_scorer) triple when available, or falls back
 * to a hardcoded evergreen string.
 */

interface BroadsheetHeadlineProps {
  kicker: string;
  winner: string | null;
  scoreDiff: number | null;
  topScorerName: string | null;
  topScorerPts: number | null;
  fallbackTitle: string;
  subhead: string;
}

function buildHeadline(props: BroadsheetHeadlineProps): string {
  const { winner, scoreDiff, topScorerName, topScorerPts, fallbackTitle } = props;
  if (winner && scoreDiff != null && topScorerName != null && topScorerPts != null) {
    if (scoreDiff <= 0) {
      return `${winner} grind out a tight one as ${topScorerName} pours in ${topScorerPts}.`;
    }
    if (scoreDiff <= 6) {
      return `${winner} edge it by ${scoreDiff}; ${topScorerName} carries the load with ${topScorerPts}.`;
    }
    return `${winner} take it by ${scoreDiff}, ${topScorerName} drops ${topScorerPts}.`;
  }
  return fallbackTitle;
}

export default function BroadsheetHeadline(props: BroadsheetHeadlineProps) {
  const headline = buildHeadline(props);
  return (
    <header className="space-y-4">
      <p className="bip-kicker">{props.kicker}</p>
      <h1
        className="bip-display font-bold text-[var(--foreground)]"
        style={{
          fontSize: "clamp(2.2rem, 4.6vw, 3.8rem)",
          letterSpacing: "-0.025em",
          lineHeight: 1.04,
        }}
      >
        {headline}
      </h1>
      <p
        className="italic text-[var(--muted)]"
        style={{
          fontFamily: "var(--font-display)",
          fontSize: "clamp(1rem, 1.4vw, 1.2rem)",
          lineHeight: 1.55,
          maxWidth: "60rem",
        }}
      >
        {props.subhead}
      </p>
      <p
        className="text-xs"
        style={{
          fontFamily: "var(--font-geist-mono)",
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          color: "var(--muted)",
        }}
      >
        — CourtVue Editorial
      </p>
    </header>
  );
}
