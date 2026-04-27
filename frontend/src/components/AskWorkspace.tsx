"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { askCourtVue, getQueryExamples, getQueryMetrics } from "@/lib/api";
import type {
  QueryAskResponse,
  QueryExample,
  QueryMetricMetadata,
  QueryResultRow,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SortDirection = "asc" | "desc";

interface SortState {
  key: string;
  direction: SortDirection;
}

interface ThreadItem {
  id: string;
  title: string;
  excerpt: string;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Static demo thread history (sidebar)
// ---------------------------------------------------------------------------

const DEMO_THREADS: ThreadItem[] = [
  {
    id: "t1",
    title: "Points leaders 2024-25",
    excerpt: "Who leads the NBA in points per game…",
    timestamp: "2h ago",
  },
  {
    id: "t2",
    title: "Best defensive teams by net rating",
    excerpt: "Best teams by net rating in 2024-25…",
    timestamp: "Yesterday",
  },
  {
    id: "t3",
    title: "Shai Gilgeous-Alexander recent form",
    excerpt: "How has Shai played recently?",
    timestamp: "2d ago",
  },
  {
    id: "t4",
    title: "Tatum vs Durant comparison",
    excerpt: "Compare Jayson Tatum to Kevin Durant…",
    timestamp: "3d ago",
  },
  {
    id: "t5",
    title: "High TS% threshold filter",
    excerpt: "Players with at least 25 ppg and 60 ts%…",
    timestamp: "4d ago",
  },
];

// ---------------------------------------------------------------------------
// Suggested query pills shown above the composer
// ---------------------------------------------------------------------------

const SUGGESTED_PILLS = [
  "Who leads in TS% this season?",
  "Compare Tatum vs Durant",
  "Best defensive teams",
  "MVP race leaders",
];

// ---------------------------------------------------------------------------
// Column priority for the inline leaderboard table
// ---------------------------------------------------------------------------

const METRIC_COLUMN_PRIORITY = [
  "pts_pg",
  "reb_pg",
  "ast_pg",
  "ts_pct",
  "off_rating",
  "def_rating",
  "net_rating",
  "pace",
  "wins",
  "losses",
  "pts",
  "reb",
  "ast",
  "min",
  "plus_minus",
];

const FALLBACK_EXAMPLES: QueryExample[] = [
  {
    category: "Player Leaders",
    prompt: "Who leads the NBA in points per game this season?",
    description: "Rank players by a season metric.",
  },
  {
    category: "Team Rankings",
    prompt: "Best teams by net rating in 2025-26",
    description: "Rank teams with official season stats.",
  },
  {
    category: "Recent Form",
    prompt: "How has Shai played recently?",
    description: "Use synced game logs for recent form.",
  },
];

// ---------------------------------------------------------------------------
// Well-known player IDs for chip links (name → person_id)
// ---------------------------------------------------------------------------

const KNOWN_PLAYER_IDS: Record<string, number> = {
  "LeBron James": 2544,
  "Stephen Curry": 201939,
  "Kevin Durant": 201142,
  "Jayson Tatum": 1628369,
  "Nikola Jokic": 203999,
  "Luka Doncic": 1629029,
  "Shai Gilgeous-Alexander": 1628983,
  "Giannis Antetokounmpo": 203507,
  "Joel Embiid": 203954,
  "Anthony Davis": 203076,
  "Devin Booker": 1626164,
  "Damian Lillard": 203081,
  "Donovan Mitchell": 1628378,
  "Tyrese Haliburton": 1630169,
  "Anthony Edwards": 1630162,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function metricLabel(key: string, metadata?: QueryMetricMetadata) {
  if (metadata) return metadata.label;
  const fallback: Record<string, string> = {
    gp: "GP",
    wins: "W",
    losses: "L",
    pts: "PTS",
    reb: "REB",
    ast: "AST",
    min: "MIN",
    plus_minus: "+/-",
  };
  return fallback[key] ?? key.replace(/_/g, " ").toUpperCase();
}

function formatMetricValue(
  value: string | number | null | undefined,
  metadata?: QueryMetricMetadata
) {
  if (value == null || value === "") return "-";
  if (typeof value === "string") return value;
  if (metadata?.format === "percent") return `${(value * 100).toFixed(1)}%`;
  if (metadata?.format === "integer") return Math.round(value).toLocaleString();
  if (Number.isInteger(value)) return value.toLocaleString();
  return value.toFixed(1);
}

function sortValue(row: QueryResultRow, key: string): string | number {
  if (key === "rank") return row.rank;
  if (key === "name") return row.name;
  if (key === "value") return row.value ?? Number.NEGATIVE_INFINITY;
  const value = row.metrics[key];
  if (typeof value === "number") return value;
  if (typeof value === "string") return value;
  return Number.NEGATIVE_INFINITY;
}

function sortRows(rows: QueryResultRow[], sort: SortState) {
  return [...rows].sort((a, b) => {
    const aValue = sortValue(a, sort.key);
    const bValue = sortValue(b, sort.key);
    if (typeof aValue === "number" && typeof bValue === "number") {
      return sort.direction === "asc" ? aValue - bValue : bValue - aValue;
    }
    return sort.direction === "asc"
      ? String(aValue).localeCompare(String(bValue))
      : String(bValue).localeCompare(String(aValue));
  });
}

/** Scan response summary text for known player names and return chip data. */
function extractPlayerChips(
  text: string
): Array<{ name: string; id: number }> {
  const found: Array<{ name: string; id: number }> = [];
  for (const [name, id] of Object.entries(KNOWN_PLAYER_IDS)) {
    if (text.includes(name)) {
      found.push({ name, id });
    }
  }
  return found;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SortableHeader({
  label,
  sortKey,
  activeSort,
  onSort,
  title,
}: {
  label: string;
  sortKey: string;
  activeSort: SortState;
  onSort: (key: string) => void;
  title?: string;
}) {
  const isActive = activeSort.key === sortKey;
  return (
    <th className="whitespace-nowrap px-3 py-2 font-semibold">
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        title={title}
        className="inline-flex items-center gap-1 text-left transition hover:text-[var(--accent-strong)]"
      >
        <span>{label}</span>
        <span className={isActive ? "text-[var(--accent-strong)]" : "text-[var(--muted)]"}>
          {isActive ? (activeSort.direction === "asc" ? "▲" : "▼") : "⇅"}
        </span>
      </button>
    </th>
  );
}

/** Compact leaderboard table embedded in an assistant chat bubble. */
function InlineLeaderboardTable({
  response,
  metadataMap,
  metricColumns,
  sort,
  sortedRows,
  onToggleSort,
}: {
  response: QueryAskResponse;
  metadataMap: Map<string, QueryMetricMetadata>;
  metricColumns: string[];
  sort: SortState;
  sortedRows: QueryResultRow[];
  onToggleSort: (key: string) => void;
}) {
  return (
    <div className="mt-3 overflow-hidden rounded-lg border border-[var(--border)]">
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse text-xs">
          <thead className="bg-[rgba(53,41,33,0.06)] text-left text-[10px] uppercase tracking-[0.14em] text-[var(--muted)]">
            <tr>
              <SortableHeader
                label="#"
                sortKey="rank"
                activeSort={sort}
                onSort={onToggleSort}
              />
              <SortableHeader
                label="Name"
                sortKey="name"
                activeSort={sort}
                onSort={onToggleSort}
              />
              <SortableHeader
                label={response.intent.metric_label ?? "Result"}
                sortKey="value"
                activeSort={sort}
                onSort={onToggleSort}
                title={
                  response.metrics.find(
                    (m) => m.key === response.intent.metric_key
                  )?.description
                }
              />
              {metricColumns.map((key) => (
                <SortableHeader
                  key={key}
                  label={metricLabel(key, metadataMap.get(key))}
                  sortKey={key}
                  activeSort={sort}
                  onSort={onToggleSort}
                  title={metadataMap.get(key)?.description}
                />
              ))}
              <th className="whitespace-nowrap px-3 py-2 font-semibold">
                Open
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {sortedRows.map((row) => (
              <tr
                key={`${row.entity_type}-${row.entity_id ?? row.rank}`}
                className="hover:bg-[rgba(33,72,59,0.045)]"
              >
                <td className="whitespace-nowrap px-3 py-2 font-semibold text-[var(--muted)]">
                  {row.rank}
                </td>
                <td className="min-w-44 px-3 py-2">
                  <div className="font-semibold text-[var(--foreground)]">
                    {row.name}
                  </div>
                  <div className="text-[10px] text-[var(--muted)]">
                    {row.subtitle ??
                      row.team_abbreviation ??
                      row.abbreviation ??
                      row.entity_type}
                  </div>
                </td>
                <td className="whitespace-nowrap px-3 py-2 font-semibold text-[var(--accent-strong)]">
                  {row.formatted_value ?? formatMetricValue(row.value)}
                </td>
                {metricColumns.map((key) => (
                  <td
                    key={key}
                    className="whitespace-nowrap px-3 py-2 text-[var(--foreground)]"
                  >
                    {formatMetricValue(row.metrics[key], metadataMap.get(key))}
                  </td>
                ))}
                <td className="whitespace-nowrap px-3 py-2">
                  {row.detail_url ? (
                    <Link
                      href={row.detail_url}
                      className="bip-link text-xs font-semibold"
                    >
                      Open
                    </Link>
                  ) : (
                    <span className="text-[var(--muted)]">-</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Query trace collapsible rendered below an assistant bubble. */
function QueryTrace({ response }: { response: QueryAskResponse }) {
  const filterCount = response.intent.filters.length;
  const traceLabel = `Query trace · ${filterCount} filter${filterCount !== 1 ? "s" : ""} applied`;

  return (
    <details className="mt-2 text-xs text-[var(--muted)]">
      <summary className="cursor-pointer select-none font-medium hover:text-[var(--foreground)]">
        {traceLabel}
      </summary>
      <div className="mt-2 rounded-lg border border-[var(--border)] bg-[rgba(53,41,33,0.04)] p-3 space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-[var(--foreground)]">Season:</span>
          <span>{response.intent.season ?? "–"}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-semibold text-[var(--foreground)]">Source:</span>
          <span>{response.source}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-semibold text-[var(--foreground)]">Intent:</span>
          <span>{response.intent.intent_type.replace(/_/g, " ")}</span>
        </div>
        {response.intent.filters.length > 0 && (
          <div>
            <span className="font-semibold text-[var(--foreground)]">Filters:</span>
            <ul className="mt-1 space-y-0.5 pl-3">
              {response.intent.filters.map((f) => (
                <li key={`${f.metric_key}-${f.value}`}>
                  {f.label}{" "}
                  {f.operator === "gte" ? "≥" : "≤"}{" "}
                  {f.formatted_value}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </details>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function AskWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryParam = searchParams.get("q") ?? "";

  const [draft, setDraft] = useState(queryParam);
  const [examples, setExamples] = useState<QueryExample[]>(FALLBACK_EXAMPLES);
  const [globalMetrics, setGlobalMetrics] = useState<QueryMetricMetadata[]>([]);
  const [response, setResponse] = useState<QueryAskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [sort, setSort] = useState<SortState>({ key: "rank", direction: "asc" });
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);

  // Composer metadata state
  const [season, setSeason] = useState("2024-25");
  const [perGame, setPerGame] = useState(true);

  useEffect(() => {
    getQueryExamples()
      .then((items) => setExamples(items.length ? items : FALLBACK_EXAMPLES))
      .catch(() => setExamples(FALLBACK_EXAMPLES));
    getQueryMetrics()
      .then(setGlobalMetrics)
      .catch(() => setGlobalMetrics([]));
  }, []);

  useEffect(() => {
    if (!queryParam.trim()) {
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      setIsLoading(true);
      setError(null);
      askCourtVue({ question: queryParam })
        .then((payload) => {
          if (!cancelled) {
            setResponse(payload);
            setSort({ key: "rank", direction: "asc" });
          }
        })
        .catch((err) => {
          if (!cancelled) {
            setResponse(null);
            setError(
              err instanceof Error
                ? err.message
                : "CourtVue Ask could not answer that right now."
            );
          }
        })
        .finally(() => {
          if (!cancelled) setIsLoading(false);
        });
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [queryParam]);

  const metadataMap = useMemo(() => {
    const map = new Map<string, QueryMetricMetadata>();
    for (const metric of globalMetrics) map.set(metric.key, metric);
    for (const metric of response?.metrics ?? []) map.set(metric.key, metric);
    return map;
  }, [globalMetrics, response?.metrics]);

  const metricColumns = useMemo(() => {
    const keys = new Set<string>();
    for (const row of response?.rows ?? []) {
      Object.keys(row.metrics ?? {}).forEach((key) => keys.add(key));
    }
    return Array.from(keys).sort((a, b) => {
      const aIndex = METRIC_COLUMN_PRIORITY.indexOf(a);
      const bIndex = METRIC_COLUMN_PRIORITY.indexOf(b);
      if (aIndex !== -1 || bIndex !== -1) {
        return (
          (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex)
        );
      }
      return metricLabel(a, metadataMap.get(a)).localeCompare(
        metricLabel(b, metadataMap.get(b))
      );
    });
  }, [metadataMap, response?.rows]);

  const sortedRows = useMemo(
    () => sortRows(response?.rows ?? [], sort),
    [response?.rows, sort]
  );

  const playerChips = useMemo(() => {
    if (!response) return [];
    const text = `${response.answer.title} ${response.answer.summary}`;
    return extractPlayerChips(text);
  }, [response]);

  function submitQuestion(question: string) {
    const trimmed = question.trim();
    if (!trimmed) return;
    setDraft(trimmed);
    router.push(`/ask?q=${encodeURIComponent(trimmed)}`);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitQuestion(draft);
  }

  function toggleSort(key: string) {
    setSort((current) =>
      current.key === key
        ? { key, direction: current.direction === "asc" ? "desc" : "asc" }
        : {
            key,
            direction:
              key === "rank" || key === "name" ? "asc" : "desc",
          }
    );
  }

  const intentLabel = response?.intent.entity_type
    ? `${response.intent.entity_type} ${response.intent.intent_type.replace(/_/g, " ")}`
    : response?.intent.intent_type.replace(/_/g, " ");

  // The current query (user bubble)
  const hasQuery = !!queryParam.trim();

  return (
    <div className="flex gap-0 min-h-[calc(100vh-12rem)]">
      {/* ------------------------------------------------------------------ */}
      {/* LEFT SIDEBAR — thread history                                        */}
      {/* ------------------------------------------------------------------ */}
      <aside
        className="hidden lg:flex flex-col shrink-0 w-[260px] mr-6"
        style={{ position: "sticky", top: "5.5rem", alignSelf: "flex-start", maxHeight: "calc(100vh - 7rem)" }}
      >
        <div className="flex flex-col h-full rounded-xl border border-[var(--border)] bg-[var(--surface)] shadow-[var(--shadow)] overflow-hidden">
          {/* Sidebar header */}
          <div className="px-4 pt-4 pb-3 border-b border-[var(--border)]">
            <p className="bip-kicker mb-1">Ask CourtVue</p>
            <p className="text-sm font-semibold text-[var(--foreground)]">Threads</p>
          </div>

          {/* Thread list */}
          <nav className="flex-1 overflow-y-auto py-2">
            {DEMO_THREADS.map((thread) => (
              <button
                key={thread.id}
                type="button"
                onClick={() => setActiveThreadId(thread.id)}
                className={[
                  "w-full text-left px-4 py-3 transition hover:bg-[rgba(33,72,59,0.06)]",
                  activeThreadId === thread.id
                    ? "bg-[rgba(33,72,59,0.08)] border-l-2 border-[var(--accent)]"
                    : "border-l-2 border-transparent",
                ].join(" ")}
              >
                <div className="flex items-center justify-between gap-2 mb-0.5">
                  <span className="text-xs font-semibold text-[var(--foreground)] truncate">
                    {thread.title}
                  </span>
                  <span className="text-[10px] text-[var(--muted)] shrink-0">
                    {thread.timestamp}
                  </span>
                </div>
                <p className="text-[11px] text-[var(--muted)] truncate leading-4">
                  {thread.excerpt}
                </p>
              </button>
            ))}
          </nav>

          {/* New thread button */}
          <div className="p-3 border-t border-[var(--border)]">
            <button
              type="button"
              onClick={() => {
                setActiveThreadId(null);
                setDraft("");
                router.push("/ask");
              }}
              className="w-full flex items-center justify-center gap-2 rounded-lg border border-[var(--border)] bg-[rgba(255,251,246,0.9)] px-3 py-2 text-xs font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
            >
              <span className="text-base leading-none">+</span>
              New thread
            </button>
          </div>
        </div>
      </aside>

      {/* ------------------------------------------------------------------ */}
      {/* RIGHT MAIN — chat area                                              */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex-1 min-w-0 flex flex-col gap-6">

        {/* Page hero (shown when no active query) */}
        {!hasQuery && (
          <section className="relative overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--surface)] px-5 py-6 shadow-[var(--shadow)]">
            <div className="absolute inset-x-0 top-0 h-1 bg-[linear-gradient(90deg,#21483b,#b4893d,#7f332b)]" />
            <p className="bip-kicker mb-2">CourtVue Ask</p>
            <h1 className="bip-display text-3xl font-semibold text-[var(--foreground)] sm:text-4xl">
              Ask for the number behind the question.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--muted)]">
              Pull player leaders, team rankings, threshold filters, recent form, and compare links from the data already synced into CourtVue.
            </p>

            {/* Example cards */}
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              {examples.slice(0, 3).map((example) => (
                <button
                  key={example.prompt}
                  type="button"
                  onClick={() => submitQuestion(example.prompt)}
                  className="rounded-lg border border-[var(--border)] bg-[rgba(255,255,255,0.52)] p-4 text-left transition hover:-translate-y-0.5 hover:border-[var(--accent)] hover:shadow-[0_8px_24px_rgba(33,72,59,0.1)]"
                >
                  <p className="bip-kicker text-[10px]">{example.category}</p>
                  <p className="mt-2 text-sm font-semibold text-[var(--foreground)]">{example.prompt}</p>
                  <p className="mt-1.5 text-xs leading-5 text-[var(--muted)]">{example.description}</p>
                </button>
              ))}
            </div>
          </section>
        )}

        {/* Chat thread */}
        {hasQuery && (
          <div className="flex flex-col gap-5">
            {/* USER bubble */}
            <div className="flex justify-end">
              <div className="max-w-[78%] rounded-2xl rounded-tr-md bg-[var(--accent)] px-4 py-3 text-sm font-medium text-[var(--accent-ink)] shadow-[0_4px_18px_rgba(33,72,59,0.22)]">
                {queryParam}
              </div>
            </div>

            {/* LOADING state */}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bip-panel rounded-2xl rounded-tl-md px-5 py-4 text-sm text-[var(--muted)]">
                  <span className="inline-flex gap-1 items-center">
                    <span className="animate-pulse">Thinking</span>
                    <span className="animate-bounce delay-75">.</span>
                    <span className="animate-bounce delay-150">.</span>
                    <span className="animate-bounce delay-300">.</span>
                  </span>
                </div>
              </div>
            )}

            {/* ERROR bubble */}
            {error && !isLoading && (
              <div className="flex justify-start">
                <div className="max-w-[85%] rounded-2xl rounded-tl-md border border-[rgba(127,51,43,0.28)] bg-[rgba(127,51,43,0.08)] px-5 py-4 text-sm text-[var(--danger-ink)]">
                  {error}
                </div>
              </div>
            )}

            {/* ASSISTANT bubble */}
            {response && !isLoading && (
              <div className="flex justify-start">
                <div className="w-full max-w-full">
                  {/* Main assistant bubble */}
                  <div className="bip-panel rounded-2xl rounded-tl-md px-5 py-4">
                    {/* Intent kicker + title */}
                    <p className="bip-kicker mb-1">{intentLabel}</p>
                    <h2 className="bip-display text-xl font-semibold text-[var(--foreground)]">
                      {response.answer.title}
                    </h2>
                    <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
                      {response.answer.summary}
                    </p>

                    {/* Filter chips */}
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      <span className="rounded-md border border-[var(--border)] px-2.5 py-1 text-xs font-semibold text-[var(--muted)]">
                        {response.intent.season ?? "Season"} · {response.source}
                      </span>
                      {response.intent.filters.map((filter) => (
                        <span
                          key={`${filter.metric_key}-${filter.value}`}
                          className="rounded-md border border-[var(--accent-soft)] bg-[rgba(33,72,59,0.08)] px-2.5 py-1 text-xs font-semibold text-[var(--accent-strong)]"
                        >
                          {filter.label}{" "}
                          {filter.operator === "gte" ? "≥" : "≤"}{" "}
                          {filter.formatted_value}
                        </span>
                      ))}
                    </div>

                    {/* Primary value callout */}
                    {response.answer.primary_value && (
                      <div className="mt-3 inline-flex flex-col rounded-lg border border-[var(--border)] bg-[rgba(33,72,59,0.06)] px-3 py-2">
                        <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                          {response.answer.primary_label ?? "Result"}
                        </span>
                        <span className="mt-0.5 text-2xl font-semibold text-[var(--foreground)]">
                          {response.answer.primary_value}
                        </span>
                        {response.answer.href && (
                          <Link
                            href={response.answer.href}
                            className="bip-link mt-1.5 text-xs font-semibold"
                          >
                            Open workspace
                          </Link>
                        )}
                      </div>
                    )}

                    {/* Warnings */}
                    {response.warnings.length > 0 && (
                      <div className="mt-3 rounded-lg border border-[rgba(180,137,61,0.32)] bg-[rgba(180,137,61,0.10)] p-3 text-xs text-[var(--muted)]">
                        {response.warnings.join(" ")}
                      </div>
                    )}

                    {/* Inline leaderboard table */}
                    {response.rows.length > 0 && (
                      <InlineLeaderboardTable
                        response={response}
                        metadataMap={metadataMap}
                        metricColumns={metricColumns}
                        sort={sort}
                        sortedRows={sortedRows}
                        onToggleSort={toggleSort}
                      />
                    )}

                    {/* Player chip links */}
                    {playerChips.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {playerChips.map(({ name, id }) => (
                          <Link
                            key={id}
                            href={`/players/${id}`}
                            className="inline-flex items-center gap-1.5 rounded-full border border-[var(--accent-soft)] bg-[rgba(33,72,59,0.07)] px-3 py-1.5 text-xs font-semibold text-[var(--accent-strong)] transition hover:bg-[rgba(33,72,59,0.14)] hover:border-[var(--accent)]"
                          >
                            {name}
                            <span className="text-[10px] tracking-[0.12em] opacity-70">
                              OPEN PROFILE →
                            </span>
                          </Link>
                        ))}
                      </div>
                    )}

                    {/* Query trace collapsible */}
                    <QueryTrace response={response} />
                  </div>

                  {/* Follow-up suggestions */}
                  {response.suggestions.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      <span className="bip-kicker self-center">Try next</span>
                      {response.suggestions.map((suggestion) => (
                        <button
                          key={suggestion}
                          type="button"
                          onClick={() => submitQuestion(suggestion)}
                          className="rounded-lg border border-[var(--border)] px-3 py-1.5 text-xs font-semibold text-[var(--foreground)] transition hover:border-[var(--accent)] hover:text-[var(--accent-strong)]"
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ---------------------------------------------------------------- */}
        {/* COMPOSER                                                          */}
        {/* ---------------------------------------------------------------- */}
        <div className="sticky bottom-4 z-10 mt-auto">
          <div className="rounded-xl border border-[var(--border)] bg-[rgba(247,239,228,0.96)] shadow-[var(--shadow-strong)] backdrop-blur-xl px-4 pt-3 pb-3">
            {/* Suggested pills */}
            <div className="mb-2.5 flex flex-wrap gap-1.5">
              {SUGGESTED_PILLS.map((pill) => (
                <button
                  key={pill}
                  type="button"
                  onClick={() => setDraft(pill)}
                  className="bip-pill text-xs py-1 px-3 transition hover:bg-[rgba(180,137,61,0.2)]"
                >
                  {pill}
                </button>
              ))}
            </div>

            {/* Text input row */}
            <form onSubmit={handleSubmit} className="flex gap-2">
              <input
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                className="bip-input flex-1 rounded-lg px-4 py-2.5 text-sm"
                placeholder="Try: players with at least 25 ppg and 60 ts%"
                aria-label="Ask CourtVue"
              />
              <button
                type="submit"
                className="rounded-lg bg-[var(--accent)] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isLoading || !draft.trim()}
              >
                {isLoading ? "Asking…" : "Ask"}
              </button>
            </form>

            {/* Composer metadata row */}
            <div className="mt-2 flex flex-wrap items-center gap-3">
              {/* Model version badge */}
              <span className="inline-flex items-center gap-1 rounded-md border border-[var(--border)] bg-[rgba(255,251,246,0.7)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--muted)]">
                CourtVue v2
              </span>

              {/* Season selector */}
              <select
                value={season}
                onChange={(e) => setSeason(e.target.value)}
                className="rounded-md border border-[var(--border)] bg-[rgba(255,251,246,0.7)] px-2 py-0.5 text-[10px] font-semibold text-[var(--muted)] focus:outline-none focus:border-[var(--accent)]"
                aria-label="Season"
              >
                <option value="2024-25">2024–25</option>
                <option value="2023-24">2023–24</option>
                <option value="2022-23">2022–23</option>
              </select>

              {/* Per-game toggle */}
              <button
                type="button"
                onClick={() => setPerGame((prev) => !prev)}
                className={[
                  "rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] transition",
                  perGame
                    ? "border-[var(--accent)] bg-[rgba(33,72,59,0.10)] text-[var(--accent-strong)]"
                    : "border-[var(--border)] bg-[rgba(255,251,246,0.7)] text-[var(--muted)]",
                ].join(" ")}
              >
                Per Game
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
