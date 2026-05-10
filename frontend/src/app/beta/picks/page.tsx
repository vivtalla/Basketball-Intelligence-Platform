"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import useSWR from "swr";

import {
  getBracket,
  getLeaderboard,
  getModelPicks,
  scorePicks,
} from "@/lib/api";
import { useSeasonPhase } from "@/hooks/useSeasonPhase";
import type {
  AwardPick,
  LeaderboardResponse,
  ModelPicks,
  PicksAward,
  PicksScorecard,
  PlayoffBracketResponse,
  PlayoffSeriesResponse,
  SeriesPick,
  UserPicks,
} from "@/lib/types";

const FALLBACK_SEASON = "2025-26";
const STORAGE_PREFIX = "bip-picks";
const ROUND_LABELS: Record<number, string> = {
  1: "First Round",
  2: "Conference Semis",
  3: "Conference Finals",
  4: "NBA Finals",
};
const ROUND_POINTS: Record<number, number> = { 1: 1, 2: 2, 3: 4, 4: 8 };
const AWARDS: { key: PicksAward; label: string; rationale: string }[] = [
  { key: "mvp", label: "Most Valuable Player", rationale: "Regular-season MVP" },
  { key: "coy", label: "Coach of the Year", rationale: "Coach of the Year" },
  { key: "dpoy", label: "Defensive Player of the Year", rationale: "DPOY" },
  { key: "roy", label: "Rookie of the Year", rationale: "ROY" },
];

function storageKey(season: string): string {
  return `${STORAGE_PREFIX}-${season}`;
}

function loadFromStorage(season: string): UserPicks {
  if (typeof window === "undefined") {
    return { season, series_picks: [], award_picks: [] };
  }
  try {
    const raw = window.localStorage.getItem(storageKey(season));
    if (!raw) return { season, series_picks: [], award_picks: [] };
    const parsed = JSON.parse(raw) as UserPicks;
    if (parsed && typeof parsed === "object" && parsed.season === season) {
      return {
        season,
        series_picks: parsed.series_picks ?? [],
        award_picks: parsed.award_picks ?? [],
      };
    }
  } catch {
    // localStorage may be unavailable or contain corrupted data — start fresh.
  }
  return { season, series_picks: [], award_picks: [] };
}

function saveToStorage(picks: UserPicks): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(storageKey(picks.season), JSON.stringify(picks));
  } catch {
    // Storage write failed — picks remain in memory for this session only.
  }
}

