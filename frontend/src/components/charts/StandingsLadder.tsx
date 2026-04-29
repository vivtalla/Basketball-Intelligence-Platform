"use client";

/**
 * StandingsLadder — bracket-style series tracker. Each row shows the
 * two teams in a series, current W-L bar, seeds, and a "next game"
 * pill. Distinct from the existing top-level <StandingsLadder> which
 * renders the regular-season conference ladder.
 *
 * Data shape mirrors the design-system handoff so the prototype's
 * series array can be passed straight through.
 */
export interface PlayoffSeriesRow {
  team1: { abbr: string; name: string; color: string; seed: number };
  team2: { abbr: string; name: string; color: string; seed: number };
  wins1: number;
  wins2: number;
  total?: number;
  next?: string;
  conf?: string;
  closed?: boolean;
}

interface StandingsLadderProps {
  series: PlayoffSeriesRow[];
}

export default function StandingsLadder({ series }: StandingsLadderProps) {
  return (
    <div className="flex flex-col gap-2.5">
      {series.map((s) => {
        const total = s.total ?? 7;
        const won = s.wins1 >= 4 ? "team1" : s.wins2 >= 4 ? "team2" : null;
        return (
          <div
            key={`${s.team1.abbr}-${s.team2.abbr}`}
            className="grid items-center gap-3 rounded-xl border border-[var(--border)] px-4 py-3"
            style={{
              gridTemplateColumns: "minmax(0, 1.1fr) auto minmax(0, 1.1fr) 110px 90px",
              background: "rgba(255,249,241,0.86)",
              opacity: s.closed ? 0.7 : 1,
            }}
          >
            <TeamCell team={s.team1} winning={won === "team1"} />
            <span
              className="px-2 text-[10px] font-mono uppercase tracking-[0.16em] text-[var(--muted)]"
              style={{ fontFamily: "var(--font-geist-mono)" }}
            >
              vs
            </span>
            <TeamCell team={s.team2} winning={won === "team2"} align="right" />
            <SeriesBar
              wins1={s.wins1}
              wins2={s.wins2}
              color1={s.team1.color}
              color2={s.team2.color}
              total={total}
            />
            <div className="flex flex-col items-end gap-1">
              <span
                className="font-mono text-xs tabular-nums text-[var(--foreground)]"
                style={{ fontFamily: "var(--font-geist-mono)", fontVariantNumeric: "tabular-nums" }}
              >
                {s.wins1}–{s.wins2}
              </span>
              {s.next && (
                <span
                  className="text-[10px] font-mono uppercase tracking-[0.12em]"
                  style={{
                    fontFamily: "var(--font-geist-mono)",
                    color: s.closed ? "var(--muted)" : "var(--signal)",
                    fontWeight: 700,
                  }}
                >
                  {s.next}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function TeamCell({
  team,
  winning,
  align = "left",
}: {
  team: PlayoffSeriesRow["team1"];
  winning: boolean;
  align?: "left" | "right";
}) {
  return (
    <div
      className="flex items-center gap-3"
      style={{ flexDirection: align === "right" ? "row-reverse" : "row" }}
    >
      <span
        className="flex h-9 w-9 items-center justify-center rounded-lg text-[11px] font-bold tracking-[0.04em] text-white"
        style={{
          background: team.color,
          fontFamily: "var(--font-geist-mono)",
        }}
      >
        {team.abbr}
      </span>
      <div style={{ textAlign: align }}>
        <div
          className="text-sm font-bold"
          style={{
            fontFamily: "var(--font-display)",
            color: winning ? "var(--accent-strong)" : "var(--foreground)",
            letterSpacing: "-0.01em",
          }}
        >
          {team.name}
        </div>
        <div
          className="text-[10px] font-mono uppercase tracking-[0.12em] text-[var(--muted)]"
          style={{ fontFamily: "var(--font-geist-mono)" }}
        >
          #{team.seed} seed
        </div>
      </div>
    </div>
  );
}

function SeriesBar({
  wins1,
  wins2,
  color1,
  color2,
  total,
}: {
  wins1: number;
  wins2: number;
  color1: string;
  color2: string;
  total: number;
}) {
  const cells: Array<"team1" | "team2" | "empty"> = [];
  for (let i = 0; i < total; i++) {
    if (i < wins1) cells.push("team1");
    else if (i < wins1 + wins2) cells.push("team2");
    else cells.push("empty");
  }
  return (
    <div className="flex gap-1">
      {cells.map((c, i) => (
        <span
          key={i}
          className="h-2 flex-1 rounded-sm"
          style={{
            background:
              c === "team1"
                ? color1
                : c === "team2"
                ? color2
                : "rgba(53,41,33,0.10)",
          }}
        />
      ))}
    </div>
  );
}