function flattenSeries(bracket: PlayoffBracketResponse | undefined): PlayoffSeriesResponse[] {
  if (!bracket) return [];
  const out: PlayoffSeriesResponse[] = [];
  out.push(...bracket.east);
  out.push(...bracket.west);
  if (bracket.finals) out.push(bracket.finals);
  return out;
}

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    correct: "bg-emerald-100 text-emerald-800 border-emerald-300",
    incorrect: "bg-rose-100 text-rose-800 border-rose-300",
    pending: "bg-amber-100 text-amber-800 border-amber-300",
    missing: "bg-stone-100 text-stone-700 border-stone-300",
  };
  const cls = styles[status] ?? styles.missing;
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider ${cls}`}
    >
      {status}
    </span>
  );
}

function MethodologyPopover() {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-[var(--border)] bg-white text-xs text-[var(--muted)] hover:text-[var(--foreground)]"
        aria-label="Methodology"
        aria-expanded={open}
      >
        i
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-80 rounded-xl border border-[var(--border)] bg-white p-4 text-xs text-[var(--muted)] shadow-lg">
          <p className="font-mono text-[10px] uppercase tracking-wider text-[var(--foreground)]">
            Scoring rubric
          </p>
          <ul className="mt-2 space-y-1.5">
            <li>Round 1 winner: <span className="font-semibold">1 pt</span></li>
            <li>Round 2 winner: <span className="font-semibold">2 pts</span></li>
            <li>Conference Finals: <span className="font-semibold">4 pts</span></li>
            <li>NBA Finals: <span className="font-semibold">8 pts</span></li>
            <li>Exact games (4–7): <span className="font-semibold">+50%</span> bonus on the round value, only if winner correct.</li>
            <li>Each award (MVP / COY / DPOY / ROY): <span className="font-semibold">5 pts</span></li>
          </ul>
          <p className="mt-3">
            Picks live in your browser only — nothing is saved server-side.
            Compare against CourtVue&apos;s simulator and award models.
          </p>
        </div>
      )}
    </div>
  );
}

interface SeriesRowProps {
  series: PlayoffSeriesResponse;
  pick: SeriesPick | undefined;
  modelWinner: string | null;
  modelGames: number | null;
  onPick: (winner: string, games?: number) => void;
}

function SeriesRow({ series, pick, modelWinner, modelGames, onPick }: SeriesRowProps) {
  const top = series.top_seed_team_abbr ?? "TOP";
  const bottom = series.bottom_seed_team_abbr ?? "BOT";
  const userWinner = pick?.winner_team_abbr;
  const userGames = pick?.games ?? null;

  const decided = series.status === "closed";
  const actualWinnerId = series.winner_team_id;
  const actualWinnerAbbr =
    actualWinnerId === series.top_seed_team_id
      ? top
      : actualWinnerId === series.bottom_seed_team_id
      ? bottom
      : null;

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-white p-4 space-y-3">
      <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-wider text-[var(--muted)]">
        <span>{ROUND_LABELS[series.round] ?? `Round ${series.round}`}</span>
        {decided && actualWinnerAbbr && (
          <span className="text-emerald-700">Actual: {actualWinnerAbbr}</span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => onPick(top, userGames ?? undefined)}
          className={`flex-1 rounded-xl border px-3 py-2 text-left text-sm transition ${
            userWinner === top
              ? "border-[var(--accent)] bg-[var(--accent)] text-white shadow"
              : "border-[var(--border)] bg-white hover:bg-stone-50"
          }`}
        >
          <span className="block text-[10px] font-mono uppercase tracking-wider opacity-70">
            #{series.top_seed} seed
          </span>
          <span className="block text-base font-semibold">{top}</span>
        </button>
        <span className="text-xs text-[var(--muted)]">vs</span>
        <button
          type="button"
          onClick={() => onPick(bottom, userGames ?? undefined)}
          className={`flex-1 rounded-xl border px-3 py-2 text-left text-sm transition ${
            userWinner === bottom
              ? "border-[var(--accent)] bg-[var(--accent)] text-white shadow"
              : "border-[var(--border)] bg-white hover:bg-stone-50"
          }`}
        >
          <span className="block text-[10px] font-mono uppercase tracking-wider opacity-70">
            #{series.bottom_seed} seed
          </span>
          <span className="block text-base font-semibold">{bottom}</span>
        </button>
      </div>

      <div className="flex items-center justify-between gap-3">
        <label className="text-xs text-[var(--muted)] flex items-center gap-2">
          <span>In</span>
          <select
            value={userGames ?? ""}
            onChange={(e) => {
              const next = e.target.value === "" ? undefined : Number(e.target.value);
              if (userWinner) onPick(userWinner, next);
            }}
            disabled={!userWinner}
            className="rounded-md border border-[var(--border)] bg-white px-2 py-1 text-sm disabled:opacity-50"
          >
            <option value="">— games —</option>
            <option value="4">4 games</option>
            <option value="5">5 games</option>
            <option value="6">6 games</option>
            <option value="7">7 games</option>
          </select>
        </label>
        <p className="text-[11px] text-[var(--muted)] text-right">
          Worth <span className="font-semibold">{ROUND_POINTS[series.round] ?? 1}pt</span>
          {userGames ? ` (+${Math.ceil((ROUND_POINTS[series.round] ?? 1) / 2)} length)` : ""}
        </p>
      </div>

      {modelWinner && (
        <p className="text-[11px] text-[var(--muted)]">
          <span className="font-mono uppercase tracking-wider">Model:</span>{" "}
          <span className="font-semibold text-[var(--foreground)]">{modelWinner}</span>
          {modelGames ? ` in ${modelGames}` : ""}
        </p>
      )}
    </div>
  );
}

interface AwardRowProps {
  award: { key: PicksAward; label: string; rationale: string };
  pick: AwardPick | undefined;
  candidates: { id: number; name: string }[];
  modelPick: { player_id: number | null; player_name: string | null } | null;
  onChange: (playerId: number | null, playerName: string | null) => void;
}

function AwardRow({ award, pick, candidates, modelPick, onChange }: AwardRowProps) {
  return (
    <div className="rounded-2xl border border-[var(--border)] bg-white p-4 space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-[var(--foreground)]">{award.label}</p>
        <span className="text-[10px] font-mono uppercase tracking-wider text-[var(--muted)]">
          5 pts
        </span>
      </div>
      <select
        value={pick?.player_id ?? ""}
        onChange={(e) => {
          if (e.target.value === "") {
            onChange(null, null);
            return;
          }
          const id = Number(e.target.value);
          const cand = candidates.find((c) => c.id === id);
          onChange(id, cand?.name ?? null);
        }}
        className="w-full rounded-md border border-[var(--border)] bg-white px-2 py-1.5 text-sm"
      >
        <option value="">— select a player —</option>
        {candidates.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>
      {modelPick && modelPick.player_name && (
        <p className="text-[11px] text-[var(--muted)]">
          <span className="font-mono uppercase tracking-wider">Model:</span>{" "}
          <span className="font-semibold text-[var(--foreground)]">
            {modelPick.player_name}
          </span>
        </p>
      )}
    </div>
  );
}

function buildSeriesNarration(
  seriesId: string,
  seriesLookup: Map<string, PlayoffSeriesResponse>,
  scorecard: PicksScorecard | undefined
): string | null {
  if (!scorecard) return null;
  const result = scorecard.series_results.find((r) => r.series_id === seriesId);
  if (!result || !result.user_winner_abbr) return null;
  const series = seriesLookup.get(seriesId);
  const round = series ? ROUND_LABELS[series.round] ?? `Round ${series.round}` : "Series";
  const userPart = `You picked ${result.user_winner_abbr}${
    result.user_games ? ` in ${result.user_games}` : ""
  }`;
  const modelPart = result.model_winner_abbr
    ? `model picked ${result.model_winner_abbr}${
        result.model_games ? ` in ${result.model_games}` : ""
      }`
    : null;
  if (result.actual_winner_abbr) {
    if (result.winner_status === "correct") {
      const lengthNote =
        result.games_status === "correct"
          ? " — exact length too."
          : result.games_status === "incorrect"
          ? ` (actual: ${result.actual_games ?? "?"} games)`
          : "";
      return `${round}: ${userPart}. Right call${lengthNote}.`;
    }
    return `${round}: ${userPart}, but ${result.actual_winner_abbr} won. ${
      modelPart ? `(${modelPart}.)` : ""
    }`;
  }
  return `${round}: ${userPart}. ${modelPart ? `(${modelPart}.)` : ""}`;
}

export default function PicksPage() {
  const phase = useSeasonPhase();
  const season = phase.season ?? FALLBACK_SEASON;
  // Re-mount the inner picker whenever the resolved season changes so the
  // localStorage hydration runs naturally inside lazy useState init,
  // avoiding setState-in-effect / refs-in-render lint complaints.
  return <PicksPicker key={season} season={season} />;
}

function PicksPicker({ season }: { season: string }) {
  // Lazy-init from localStorage scoped to this season.
  const [picks, setPicks] = useState<UserPicks>(() => loadFromStorage(season));
  const [scorecard, setScorecard] = useState<PicksScorecard | undefined>();
  const [scoreLoading, setScoreLoading] = useState(false);
  const [scoreError, setScoreError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { data: bracket } = useSWR<PlayoffBracketResponse>(
    season ? `bracket-${season}` : null,
    () => getBracket(season)
  );
  const { data: model } = useSWR<ModelPicks>(
    season ? `picks-model-${season}` : null,
    () => getModelPicks(season)
  );

  // Pull a small candidate pool for each award from the leaderboard. Same
  // metric (BPM) for all four awards so the dropdowns aren't empty when
  // award-specific stats aren't tracked yet (Sprint 78 scope decision).
  const { data: bpmLeaders } = useSWR<LeaderboardResponse>(
    season ? `picks-leaders-bpm-${season}` : null,
    () => getLeaderboard("bpm", season, "Regular Season", 30)
  );

  const seriesList = useMemo(() => flattenSeries(bracket), [bracket]);
  const seriesLookup = useMemo(() => {
    const map = new Map<string, PlayoffSeriesResponse>();
    for (const s of seriesList) map.set(s.series_id, s);
    return map;
  }, [seriesList]);

  const candidates = useMemo(() => {
    if (!bpmLeaders?.entries) return [];
    return bpmLeaders.entries.map((e) => ({ id: e.player_id, name: e.player_name }));
  }, [bpmLeaders]);

  const modelSeriesById = useMemo(() => {
    const map = new Map<string, { winner: string | null; games: number | null }>();
    if (model) {
      for (const m of model.series_picks) {
        map.set(m.series_id, { winner: m.winner_team_abbr, games: m.games });
      }
    }
    return map;
  }, [model]);

  const modelAwardsByKey = useMemo(() => {
    const map = new Map<string, { player_id: number | null; player_name: string | null }>();
    if (model) {
      for (const a of model.award_picks) {
        map.set(a.award, { player_id: a.player_id, player_name: a.player_name });
      }
    }
    return map;
  }, [model]);

  const updatePicks = useCallback((next: UserPicks) => {
    setPicks(next);
    saveToStorage(next);
  }, []);

  const handleSeriesPick = useCallback(
    (seriesId: string, winner: string, games?: number) => {
      const filtered = picks.series_picks.filter((p) => p.series_id !== seriesId);
      const nextPick: SeriesPick = {
        series_id: seriesId,
        winner_team_abbr: winner,
        games: games ?? null,
      };
      updatePicks({
        ...picks,
        series_picks: [...filtered, nextPick],
      });
    },
    [picks, updatePicks]
  );

  const handleAwardChange = useCallback(
    (award: PicksAward, playerId: number | null, playerName: string | null) => {
      const filtered = picks.award_picks.filter((p) => p.award !== award);
      const next = playerId
        ? [...filtered, { award, player_id: playerId, player_name: playerName }]
        : filtered;
      updatePicks({ ...picks, award_picks: next });
    },
    [picks, updatePicks]
  );

  const handleReset = useCallback(() => {
    const fresh: UserPicks = { season, series_picks: [], award_picks: [] };
    updatePicks(fresh);
  }, [season, updatePicks]);

  // Debounced auto-score whenever picks change. Backend has no persistence,
  // so this just refreshes the scorecard panel. When the user has no picks
  // at all we skip the round-trip and show the empty scorecard derived
  // below — no setState here in that case.
  const hasPicks = picks.series_picks.length > 0 || picks.award_picks.length > 0;
  useEffect(() => {
    if (!hasPicks) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    let cancelled = false;
    debounceRef.current = setTimeout(() => {
      scorePicks(picks)
        .then((sc) => {
          if (!cancelled) {
            setScorecard(sc);
            setScoreLoading(false);
          }
        })
        .catch((err: unknown) => {
          if (!cancelled) {
            setScoreError(err instanceof Error ? err.message : "Score request failed");
            setScoreLoading(false);
          }
        });
      if (!cancelled) {
        setScoreLoading(true);
        setScoreError(null);
      }
    }, 350);
    return () => {
      cancelled = true;
    };
  }, [hasPicks, picks]);

  // When picks go empty, the scorecard / error / loading state gets cleared
  // via this derived view — no setState in render path required.
  const effectiveScorecard = hasPicks ? scorecard : undefined;
  const effectiveScoreError = hasPicks ? scoreError : null;
  const effectiveScoreLoading = hasPicks ? scoreLoading : false;

  const totalPossibleAcrossBracket = useMemo(() => {
    let possible = 0;
    for (const s of seriesList) {
      possible += (ROUND_POINTS[s.round] ?? 1) + Math.ceil((ROUND_POINTS[s.round] ?? 1) / 2);
    }
    possible += AWARDS.length * 5;
    return possible;
  }, [seriesList]);

  const seriesByRound = useMemo(() => {
    const map = new Map<number, PlayoffSeriesResponse[]>();
    for (const s of seriesList) {
      const list = map.get(s.round);
      if (list) list.push(s);
      else map.set(s.round, [s]);
    }
    return Array.from(map.entries()).sort((a, b) => a[0] - b[0]);
  }, [seriesList]);

  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <Link href="/" className="bip-link inline-flex items-center gap-1 text-sm">
          ← Back to Home
        </Link>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="bip-kicker">Bracket Pick&apos;em</p>
            <h1 className="bip-display text-4xl font-semibold text-[var(--foreground)]">
              You vs. CourtVue
            </h1>
            <p className="mt-2 max-w-2xl text-[var(--muted)]">
              Pick every series, choose the length, lock your award votes — then
              we&apos;ll tally your accuracy against CourtVue&apos;s model. Picks
              save to your browser only; nothing is sent off your machine.
            </p>
          </div>
          <MethodologyPopover />
        </div>
      </div>

      {/* Scorecard rail */}
      <div className="rounded-2xl border border-[var(--border)] bg-white p-5">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-[10px] font-mono uppercase tracking-wider text-[var(--muted)]">
              Your points
            </p>
            <p className="mt-1 text-2xl font-semibold text-[var(--foreground)]">
              {effectiveScorecard ? effectiveScorecard.total_points : 0}
              <span className="ml-1 text-sm font-normal text-[var(--muted)]">
                / {effectiveScorecard?.total_points_possible ?? totalPossibleAcrossBracket}
              </span>
            </p>
          </div>
          <div>
            <p className="text-[10px] font-mono uppercase tracking-wider text-[var(--muted)]">
              Accuracy
            </p>
            <p className="mt-1 text-2xl font-semibold text-[var(--foreground)]">
              {effectiveScorecard ? `${effectiveScorecard.accuracy_pct}%` : "—"}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-mono uppercase tracking-wider text-[var(--muted)]">
              CourtVue model
            </p>
            <p className="mt-1 text-2xl font-semibold text-[var(--foreground)]">
              {effectiveScorecard ? effectiveScorecard.head_to_head.model_points : 0}
            </p>
          </div>
          <div>
            <p className="text-[10px] font-mono uppercase tracking-wider text-[var(--muted)]">
              Delta vs model
            </p>
            <p
              className={`mt-1 text-2xl font-semibold ${
                effectiveScorecard && effectiveScorecard.head_to_head.delta_points > 0
                  ? "text-emerald-700"
                  : effectiveScorecard && effectiveScorecard.head_to_head.delta_points < 0
                  ? "text-rose-700"
                  : "text-[var(--foreground)]"
              }`}
            >
              {effectiveScorecard
                ? `${effectiveScorecard.head_to_head.delta_points >= 0 ? "+" : ""}${effectiveScorecard.head_to_head.delta_points}`
                : "—"}
            </p>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-3 text-xs text-[var(--muted)]">
          {effectiveScoreLoading && <span>Scoring…</span>}
          {effectiveScoreError && <span className="text-rose-700">{effectiveScoreError}</span>}
          <button
            type="button"
            onClick={handleReset}
            className="ml-auto inline-flex items-center rounded-md border border-[var(--border)] bg-white px-3 py-1.5 text-xs hover:bg-stone-50"
          >
            Reset picks
          </button>
        </div>
      </div>

      {/* Bracket picker */}
      {seriesList.length === 0 ? (
        <div className="bip-empty rounded-3xl p-10 text-center">
          <h2 className="text-xl font-semibold text-[var(--foreground)]">
            No bracket loaded yet.
          </h2>
          <p className="mt-2 text-[var(--muted)]">
            Series matchups will populate when the playoff bracket data is available.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {seriesByRound.map(([round, list]) => (
            <section key={round} className="space-y-3">
              <p className="bip-kicker">{ROUND_LABELS[round] ?? `Round ${round}`}</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {list.map((s) => {
                  const userPick = picks.series_picks.find((p) => p.series_id === s.series_id);
                  const m = modelSeriesById.get(s.series_id);
                  return (
                    <SeriesRow
                      key={s.series_id}
                      series={s}
                      pick={userPick}
                      modelWinner={m?.winner ?? null}
                      modelGames={m?.games ?? null}
                      onPick={(winner, games) => handleSeriesPick(s.series_id, winner, games)}
                    />
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}

      {/* Awards */}
      <section className="space-y-3">
        <p className="bip-kicker">Awards</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {AWARDS.map((award) => {
            const userPick = picks.award_picks.find((p) => p.award === award.key);
            const modelPick = modelAwardsByKey.get(award.key) ?? null;
            return (
              <AwardRow
                key={award.key}
                award={award}
                pick={userPick}
                candidates={candidates}
                modelPick={modelPick}
                onChange={(id, name) => handleAwardChange(award.key, id, name)}
              />
            );
          })}
        </div>
      </section>

      {/* Vs-model narration */}
      {effectiveScorecard && effectiveScorecard.series_results.some((r) => r.user_winner_abbr) && (
        <section className="space-y-3">
          <p className="bip-kicker">You vs. the model</p>
          <ul className="space-y-2 text-sm text-[var(--foreground)]">
            {effectiveScorecard.series_results
              .filter((r) => r.user_winner_abbr)
              .map((r) => {
                const text = buildSeriesNarration(r.series_id, seriesLookup, effectiveScorecard);
                if (!text) return null;
                return (
                  <li
                    key={r.series_id}
                    className="rounded-xl border border-[var(--border)] bg-white p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span>{text}</span>
                      <StatusPill status={r.winner_status} />
                    </div>
                  </li>
                );
              })}
          </ul>
        </section>
      )}
    </div>
  );
}
